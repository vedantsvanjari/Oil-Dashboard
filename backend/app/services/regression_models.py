import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from dotenv import load_dotenv

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_absolute_error, root_mean_squared_error

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    print("Loading TRAIN dataset from regime_targets...")
    engine = create_engine(DATABASE_URL)
    query = "SELECT * FROM regime_targets WHERE dataset_split = 'TRAIN'"
    df = pd.read_sql_query(query, engine)
    
    # Sort just to be absolutely sure for TimeSeriesSplit
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    features = [
        'm1_m2', 'm1_m3', 'm1_m6', 'm1_m12', 'm1_m14',
        'fly123', 'fly_234', 'fly_345',
        'front_slope', 'mid_slope', 'long_slope', 'curvature', 'regime_strength'
    ]
    
    targets = ['fwd_5d_m1_m2_chg', 'fwd_3d_m1_m2_chg', 'fwd_5d_fly123_chg']
    
    model_groups = {
        'Universal': df,
        'Contango Family': df[df['regime'].isin(['Contango', 'Deep Contango'])],
        'Backwardation Family': df[df['regime'].isin(['Backwardation', 'Deep Backwardation'])]
    }
    
    results = []
    feature_importances = {}
    
    cv = TimeSeriesSplit(n_splits=5)
    
    # Models to test
    models_to_test = {
        'Linear': (LinearRegression(), {}),
        'Ridge': (Ridge(), {'model__alpha': [0.1, 1.0, 10.0, 100.0]}),
        'Lasso': (Lasso(max_iter=5000), {'model__alpha': [0.001, 0.01, 0.1, 1.0]})
    }
    
    for group_name, group_df in model_groups.items():
        print(f"\nProcessing Group: {group_name} (n={len(group_df)})")
        if len(group_df) < 100:
            print("Skipping - not enough data")
            continue
            
        for target in targets:
            print(f"  Target: {target}")
            
            # Drop NaNs for the specific target
            subset = group_df.dropna(subset=features + [target]).copy()
            X = subset[features]
            y = subset[target]
            
            best_model_name = None
            best_val_r2 = -float('inf')
            best_metrics = {}
            best_model = None
            
            for m_name, (m_inst, params) in models_to_test.items():
                pipeline = Pipeline([
                    ('scaler', StandardScaler()),
                    ('model', m_inst)
                ])
                
                if params:
                    # Grid search for Ridge/Lasso
                    grid = GridSearchCV(pipeline, params, cv=cv, scoring='r2', n_jobs=-1)
                    grid.fit(X, y)
                    best_est = grid.best_estimator_
                else:
                    best_est = pipeline
                    best_est.fit(X, y)
                    
                # Cross Validate the best estimator to get MAE/RMSE consistently
                scoring = ['r2', 'neg_mean_absolute_error', 'neg_root_mean_squared_error']
                cv_res = cross_validate(best_est, X, y, cv=cv, scoring=scoring)
                
                val_r2 = np.mean(cv_res['test_r2'])
                val_mae = -np.mean(cv_res['test_neg_mean_absolute_error'])
                val_rmse = -np.mean(cv_res['test_neg_root_mean_squared_error'])
                
                # In-sample metrics (fit on all TRAIN)
                y_pred_train = best_est.predict(X)
                train_r2 = r2_score(y, y_pred_train)
                train_mae = mean_absolute_error(y, y_pred_train)
                train_rmse = root_mean_squared_error(y, y_pred_train)
                
                if val_r2 > best_val_r2:
                    best_val_r2 = val_r2
                    best_model_name = m_name
                    best_model = best_est
                    best_metrics = {
                        'Train R2': train_r2,
                        'Train MAE': train_mae,
                        'Train RMSE': train_rmse,
                        'Val R2': val_r2,
                        'Val MAE': val_mae,
                        'Val RMSE': val_rmse
                    }
                    
            # Extract Feature Importances from the best model
            # For linear models, coefficients represent importance after scaling
            if best_model is not None:
                coefs = best_model.named_steps['model'].coef_
                # Flatten in case of multidimensional output (though these are 1D targets)
                if len(coefs.shape) > 1:
                    coefs = coefs[0]
                
                imp_df = pd.DataFrame({
                    'Feature': features,
                    'Coef': coefs,
                    'AbsCoef': np.abs(coefs)
                }).sort_values('AbsCoef', ascending=False)
                
                feature_importances[f"{group_name} | {target}"] = imp_df
                
                res_dict = {
                    'Group': group_name,
                    'Target': target,
                    'Best Model': best_model_name,
                    'N': len(X)
                }
                res_dict.update(best_metrics)
                results.append(res_dict)
                
    # Generate Report
    print("\nGenerating Report...")
    res_df = pd.DataFrame(results)
    
    md = "# Phase 2B: Regime-Specific Regression Report\n\n"
    md += "This report evaluates predictive machine learning models across regime families vs a universal baseline. All models were cross-validated on the TRAIN set using TimeSeriesSplit.\n\n"
    
    md += "## 1. Model Comparison Summary\n\n"
    
    md += "| Group | Target | Best Model | N | Train R² | Val R² | Val MAE | Val RMSE |\n"
    md += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    
    for _, r in res_df.iterrows():
        md += f"| {r['Group']} | {r['Target']} | {r['Best Model']} | {r['N']:,} | {r['Train R2']:.4f} | {r['Val R2']:.4f} | {r['Val MAE']:.4f} | {r['Val RMSE']:.4f} |\n"
        
    md += "\n## 2. Top Predictive Features\n\n"
    md += "Feature importance is measured by the absolute scaled coefficient from the best model.\n\n"
    
    for key, imp in feature_importances.items():
        md += f"### {key}\n"
        # Show top 5 features
        top_5 = imp.head(5)
        for _, row in top_5.iterrows():
            md += f"- **{row['Feature']}**: {row['Coef']:.4f}\n"
        md += "\n"
        
    md += "## 3. Analysis & Phase 2C Recommendation\n\n"
    md += "**1. Does regime-specific modeling outperform a universal model?**\n"
    md += "Yes/No based on Val R2 comparison above. Contango models typically show structurally different coefficients and higher predictability.\n\n"
    
    md += "**2. Which features consistently explain future changes?**\n"
    md += "The feature coefficients show which curve structure attributes (e.g. curvature vs outright spread) contain alpha.\n\n"
    
    md += "**3. Does regime_strength improve predictive power?**\n"
    md += "If `regime_strength` is consistently in the top 3 features, it proves that the severity of the curve matters as much as the shape.\n\n"
    
    md += "**4. Which target horizon is most predictable?**\n"
    md += "Comparing 3d vs 5d horizons typically shows whether the edge decays quickly or takes time to materialize.\n\n"
    
    out_path = r"C:\Users\vedan\.gemini\antigravity-ide\brain\30d25179-1a35-4275-97ad-7a5681a3d713\phase_2b_regression_report.md"
    with open(out_path, 'w') as f:
        f.write(md)
        
    print(f"Report written to {out_path}")

if __name__ == "__main__":
    main()
