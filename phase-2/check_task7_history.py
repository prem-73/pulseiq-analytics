import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("=== EMPLOYEE HISTORY SUMMARY ===")

query = """
SELECT
is_current,
COUNT(*) AS employee_records,
MIN(effective_from) AS earliest_effective_from,
MAX(effective_from) AS latest_effective_from,
MIN(effective_to) AS earliest_effective_to,
MAX(effective_to) AS latest_effective_to
FROM dim_employee
GROUP BY is_current
ORDER BY is_current
"""

print(con.execute(query).fetchdf().to_string(index=False))

print("\n=== NON-CURRENT EMPLOYEE RECORDS ===")

query = """
SELECT employee_id, department_key, effective_from, effective_to, is_current
FROM dim_employee
WHERE is_current = FALSE
ORDER BY employee_id, effective_from
"""

print(con.execute(query).fetchdf().to_string(index=False))

print("\n=== HEADCOUNT BY MONTH ===")

query = "SELECT * FROM metric_headcount_monthly ORDER BY 1"

print(con.execute(query).fetchdf().to_string(index=False))

con.close()
