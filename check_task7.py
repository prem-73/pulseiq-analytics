import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

tables = con.execute("SHOW TABLES").fetchdf()["name"].tolist()

print("\n========== ATTRITION TABLES ==========")

for table in tables:
    if any(word in table.lower() for word in [
        "attrition",
        "headcount",
        "employee",
        "department"
    ]):
        print(f"\nTable: {table}")

        try:
            schema = con.execute(
                f'DESCRIBE "{table}"'
            ).fetchdf()

            print(schema.to_string(index=False))

            data = con.execute(
                f'SELECT * FROM "{table}" LIMIT 5'
            ).fetchdf()

            print("\nSample records:")
            print(data.to_string(index=False))

        except Exception as error:
            print("Error:", error)

con.close()