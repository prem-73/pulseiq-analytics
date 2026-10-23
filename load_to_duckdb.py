from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "pulseiq.duckdb"

def main():
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Raw data folder not found: {DATA_DIR}")
    con = duckdb.connect(str(DB_PATH))
    try:
        for csv_path in sorted(DATA_DIR.glob("*.csv")):
            table = csv_path.stem
            # Replacing the table makes re-runs deterministic and avoids duplicate rows.
            escaped_path = str(csv_path).replace("\\", "/").replace("'", "''")
            con.execute(f'CREATE OR REPLACE TABLE raw_{table} AS SELECT * FROM read_csv_auto(\'{escaped_path}\', header=true)')
            count = con.execute(f'SELECT COUNT(*) FROM raw_{table}').fetchone()[0]
            print(f"Loaded raw_{table}: {count} rows")
        print(f"\nDatabase ready: {DB_PATH}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
