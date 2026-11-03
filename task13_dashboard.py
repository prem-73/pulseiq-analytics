import os
import duckdb
import pandas as pd
import streamlit as st

DB_PATH = "pulseiq.duckdb"
REFERENCE_PATHS = [
    "unlock_PQ-13_reference_summary_dept_month.csv",
    os.path.join("data", "reference", "unlock_PQ-13_reference_summary_dept_month.csv"),
    os.path.join("data", "raw", "unlock_PQ-13_reference_summary_dept_month.csv"),
]

st.set_page_config(page_title="Task 13 | Department Impact", layout="wide")
st.title("Task 13 – Cross-Department Impact Dashboard")
st.caption("Department-month view combining payroll, attendance, leave and available attrition context.")

if not os.path.exists(DB_PATH):
    st.error(f"Database not found: {DB_PATH}. Run this app from your pulseiq project folder.")
    st.stop()

@st.cache_data
def load_local_data(db_path):
    con = duckdb.connect(db_path, read_only=True)
    try:
        # Aggregate each fact independently at department-month grain before joining.
        payroll = con.execute("""
            SELECT e.department_key, d.year, d.month,
                   SUM(p.gross_pay) AS gross_pay,
                   SUM(p.net_pay) AS net_pay,
                   COUNT(*) AS payroll_records,
                   COUNT(DISTINCT p.employee_key) AS employees_paid
            FROM fact_payroll p
            JOIN dim_date d ON p.date_key = d.date_key
            JOIN dim_employee e ON p.employee_key = e.employee_key
            GROUP BY e.department_key, d.year, d.month
        """).df()

        attendance = con.execute("""
            SELECT e.department_key, d.year, d.month,
                   COUNT(*) AS attendance_records,
                   COUNT(DISTINCT a.employee_key) AS employees_with_attendance,
                   SUM(CASE WHEN lower(a.status) = 'present' THEN 1 ELSE 0 END) AS present_records,
                   SUM(CASE WHEN lower(a.status) = 'absent' THEN 1 ELSE 0 END) AS absent_records,
                   SUM(CASE WHEN lower(a.status) = 'leave' THEN 1 ELSE 0 END) AS leave_attendance_records,
                   SUM(a.hours_worked) AS total_hours_worked
            FROM fact_attendance a
            JOIN dim_date d ON a.date_key = d.date_key
            JOIN dim_employee e ON a.employee_key = e.employee_key
            GROUP BY e.department_key, d.year, d.month
        """).df()

        # Expand approved leave intervals into calendar days, then aggregate by
        # the month in which each leave day occurs. This avoids counting a
        # multi-day request only in its start month.
        leave = con.execute("""
            WITH approved AS (
                SELECT l.employee_key,
                       s.full_date AS start_date,
                       en.full_date AS end_date,
                       e.department_key
                FROM fact_leave l
                JOIN dim_date s ON l.start_date_key = s.date_key
                JOIN dim_date en ON l.end_date_key = en.date_key
                JOIN dim_employee e ON l.employee_key = e.employee_key
                WHERE lower(l.status) = 'approved'
                  AND en.full_date >= s.full_date
            ),
            leave_days AS (
                SELECT department_key, employee_key, CAST(day_value AS DATE) AS leave_date
                FROM approved,
                UNNEST(generate_series(start_date, end_date, INTERVAL 1 DAY)) AS t(day_value)
            )
            SELECT department_key,
                   EXTRACT(year FROM leave_date)::INTEGER AS year,
                   EXTRACT(month FROM leave_date)::INTEGER AS month,
                   COUNT(*) AS approved_leave_days,
                   COUNT(DISTINCT employee_key) AS employees_taking_approved_leave
            FROM leave_days
            GROUP BY department_key, year, month
        """).df()

        departments = con.execute("""
            SELECT department_key, department_name
            FROM dim_department
            ORDER BY department_name
        """).df()

        headcount = con.execute("""
            SELECT department_key, COUNT(DISTINCT employee_key) AS current_headcount
            FROM dim_employee
            WHERE is_current = TRUE
            GROUP BY department_key
        """).df()
        return payroll, attendance, leave, departments, headcount
    finally:
        con.close()

try:
    payroll, attendance, leave, departments, headcount = load_local_data(DB_PATH)
except Exception as exc:
    st.error(f"Could not build the department-month dataset: {exc}")
    st.info("Check that the database contains fact_payroll, fact_attendance, fact_leave, dim_date, dim_employee and dim_department.")
    st.stop()

# Use the union of source department-month keys; merge only already-aggregated data.
keys = pd.concat([
    payroll[["department_key", "year", "month"]],
    attendance[["department_key", "year", "month"]],
    leave[["department_key", "year", "month"]],
], ignore_index=True).drop_duplicates()

result = (keys
          .merge(departments, on="department_key", how="left")
          .merge(payroll, on=["department_key", "year", "month"], how="left")
          .merge(attendance, on=["department_key", "year", "month"], how="left")
          .merge(leave, on=["department_key", "year", "month"], how="left")
          .merge(headcount, on="department_key", how="left"))

