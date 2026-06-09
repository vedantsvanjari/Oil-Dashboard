import os
import requests
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.inventories import Inventory

EIA_API_KEY = os.getenv("EIA_API_KEY", "")

FACET_MAP = {
    "crude": "&facets[duoarea][]=NUS&facets[product][]=EPC0&facets[process][]=SAX",
    "gasoline": "&facets[duoarea][]=NUS&facets[product][]=EPM0&facets[process][]=SAE",
    "distillate": "&facets[duoarea][]=NUS&facets[product][]=EPD0&facets[process][]=SAE",
    "spr": "&facets[duoarea][]=NUS&facets[product][]=EPC0&facets[process][]=SAS"
}

def fetch_eia_inventories(db: Session = None):
    result = {
        "crude": 0.0,
        "gasoline": 0.0,
        "distillate": 0.0,
        "spr": 0.0,
        "date": None
    }
    
    if not EIA_API_KEY:
        print("Warning: EIA_API_KEY is not set. Using mocked data.")
        result = {
            "crude": 420.5,
            "gasoline": 215.3,
            "distillate": 110.2,
            "spr": 350.0,
            "date": datetime.now(timezone.utc).isoformat()
        }
    else:
        try:
            latest_date_str = None
            for key, facets in FACET_MAP.items():
                url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value{facets}&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=1"
                print(f"[DEBUG] URL: {url}")
                response = requests.get(url)
                print(f"[DEBUG] Status Code: {response.status_code}")
                try:
                    print(f"[DEBUG] Response JSON: {response.json()}")
                except Exception:
                    print(f"[DEBUG] Response Text: {response.text}")
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
            print(f"Error fetching EIA data: {e}")
            result["date"] = datetime.now(timezone.utc).isoformat()

    if db:
        try:
            dt = datetime.fromisoformat(result["date"]) if result.get("date") else datetime.now(timezone.utc)
            for key in ["crude", "gasoline", "distillate", "spr"]:
                existing = db.query(Inventory).filter(Inventory.item_name == key, Inventory.date == dt).first()
                if existing:
                    existing.quantity = result[key]
                else:
                    new_inv = Inventory(
                        item_name=key,
                        quantity=result[key],
                        date=dt
                    )
                    db.add(new_inv)
            db.commit()
        except Exception as e:
            print(f"Error saving inventory to DB: {e}")
            db.rollback()

    return result

def fetch_historical_inventories():
    if not EIA_API_KEY:
        print("Warning: EIA_API_KEY is not set. Using mocked historical data.")
        return [
            {"date": "2024-10-18", "crude": 420.5, "gasoline": 215.3, "distillate": 110.2, "spr": 350.0},
            {"date": "2024-10-11", "crude": 422.1, "gasoline": 212.1, "distillate": 112.5, "spr": 350.0},
            {"date": "2024-10-04", "crude": 418.9, "gasoline": 214.0, "distillate": 113.8, "spr": 350.0},
            {"date": "2024-09-27", "crude": 415.0, "gasoline": 211.5, "distillate": 114.5, "spr": 350.0},
            {"date": "2024-09-20", "crude": 412.0, "gasoline": 209.5, "distillate": 115.5, "spr": 350.0},
        ]

    history = {}
    try:
        for key, facets in FACET_MAP.items():
            url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value{facets}&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=52"
            print(f"[DEBUG] URL: {url}")
            response = requests.get(url)
            print(f"[DEBUG] Status Code: {response.status_code}")
            try:
                print(f"[DEBUG] Response JSON: {response.json()}")
            except Exception:
                print(f"[DEBUG] Response Text: {response.text}")
            response.raise_for_status()
            data = response.json()
            
            if "response" in data and "data" in data["response"]:
                for row in data["response"]["data"]:
                    period = row.get("period", "")
                    if period:
                        if period not in history:
                            history[period] = {"date": period, "crude": 0.0, "gasoline": 0.0, "distillate": 0.0, "spr": 0.0}
                        history[period][key] = float(row.get("value", 0.0))
                        
        result = sorted(list(history.values()), key=lambda x: x["date"], reverse=True)
        return result
    except Exception as e:
        print(f"Error fetching historical EIA data: {e}")
        return []
