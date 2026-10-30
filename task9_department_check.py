import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

query = """
SELECT
    d.department_name,
    f.pay_period,
    COUNT(DISTINCT f.employee_key) AS employee_count,
    SUM(f.gross_pay) AS gross_pay_total,
    SUM(f.deductions) AS deductions_total,
    SUM(f.net_pay) AS net_pay_total,
    ROUND(AVG(f.gross_pay), 2) AS average_gross_pay,
    ROUND(AVG(f.net_pay), 2) AS average_net_pay
FROM fact_payroll f
JOIN dim_employee e
    ON f.employee_key = e.employee_key
JOIN dim_department d
    ON e.department_key = d.department_key
GROUP BY
    d.department_name,
    f.pay_period
ORDER BY
    f.pay_period,
    d.department_name
"""

result = con.execute(query).fetchdf()

print("\n--- DEPARTMENT MONTHLY PAYROLL ---")
print(result.to_string(index=False))

con.close()