import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("--- PAYROLL QUALITY CHECK ---")

result = con.execute("""
SELECT
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE payroll_id IS NULL) AS missing_payroll_id,
    COUNT(*) FILTER (WHERE employee_key IS NULL) AS missing_employee_key,
    COUNT(*) FILTER (WHERE date_key IS NULL) AS missing_date_key,
    COUNT(*) FILTER (WHERE gross_pay IS NULL) AS missing_gross,
    COUNT(*) FILTER (WHERE deductions IS NULL) AS missing_deductions,
    COUNT(*) FILTER (WHERE net_pay IS NULL) AS missing_net,
    COUNT(*) FILTER (WHERE gross_pay < 0) AS negative_gross,
    COUNT(*) FILTER (WHERE deductions < 0) AS negative_deductions,
    COUNT(*) FILTER (WHERE net_pay < 0) AS negative_net,
    COUNT(*) - COUNT(DISTINCT payroll_id) AS duplicate_payroll_ids
FROM fact_payroll
""").fetchdf()

print(result.to_string(index=False))

con.close()