"""
Correlation Diagnostics Script
================================
Captures full tracebacks, inspects every dataset, and prints DataFrame shapes,
null counts, column names, and correlation matrix dimensions.

Run from backend/ directory:
    python scratch/diagnose_correlation.py
"""
import os
import sys
import traceback
import json

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal

# ─────────────────────────────────────────────────────────────────
# 1. Open DB session
# ─────────────────────────────────────────────────────────────────
db: Session = SessionLocal()

print("=" * 70)
print("STEP 1 — Discover datasets")
print("=" * 70)

from app.services.correlation_service import (
    discover_datasets,
    _resolve_series,
    _align_series,
    _compute_pearson_matrix,
    MATRIX_GROUPS,
    VALID_WINDOWS,
)

try:
    datasets = discover_datasets(db)
    print(f"Total datasets discovered: {len(datasets)}")
    for d in datasets:
        print(f"  [{d['category']:15s}] {d['name']:30s}  source={d['source']}")
except Exception:
    print("ERROR discovering datasets:")
    traceback.print_exc()
    datasets = []

# ─────────────────────────────────────────────────────────────────
# 2. Load every series and inspect
# ─────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("STEP 2 — Load and inspect every series (window=30D)")
print("=" * 70)

DAYS = 30
all_names = []
for names in MATRIX_GROUPS.values():
    for n in names:
        if n not in all_names:
            all_names.append(n)

series_results = {}

for name in all_names:
    try:
        s = _resolve_series(db, name, DAYS)
        status = "OK"
        shape = len(s)
        non_null = int(s.notna().sum())
        dtype = str(s.dtype)
        sample = s.dropna().head(2).tolist() if not s.empty else []
        idx_type = type(s.index).__name__ if not s.empty else "N/A"
        dup_idx = int(s.index.duplicated().sum()) if not s.empty else 0

        series_results[name] = {
            "status": status,
            "len": shape,
            "non_null": non_null,
            "dtype": dtype,
            "idx_type": idx_type,
            "dup_idx": dup_idx,
            "sample": sample,
        }

        flag = ""
        if shape == 0:
            flag = " ← EMPTY"
        elif non_null == 0:
            flag = " ← ALL NULL"
        elif non_null < 5:
            flag = f" ← SPARSE ({non_null} obs)"
        elif dup_idx > 0:
            flag = f" ← {dup_idx} DUPLICATE INDEX ENTRIES"

        print(f"  {name:35s} len={shape:4d}  non_null={non_null:4d}  dtype={dtype:10s}  idx={idx_type}{flag}")

    except Exception:
        series_results[name] = {"status": "ERROR"}
        print(f"  {name:35s} ERROR:")
        traceback.print_exc()

# ─────────────────────────────────────────────────────────────────
# 3. Build combined DataFrame and inspect alignment
# ─────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("STEP 3 — DataFrame alignment check (window=30D, matrix_type=product)")
print("=" * 70)

product_names = MATRIX_GROUPS["product"]
series_dict = {}
for name in product_names:
    try:
        s = _resolve_series(db, name, DAYS)
        if not s.empty:
            series_dict[name] = s
    except Exception:
        traceback.print_exc()

print(f"Series fed into _align_series: {list(series_dict.keys())}")

try:
    df = _align_series(series_dict)
    print(f"Aligned DataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Index dtype: {df.index.dtype}")
    print(f"Index has duplicates: {df.index.duplicated().any()}")
    print(f"Date range: {df.index.min()} → {df.index.max()}")
    print()
    print("Null counts per column:")
    for col in df.columns:
        total = len(df)
        nulls = int(df[col].isna().sum())
        print(f"  {col:30s}: {nulls}/{total} null")
    print()
    print("Non-numeric columns:")
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            print(f"  {col}: dtype={df[col].dtype}")
except Exception:
    print("ERROR in _align_series:")
    traceback.print_exc()
    df = pd.DataFrame()

# ─────────────────────────────────────────────────────────────────
# 4. Attempt Pearson matrix and capture traceback
# ─────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("STEP 4 — Pearson correlation attempt")
print("=" * 70)

if not df.empty:
    try:
        labels, matrix = _compute_pearson_matrix(df, product_names)
        print(f"SUCCESS: labels={labels}, matrix size={len(matrix)}x{len(matrix[0]) if matrix else 0}")
    except Exception:
        print("ERROR in _compute_pearson_matrix:")
        traceback.print_exc()
else:
    print("Skipped — DataFrame is empty")

# ─────────────────────────────────────────────────────────────────
# 5. Call get_matrix and capture full traceback
# ─────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("STEP 5 — Full get_matrix() call with traceback")
print("=" * 70)

from app.services.correlation_service import get_matrix

for matrix_type in ["product", "macro", "spread", "inventory"]:
    print(f"\n  matrix_type={matrix_type!r}:")
    try:
        result = get_matrix(db, window="30D", matrix_type=matrix_type, force_refresh=True)
        print(f"    OK → labels={result['labels']}, cached={result.get('cached')}")
        if result.get("error"):
            print(f"    SOFT ERROR: {result['error']}")
    except Exception:
        print(f"    HARD ERROR:")
        traceback.print_exc()

# ─────────────────────────────────────────────────────────────────
# 6. DB row counts for every relevant table
# ─────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("STEP 6 — DB row counts")
print("=" * 70)

from app.models.prices import Price
from app.models.macro import MacroData
from app.models.inventories import Inventory
from app.models.refineries import RefineryData
from app.models.calendar_spread import CalendarSpread
from app.models.crack_spread import CrackSpread

for model, label in [
    (Price, "prices"),
    (MacroData, "macro_data"),
    (Inventory, "inventories"),
    (RefineryData, "refineries"),
    (CalendarSpread, "calendar_spreads"),
    (CrackSpread, "crack_spreads"),
]:
    try:
        n = db.query(model).count()
        print(f"  {label:25s}: {n} rows")
    except Exception as e:
        print(f"  {label:25s}: ERROR — {e}")

# ─────────────────────────────────────────────────────────────────
# 7. Check prices symbols
# ─────────────────────────────────────────────────────────────────
print()
print("=" * 70)
print("STEP 7 — Distinct symbols in prices table")
print("=" * 70)

try:
    symbols = db.query(Price.symbol).distinct().all()
    print(f"  Symbols: {[s[0] for s in symbols]}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=" * 70)
print("STEP 8 — check _resolve_series for 'dxy' (macro DB field)")
print("=" * 70)

from app.services.correlation_service import _load_macro_series
try:
    s = _load_macro_series(db, "dxy", 30)
    print(f"  dxy series: len={len(s)}, non_null={s.notna().sum()}, idx type={type(s.index)}")
    print(f"  Index sample: {s.index[:3].tolist() if len(s) > 0 else 'empty'}")
    print(f"  Values sample: {s.values[:3].tolist() if len(s) > 0 else 'empty'}")
except Exception:
    traceback.print_exc()

db.close()
print()
print("=" * 70)
print("DIAGNOSTICS COMPLETE")
print("=" * 70)
