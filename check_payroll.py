import duckdb

con = duckdb.connect("pulseiq.duckdb", read_only=True)

print("\n--- PAYROLL SUMMARY ---")

result = con.execute("""
SELECT
    COUNT(*) AS total_rows,
    COUNT(DISTINCT payroll_id) AS unique_payroll_ids,
    SUM(gross_pay) AS gross_total,
    SUM(deductions) AS deductions_total,
    SUM(net_pay) AS net_total,
    SUM(CASE
        WHEN ABS(gross_pay - deductions - net_pay) > 0.01
        THEN 1 ELSE 0
    END) AS calculation_mismatches
FROM fact_payroll
""").fetchdf()

print(result.to_string(index=False))

print("\n--- MISMATCH ROWS ---")

bad_rows = con.execute("""
SELECT
    payroll_id,
    pay_period,
    gross_pay - deductions - net_pay AS difference
FROM fact_payroll
WHERE ABS(gross_pay - deductions - net_pay) > 0.01
""").fetchdf()

print(bad_rows.to_string(index=False))

con.close()