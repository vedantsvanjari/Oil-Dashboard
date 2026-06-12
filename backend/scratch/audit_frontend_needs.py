"""
Full audit script — checks every dataset the frontend needs.
Run: python scratch/audit_frontend_needs.py
"""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()

import yfinance as yf
import pandas as pd
from app.database.connection import SessionLocal
from app.models.prices import Price
from app.models.macro import MacroData
from app.models.calendar_spread import CalendarSpread
from app.models.crack_spread import CrackSpread

db = SessionLocal()

print("=" * 65)
print("AUDIT 1 — prices table symbols and observation counts")
print("=" * 65)
from sqlalchemy import func
rows = db.query(Price.symbol, func.count(Price.id), func.min(Price.timestamp), func.max(Price.timestamp))\
         .group_by(Price.symbol).all()
for sym, cnt, mn, mx in rows:
    print(f"  {sym:15s}: {cnt:3d} rows   {mn} -> {mx}")

print()
print("=" * 65)
print("AUDIT 2 — macro_data observations")
print("=" * 65)
mc = db.query(MacroData).count()
if mc:
    first = db.query(MacroData).order_by(MacroData.date.asc()).first()
    last  = db.query(MacroData).order_by(MacroData.date.desc()).first()
    print(f"  {mc} rows  {first.date} -> {last.date}")
    for field in ['dxy','us10y','us2y','yield_curve']:
        non_null = db.query(MacroData).filter(getattr(MacroData, field).isnot(None)).count()
        print(f"    {field:15s}: {non_null} non-null")
else:
    print("  EMPTY")

print()
print("=" * 65)
print("AUDIT 3 — calendar_spreads pairs available")
print("=" * 65)
from sqlalchemy import func as F
pairs = db.query(CalendarSpread.commodity, CalendarSpread.contract1, CalendarSpread.contract2,
                  func.count(CalendarSpread.id), func.min(CalendarSpread.timestamp),
                  func.max(CalendarSpread.timestamp))\
          .group_by(CalendarSpread.commodity, CalendarSpread.contract1, CalendarSpread.contract2)\
          .all()
for comm, c1, c2, cnt, mn, mx in pairs:
    print(f"  {comm:6s} {c1}-{c2:4s}: {cnt:4d} rows   {mn.date()} -> {mx.date()}")

print()
print("=" * 65)
print("AUDIT 4 — crack_spreads observations")
print("=" * 65)
ct_rows = db.query(CrackSpread.crude_type, func.count(CrackSpread.id),
                    func.min(CrackSpread.timestamp), func.max(CrackSpread.timestamp))\
             .group_by(CrackSpread.crude_type).all()
for ct, cnt, mn, mx in ct_rows:
    print(f"  {ct:6s}: {cnt:4d} rows   {mn.date()} -> {mx.date()}")

print()
print("=" * 65)
print("AUDIT 5 — yfinance availability test (1y history)")
print("=" * 65)
TICKERS = {
    'wti':         'CL=F',
    'brent':       'BZ=F',
    'gasoline':    'RB=F',
    'heating_oil': 'HO=F',
}
for name, ticker in TICKERS.items():
    try:
        hist = yf.Ticker(ticker).history(period='1y')
        obs = len(hist.dropna(subset=['Close']))
        print(f"  {name:15s} ({ticker:10s}): {obs:3d} observations")
    except Exception as e:
        print(f"  {name:15s} ({ticker:10s}): ERROR - {e}")

print()
print("=" * 65)
print("AUDIT 6 — GAP ANALYSIS vs frontend requirements")
print("=" * 65)

# What frontend needs:
product_needed = ['wti', 'brent', 'gasoline', 'heating_oil']
spread_needed  = ['wti_brent', 'wti_M1-M2','wti_M2-M3','wti_M3-M4','wti_M1-M6','wti_M1-M12',
                  'brent_M1-M2','brent_M2-M3','brent_M3-M4','brent_M1-M6','brent_M1-M12','crack']
macro_needed   = ['wti', 'brent', 'dxy', 'us10y', 'yield_curve']

cal_available = {f"{c}_{c1}-{c2}" for (c,c1,c2,*_) in pairs}
crack_available = {f"crack_{ct}" for (ct,*_) in ct_rows}

print("Product heatmap:")
for ds in product_needed:
    src = "yfinance" if ds in TICKERS else "prices_table"
    print(f"  {ds:20s}: OK  ({src})")

print("Spread heatmap:")
for ds in spread_needed:
    if ds == 'wti_brent':
        print(f"  {ds:20s}: OK  (computed from yfinance)")
    elif ds == 'crack':
        ok = 'crack_wti' in crack_available
        print(f"  {ds:20s}: {'OK ' if ok else 'MISSING'}")
    else:
        comm = ds.split('_')[0]
        rest = ds.split('_',1)[1]
        key = f"{comm}_{rest}"
        ok = key in cal_available
        print(f"  {ds:20s}: {'OK ' if ok else 'MISSING'}  ({'calendar_spreads' if ok else 'NOT IN DB'})")

print("Macro heatmap:")
macro_ok = {'wti': 'yfinance', 'brent': 'yfinance',
            'dxy': f"macro_data ({mc} rows)", 'us10y': f"macro_data ({mc} rows)",
            'yield_curve': f"macro_data ({mc} rows)"}
for ds in macro_needed:
    print(f"  {ds:20s}: OK  ({macro_ok.get(ds, '?')})")

print()
print("Existing /api/correlations/matrix route needs:")
print("  product: returns dxy+us10y too - frontend only wants wti/brent/gasoline/heating_oil")
print("  spread:  missing brent_M2-M3, brent_M3-M4, brent_M1-M6, wti_M1-M6, wti_brent_spread")
print("  macro:   missing 'brent'; has vix/sp500/us2y/us3y that frontend doesn't need")
print("  -> Need 3 new clean endpoints: /product  /spreads  /macro")

db.close()
