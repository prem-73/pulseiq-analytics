# Day 2 — Star-schema warehouse

Run these commands from the project root in PowerShell, in order:

```powershell
python load_to_duckdb.py
python etl.py
python build_warehouse.py
```

`build_warehouse.py` creates `dim_employee`, `dim_department`, `dim_date`, `fact_salary`, `fact_attendance`, `fact_leave`, and `fact_payroll` in the same `pulseiq.duckdb` database.

## Employee history (SCD Type 2)

If verified employee history is available, fill `data/employee_history.csv` with one row per effective period. Example only:

```csv
employee_id,employee_name,department,age,email,effective_from,effective_to,is_current
101,Example Person,Sales,30,person@example.com,2026-01-01,2026-06-30,false
101,Example Person,Support,30,person@example.com,2026-07-01,9999-12-31,true
```

Do not submit invented history as real data. With this example, June facts use Sales and July facts use Support. Dates are inclusive and periods cannot overlap. If the file is empty, the script uses the current employee rows from Task 1 and cannot infer previous departments.

## Checks and evidence

The script checks each fact count against its Task 1 clean table and runs anti-join orphan checks for employee/date keys. It stops on a mismatch or orphan.

Capture screenshots of:
1. `docs/star_schema.md` rendered as a Mermaid diagram.
2. Terminal output from `python build_warehouse.py` showing fact counts and zero orphan checks.
3. Commit the new files to your private GitHub repository.
