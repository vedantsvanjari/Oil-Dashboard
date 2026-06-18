import pandas as pd
import numpy as np
import json
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv('backend/.env')

def main():
    print("Loading TRAIN dataset from database...")
    engine = create_engine(os.getenv("DATABASE_URL"))
    df = pd.read_sql("SELECT * FROM regime_targets WHERE dataset_split = 'TRAIN'", engine)
    
    # Sort chronologically to ensure stability splits are correct
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"Total TRAIN rows: {len(df)}")
    
    # Recalculate thresholds
    back_thresh = df['m1_m12'].quantile(0.80)
    cont_thresh = df['m1_m12'].quantile(0.20)
    
    memory_map = {
        "regime_thresholds": {
            "back_thresh": back_thresh,
            "cont_thresh": cont_thresh,
            "neutral_band": 0.10
        },
        "regimes": {}
    }
    
    instruments = {
        'M1-M2': 'm1_m2',
        'M1-M6': 'm1_m6',
        'M1-M12': 'm1_m12',
        'Fly123': 'fly123',
        'Fly234': 'fly_234',
        'Fly345': 'fly_345'
    }
    
    horizons = {'1d': 96, '3d': 288, '5d': 480}
    regimes = ['Deep Contango', 'Contango', 'Neutral', 'Backwardation', 'Deep Backwardation']
    
    # Calculate regime persistence
    df['next_regime'] = df['regime'].shift(-1)
    
    # We will track edge scores to normalize them later
    all_edges = []
    
    for r in regimes:
        print(f"Processing {r}...")
        sub_df = df[df['regime'] == r].copy()
        n = len(sub_df)
        
        if n == 0:
            continue
            
        persistence = (sub_df['next_regime'] == r).mean() * 100
        sample_size_score = min(100, (n / 5000.0) * 100)
        
        regime_data = {
            "metrics": {
                "sample_size": n,
                "persistence_prob": persistence,
                "sample_size_score": sample_size_score
            },
            "instruments": {}
        }
        
        regime_edges = []
        
        for inst_name, col_name in instruments.items():
            inst_data = {
                "raw_distribution": {
                    "p10": sub_df[col_name].quantile(0.10),
                    "p30": sub_df[col_name].quantile(0.30),
                    "p50": sub_df[col_name].quantile(0.50),
                    "p70": sub_df[col_name].quantile(0.70),
                    "p90": sub_df[col_name].quantile(0.90)
                },
                "horizons": {}
            }
            
            for h_name, h_shift in horizons.items():
                target_col = f'fwd_{h_name}_{col_name}_chg'
                target_series = sub_df[target_col].dropna()
                
                if len(target_series) < 10:
                    continue
                    
                mean_move = target_series.mean()
                median_move = target_series.median()
                std_move = target_series.std()
                
                # Directional Win Rate
                if mean_move > 0:
                    win_rate = (target_series > 0).mean()
                else:
                    win_rate = (target_series < 0).mean()
                    
                dir_win_rate_score = max(0, min(100, (win_rate - 0.5) * 200))
                
                # Edge
                if std_move > 0:
                    raw_edge = abs(mean_move) / std_move
                else:
                    raw_edge = 0
                all_edges.append(raw_edge)
                regime_edges.append(raw_edge)
                
                # Stability Score (Chronological Split)
                # Split indices in half
                half_idx = len(target_series) // 2
                early_series = target_series.iloc[:half_idx]
                late_series = target_series.iloc[half_idx:]
                
                early_mean = early_series.mean()
                late_mean = late_series.mean()
                
                if std_move > 0:
                    mean_drift_penalty = abs(late_mean - early_mean) / std_move
                else:
                    mean_drift_penalty = 1.0
                    
                stability_score = max(0, 100 - (mean_drift_penalty * 50))
                
                inst_data["horizons"][h_name] = {
                    "mean": mean_move,
                    "median": median_move,
                    "std": std_move,
                    "win_rate": win_rate * 100,
                    "dir_win_rate_score": dir_win_rate_score,
                    "raw_edge": raw_edge,
                    "stability_score": stability_score
                }
                
            regime_data["instruments"][inst_name] = inst_data
            
        regime_data["metrics"]["avg_raw_edge"] = np.mean(regime_edges) if regime_edges else 0
        memory_map["regimes"][r] = regime_data
        
    # Normalize Edge Scores (0-100) across all regimes/instruments
    max_edge = max(all_edges) if all_edges else 1.0
    
    for r, r_data in memory_map["regimes"].items():
        avg_raw_edge = r_data["metrics"]["avg_raw_edge"]
        normalized_regime_edge = (avg_raw_edge / max_edge) * 100
        
        # Calculate Regime Quality Score
        persistence = r_data["metrics"]["persistence_prob"]
        sample_score = r_data["metrics"]["sample_size_score"]
        
        regime_quality = (persistence + sample_score + normalized_regime_edge) / 3.0
        r_data["metrics"]["regime_quality_score"] = regime_quality
        
        # Normalize individual instrument edges
        for inst_name, inst_data in r_data["instruments"].items():
            for h_name, h_data in inst_data["horizons"].items():
                h_data["economic_edge_score"] = (h_data["raw_edge"] / max_edge) * 100

    out_path = os.path.join("backend", "app", "models", "ml", "statistical_memory_map.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    with open(out_path, 'w') as f:
        json.dump(memory_map, f, indent=4)
        
    print(f"Successfully generated {out_path}")

if __name__ == "__main__":
    main()
