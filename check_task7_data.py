import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("=== ATTRITION / HEADCOUNT OBJECTS ===")

query = "SELECT table_name, table_type FROM information_schema.tables WHERE lower(table_name) LIKE '%attrition%' OR lower(table_name) LIKE '%exit%' OR lower(table_name) LIKE '%headcount%' OR lower(table_name) LIKE '%risk%' ORDER BY table_name"

result = con.execute(query).fetchdf()
print(result.to_string(index=False))

print("\n=== EMPLOYEES TABLE COLUMNS ===")
result = con.execute("DESCRIBE SELECT * FROM employees").fetchdf()
print(result.to_string(index=False))

print("\n=== DIM_EMPLOYEE TABLE COLUMNS ===")
result = con.execute("DESCRIBE SELECT * FROM dim_employee").fetchdf()
print(result.to_string(index=False))

con.close()