numeric_cols = [
    "gross_pay", "net_pay", "payroll_records", "employees_paid",
    "attendance_records", "employees_with_attendance", "present_records",
    "absent_records", "leave_attendance_records", "total_hours_worked",
    "approved_leave_days", "employees_taking_approved_leave"
]
for col in numeric_cols:
    if col in result:
        result[col] = result[col].fillna(0)

result["month_label"] = (
    result["year"].astype(int).astype(str) + "-" +
    result["month"].astype(int).astype(str).str.zfill(2)
)
result["attendance_rate_pct"] = (
    result["present_records"] / result["attendance_records"].replace(0, pd.NA) * 100
)
result["leave_days_per_head"] = (
    result["approved_leave_days"] / result["current_headcount"].replace(0, pd.NA)
)
result["overtime_cost"] = pd.NA
result["overtime_hours"] = pd.NA
result["late_arrivals"] = pd.NA
result["monthly_exits"] = pd.NA
result["monthly_attrition_rate_pct"] = pd.NA

# Reference file is optional; local data and reference periods do not overlap
# in this starter dataset, so do not present a false reconciliation.
reference_path = next((p for p in REFERENCE_PATHS if os.path.exists(p)), None)

months = sorted(result["month_label"].dropna().unique().tolist())
if months:
    selected_month = st.selectbox("Select month", months, index=len(months)-1)
    view = result[result["month_label"] == selected_month].sort_values("department_name")
else:
    view = result.copy()

st.subheader("Current local data – department comparison")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Departments", int(result["department_key"].nunique()))
c2.metric("Gross payroll", f"₹{result['gross_pay'].sum():,.2f}")
c3.metric("Present records", f"{int(result['present_records'].sum()):,}")
c4.metric("Approved leave days", f"{int(result['approved_leave_days'].sum()):,}")

display_cols = [
    "department_name", "current_headcount", "gross_pay", "net_pay",
    "attendance_rate_pct", "approved_leave_days", "leave_days_per_head",
    "total_hours_worked"
]
st.dataframe(view[display_cols].rename(columns={
    "department_name": "Department",
    "current_headcount": "Current headcount",
    "gross_pay": "Gross payroll",
    "net_pay": "Net payroll",
    "attendance_rate_pct": "Attendance rate (%)",
    "approved_leave_days": "Approved leave days",
    "leave_days_per_head": "Leave days per head",
    "total_hours_worked": "Hours worked"
}), use_container_width=True)

st.subheader("Department charts")
chart_data = view.set_index("department_name")
left, right = st.columns(2)
with left:
    st.caption("Gross payroll by department")
    st.bar_chart(chart_data[["gross_pay"]])
with right:
    st.caption("Attendance rate by department (%)")
    st.bar_chart(chart_data[["attendance_rate_pct"]])

st.subheader("Overtime and attrition")
st.warning(
    "Overtime hours/cost, late arrivals and monthly exits are not available in the "
    "current local fact tables. They are intentionally shown as unavailable rather "
    "than inferred from ordinary hours or unrelated records."
)
st.info(
    "The external emp_attrition.csv is a separate 1,470-row attrition dataset. "
    "It has department, Attrition and OverTime fields but no exit month/date, and its "
    "department categories do not map reliably to the five local departments. "
    "It must be analysed separately and must not be joined into this monthly view."
)

st.subheader("Reference summary reconciliation")
if reference_path:
    ref = pd.read_csv(reference_path)
    st.write(f"Reference file loaded: `{reference_path}` ({len(ref)} rows).")
    st.write(
        "Reference coverage: "
        f"{ref['department_id'].nunique()} departments; "
        f"{ref['month'].nunique()} months; "
        f"{ref['month'].min()} to {ref['month'].max()}."
    )
    local_months = set(result["month_label"])
    ref_months = set(pd.to_datetime(ref["month"]).dt.strftime("%Y-%m"))
    overlap = sorted(local_months.intersection(ref_months))
    if overlap:
        st.success("Overlapping months found: " + ", ".join(overlap))
        st.info("Department IDs and metric definitions must also be mapped/validated before declaring a match.")
    else:
        st.error(
            "No overlapping month exists between local payroll/attendance data "
            "and the reference summary. Local data is October 2026; reference data "
            "ends September 2026. Exact monthly reconciliation is not possible."
        )
    st.dataframe(ref.head(20), use_container_width=True)
else:
    st.warning(
        "Reference summary CSV not found. Copy "
        "`unlock_PQ-13_reference_summary_dept_month.csv` into the project root "
        "to display the reference coverage and reconciliation note."
    )

st.subheader("Method and limitations")
st.markdown("""
- Each fact source is aggregated independently to **department + month** before joining.
- Payroll and attendance are joined using employee department mapping and `dim_date`.
- Approved leave intervals are expanded into calendar days and assigned to the month of each leave day.
- Leave days per head = approved leave days / current department headcount. This uses current headcount as a denominator, not historical month-end headcount.
- Overtime, late arrivals and monthly attrition are unavailable in the local fact schema; no estimates are fabricated.
- The external attrition sample is kept separate because it has no exit date and incompatible department categories.
""")

os.makedirs("outputs", exist_ok=True)
result.sort_values(["year", "month", "department_name"]).to_csv(
    os.path.join("outputs", "task13_department_month.csv"), index=False
)
st.success("Department-month output saved to outputs/task13_department_month.csv")
