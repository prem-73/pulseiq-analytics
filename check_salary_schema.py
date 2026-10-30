import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("--- FACT SALARY SCHEMA ---")
print(con.execute("DESCRIBE fact_salary").fetchdf().to_string(index=False))

print("\n--- FACT SALARY SAMPLE ---")
print(con.execute("SELECT * FROM fact_salary LIMIT 5").fetchdf().to_string(index=False))

con.close()