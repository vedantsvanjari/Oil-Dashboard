import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("TWELVE_DATA_API_KEY", "")

dxy_candidates = ["DXY", "USDX", "DX-Y.NYB", "USDI", "DXY:CUR", "IXUSD", "USD_I", "USDINDEX", "DX"]
us10y_candidates = ["US10Y", "US10", "TNX", "^TNX", "$TNX", "TR10", "TR10Y", "DGS10", "US10YT", "US10Y:GOV"]

print("Testing DXY candidates...")
for sym in dxy_candidates:
    url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval=1day&apikey={api_key}"
    res = requests.get(url).json()
    status = res.get("status")
    if status == "ok":
        latest = float(res["values"][0]["close"])
        t = res.get("meta", {}).get("type", "")
        exch = res.get("meta", {}).get("exchange", "")
        print(f"[SUCCESS] {sym}: {latest} (Type: {t}, Exchange: {exch})")
        if 90 <= latest <= 120:
            print("   -> VALID DXY RANGE")
    else:
        print(f"[FAILED] {sym}: {res.get('code')} - {res.get('message')}")

print("\nTesting US10Y candidates...")
for sym in us10y_candidates:
    url = f"https://api.twelvedata.com/time_series?symbol={sym}&interval=1day&apikey={api_key}"
    res = requests.get(url).json()
    status = res.get("status")
    if status == "ok":
        latest = float(res["values"][0]["close"])
        t = res.get("meta", {}).get("type", "")
        exch = res.get("meta", {}).get("exchange", "")
        print(f"[SUCCESS] {sym}: {latest} (Type: {t}, Exchange: {exch})")
        if 1 <= latest <= 10:
            print("   -> VALID YIELD RANGE")
    else:
        print(f"[FAILED] {sym}: {res.get('code')} - {res.get('message')}")
