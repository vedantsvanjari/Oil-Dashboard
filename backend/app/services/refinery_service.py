import os
import requests
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.refineries import RefineryData

EIA_API_KEY = os.getenv("EIA_API_KEY", "")

SERIES_MAP = {
    "refinery_utilization": {"route": "petroleum/pnp/wiup/data", "series": "WPULEUS3"},
    "gross_inputs": {"route": "petroleum/pnp/wiup/data", "series": "WGIRIUS2"},
    "gasoline_production": {"route": "petroleum/pnp/wprodrb/data", "series": "WGFRPUS2"},
    "distillate_production": {"route": "petroleum/pnp/wprodrb/data", "series": "WDIRPUS2"}
}

def fetch_latest_refinery_data(db: Session = None):
    result = {
        "refinery_utilization": 0.0,
        "gross_inputs": 0.0,
        "gasoline_production": 0.0,
        "distillate_production": 0.0,
        "date": None
    }
    
    if not EIA_API_KEY:
        print("Warning: EIA_API_KEY is not set. Using mocked data.")
        result.update({
            "refinery_utilization": 91.2,
            "gross_inputs": 16500.0,
            "gasoline_production": 9800.0,
            "distillate_production": 4900.0,
            "date": datetime.now(timezone.utc).isoformat()
        })
    else:
        try:
            latest_date_str = None
            for key, config in SERIES_MAP.items():
                route = config["route"]
                series = config["series"]
                url = f"https://api.eia.gov/v2/{route}/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&facets[series][]={series}&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=1"
                
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                
                if "response" in data and "data" in data["response"] and len(data["response"]["data"]) > 0:
                    latest = data["response"]["data"][0]
                    result[key] = float(latest.get("value", 0.0))
                    
                    if latest_date_str is None:
                        period = latest.get("period", "")
                        if period:
                            try:
                                dt = datetime.strptime(period, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                latest_date_str = dt.isoformat()
                            except ValueError:
                                pass
                                
            if latest_date_str:
                result["date"] = latest_date_str
            else:
                result["date"] = datetime.now(timezone.utc).isoformat()
                
        except Exception as e:
            print(f"Error fetching EIA refinery data: {e}")
            result["date"] = datetime.now(timezone.utc).isoformat()

    if db:
        try:
            dt = datetime.fromisoformat(result["date"]) if result.get("date") else datetime.now(timezone.utc)
            existing = db.query(RefineryData).filter(RefineryData.date == dt).first()
            if existing:
                existing.refinery_utilization = result["refinery_utilization"]
                existing.gross_inputs = result["gross_inputs"]
                existing.gasoline_production = result["gasoline_production"]
                existing.distillate_production = result["distillate_production"]
            else:
                new_ref = RefineryData(
                    date=dt,
                    refinery_utilization=result["refinery_utilization"],
                    gross_inputs=result["gross_inputs"],
                    gasoline_production=result["gasoline_production"],
                    distillate_production=result["distillate_production"]
                )
                db.add(new_ref)
            db.commit()
        except Exception as e:
            print(f"Error saving refinery data to DB: {e}")
            db.rollback()

    return result

def fetch_historical_refinery_data():
    if not EIA_API_KEY:
        print("Warning: EIA_API_KEY is not set. Using mocked historical data.")
        return [
            {"date": "2024-10-18", "refinery_utilization": 91.2, "gross_inputs": 16500.0, "gasoline_production": 9800.0, "distillate_production": 4900.0},
            {"date": "2024-10-11", "refinery_utilization": 90.5, "gross_inputs": 16300.0, "gasoline_production": 9700.0, "distillate_production": 4850.0},
            {"date": "2024-10-04", "refinery_utilization": 89.8, "gross_inputs": 16100.0, "gasoline_production": 9500.0, "distillate_production": 4800.0},
            {"date": "2024-09-27", "refinery_utilization": 88.5, "gross_inputs": 15900.0, "gasoline_production": 9400.0, "distillate_production": 4750.0},
            {"date": "2024-09-20", "refinery_utilization": 87.2, "gross_inputs": 15800.0, "gasoline_production": 9300.0, "distillate_production": 4700.0},
        ]

    history = {}
    try:
        for key, config in SERIES_MAP.items():
            route = config["route"]
            series = config["series"]
            url = f"https://api.eia.gov/v2/{route}/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&facets[series][]={series}&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=52"
            
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if "response" in data and "data" in data["response"]:
                for row in data["response"]["data"]:
                    period = row.get("period", "")
                    if period:
                        if period not in history:
                            history[period] = {
                                "date": period, 
                                "refinery_utilization": 0.0, 
                                "gross_inputs": 0.0, 
                                "gasoline_production": 0.0, 
                                "distillate_production": 0.0
                            }
                        history[period][key] = float(row.get("value", 0.0))
                        
        result = sorted(list(history.values()), key=lambda x: x["date"], reverse=True)
        return result
    except Exception as e:
        print(f"Error fetching historical EIA refinery data: {e}")
        return []
