import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

EIA_API_KEY = os.getenv("EIA_API_KEY")

class OPECService:
    def __init__(self):
        self.api_key = EIA_API_KEY
        self.base_steo_url = "https://api.eia.gov/v2/steo/data/"
        self.base_intl_url = "https://api.eia.gov/v2/international/data/"

    def get_opec_data(self):
        """
        Fetches total OPEC production and member production from EIA.
        Returns historical series for charting and latest data for current stats.
        """
        if not self.api_key:
            logger.warning("EIA_API_KEY not found. OPEC Service cannot fetch real data.")
            return {"error": "EIA API key not configured"}

        try:
            # 1. Fetch Total OPEC Production (STEO)
            # PAPR_OPEC: Total OPEC Petroleum Supply (mb/d)
            steo_params = {
                "api_key": self.api_key,
                "frequency": "monthly",
                "data[0]": "value",
                "facets[seriesId][]": "PAPR_OPEC",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 24  # Last 2 years
            }
            steo_resp = requests.get(self.base_steo_url, params=steo_params, timeout=10)
            steo_resp.raise_for_status()
            steo_data = steo_resp.json().get("response", {}).get("data", [])
            
            # Format STEO data
            opec_total_history = []
            latest_total = 0
            for row in reversed(steo_data):  # Reverse for chronological order
                if "value" in row and row["value"] is not None:
                    try:
                        val = float(row["value"])
                        # Period is YYYY-MM
                        opec_total_history.append({
                            "period": row["period"],
                            "value": val
                        })
                        latest_total = val
                    except ValueError:
                        pass
            
            # 2. Fetch Member Production (International)
            # activityId: 1 (Production)
            # productId: 55 (Crude oil, NGPL, and other liquids)
            member_countries = {
                "SAU": {"name": "Saudi Arabia", "flag": "🇸🇦"},
                "IRQ": {"name": "Iraq", "flag": "🇮🇶"},
                "ARE": {"name": "UAE", "flag": "🇦🇪"},
                "KWT": {"name": "Kuwait", "flag": "🇰🇼"},
                "IRN": {"name": "Iran", "flag": "🇮🇷"}
            }
            
            intl_params = {
                "api_key": self.api_key,
                "frequency": "monthly",
                "data[0]": "value",
                "facets[activityId][]": "1",
                "facets[productId][]": "55",
                "sort[0][column]": "period",
                "sort[0][direction]": "desc",
                "length": 100
            }
            # Add multiple countryRegionIds
            for cid in member_countries.keys():
                if "facets[countryRegionId][]" not in intl_params:
                    intl_params["facets[countryRegionId][]"] = []
                intl_params["facets[countryRegionId][]"].append(cid)
                
            intl_resp = requests.get(self.base_intl_url, params=intl_params, timeout=10)
            intl_resp.raise_for_status()
            intl_data = intl_resp.json().get("response", {}).get("data", [])

            # Group international data by country
            country_data = {cid: [] for cid in member_countries.keys()}
            for row in intl_data:
                cid = row.get("countryRegionId")
                val = row.get("value")
                period = row.get("period")
                if cid in country_data and val is not None:
                    try:
                        # Convert TBPD to MBPD
                        val_mbpd = float(val) / 1000.0
                        country_data[cid].append({
                            "period": period,
                            "value": val_mbpd
                        })
                    except ValueError:
                        pass
            
            # Prepare members list
            members = []
            for cid, history in country_data.items():
                if not history:
                    continue
                # Sort chronological
                history = sorted(history, key=lambda x: x["period"])
                latest_actual = history[-1]["value"]
                
                members.append({
                    "id": cid,
                    "country": member_countries[cid]["name"],
                    "flag": member_countries[cid]["flag"],
                    "actual": latest_actual,
                    "history": history[-24:] # Last 2 years
                })

            # Calculate trends
            # Total OPEC trend
            trend_val = 0
            if len(opec_total_history) >= 2:
                trend_val = opec_total_history[-1]["value"] - opec_total_history[-2]["value"]

            result = {
                "totalProduction": {
                    "latest": latest_total,
                    "trend": trend_val,
                    "history": opec_total_history[-24:]
                },
                "members": members,
                "placeholders": {
                    "targets": "Data source not implemented",
                    "compliance": "Data source not implemented",
                    "nextMeeting": "Data source not implemented",
                    "statement": "Data source not implemented"
                }
            }
            
            return result

        except Exception as e:
            logger.error(f"Error fetching OPEC data from EIA: {str(e)}")
            return {"error": str(e)}

opec_service = OPECService()
