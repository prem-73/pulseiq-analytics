import duckdb

con = duckdb.connect("pulseiq.duckdb")

# 1. Budget summary view
con.execute("""
CREATE OR REPLACE VIEW task10_budget_summary AS
SELECT
    department_id,
    month,
    budget_payroll_cost
FROM budget_payroll_dept_month
""")

# 2. KPI targets summary view
con.execute("""
CREATE OR REPLACE VIEW task10_kpi_summary AS
SELECT
    department_id,
    month,
    attendance_rate_target,
    overtime_share_target_pct,
    attrition_monthly_target_pct,
    task_completion_target_pct
FROM kpi_targets
""")

# 3. Budget and KPI coverage
print("\n--- BUDGET SUMMARY ---")
print(con.execute("""
SELECT
    COUNT(*) AS records,
    COUNT(DISTINCT department_id) AS departments,
    COUNT(DISTINCT month) AS months,
    SUM(budget_payroll_cost) AS total_budget
FROM task10_budget_summary
""").fetchdf().to_string(index=False))

print("\n--- KPI SUMMARY ---")
print(con.execute("""
SELECT
    COUNT(*) AS records,
    COUNT(DISTINCT department_id) AS departments,
    COUNT(DISTINCT month) AS months
FROM task10_kpi_summary
""").fetchdf().to_string(index=False))

# 4. Missing KPI targets
print("\n--- MISSING KPI TARGETS ---")
print(con.execute("""
SELECT
    COUNT(*) AS total_missing_task_targets
FROM task10_kpi_summary
WHERE task_completion_target_pct IS NULL
""").fetchdf().to_string(index=False))

# 5. Verify budget and KPI department coverage
print("\n--- DEPARTMENT COVERAGE ---")
print(con.execute("""
SELECT
    b.department_id,
    COUNT(DISTINCT b.month) AS budget_months,
    COUNT(DISTINCT k.month) AS kpi_months
FROM task10_budget_summary b
LEFT JOIN task10_kpi_summary k
    ON b.department_id = k.department_id
    AND b.month = k.month
GROUP BY b.department_id
ORDER BY b.department_id
""").fetchdf().to_string(index=False))

con.close()

print("\nTask 10 analysis views created successfully.")