from pathlib import Path

import duckdb
import pandas as pd

root = Path(".")
folders = [root / "data", root / "data" / "raw"]

print("=== DATA FILES ===")

files = []

for folder in folders:
    if folder.exists():
        files.extend(folder.glob("*.csv"))
        files.extend(folder.glob("*.xlsx"))
        files.extend(folder.glob("*.json"))

files = sorted(set(files))

for file in files:
    print("\nFILE:", file)

    if file.suffix.lower() == ".csv":
        df = pd.read_csv(file, nrows=3)
        print("COLUMNS:", df.columns.tolist())

    elif file.suffix.lower() == ".xlsx":
        workbook = pd.ExcelFile(file)
        print("SHEETS:", workbook.sheet_names)

    elif file.suffix.lower() == ".json":
        print("JSON file found")

print("\n=== DATABASE TABLES ===")

con = duckdb.connect("pulseiq.duckdb", read_only=True)

objects = con.execute("""
    SELECT table_name, table_type
    FROM information_schema.tables
    ORDER BY table_name
""").fetchdf()

print(objects.to_string(index=False))

print("\n=== ATTRITION-RELATED COLUMNS ===")

for object_name in objects["table_name"].tolist():
    safe_name = object_name.replace('"', '""')

    columns = con.execute(
        'DESCRIBE SELECT * FROM "' + safe_name + '"'
    ).fetchdf()["column_name"].tolist()

    matches = [
        column
        for column in columns
        if any(
            term in column.lower()
            for term in [
                "exit", "attrition", "termination", "resign",
                "hire", "join", "effective", "tenure",
                "reason", "turnover"
            ]
        )
    ]

    if matches:
        print(object_name, ":", matches)

con.close()

print("\nData discovery completed.")

