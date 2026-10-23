from pathlib import Path
import duckdb
ROOT=Path(__file__).resolve().parent
DB=ROOT/'pulseiq.duckdb'
SQL=ROOT/'metric_views.sql'
def main():
 if not DB.exists(): raise SystemExit('pulseiq.duckdb missing. Run Tasks 1 and 2 first.')
 con=duckdb.connect(str(DB))
 try:
  con.execute(SQL.read_text(encoding='utf-8'))
  views=[r[0] for r in con.execute("SELECT table_name FROM information_schema.views WHERE table_name LIKE 'metric_%' ORDER BY table_name").fetchall()]
  catalog=con.execute('SELECT * FROM metric_catalog ORDER BY metric_name').fetchdf()
  print(f'Created metric views and catalog. Catalog rows: {len(catalog)}')
  print(catalog.to_string(index=False))
  print(f'\nMetric views found: {len([v for v in views if v != "metric_catalog"])} (expected 28)')
  if len(catalog)!=28: raise SystemExit('Metric catalog must contain 28 rows.')
  for name in catalog['metric_name']:
   con.execute(f'SELECT * FROM {name} LIMIT 1').fetchall()
  print('PASS: all 28 metric views execute.')
 finally: con.close()
if __name__=='__main__': main()
