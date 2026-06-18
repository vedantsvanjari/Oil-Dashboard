import json
import os
import numpy as np

class StatisticalSignalEngine:
    def __init__(self, memory_map_path=None):
        if memory_map_path is None:
            memory_map_path = os.path.join("backend", "app", "models", "ml", "statistical_memory_map.json")
            
        with open(memory_map_path, 'r') as f:
            self.memory = json.load(f)
            
        self.liquidity_scores = {
            'M1-M2': 100.0,
            'M1-M6': 90.0,
            'M1-M12': 80.0,
            'Fly123': 75.0,
            'Fly234': 60.0,
            'Fly345': 50.0
        }
        
        # We also need the mapping back to row column names
        self.col_map = {
            'M1-M2': 'm1_m2',
            'M1-M6': 'm1_m6',
            'M1-M12': 'm1_m12',
            'Fly123': 'fly123',
            'Fly234': 'fly_234',
            'Fly345': 'fly_345'
        }

    def detect_regime(self, m1_m12):
        t = self.memory["regime_thresholds"]
        if m1_m12 >= t["back_thresh"]:
            return "Deep Backwardation"
        elif m1_m12 <= t["cont_thresh"]:
            return "Deep Contango"
        elif m1_m12 > t["neutral_band"]:
            return "Backwardation"
        elif m1_m12 < -t["neutral_band"]:
            return "Contango"
        else:
            return "Neutral"

    def get_relative_value_signal(self, current_val, dist):
        if current_val <= dist["p10"]:
            return "Extremely Cheap"
        elif current_val <= dist["p30"]:
            return "Cheap"
        elif current_val >= dist["p90"]:
            return "Extremely Rich"
        elif current_val >= dist["p70"]:
            return "Rich"
        else:
            return "Fair Value"
            
    def get_drift_signal(self, mean_move, win_rate, edge_score):
        # Determine strength of drift
        if mean_move > 0:
            if edge_score > 60 and win_rate > 60:
                return "Strong Bullish"
            elif edge_score > 30 and win_rate > 55:
                return "Bullish"
            else:
                return "Neutral Bullish"
        elif mean_move < 0:
            if edge_score > 60 and win_rate > 60:
                return "Strong Bearish"
            elif edge_score > 30 and win_rate > 55:
                return "Bearish"
            else:
                return "Neutral Bearish"
        else:
            return "Neutral"

    def get_decision_matrix_recommendation(self, drift, rv):
        # A simple decision matrix combining drift expectation and current relative value
        # Bullish drift + Cheap RV = Strong Buy
        # Bullish drift + Rich RV = Neutral/Wait
        # Bearish drift + Rich RV = Strong Sell
        # Bearish drift + Cheap RV = Neutral/Wait
        
        drift_val = 0
        if "Strong Bullish" in drift: drift_val = 2
        elif "Bullish" in drift: drift_val = 1
        elif "Strong Bearish" in drift: drift_val = -2
        elif "Bearish" in drift: drift_val = -1
        
        rv_val = 0
        if rv == "Extremely Cheap": rv_val = 2
        elif rv == "Cheap": rv_val = 1
        elif rv == "Extremely Rich": rv_val = -2
        elif rv == "Rich": rv_val = -1
        
        combined = drift_val + rv_val
        
        if combined >= 3: return "Strong Buy"
        if combined == 2: return "Buy"
        if combined <= -3: return "Strong Sell"
        if combined == -2: return "Sell"
        return "Neutral"

    def generate_signals(self, row):
        m1_m12 = row.get('m1_m12', 0.0)
        current_regime = self.detect_regime(m1_m12)
        
        if current_regime not in self.memory["regimes"]:
            return [] # Unseen regime or no data
            
        r_data = self.memory["regimes"][current_regime]
        
        signals = []
        
        for inst_name, col_name in self.col_map.items():
            if inst_name not in r_data["instruments"]:
                continue
                
            current_val = row.get(col_name, 0.0)
            inst_data = r_data["instruments"][inst_name]
            rv_signal = self.get_relative_value_signal(current_val, inst_data["raw_distribution"])
            
            for h_name, h_data in inst_data["horizons"].items():
                win_rate_score = h_data["dir_win_rate_score"]
                edge_score = h_data.get("economic_edge_score", 0.0)
                stability_score = h_data["stability_score"]
                sample_score = r_data["metrics"]["sample_size_score"]
                liquidity_score = self.liquidity_scores.get(inst_name, 0.0)
                
                # Composite Confidence Score
                conf = (
                    (0.25 * win_rate_score) +
                    (0.25 * edge_score) +
                    (0.20 * stability_score) +
                    (0.15 * sample_score) +
                    (0.15 * liquidity_score)
                )
                
                drift_signal = self.get_drift_signal(h_data["mean"], h_data["win_rate"], edge_score)
                recommendation = self.get_decision_matrix_recommendation(drift_signal, rv_signal)
                
                sig = {
                    "Instrument": inst_name,
                    "Horizon": h_name,
                    "Current_Regime": current_regime,
                    "Structural_Drift_Signal": drift_signal,
                    "Relative_Value_Signal": rv_signal,
                    "Historical_Mean_Move": h_data["mean"],
                    "Historical_Median_Move": h_data["median"],
                    "Historical_Win_Rate": h_data["win_rate"],
                    "Historical_Volatility": h_data["std"],
                    "Regime_Quality_Score": r_data["metrics"].get("regime_quality_score", 0.0),
                    "Economic_Edge_Score": edge_score,
                    "Stability_Score": stability_score,
                    "Sample_Size": r_data["metrics"]["sample_size"],
                    "Liquidity_Score": liquidity_score,
                    "Confidence_Score": conf,
                    "Final_Recommendation": recommendation
                }
                signals.append(sig)
                
        # Sort by Confidence Score descending
        signals.sort(key=lambda x: x["Confidence_Score"], reverse=True)
        return signals
