import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

query = """
SELECT
    a.attendance_date,
    d.department_name,
    a.status,
    COUNT(*) AS records,
    SUM(TRY_CAST(a.hours_worked AS DOUBLE)) AS total_hours
FROM attendance a
JOIN dim_employee e
    ON TRY_CAST(a.employee_id AS BIGINT) = e.employee_id
JOIN dim_department d
    ON e.department_key = d.department_key
GROUP BY
    a.attendance_date,
    d.department_name,
    a.status
ORDER BY
    a.attendance_date,
    d.department_name,
    a.status
"""

print(con.execute(query).fetchdf().to_string(index=False))

con.close()