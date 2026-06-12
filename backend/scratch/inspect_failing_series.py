"""
Deep inspect the failing series loaders.
Run from backend/: python scratch/inspect_failing_series.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal

db = SessionLocal()

print("=== PRICES TABLE - brent ===")
from app.models.prices import Price
from datetime import datetime, timezone, timedelta
cutoff = datetime.now(timezone.utc) - timedelta(days=30)
rows = db.query(Price.timestamp, Price.price).filter(Price.symbol == "brent", Price.timestamp >= cutoff).order_by(Price.timestamp.asc()).all()
print(f"Rows: {len(rows)}")
if rows:
    ts_sample = rows[0].timestamp
    print(f"First timestamp type: {type(ts_sample)}, value: {ts_sample}, tzinfo: {ts_sample.tzinfo}")
    idx = pd.to_datetime([r.timestamp for r in rows]).normalize()
    print(f"After pd.to_datetime().normalize() - tzinfo: {idx.tzinfo}, dtype: {idx.dtype}")
    print(f"Dup count: {idx.duplicated().sum()}")

print()
print("=== MACRO TABLE - dxy ===")
from app.models.macro import MacroData
cutoff_date = cutoff.date()
rows2 = db.query(MacroData.date, MacroData.dxy).filter(MacroData.date >= cutoff_date).order_by(MacroData.date.asc()).all()
print(f"Rows: {len(rows2)}")
if rows2:
    d_sample = rows2[0][0]
    print(f"First date type: {type(d_sample)}, value: {d_sample}")
    idx2 = pd.to_datetime([r[0] for r in rows2])
    print(f"After pd.to_datetime() - tzinfo: {idx2.tzinfo}, dtype: {idx2.dtype}")

print()
print("=== INVENTORIES TABLE - crude ===")
from app.models.inventories import Inventory
rows3 = db.query(Inventory.date, Inventory.quantity).filter(Inventory.item_name == "crude", Inventory.date >= cutoff).order_by(Inventory.date.asc()).all()
print(f"Rows: {len(rows3)}")
if rows3:
    d_sample = rows3[0].date
    print(f"First date type: {type(d_sample)}, value: {d_sample}, tzinfo: {getattr(d_sample, 'tzinfo', 'N/A')}")
    idx3 = pd.to_datetime([r.date for r in rows3]).normalize()
    print(f"After pd.to_datetime().normalize() - tzinfo: {idx3.tzinfo}, dtype: {idx3.dtype}")
    print(f"Dup count: {idx3.duplicated().sum()}")

print()
print("=== REFINERIES TABLE ===")
from app.models.refineries import RefineryData
rows4 = db.query(RefineryData.date, RefineryData.refinery_utilization).filter(RefineryData.date >= cutoff).all()
print(f"Rows: {len(rows4)}")
if rows4:
    d_sample = rows4[0][0]
    print(f"First date type: {type(d_sample)}, value: {d_sample}, tzinfo: {getattr(d_sample, 'tzinfo', 'N/A')}")

print()
print("=== CALENDAR SPREADS TABLE ===")
from app.models.calendar_spread import CalendarSpread
rows5 = db.query(CalendarSpread.timestamp, CalendarSpread.spread).filter(
    CalendarSpread.commodity == "wti", CalendarSpread.contract1 == "M1",
    CalendarSpread.contract2 == "M2", CalendarSpread.timestamp >= cutoff
).order_by(CalendarSpread.timestamp.asc()).all()
print(f"Rows: {len(rows5)}")
if rows5:
    ts_sample = rows5[0].timestamp
    print(f"First timestamp type: {type(ts_sample)}, value: {ts_sample}, tzinfo: {ts_sample.tzinfo}")
    idx5 = pd.to_datetime([r.timestamp for r in rows5]).normalize()
    print(f"After pd.to_datetime().normalize() - tzinfo: {idx5.tzinfo}, dtype: {idx5.dtype}")
    print(f"Dup count: {idx5.duplicated().sum()}")

db.close()
print()
print("CONCLUSION:")
print("  prices.timestamp    -> timezone-AWARE  (stored as TIMESTAMPTZ)")
print("  macro_data.date     -> timezone-NAIVE  (stored as DATE)")
print("  inventories.date    -> timezone-AWARE  (stored as TIMESTAMPTZ)")
print("  refineries.date     -> timezone-AWARE  (stored as TIMESTAMPTZ)")
print("  calendar_spreads.ts -> timezone-AWARE  (stored as TIMESTAMPTZ)")
