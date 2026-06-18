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

# Load env
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    parser = argparse.ArgumentParser(description="Run the Brent regime classification pipeline.")
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
    # We skip the first row because it contains metadata "#meta:1min||contract_num||field"
    df = pd.read_csv(csv_path, skiprows=1)
    
    print(f"Loaded {len(df)} rows.")
    
    # Target columns
    target_cols = ['timestamp'] + [f'c{i}||weighted_mid' for i in range(1, 15)]
    df = df[target_cols].copy()
    
    # Rename columns to m1...m14
    rename_dict = {f'c{i}||weighted_mid': f'm{i}' for i in range(1, 15)}
    df = df.rename(columns=rename_dict)
    
    print("Converting timestamps and resampling to 15min...")
    # Clean timestamp and set index
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    
    # Resample to 15 minute using last observation
    df_resampled = df.resample('15min').last()
    
    # Drop where M1 is NaN (meaning no trading in that 15 min window)
    df_resampled = df_resampled.dropna(subset=['m1', 'm12'])
    print(f"Resampled to {len(df_resampled)} rows.")
    
    print("Engineering features...")
    # Calendar Spreads
    df_resampled['m1_m2'] = df_resampled['m1'] - df_resampled['m2']
    df_resampled['m1_m3'] = df_resampled['m1'] - df_resampled['m3']
    df_resampled['m1_m6'] = df_resampled['m1'] - df_resampled['m6']
    df_resampled['m1_m12'] = df_resampled['m1'] - df_resampled['m12']
    df_resampled['m1_m14'] = df_resampled['m1'] - df_resampled['m14']
    
    # Butterflies
    df_resampled['fly_123'] = df_resampled['m1'] - 2*df_resampled['m2'] + df_resampled['m3']
    df_resampled['fly_234'] = df_resampled['m2'] - 2*df_resampled['m3'] + df_resampled['m4']
    df_resampled['fly_345'] = df_resampled['m3'] - 2*df_resampled['m4'] + df_resampled['m5']
    
    # Curve Features (Proposed Definitions)
    df_resampled['front_slope'] = df_resampled['m1'] - df_resampled['m3']
    df_resampled['mid_slope'] = df_resampled['m3'] - df_resampled['m6']
    df_resampled['long_slope'] = df_resampled['m6'] - df_resampled['m12']
    df_resampled['curvature'] = df_resampled['front_slope'] - df_resampled['mid_slope']
    
    print("Applying Regime Classification...")
    NEUTRAL_BAND = 0.10
    
    # Stage 1: Direction
    conditions = [
        df_resampled['m1_m12'] > NEUTRAL_BAND,
        df_resampled['m1_m12'] < -NEUTRAL_BAND
    ]
    choices = ['Backwardation_side', 'Contango_side']
    df_resampled['regime'] = np.select(conditions, choices, default='Neutral')
    
    # Stage 2: Percentiles within subsets
    back_mask = df_resampled['regime'] == 'Backwardation_side'
    cont_mask = df_resampled['regime'] == 'Contango_side'
    
    # Top 20% of backwardation
    back_thresh = df_resampled.loc[back_mask, 'm1_m12'].quantile(0.80)
    # Bottom 20% of contango
    cont_thresh = df_resampled.loc[cont_mask, 'm1_m12'].quantile(0.20)
    
    def classify_stage_two(row):
        r = row['regime']
        s = row['m1_m12']
        if pd.isna(s):
            return None
            
        if r == 'Backwardation_side':
            if s >= back_thresh:
                return 'Deep Backwardation'
            else:
                return 'Backwardation'
        elif r == 'Contango_side':
            if s <= cont_thresh:
                return 'Deep Contango'
            else:
                return 'Contango'
        else:
            return 'Neutral'
            
    df_resampled['regime'] = df_resampled.apply(classify_stage_two, axis=1)
    
    # Percentile rank of the entire distribution as the regime score
    df_resampled['regime_score'] = df_resampled['m1_m12'].rank(pct=True)
    
    # Print historical stats
    print("\n--- HISTORICAL REGIME ANALYSIS ---")
    regime_counts = df_resampled['regime'].value_counts()
    regime_pct = df_resampled['regime'].value_counts(normalize=True) * 100
    
    print("Regime Counts:")
    print(regime_counts)
    print("\nRegime Percentages:")
    print(regime_pct)
    
    # Calculate duration (blocks of same regime)
    df_resampled['regime_block'] = (df_resampled['regime'] != df_resampled['regime'].shift(1)).cumsum()
    durations = df_resampled.groupby('regime_block')['regime'].count()
    regimes_by_block = df_resampled.groupby('regime_block')['regime'].first()
    
    block_df = pd.DataFrame({'regime': regimes_by_block, 'duration_15m_periods': durations})
    avg_duration = block_df.groupby('regime')['duration_15m_periods'].mean()
    max_duration = block_df.groupby('regime')['duration_15m_periods'].max()
    
    print("\nAverage Duration (in 15m periods):")
    print(avg_duration)
    print("\nLongest Duration (in 15m periods):")
    print(max_duration)
    
    # Transition Matrix
    print("\nTransition Matrix:")
    df_resampled['next_regime'] = df_resampled['regime'].shift(-1)
    transitions = pd.crosstab(df_resampled['regime'], df_resampled['next_regime'], normalize='index') * 100
    print(transitions)
    
    print("\nWriting to database...")
    engine = create_engine(DATABASE_URL)
    
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE regime_analysis;"))
    
    # Reset index to make timestamp a column
    df_to_sql = df_resampled.reset_index()
    # Drop temporary columns
    df_to_sql = df_to_sql.drop(columns=['regime_block', 'next_regime'])
    
    # Insert in chunks
    df_to_sql.to_sql('regime_analysis', engine, if_exists='append', index=False, chunksize=10000)
    print("Database insertion complete!")

if __name__ == "__main__":
    main()
