import streamlit as st
import duckdb
import pandas as pd

# -------------------------------
# PAGE CONFIG
# -------------------------------

st.set_page_config(
    page_title="Task 9 - Payroll Dashboard",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Payroll Cost Dashboard")
st.caption("Task 9 | Payroll Analysis and Reconciliation")

DB_PATH = "pulseiq.duckdb"
MIN_EMPLOYEES = 5

# -------------------------------
# DATABASE CONNECTION
# -------------------------------

@st.cache_data
def load_payroll_data():

    con = duckdb.connect(DB_PATH, read_only=True)

    query = """
    SELECT
        f.payroll_id,
        f.employee_key,
        f.pay_period,
        d.department_name,
        f.gross_pay,
        f.deductions,
        f.net_pay

    FROM fact_payroll f

    JOIN dim_employee e
        ON f.employee_key = e.employee_key

    JOIN dim_department d
        ON e.department_key = d.department_key

    ORDER BY f.pay_period, d.department_name
    """

    df = con.execute(query).fetchdf()

    con.close()

    return df


df = load_payroll_data()

if df.empty:
    st.error("No payroll data found.")
    st.stop()

# -------------------------------
# FILTERS
# -------------------------------

st.sidebar.header("Dashboard Filters")

periods = sorted(df["pay_period"].dropna().unique())

selected_periods = st.sidebar.multiselect(
    "Select Payroll Month",
    periods,
    default=periods
)

departments = sorted(df["department_name"].dropna().unique())

selected_departments = st.sidebar.multiselect(
    "Select Department",
    departments,
    default=departments
)

filtered = df[
    df["pay_period"].isin(selected_periods)
    & df["department_name"].isin(selected_departments)
].copy()

if filtered.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# -------------------------------
# KPI CALCULATIONS
# -------------------------------

total_employees = filtered["employee_key"].nunique()

gross_total = filtered["gross_pay"].sum()
deductions_total = filtered["deductions"].sum()
net_total = filtered["net_pay"].sum()

average_gross = (
    gross_total / total_employees
    if total_employees else 0
)

average_net = (
    net_total / total_employees
    if total_employees else 0
)

# -------------------------------
# KPI DISPLAY
# -------------------------------

st.subheader("Payroll Overview")

c1, c2, c3 = st.columns(3)

c1.metric(
    "Total Gross Payroll",
    f"₹{gross_total:,.0f}"
)

c2.metric(
    "Total Deductions",
    f"₹{deductions_total:,.0f}"
)

c3.metric(
    "Total Net Payroll",
    f"₹{net_total:,.0f}"
)

c4, c5, c6 = st.columns(3)

c4.metric(
    "Employees",
    f"{total_employees:,}"
)

c5.metric(
    "Average Gross / Employee",
    f"₹{average_gross:,.2f}"
)

c6.metric(
    "Average Net / Employee",
    f"₹{average_net:,.2f}"
)

st.divider()

# -------------------------------
# DEPARTMENT SUMMARY
# -------------------------------

st.subheader("Department-wise Payroll")

department_summary = (
    filtered.groupby(
        ["department_name", "pay_period"]
    )
    .agg(
        employee_count=("employee_key", "nunique"),
        gross_pay=("gross_pay", "sum"),
        deductions=("deductions", "sum"),
        net_pay=("net_pay", "sum")
    )
    .reset_index()
)

# Privacy protection
department_summary = department_summary[
    department_summary["employee_count"] >= MIN_EMPLOYEES
].copy()

if not department_summary.empty:

    department_summary["cost_per_employee"] = (
        department_summary["gross_pay"]
        / department_summary["employee_count"]
    )

    display_summary = department_summary.rename(
        columns={
            "department_name": "Department",
            "pay_period": "Payroll Month",
            "employee_count": "Employees",
            "gross_pay": "Gross Payroll",
            "deductions": "Deductions",
            "net_pay": "Net Payroll",
            "cost_per_employee": "Gross Cost per Employee"
        }
    )

    st.dataframe(
        display_summary.style.format({
            "Gross Payroll": "₹{:,.2f}",
            "Deductions": "₹{:,.2f}",
            "Net Payroll": "₹{:,.2f}",
            "Gross Cost per Employee": "₹{:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

else:
    st.info("No department groups meet the minimum employee threshold.")

# -------------------------------
# DEPARTMENT COMPARISON
# -------------------------------

st.subheader("Department Payroll Comparison")

if not department_summary.empty:

    chart_data = department_summary.groupby(
        "department_name"
    )["gross_pay"].sum()

    st.bar_chart(chart_data)

# -------------------------------
# MONTHLY TREND
# -------------------------------

st.subheader("Monthly Payroll Trend")

monthly = (
    filtered.groupby("pay_period")
    .agg(
        gross_pay=("gross_pay", "sum"),
        deductions=("deductions", "sum"),
        net_pay=("net_pay", "sum")
    )
    .sort_index()
)

st.line_chart(monthly)

# -------------------------------
# PAYROLL RECONCILIATION
# -------------------------------

st.divider()

st.subheader("Payroll Reconciliation")

calculation_difference = (
    filtered["gross_pay"]
    - filtered["deductions"]
    - filtered["net_pay"]
)

mismatch_count = (
    calculation_difference.abs() > 0.01
).sum()

r1, r2, r3 = st.columns(3)

r1.metric(
    "Payroll Records",
    f"{len(filtered):,}"
)

r2.metric(
    "Calculation Mismatches",
    f"{mismatch_count:,}"
)

r3.metric(
    "Arithmetic Validation",
    "PASS" if mismatch_count == 0 else "REVIEW"
)

if mismatch_count == 0:
    st.success(
        "All selected payroll records satisfy "
        "Gross Pay - Deductions = Net Pay."
    )
else:
    st.error(
        "Some payroll records have calculation mismatches. "
        "Further investigation is required."
    )

st.info(
    "Official answer-key reconciliation is pending because "
    "unlock_PQ-09 has not been located. Arithmetic validation "
    "does not establish a match with the official answer key."
)

# -------------------------------
# EXCLUDED ROWS
# -------------------------------

st.subheader("Excluded Payroll Records")

st.write(
    "No payroll records have been excluded. "
    "The checks performed so far found no missing values, "
    "duplicate payroll IDs, negative amounts or arithmetic mismatches."
)

st.write(
    "Any future exclusion must have a documented validation reason."
)

# -------------------------------
# EMPLOYER COST
# -------------------------------

st.subheader("Employer Cost")

st.warning(
    "Employer cost is unavailable. "
    "The current fact_payroll and fact_salary tables "
    "do not contain employer contribution information."
)

# -------------------------------
# FINANCE COMMUNICATION
# -------------------------------

st.divider()

st.subheader("Finance Reconciliation Note")

st.write(
    "The payroll dataset passed the initial arithmetic and "
    "data-quality checks performed so far."
)

st.write(
    "No records have been excluded because no supported "
    "exclusion reason has been identified."
)

st.write(
    "Official reconciliation with the approved answer key "
    "remains pending, and employer contribution data is "
    "required to calculate total employer cost."
)

# -------------------------------
# FOOTER
# -------------------------------

st.divider()

st.caption(
    "Task 9 | Payroll Cost Dashboard | "
    "Data source: pulseiq.duckdb | "
    "Minimum displayed group size: 5 employees"
)