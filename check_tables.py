import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("DATABASE TABLES AND VIEWS")

tables = con.execute("""
    SELECT table_name, table_type
    FROM information_schema.tables
    WHERE table_schema = 'main'
    ORDER BY table_name
""").fetchall()

for table in tables:
    print(table)

con.close()