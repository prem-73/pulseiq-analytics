# Day 3 — Data Quality Gatekeeper

Run after Day 1 and Day 2:

```powershell
python load_to_duckdb.py
python etl.py
python build_warehouse.py
python dq_checks.py
```

The runner executes 14 SQL checks and stores each result in `dq_results` (`check_name`, `table_name`, `severity`, `bad_rows`, `status`, `run_time`). Critical checks stop the run when bad rows are found; the email-format check is a warning. Run `python test_dq_checks.py` to see examples of mutation testing using temporary copies, not the production tables. To meet the full task rubric, repeat the mutation-test pattern for every check.

## Check catalogue (plain English)

1. Employee IDs are unique.
2. Required employee fields are populated.
3. Department belongs to the allowed list.
4. Employee age is 18–65.
5. Email contains `@` (warning).
6. Salary IDs are unique.
7. Salary amount is non-negative.
8. Attendance status is allowed.
9. Hours worked are 0–24.
10. Leave start date is not after end date.
11. Leave status is allowed.
12. Net pay equals gross pay minus deductions (±0.01).
13. Fact employee keys resolve to a dimension row.
14. Fact row counts reconcile to the clean Task 1 tables.

## Planted issue review

The uploaded project archive did not contain `dq_checks_catalog` or `04_Validation_Vault/unlock_PQ-03`. Therefore this folder cannot honestly claim a comparison against the 11 planted issues. When the official vault/catalog is available, compare its 11 issue descriptions against the checks above and record `issue`, `detected by check`, `missed?`, and `reason` in your report.
