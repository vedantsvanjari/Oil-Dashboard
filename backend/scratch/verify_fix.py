"""Quick post-fix verification. Run: python scratch/verify_fix.py"""
import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()
from app.database.connection import SessionLocal
from app.services.correlation_service import get_matrix, _resolve_series

db = SessionLocal()

print("=== Series individual loads ===")
for name in ['brent', 'wti', 'gasoline', 'heating_oil', 'crude_inv',
             'refinery_utilization', 'wti_brent_spread', 'dxy', 'vix']:
    try:
        s = _resolve_series(db, name, 30)
        tz = getattr(s.index, 'tz', None)
        dups = int(s.index.duplicated().sum()) if not s.empty else 0
        print(f"  {name:30s}: len={len(s):3d}  tz={tz}  dups={dups}")
    except Exception as e:
        print(f"  {name:30s}: ERROR - {e}")
        traceback.print_exc()

print()
print("=== get_matrix calls ===")
for mt in ['product', 'macro', 'spread', 'inventory']:
    try:
        r = get_matrix(db, window='30D', matrix_type=mt, force_refresh=True)
        labels = r.get('labels', [])
        err = r.get('error', None)
        mat_size = f"{len(r.get('matrix', []))}x{len(r.get('matrix', [[]])[0]) if r.get('matrix') else 0}"
        print(f"  {mt:12s}: labels={labels}  matrix={mat_size}  error={err}")
    except Exception as e:
        print(f"  {mt:12s}: EXCEPTION - {e}")
        traceback.print_exc()

db.close()
print("Done.")
