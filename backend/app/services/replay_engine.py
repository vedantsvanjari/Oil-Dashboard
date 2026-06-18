import pandas as pd
import numpy as np
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from statistical_signal_engine import StatisticalSignalEngine

load_dotenv('backend/.env')

def main():
    print("Loading TEST dataset for Replay...")
    engine = create_engine(os.getenv("DATABASE_URL"))
    df = pd.read_sql("SELECT * FROM regime_targets WHERE dataset_split = 'TEST' ORDER BY timestamp ASC", engine)
    
    print(f"Total TEST rows for replay: {len(df)}")
    
    signal_engine = StatisticalSignalEngine()
    
    results = []
    
    # Fast row iteration
    for idx, row in df.iterrows():
        signals = signal_engine.generate_signals(row)
        
        # Only evaluate signals that have a Strong recommendation to simulate an actual trading strategy
        for sig in signals:
            rec = sig["Final_Recommendation"]
            if rec not in ["Strong Buy", "Strong Sell", "Buy", "Sell"]:
                continue
                
            # Find the actual move
            inst_col = signal_engine.col_map[sig["Instrument"]]
            horizon = sig["Horizon"]
            
            # Map "5 Day" to "5d"
            h_prefix = "5d" if "5" in horizon else ("3d" if "3" in horizon else "1d")
            actual_target_col = f"fwd_{h_prefix}_{inst_col}_chg"
            
            actual_move = row.get(actual_target_col, np.nan)
            if pd.isna(actual_move):
                continue
                
            # Determine expected direction based on Recommendation
            expected_dir = 1 if "Buy" in rec else -1
            
            # Calculate hit
            is_hit = 1 if (expected_dir > 0 and actual_move > 0) or (expected_dir < 0 and actual_move < 0) else 0
            
            # Realized move (if we went short, a negative actual move is positive for us)
            realized_move = actual_move * expected_dir
            
            results.append({
                "Timestamp": row["timestamp"],
                "Instrument": sig["Instrument"],
                "Horizon": horizon,
                "Regime": sig["Current_Regime"],
                "Confidence": sig["Confidence_Score"],
                "Recommendation": rec,
                "Expected_Dir": expected_dir,
                "Actual_Move": actual_move,
                "Is_Hit": is_hit,
                "Realized_Move": realized_move
            })
            
    if not results:
        print("No signals generated.")
        return
        
    res_df = pd.DataFrame(results)
    
    # Calculate Statistics
    total_signals = len(res_df)
    overall_hit_rate = res_df['Is_Hit'].mean() * 100
    overall_avg_move = res_df['Realized_Move'].mean()
    
    regime_stats = res_df.groupby('Regime').agg(
        Hit_Rate=('Is_Hit', lambda x: x.mean() * 100),
        Avg_Move=('Realized_Move', 'mean'),
        Count=('Is_Hit', 'count')
    ).round(4)
    
    inst_stats = res_df.groupby('Instrument').agg(
        Hit_Rate=('Is_Hit', lambda x: x.mean() * 100),
        Avg_Move=('Realized_Move', 'mean'),
        Count=('Is_Hit', 'count')
    ).round(4)
    
    horizon_stats = res_df.groupby('Horizon').agg(
        Hit_Rate=('Is_Hit', lambda x: x.mean() * 100),
        Avg_Move=('Realized_Move', 'mean'),
        Count=('Is_Hit', 'count')
    ).round(4)
    
    # Confidence Calibration
    res_df['Conf_Bucket'] = pd.cut(res_df['Confidence'], bins=[0, 60, 70, 80, 90, 100])
    calib_stats = res_df.groupby('Conf_Bucket', observed=False).agg(
        Hit_Rate=('Is_Hit', lambda x: x.mean() * 100),
        Count=('Is_Hit', 'count')
    )
    
    # Drawdown Calculation (Assuming a simple cumulative sum of realized moves across all signals over time)
    # Group by timestamp to aggregate overlapping signals
    time_series = res_df.groupby('Timestamp')['Realized_Move'].sum().reset_index()
    time_series['Cumulative'] = time_series['Realized_Move'].cumsum()
    time_series['Peak'] = time_series['Cumulative'].cummax()
    time_series['Drawdown'] = time_series['Cumulative'] - time_series['Peak']
    max_drawdown = time_series['Drawdown'].min()
    
    # Helper to print markdown tables without tabulate
    def df_to_md(df, index_name=""):
        headers = [index_name] + list(df.columns)
        md_str = "| " + " | ".join(headers) + " |\n"
        md_str += "|---" * len(headers) + "|\n"
        for idx, row in df.iterrows():
            row_str = f"| {idx} | "
            row_str += " | ".join([f"{val:.4f}" if isinstance(val, float) else str(val) for val in row])
            row_str += " |\n"
        return md_str
        
    # Generate Markdown Report
    md = "# Statistical Signal Framework - Historical Replay Report\n\n"
    md += f"**Dataset**: Out-of-Sample `TEST` Split\n"
    md += f"**Total Signals Fired**: {total_signals:,}\n"
    md += f"**Overall Hit Rate**: {overall_hit_rate:.2f}%\n"
    md += f"**Overall Average Realized Move**: {overall_avg_move:.5f}\n"
    md += f"**Maximum Drawdown (Cumulative Move)**: {max_drawdown:.5f}\n\n"
    
    md += "## Performance by Regime\n\n"
    md += df_to_md(regime_stats, "Regime") + "\n\n"
    
    md += "## Performance by Instrument\n\n"
    md += df_to_md(inst_stats, "Instrument") + "\n\n"
    
    md += "## Performance by Horizon\n\n"
    md += df_to_md(horizon_stats, "Horizon") + "\n\n"
    
    md += "## Confidence Calibration\n\n"
    md += "Validates whether a higher Confidence Score actually translates to a higher out-of-sample Hit Rate.\n\n"
    md += df_to_md(calib_stats, "Conf_Bucket") + "\n\n"
    
    out_path = r"C:\Users\vanjari.sunil\.gemini\antigravity-ide\brain\68083f4d-3d7c-4f29-a9e4-6575f1b6edd6\replay_performance_report.md"
    with open(out_path, 'w') as f:
        f.write(md)
        
    print(f"Replay complete! Report saved to {out_path}")
    
    # Dump JSON Cache for API
    import json
    
    # 1. Performance JSON
    perf_data = {
        "overall": {
            "total_signals": total_signals,
            "hit_rate": overall_hit_rate,
            "avg_move": overall_avg_move,
            "max_drawdown": max_drawdown
        },
        "by_regime": regime_stats.reset_index().to_dict(orient="records"),
        "by_instrument": inst_stats.reset_index().to_dict(orient="records"),
        "by_horizon": horizon_stats.reset_index().to_dict(orient="records"),
        "calibration": calib_stats.reset_index().assign(Conf_Bucket=lambda df: df['Conf_Bucket'].astype(str)).to_dict(orient="records")
    }
    
    perf_path = os.path.join("backend", "app", "models", "ml", "replay_performance.json")
    os.makedirs(os.path.dirname(perf_path), exist_ok=True)
    with open(perf_path, 'w') as f:
        json.dump(perf_data, f, indent=4)
        
    # 2. Trades JSON
    # Convert Timestamp to string for JSON serialization
    res_df['Timestamp'] = res_df['Timestamp'].astype(str)
    res_df['Conf_Bucket'] = res_df['Conf_Bucket'].astype(str)
    
    # We want entry, exit (which is expected move), PnL, etc.
    trades_json = res_df.to_dict(orient="records")
    trades_path = os.path.join("backend", "app", "models", "ml", "replay_trades.json")
    with open(trades_path, 'w') as f:
        json.dump(trades_json, f, indent=4)
        
    print("API cache JSON files generated successfully.")

if __name__ == "__main__":
    main()
