import duckdb
import pandas as pd

con = duckdb.connect("pulseiq.duckdb")

# Load budget data
budget = pd.read_csv("budget_payroll_dept_month.csv")
budget["month"] = pd.to_datetime(budget["month"]).dt.date

con.register("budget_df", budget)

con.execute("""
CREATE OR REPLACE TABLE budget_payroll_dept_month AS
SELECT * FROM budget_df
""")

# Load KPI targets
kpi = pd.read_csv("kpi_targets.csv")
kpi["month"] = pd.to_datetime(kpi["month"]).dt.date

con.register("kpi_df", kpi)

con.execute("""
CREATE OR REPLACE TABLE kpi_targets AS
SELECT * FROM kpi_df
""")

print("Task 10 tables loaded successfully!")

print("\nBudget rows:")
print(con.execute(
    "SELECT COUNT(*) FROM budget_payroll_dept_month"
).fetchone())

print("\nKPI target rows:")
print(con.execute(
    "SELECT COUNT(*) FROM kpi_targets"
).fetchone())

print("\nBudget sample:")
print(con.execute(
    "SELECT * FROM budget_payroll_dept_month LIMIT 5"
).fetchdf().to_string(index=False))

print("\nKPI sample:")
print(con.execute(
    "SELECT * FROM kpi_targets LIMIT 5"
).fetchdf().to_string(index=False))

con.close()