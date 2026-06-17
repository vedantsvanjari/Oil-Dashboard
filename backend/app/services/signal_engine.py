import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import joblib
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
DATABASE_URL = os.getenv("DATABASE_URL")

ARTIFACTS_PATH = os.path.join(os.path.dirname(__file__), '../models/ml/signal_artifacts.joblib')

def get_signal_strength_label(percentile):
    if percentile <= 20:
        return "Very Bearish"
    elif percentile <= 40:
        return "Bearish"
    elif percentile <= 60:
        return "Neutral"
    elif percentile <= 80:
        return "Bullish"
    else:
        return "Very Bullish"

def extract_drivers(pipeline, feature_values, feature_names):
    # pipeline[0] is scaler, pipeline[1] is model
    scaler = pipeline.named_steps['scaler']
    model = pipeline.named_steps['model']
    
    scaled_features = scaler.transform([feature_values])[0]
    coefs = model.coef_
    if len(coefs.shape) > 1:
        coefs = coefs[0]
        
    contributions = scaled_features * coefs
    
    # Create list of tuples (feature, contribution)
    contrib_list = [(feature_names[i], float(contributions[i])) for i in range(len(feature_names))]
    
    # Sort by absolute contribution
    contrib_list.sort(key=lambda x: abs(x[1]), reverse=True)
    
    # Return top 3
    drivers = []
    for feat, val in contrib_list[:3]:
        impact = "positive" if val > 0 else "negative"
        drivers.append(f"{feat} ({impact} driver: {val:.4f})")
        
    return drivers

def generate_current_signal():
    if not os.path.exists(ARTIFACTS_PATH):
        raise FileNotFoundError("Signal artifacts not found. Please run train_signals.py first.")
        
    artifacts = joblib.load(ARTIFACTS_PATH)
    
    engine = create_engine(DATABASE_URL)
    query = "SELECT * FROM regime_targets ORDER BY timestamp DESC LIMIT 1"
    df_latest = pd.read_sql_query(query, engine)
    
    if len(df_latest) == 0:
        raise ValueError("No data found in regime_targets.")
        
    row = df_latest.iloc[0]
    
    # 1. Determine Regime
    m1_m12 = float(row['m1_m12'])
    thresh = artifacts['thresholds']
    
    regime = "Neutral"
    if m1_m12 > thresh['neutral_band']:
        if m1_m12 >= thresh['back_thresh']:
            regime = "Deep Backwardation"
        else:
            regime = "Backwardation"
    elif m1_m12 < -thresh['neutral_band']:
        if m1_m12 <= thresh['cont_thresh']:
            regime = "Deep Contango"
        else:
            regime = "Contango"
            
    # Calculate regime percentile
    dist_m1_m12 = thresh['m1_m12_distribution']
    regime_percentile = np.searchsorted(dist_m1_m12, m1_m12) / len(dist_m1_m12) * 100.0
    
    # 2. Select Model
    family_name = "Backwardation Family"
    if "Contango" in regime:
        family_name = "Contango Family"
        
    models_dict = artifacts['models'][family_name]
    
    features = artifacts['features']
    feature_values = [float(row[f]) for f in features]
    
    # 3. Generate Predictions
    model_m1m2 = models_dict['m1_m2_model']
    pred_m1m2 = float(model_m1m2.predict([feature_values])[0])
    
    model_fly = models_dict['fly123_model']
    pred_fly = float(model_fly.predict([feature_values])[0])
    
    # 4. Signal Strength (Mispricing Percentile)
    dist_m1m2 = models_dict['m1_m2_preds_dist']
    perc_m1m2 = np.searchsorted(dist_m1m2, pred_m1m2) / len(dist_m1m2) * 100.0
    
    dist_fly = models_dict['fly123_preds_dist']
    perc_fly = np.searchsorted(dist_fly, pred_fly) / len(dist_fly) * 100.0
    
    # 5. Model Confidence
    confidence = "Medium"
    if "Contango" in regime:
        confidence = "High" # Extremely high Train R2
    elif "Deep" in regime:
        confidence = "Medium"
    else:
        confidence = "Low" # Standard backwardation is mostly random walk
        
    # 6. Extract Drivers
    drivers_m1m2 = extract_drivers(model_m1m2, feature_values, features)
    drivers_fly = extract_drivers(model_fly, feature_values, features)
    
    # Construct Response
    response = {
        "timestamp": str(row['timestamp']),
        "regime": regime,
        "regime_strength_absolute": abs(m1_m12),
        "regime_percentile": round(regime_percentile, 2),
        "model_used": family_name,
        "confidence": confidence,
        "opportunities": [
            {
                "target": "M1-M2 Spread",
                "predicted_5d_change": round(pred_m1m2, 4),
                "mispricing_score_percentile": round(perc_m1m2, 2),
                "signal_strength": get_signal_strength_label(perc_m1m2),
                "drivers": drivers_m1m2
            },
            {
                "target": "Fly123",
                "predicted_5d_change": round(pred_fly, 4),
                "mispricing_score_percentile": round(perc_fly, 2),
                "signal_strength": get_signal_strength_label(perc_fly),
                "drivers": drivers_fly
            }
        ]
    }
    
    return response
