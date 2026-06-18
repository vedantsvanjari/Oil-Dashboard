import os
import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Resolve project root: backend/app/services/ -> ../../.. -> project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    parser = argparse.ArgumentParser(description="Clean, resample and engineer targets from raw Brent CSV.")
    parser.add_argument(
        "--csv",
        type=Path,
        default=PROJECT_ROOT / "LCO_3_year_test.csv",
        help="Path to the raw Brent CSV file (default: <project_root>/LCO_3_year_test.csv)"
    )
    args = parser.parse_args()

    csv_path = args.csv
    if not csv_path.exists():
        print(f"ERROR: CSV file not found at: {csv_path}")
        print("Pass the correct path with:  --csv /path/to/your/data.csv")
        sys.exit(1)

    print(f"Loading {csv_path.name}...")
    df = pd.read_csv(csv_path, skiprows=1)
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 1. Bad Tick Filtering
    m1 = df['c1||weighted_mid']
    m12 = df['c12||weighted_mid']
    bad_ticks_mask = (m1 < 10) | (m12 < 10) | (m1 > 250) | (m12 > 250)
    df = df[~bad_ticks_mask].copy()
    
    # Expiry Filtering A/B Decision: We keep Dataset A (No expiry filter) based on immaterial diff
    
    print("Resampling to 15min...")
    df.set_index('timestamp', inplace=True)
    df_resampled = df.resample('15min').last()
    
    # Forward fill is standard for financial timeseries to maintain continuous 15m grid
    # but we only ffill up to 1 day to avoid stale data over weekends
    df_resampled = df_resampled.ffill(limit=96)
    
    # Drop rows where we don't have M1 and M12
    df_resampled = df_resampled.dropna(subset=['c1||weighted_mid', 'c12||weighted_mid'])
    
    print("Calculating spreads and features...")
    df_resampled['m1_m2'] = df_resampled['c1||weighted_mid'] - df_resampled['c2||weighted_mid']
    df_resampled['m1_m3'] = df_resampled['c1||weighted_mid'] - df_resampled['c3||weighted_mid']
    df_resampled['m1_m6'] = df_resampled['c1||weighted_mid'] - df_resampled['c6||weighted_mid']
    df_resampled['m1_m12'] = df_resampled['c1||weighted_mid'] - df_resampled['c12||weighted_mid']
    df_resampled['m1_m14'] = df_resampled['c1||weighted_mid'] - df_resampled['c14||weighted_mid']
    
    df_resampled['fly123'] = df_resampled['c1||weighted_mid'] - 2 * df_resampled['c2||weighted_mid'] + df_resampled['c3||weighted_mid']
    df_resampled['fly_234'] = df_resampled['c2||weighted_mid'] - 2 * df_resampled['c3||weighted_mid'] + df_resampled['c4||weighted_mid']
    df_resampled['fly_345'] = df_resampled['c3||weighted_mid'] - 2 * df_resampled['c4||weighted_mid'] + df_resampled['c5||weighted_mid']
    
    # Slopes
    df_resampled['front_slope'] = df_resampled['m1_m3'] / 2.0
    df_resampled['mid_slope'] = (df_resampled['c3||weighted_mid'] - df_resampled['c6||weighted_mid']) / 3.0
    df_resampled['long_slope'] = (df_resampled['c6||weighted_mid'] - df_resampled['c12||weighted_mid']) / 6.0
    df_resampled['curvature'] = df_resampled['front_slope'] - df_resampled['mid_slope']
    df_resampled['regime_strength'] = df_resampled['m1_m12'].abs()
    
    print("Computing Train/Test Split...")
    max_date = df_resampled.index.max()
    test_start_date = max_date - pd.DateOffset(months=2)
    
    df_resampled['dataset_split'] = np.where(df_resampled.index >= test_start_date, 'TEST', 'TRAIN')
    
    train_df = df_resampled[df_resampled['dataset_split'] == 'TRAIN']
    test_df = df_resampled[df_resampled['dataset_split'] == 'TEST']
    
    print(f"Train Size: {len(train_df)}")
    print(f"Test Size: {len(test_df)}")
    
    print("Recomputing Regimes strictly on TRAIN...")
    NEUTRAL_BAND = 0.10
    
    # Get Train thresholds
    train_m1_m12 = train_df['m1_m12']
    back_mask = train_m1_m12 > NEUTRAL_BAND
    cont_mask = train_m1_m12 < -NEUTRAL_BAND
    
    back_thresh = train_m1_m12[back_mask].quantile(0.80)
    cont_thresh = train_m1_m12[cont_mask].quantile(0.20)
    
    print(f"TRAIN back_thresh: {back_thresh:.3f}")
    print(f"TRAIN cont_thresh: {cont_thresh:.3f}")
    
    def classify_regime(row):
        s = row['m1_m12']
        if pd.isna(s):
            return None
        
        if s > NEUTRAL_BAND:
            if s >= back_thresh:
                return 'Deep Backwardation'
            else:
                return 'Backwardation'
        elif s < -NEUTRAL_BAND:
            if s <= cont_thresh:
                return 'Deep Contango'
            else:
                return 'Contango'
        else:
            return 'Neutral'
            
    df_resampled['regime'] = df_resampled.apply(classify_regime, axis=1)
    
    print("Engineering Targets...")
    # 1d = 96, 3d = 288, 5d = 480
    
    features_to_target = [
        'm1_m2', 'm1_m3', 'm1_m6', 'm1_m12', 'm1_m14',
        'fly123', 'fly_234', 'fly_345',
        'front_slope', 'mid_slope', 'long_slope', 'curvature', 'regime_strength'
    ]
    
    horizons = {'1d': 96, '3d': 288, '5d': 480}
    all_targets = []
    
    for feat in features_to_target:
        for h_name, h_shift in horizons.items():
            target_col = f'fwd_{h_name}_{feat}_chg'
            df_resampled[target_col] = df_resampled[feat].shift(-h_shift) - df_resampled[feat]
            all_targets.append(target_col)
    
    print("Generating Predictive Characterization Report...")
    regimes = ['Deep Contango', 'Contango', 'Neutral', 'Backwardation', 'Deep Backwardation']
    report_targets = ['fwd_1d_m1_m2_chg', 'fwd_3d_m1_m2_chg', 'fwd_5d_m1_m2_chg', 
                      'fwd_1d_fly123_chg', 'fwd_3d_fly123_chg', 'fwd_5d_fly123_chg']
               
    report_md = "# Phase 2A: Predictive Characterization Report\n\n"
    report_md += "This report analyzes the forward statistical behavior of the Brent curve across the 5 structural regimes. Statistics are generated STRICTLY on the TRAIN dataset to prevent out-of-sample data leakage.\n\n"
    
    report_df = df_resampled[df_resampled['dataset_split'] == 'TRAIN']
    
    for r in regimes:
        report_md += f"## Regime: {r}\n\n"
        sub_df = report_df[report_df['regime'] == r]
        count = len(sub_df)
        report_md += f"**Observation Count**: {count:,}\n\n"
        
        report_md += "| Target | Mean Change | Median Change | Std Dev | Win Rate (>0) | Sharpe Ratio | T-Statistic |\n"
        report_md += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
        
        for t in report_targets:
            target_series = sub_df[t].dropna()
            n = len(target_series)
            if n > 0:
                mean_chg = target_series.mean()
                med_chg = target_series.median()
                std_chg = target_series.std()
                win_rate = (target_series > 0).mean() * 100
                sharpe = mean_chg / std_chg if std_chg != 0 else 0
                t_stat = mean_chg / (std_chg / np.sqrt(n)) if std_chg != 0 else 0
                
                report_md += f"| `{t}` | {mean_chg:.4f} | {med_chg:.4f} | {std_chg:.4f} | {win_rate:.1f}% | {sharpe:.3f} | {t_stat:.2f} |\n"
            else:
                report_md += f"| `{t}` | N/A | N/A | N/A | N/A | N/A | N/A |\n"
                
        report_md += "\n"
        
    out_path = PROJECT_ROOT / "backend" / "app" / "services" / "predictive_characterization_report.md"
    with open(out_path, 'w') as f:
        f.write(report_md)

    print(f"Report saved to {out_path}")
    
    print("Writing engineered dataset to database...")
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS regime_targets;"))
        
    df_to_sql = df_resampled.reset_index()
    # Keep only necessary columns for DB
    cols_to_keep = [
        'timestamp', 'dataset_split', 'regime', 'regime_strength',
        'm1_m2', 'm1_m3', 'm1_m6', 'm1_m12', 'm1_m14',
        'fly123', 'fly_234', 'fly_345',
        'front_slope', 'mid_slope', 'long_slope', 'curvature'
    ] + all_targets
    df_to_sql = df_to_sql[cols_to_keep]
    
    df_to_sql.to_sql('regime_targets', engine, if_exists='replace', index=False, chunksize=10000)
    print("Done!")

if __name__ == "__main__":
    main()
