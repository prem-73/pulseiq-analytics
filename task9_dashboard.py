import streamlit as st
import duckdb
import pandas as pd
from pathlib import Path

DB_PATH = "pulseiq.duckdb"
ANSWER_KEY_PATH = "unlock_PQ-09_reconciliation_answer_key.csv"
MIN_EMPLOYEES = 5

st.set_page_config(
    page_title="Task 9 - Payroll Cost & Reconciliation",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Payroll Cost Dashboard")
st.caption("Task 9 | Department Payroll, Employer Cost & Official Reconciliation")

@st.cache_data
def load_local_payroll():
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
    """
    data = con.execute(query).fetchdf()
    con.close()
    return data

@st.cache_data
def load_answer_key():
    path = Path(ANSWER_KEY_PATH)
    if not path.exists():
        return None
    data = pd.read_csv(path)
    data["month"] = pd.to_datetime(data["month"]).dt.to_period("M").astype(str)
    return data

try:
    local = load_local_payroll()
except Exception as exc:
    st.error(f"Could not load local payroll data: {exc}")
    st.stop()

if local.empty:
    st.warning("No local payroll records were found.")
    st.stop()

local["pay_period"] = local["pay_period"].astype(str)
answer = load_answer_key()

# Sidebar filters
st.sidebar.header("Dashboard Filters")
period_options = sorted(local["pay_period"].dropna().unique())
selected_periods = st.sidebar.multiselect(
    "Local payroll month",
    period_options,
    default=period_options
)
department_options = sorted(local["department_name"].dropna().unique())
selected_departments = st.sidebar.multiselect(
    "Department",
    department_options,
    default=department_options
)

filtered = local[
    local["pay_period"].isin(selected_periods)
    & local["department_name"].isin(selected_departments)
].copy()

if filtered.empty:
    st.warning("No local payroll records match the selected filters.")
    st.stop()

# Local payroll KPIs
st.header("1. Local Payroll Overview")
employees = filtered["employee_key"].nunique()
gross = filtered["gross_pay"].sum()
deductions = filtered["deductions"].sum()
net = filtered["net_pay"].sum()
avg_gross = gross / employees if employees else 0
avg_net = net / employees if employees else 0

a, b, c = st.columns(3)
a.metric("Gross Payroll", f"₹{gross:,.2f}")
b.metric("Deductions", f"₹{deductions:,.2f}")
c.metric("Net Payroll", f"₹{net:,.2f}")

a, b, c = st.columns(3)
a.metric("Employees Paid", f"{employees:,}")
b.metric("Average Gross / Employee", f"₹{avg_gross:,.2f}")
c.metric("Average Net / Employee", f"₹{avg_net:,.2f}")

# Department table with minimum group-size protection
st.subheader("Department-wise Monthly Payroll")
dept = (
    filtered.groupby(["pay_period", "department_name"])
    .agg(
        employee_count=("employee_key", "nunique"),
        gross_pay=("gross_pay", "sum"),
        deductions=("deductions", "sum"),
        net_pay=("net_pay", "sum")
    )
    .reset_index()
)
dept = dept[dept["employee_count"] >= MIN_EMPLOYEES].copy()
if dept.empty:
    st.info(f"No department-month group meets the minimum size of {MIN_EMPLOYEES}.")
else:
    dept["gross_cost_per_employee"] = dept["gross_pay"] / dept["employee_count"]
    dept_display = dept.rename(columns={
        "pay_period": "Month",
        "department_name": "Department",
        "employee_count": "Employees",
        "gross_pay": "Gross Payroll",
        "deductions": "Deductions",
        "net_pay": "Net Payroll",
        "gross_cost_per_employee": "Average Gross per Employee"
    })
    st.dataframe(
        dept_display.style.format({
            "Gross Payroll": "₹{:,.2f}",
            "Deductions": "₹{:,.2f}",
            "Net Payroll": "₹{:,.2f}",
            "Average Gross per Employee": "₹{:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )
    st.subheader("Department Gross Payroll Comparison")
    st.bar_chart(dept.groupby("department_name")["gross_pay"].sum())

st.subheader("Local Monthly Payroll Trend")
monthly_local = (
    filtered.groupby("pay_period")
    .agg(
        gross_pay=("gross_pay", "sum"),
        deductions=("deductions", "sum"),
        net_pay=("net_pay", "sum")
    )
    .sort_index()
)
st.line_chart(monthly_local)

# Arithmetic checks on local data
st.header("2. Local Payroll Validation")
diff = filtered["gross_pay"] - filtered["deductions"] - filtered["net_pay"]
mismatch_count = int((diff.abs() > 0.01).sum())
missing_count = int(filtered[
    ["payroll_id", "employee_key", "pay_period", "gross_pay", "deductions", "net_pay"]
].isna().any(axis=1).sum())
duplicate_ids = int(filtered["payroll_id"].duplicated().sum())
negative_amount_rows = int(
    ((filtered[["gross_pay", "deductions", "net_pay"]] < 0).any(axis=1)).sum()
)

x, y, z, w = st.columns(4)
x.metric("Rows Checked", f"{len(filtered):,}")
y.metric("Arithmetic Mismatches", f"{mismatch_count:,}")
z.metric("Rows with Missing Values", f"{missing_count:,}")
w.metric("Duplicate Payroll IDs", f"{duplicate_ids:,}")

if mismatch_count == 0 and missing_count == 0 and duplicate_ids == 0 and negative_amount_rows == 0:
    st.success("Selected local payroll rows passed the displayed validation checks.")
else:
    st.warning("Review local payroll validation exceptions before reconciliation.")

# Official answer-key reconciliation
st.header("3. Official Answer-Key Reconciliation")

if answer is None:
    st.error(
        f"Answer key not found: {ANSWER_KEY_PATH}. "
        "Place the supplied CSV beside task9_dashboard.py."
    )
else:
    st.caption(
        f"Official answer-key coverage: {answer['month'].min()} to {answer['month'].max()} "
        f"({len(answer)} monthly records)."
    )

    answer_total_gross = answer["payroll_gross_pay"].sum()
    answer_total_net = answer["payroll_net_pay"].sum()
    answer_total_employer = answer["payroll_employer_cost"].sum()
    answer_total_ledger = answer["ledger_salary_related_expense"].sum()
    answer_total_variance = answer["payroll_vs_ledger_difference"].sum()
    employer_contribution = answer_total_employer - answer_total_gross

    k1, k2, k3 = st.columns(3)
    k1.metric("Official Gross Payroll (18 months)", f"₹{answer_total_gross:,.2f}")
    k2.metric("Official Net Payroll (18 months)", f"₹{answer_total_net:,.2f}")
    k3.metric("Official Employer Cost (18 months)", f"₹{answer_total_employer:,.2f}")

    k1, k2, k3 = st.columns(3)
    k1.metric("Employer Contribution (18 months)", f"₹{employer_contribution:,.2f}")
    k2.metric("Ledger Salary Expense (18 months)", f"₹{answer_total_ledger:,.2f}")
    k3.metric("Payroll vs Ledger Difference", f"₹{answer_total_variance:,.2f}")

    # Month-by-month answer-key reconciliation
    recon = answer[[
        "month",
        "payroll_gross_pay",
        "payroll_net_pay",
        "payroll_employer_cost",
        "ledger_salary_related_expense",
        "payroll_vs_ledger_difference"
    ]].copy()
    recon["reconciliation_status"] = recon["payroll_vs_ledger_difference"].abs().le(0.01).map(
        {True: "RECONCILED", False: "REVIEW"}
    )
    st.subheader("Official Monthly Payroll-to-Ledger Reconciliation")
    st.dataframe(
        recon.rename(columns={
            "month": "Month",
            "payroll_gross_pay": "Gross Payroll",
            "payroll_net_pay": "Net Payroll",
            "payroll_employer_cost": "Employer Cost",
            "ledger_salary_related_expense": "Ledger Salary Expense",
            "payroll_vs_ledger_difference": "Difference",
            "reconciliation_status": "Status"
        }).style.format({
            "Gross Payroll": "₹{:,.2f}",
            "Net Payroll": "₹{:,.2f}",
            "Employer Cost": "₹{:,.2f}",
            "Ledger Salary Expense": "₹{:,.2f}",
            "Difference": "₹{:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )

    reconciled_months = int(recon["reconciliation_status"].eq("RECONCILED").sum())
    review_months = len(recon) - reconciled_months
    r1, r2 = st.columns(2)
    r1.metric("Months Reconciled", f"{reconciled_months} / {len(recon)}")
    r2.metric("Months Requiring Review", f"{review_months}")

    if review_months == 0:
        st.success("All official answer-key months reconcile: payroll employer cost equals ledger salary-related expense.")
    else:
        st.warning("One or more official answer-key months have a non-zero payroll-to-ledger difference.")

    st.subheader("Official Employer Cost Trend")
    employer_trend = answer.set_index("month")[[
        "payroll_gross_pay",
        "payroll_employer_cost",
        "ledger_salary_related_expense"
    ]]
    st.line_chart(employer_trend)

    # Compare only months present in both local data and answer key
    local_monthly = (
        local.groupby("pay_period")
        .agg(
            local_gross=("gross_pay", "sum"),
            local_net=("net_pay", "sum")
        )
        .reset_index()
        .rename(columns={"pay_period": "month"})
    )
    overlap = local_monthly.merge(
        answer[["month", "payroll_gross_pay", "payroll_net_pay"]],
        on="month",
        how="inner"
    )

    st.subheader("Local Database vs Official Answer Key")
    if overlap.empty:
        st.info(
            "No overlapping months exist between the current local fact_payroll data "
            "and the official answer key. The local database currently contains October 2026, "
            "while the supplied answer key covers April 2025 through September 2026. "
            "Therefore a direct month-level comparison cannot be performed yet."
        )
    else:
        overlap["gross_difference"] = overlap["local_gross"] - overlap["payroll_gross_pay"]
        overlap["net_difference"] = overlap["local_net"] - overlap["payroll_net_pay"]
        st.dataframe(overlap, use_container_width=True, hide_index=True)

    st.subheader("Excluded Payroll Records")
    st.write(
        "No records have been excluded from the local payroll dataset. "
        "The initial checks found no arithmetic mismatches, missing required values, "
        "duplicate payroll IDs, or negative pay amounts. Official answer-key differences "
        "must be investigated before excluding any row."
    )

# Employer-cost scope note
st.header("4. Employer Cost – Data Scope")
st.info(
    "Employer cost is available in the official reconciliation answer key for April 2025 "
    "through September 2026. The local fact_payroll and fact_salary tables do not contain "
    "an employer contribution field, so employer cost cannot be derived for the local "
    "October 2026 payroll from those tables alone."
)

st.header("5. Finance Summary")
st.write(
    "The supplied official answer key contains 18 monthly records from April 2025 "
    "through September 2026. Payroll employer cost and ledger salary-related expense "
    "reconcile to a zero reported difference across those months."
)
st.write(
    "The current local payroll database contains October 2026 records and passes the "
    "initial arithmetic and data-quality checks performed. A direct comparison with the "
    "answer key is not possible because the month ranges do not overlap."
)
st.write(
    "Employer cost for the local October 2026 records remains uncalculated until an "
    "authoritative employer contribution amount or rate is supplied."
)

st.divider()
st.caption(
    "Task 9 | Payroll Cost & Reconciliation | "
    f"Department privacy threshold: at least {MIN_EMPLOYEES} employees"
)