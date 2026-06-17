import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from dotenv import load_dotenv
import joblib

from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Lasso, Ridge
from sklearn.pipeline import Pipeline

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    print("Loading TRAIN dataset...")
    engine = create_engine(DATABASE_URL)
    df = pd.read_sql_query("SELECT * FROM regime_targets WHERE dataset_split = 'TRAIN'", engine)
    
    features = [
        'm1_m2', 'm1_m3', 'm1_m6', 'm1_m12', 'm1_m14',
        'fly123', 'fly_234', 'fly_345',
        'front_slope', 'mid_slope', 'long_slope', 'curvature', 'regime_strength'
    ]
    target_m1m2 = 'fwd_5d_m1_m2_chg'
    target_fly = 'fwd_5d_fly123_chg'
    
    # 1. Compute Regime Thresholds
    NEUTRAL_BAND = 0.10
    m1_m12_s = df['m1_m12'].dropna()
    back_mask = m1_m12_s > NEUTRAL_BAND
    cont_mask = m1_m12_s < -NEUTRAL_BAND
    
    back_thresh = m1_m12_s[back_mask].quantile(0.80)
    cont_thresh = m1_m12_s[cont_mask].quantile(0.20)
    
    print(f"Persisting Thresholds: Contango < {cont_thresh:.3f}, Backwardation > {back_thresh:.3f}")
    
    # 2. Extract families
    df_contango = df[df['regime'].isin(['Contango', 'Deep Contango'])].dropna(subset=features + [target_m1m2, target_fly])
    df_backwardation = df[df['regime'].isin(['Backwardation', 'Deep Backwardation'])].dropna(subset=features + [target_m1m2, target_fly])
    
    # 3. Train Pipelines
    print("Training Contango Models...")
    pipe_cont_m1m2 = Pipeline([('scaler', StandardScaler()), ('model', Ridge(alpha=10.0))])
    pipe_cont_m1m2.fit(df_contango[features], df_contango[target_m1m2])
    preds_cont_m1m2 = np.sort(pipe_cont_m1m2.predict(df_contango[features]))
    
    pipe_cont_fly = Pipeline([('scaler', StandardScaler()), ('model', Ridge(alpha=10.0))])
    pipe_cont_fly.fit(df_contango[features], df_contango[target_fly])
    preds_cont_fly = np.sort(pipe_cont_fly.predict(df_contango[features]))
    
    print("Training Backwardation Models...")
    pipe_back_m1m2 = Pipeline([('scaler', StandardScaler()), ('model', Lasso(alpha=0.001, max_iter=2000))])
    pipe_back_m1m2.fit(df_backwardation[features], df_backwardation[target_m1m2])
    preds_back_m1m2 = np.sort(pipe_back_m1m2.predict(df_backwardation[features]))
    
    pipe_back_fly = Pipeline([('scaler', StandardScaler()), ('model', Lasso(alpha=0.001, max_iter=2000))])
    pipe_back_fly.fit(df_backwardation[features], df_backwardation[target_fly])
    preds_back_fly = np.sort(pipe_back_fly.predict(df_backwardation[features]))
    
    # 4. Save Artifacts
    artifacts = {
        'thresholds': {
            'neutral_band': NEUTRAL_BAND,
            'back_thresh': back_thresh,
            'cont_thresh': cont_thresh,
            'm1_m12_distribution': np.sort(m1_m12_s.values) # For regime_percentile
        },
        'features': features,
        'models': {
            'Contango Family': {
                'm1_m2_model': pipe_cont_m1m2,
                'fly123_model': pipe_cont_fly,
                'm1_m2_preds_dist': preds_cont_m1m2,
                'fly123_preds_dist': preds_cont_fly
            },
            'Backwardation Family': {
                'm1_m2_model': pipe_back_m1m2,
                'fly123_model': pipe_back_fly,
                'm1_m2_preds_dist': preds_back_m1m2,
                'fly123_preds_dist': preds_back_fly
            }
        }
    }
    
    out_dir = os.path.join(os.path.dirname(__file__), '../models/ml')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'signal_artifacts.joblib')
    
    joblib.dump(artifacts, out_path)
    print(f"Artifacts saved to {out_path}")

if __name__ == "__main__":
    main()
