import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()
from app.database.connection import SessionLocal
from app.services.correlation_service import get_frontend_matrix

db = SessionLocal()

for mt in ['product', 'spreads', 'macro']:
    try:
        r = get_frontend_matrix(db, window='30D', matrix_type=mt, force_refresh=True)
        labels = r.get('labels', [])
        err = r.get('error', None)
        matrix = r.get('matrix', [])
        mat_size = f"{len(matrix)}x{len(matrix[0]) if matrix else 0}"
        print(f"  {mt:12s}: labels={labels}  matrix={mat_size}  error={err}")
    except Exception as e:
        print(f"  {mt:12s}: EXCEPTION - {e}")
        traceback.print_exc()

db.close()
print('Done.')
