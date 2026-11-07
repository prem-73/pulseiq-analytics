# PulseIQ Star Schema — Day 2

```mermaid
erDiagram
    DIM_DEPARTMENT ||--o{ DIM_EMPLOYEE : classifies
    DIM_EMPLOYEE ||--o{ FACT_SALARY : receives
    DIM_DATE ||--o{ FACT_SALARY : effective_on
    DIM_EMPLOYEE ||--o{ FACT_ATTENDANCE : records
    DIM_DATE ||--o{ FACT_ATTENDANCE : occurs_on
    DIM_EMPLOYEE ||--o{ FACT_LEAVE : requests
    DIM_DATE ||--o{ FACT_LEAVE : starts_on
    DIM_DATE ||--o{ FACT_LEAVE : ends_on
    DIM_EMPLOYEE ||--o{ FACT_PAYROLL : paid_to
    DIM_DATE ||--o{ FACT_PAYROLL : pay_month

    DIM_DEPARTMENT { int department_key PK string department_name }
    DIM_EMPLOYEE { int employee_key PK int employee_id int department_key FK date effective_from date effective_to boolean is_current }
    DIM_DATE { int date_key PK date full_date int year int quarter int month }
    FACT_SALARY { int fact_salary_key PK int salary_id int employee_key FK int date_key FK float salary_amount }
    FACT_ATTENDANCE { int fact_attendance_key PK int attendance_id int employee_key FK int date_key FK string status float hours_worked }
    FACT_LEAVE { int fact_leave_key PK int leave_id int employee_key FK int start_date_key FK int end_date_key FK string leave_type string status }
    FACT_PAYROLL { int fact_payroll_key PK int payroll_id int employee_key FK int date_key FK float gross_pay float deductions float net_pay }
```

## Join map and fact grain

- `fact_salary`: one row per `salary_id`; joins to employee via `employee_key` and date via `date_key`.
- `fact_attendance`: one row per `attendance_id`; joins to employee via `employee_key` and date via `date_key`.
- `fact_leave`: one row per `leave_id`; joins to employee via `employee_key`; dates via `start_date_key` and `end_date_key`.
- `fact_payroll`: one row per `payroll_id`; joins to employee via `employee_key` and date via `date_key`.
- `dim_employee` joins to `dim_department` via `department_key`.

## Surrogate key and history

`employee_id` is the source/business ID. `employee_key` is a warehouse surrogate key for one version of an employee. Under SCD Type 2, the same `employee_id` can have multiple `employee_key` values with different effective dates.

If a person moves from Sales to Support on July 1, June facts map to the Sales version and July facts map to the Support version. Effective dates are inclusive and must not overlap.

`data/employee_history.csv` is a header-only template. Populate it only with verified history. If it remains empty, the script makes one open-ended version per employee from Task 1's clean table; past department changes cannot be inferred.
