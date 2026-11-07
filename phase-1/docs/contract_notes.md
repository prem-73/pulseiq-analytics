# Data contract notes (sample)

These notes describe the sample contract bundled with this starter project. For your course submission, compare every rule against the official data-contract sheet and revise as needed.

## 1. employees
- `employee_id`: required integer, minimum 1, unique.
- `employee_name`: required non-empty string.
- `department`: required string; allowed values: IT, HR, Finance, Operations.
- `age`: required integer between 18 and 65.
- `email`: required string containing `@`.

## 2. attendance
- `attendance_id`: required integer, minimum 1, unique.
- `employee_id`: required integer, minimum 1.
- `attendance_date`: required ISO date (`YYYY-MM-DD`).
- `status`: required string; allowed values: Present, Absent, Leave, Holiday.
- `hours_worked`: required number between 0 and 24.

## 3. payroll
- `payroll_id`: required integer, minimum 1, unique.
- `employee_id`: required integer, minimum 1.
- `pay_period`: required string.
- `gross_pay`, `deductions`, `net_pay`: required non-negative numbers.
- Business rule: `net_pay = gross_pay - deductions`, allowing 0.01 rounding tolerance.

## Design decision: unexpected columns
Warn and quarantine the feed for review. This avoids silently dropping new data or accepting a column before its meaning and validation rules are approved.
