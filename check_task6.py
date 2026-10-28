import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

tables = con.execute("SHOW TABLES").fetchdf()

print("\n=== AVAILABLE TABLES ===")
print(tables)

for table in tables["name"]:
    if "attendance" in table.lower() or "leave" in table.lower():
        print(f"\n=== {table} ===")

        result = con.execute(
            f'SELECT * FROM "{table}" LIMIT 5'
        ).fetchdf()

        print(result)

con.close()