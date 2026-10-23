# Day 4 — Governed metric layer

Run after Tasks 1–3:

```powershell
python build_metrics.py
```

This creates 28 reusable `metric_*` views and a `metric_catalog` view in `pulseiq.duckdb`. Definitions are based on columns available in this starter project. The official `metric_dictionary` and `metric_views_examples.sql` were not present in the uploaded archive, so these definitions are provisional and must be reconciled against the official course dictionary before you claim they are the 28 official metrics.

## Small-group privacy rule

Do not expose a group-level result when its distinct employee count is below the official dictionary's minimum group size. That minimum value was not provided, so do not invent one. Apply it to group-level views/dashboard queries once the official value is available. Current simple aggregates are suitable for local practice, not automatically approved for publication.

## Manual checks

Check five views against the source rows using a calculator: headcount, salary total, present records, approved leaves, and net payroll total. Record source rows, manual calculation, SQL result, and match/mismatch in your report.

## Attrition definition

Choose and document the denominator required by the official metric dictionary. A common period-based definition is departures during the period divided by average headcount ((start headcount + end headcount) / 2), but this starter schema does not contain a verified employee termination field, so it cannot calculate attrition correctly yet. Do not publish an attrition metric without that source.

## Manual Validation Results

The five selected metric views were compared against their source tables in the local DuckDB database, `pulseiq.duckdb`.

| Metric            | Metric View Result |                       Source Table Result | Status |
| ----------------- | -----------------: | ----------------------------------------: | ------ |
| Headcount         |      100 employees | 100 current employees from `dim_employee` | PASS   |
| Salary Total      |          4,530,000 |                 4,530,000 from `salaries` | PASS   |
| Present Records   |                 70 |                      70 from `attendance` | PASS   |
| Approved Leaves   |                 50 |                           50 from `leave` | PASS   |
| Net Payroll Total |          4,260,000 |                  4,260,000 from `payroll` | PASS   |

### Verification Method

1. **Headcount:** Counted distinct employee IDs in `dim_employee` where `is_current = TRUE`. The result was 100. The `metric_headcount` view was updated to use the current employee dimension records.
2. **Salary Total:** Calculated the sum of `TRY_CAST(salary_amount AS DOUBLE)` from `salaries`. The result was 4,530,000.
3. **Present Records:** Counted rows in `attendance` where the trimmed, lower-case `status` equals `present`. The result was 70.
4. **Approved Leaves:** Counted rows in `leave` where the trimmed, lower-case `status` equals `approved`. The result was 50.
5. **Net Payroll Total:** Calculated the sum of `TRY_CAST(net_pay AS DOUBLE)` from `payroll`. The result was 4,260,000.

All five metric results matched their corresponding source-table calculations.

### Limitations and Governance

* The metric definitions remain provisional until reconciled with the official course metric dictionary.
* The official minimum group size for small-group privacy was not provided. Group-level metrics must not be treated as approved for publication until the required privacy threshold is confirmed and applied.
* Attrition cannot be calculated reliably until a verified employee termination source and the official denominator definition are available.
* The five checks validate the selected totals and counts; they do not independently prove that all 28 metric definitions are correct.

