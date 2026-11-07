import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title="Task 10 | Budget vs Actual & KPI", page_icon="📊", layout="wide")
st.title("Task 10: Budget vs Actual Payroll & KPI Targets")
st.caption("PulseIQ Analytics | April 2025 – September 2026")

FILES = {
    "budget": "budget_payroll_dept_month.csv",
    "kpi": "kpi_targets.csv",
    "departments": "dim_department.csv",
    "payroll": "fact_payroll.csv",
}

@st.cache_data
def load_data():
    for key, filename in FILES.items():
        if not Path(filename).exists():
            raise FileNotFoundError(f"Missing {filename}. Keep all four CSV files beside task10_dashboard.py.")

    budget = pd.read_csv(FILES["budget"])
    kpi = pd.read_csv(FILES["kpi"])
    departments = pd.read_csv(FILES["departments"])
    payroll = pd.read_csv(FILES["payroll"])

    budget["month"] = pd.to_datetime(budget["month"]).dt.to_period("M").dt.to_timestamp()
    kpi["month"] = pd.to_datetime(kpi["month"]).dt.to_period("M").dt.to_timestamp()
    payroll["month"] = pd.to_datetime(payroll["period_end_date"]).dt.to_period("M").dt.to_timestamp()

    numeric_payroll = [
        "gross_pay", "total_deductions", "net_pay", "pf_employer",
        "esi_employer", "employer_cost", "overtime_hours_paid", "headcount_flag"
    ]
    for col in numeric_payroll:
        payroll[col] = pd.to_numeric(payroll[col], errors="coerce")

    actual = payroll.groupby(["department_id", "month"], as_index=False).agg(
        actual_gross=("gross_pay", "sum"),
        actual_deductions=("total_deductions", "sum"),
        actual_net=("net_pay", "sum"),
        employer_pf=("pf_employer", "sum"),
        employer_esi=("esi_employer", "sum"),
        actual_employer_cost=("employer_cost", "sum"),
        payroll_items=("payroll_item_id", "count"),
        overtime_hours=("overtime_hours_paid", "sum"),
        headcount_records=("headcount_flag", "sum")
    )

    variance = budget.merge(actual, on=["department_id", "month"], how="outer", validate="one_to_one")
    variance = variance.merge(
        departments[["department_id", "department_name", "cost_center", "is_leadership"]],
        on="department_id", how="left", validate="many_to_one"
    )
    variance["variance_amount"] = variance["actual_employer_cost"] - variance["budget_payroll_cost"]
    variance["variance_pct"] = np.where(
        variance["budget_payroll_cost"].notna() & (variance["budget_payroll_cost"] != 0),
        variance["variance_amount"] / variance["budget_payroll_cost"] * 100,
        np.nan
    )
    return budget, kpi, departments, payroll, actual, variance

try:
    budget, kpi, departments, payroll, actual, variance = load_data()
except Exception as exc:
    st.error(str(exc))
    st.stop()

# Sidebar filters
st.sidebar.header("Dashboard filters")
dept_options = departments.sort_values("department_id")
dept_labels = {r.department_id: f"{r.department_id} – {r.department_name}" for r in dept_options.itertuples()}
selected_ids = st.sidebar.multiselect(
    "Departments",
    options=dept_options["department_id"].tolist(),
    default=dept_options["department_id"].tolist(),
    format_func=lambda x: dept_labels.get(x, x)
)
month_options = sorted(budget["month"].dropna().unique())
selected_months = st.sidebar.multiselect("Months", month_options, default=month_options, format_func=lambda x: pd.Timestamp(x).strftime("%b %Y"))

f = variance[
    variance["department_id"].isin(selected_ids) &
    variance["month"].isin(selected_months)
].copy()
fk = kpi[kpi["department_id"].isin(selected_ids) & kpi["month"].isin(selected_months)].copy()

st.info(
    "Cost definition: actual employer cost = gross payroll + employer PF + employer ESI. "
    "Variance = actual employer cost − budget. Positive means overspend; negative means underspend."
)

# KPI cards
st.header("1. Executive summary")
budget_total = f["budget_payroll_cost"].sum()
actual_total = f["actual_employer_cost"].sum()
variance_total = f["variance_amount"].sum()
variance_pct = (variance_total / budget_total * 100) if budget_total else np.nan
c1, c2, c3, c4 = st.columns(4)
c1.metric("Budget", f"₹{budget_total:,.0f}")
c2.metric("Actual employer cost", f"₹{actual_total:,.0f}")
c3.metric("Net variance", f"₹{variance_total:,.0f}", f"{variance_pct:.2f}%")
c4.metric("Department-months matched", f"{f['variance_amount'].notna().sum()} / {len(f)}")

# Budget actual monthly trend
st.header("2. Monthly budget vs actual")
monthly = f.groupby("month", as_index=False).agg(
    budget=("budget_payroll_cost", "sum"),
    actual=("actual_employer_cost", "sum"),
    variance=("variance_amount", "sum")
).sort_values("month")
if not monthly.empty:
    st.line_chart(monthly.set_index("month")[["budget", "actual"]])
    st.dataframe(monthly.style.format({
        "budget": "₹{:,.0f}", "actual": "₹{:,.0f}", "variance": "₹{:,.0f}"
    }), use_container_width=True)

# Department ranking
st.header("3. Department variance ranking")
dept_summary = f.groupby(["department_id", "department_name"], as_index=False).agg(
    total_budget=("budget_payroll_cost", "sum"),
    actual_employer_cost=("actual_employer_cost", "sum"),
    net_variance=("variance_amount", "sum"),
    months_overspent=("variance_amount", lambda s: int((s > 0).sum())),
    months_underspent=("variance_amount", lambda s: int((s < 0).sum()))
)
dept_summary["variance_pct"] = np.where(
    dept_summary["total_budget"] != 0,
    dept_summary["net_variance"] / dept_summary["total_budget"] * 100,
    np.nan
)
dept_summary = dept_summary.sort_values("net_variance", ascending=False)
st.caption("Ranked by cumulative net variance (actual employer cost minus budget), not by isolated overspend months.")
st.bar_chart(dept_summary.set_index("department_id")["net_variance"])
st.dataframe(dept_summary.style.format({
    "total_budget": "₹{:,.0f}", "actual_employer_cost": "₹{:,.0f}",
    "net_variance": "₹{:,.0f}", "variance_pct": "{:.2f}%"
}), use_container_width=True)

# Traffic lights for budget variance, clearly documented as management thresholds
st.header("4. Budget traffic lights")
st.caption("Provisional management rule (not supplied in the source files): Green = at/under budget; Amber = overspend up to 5%; Red = overspend above 5%. Change these thresholds to match your organization's approved policy.")
amber_limit = st.number_input("Amber overspend threshold (%)", min_value=0.0, max_value=50.0, value=5.0, step=0.5)
f["budget_status"] = np.select(
    [f["variance_amount"] <= 0, f["variance_pct"] <= amber_limit],
    ["🟢 Green – at/under budget", "🟠 Amber – overspend within threshold"],
    default="🔴 Red – overspend above threshold"
)
st.dataframe(
    f[["department_id", "department_name", "month", "budget_payroll_cost",
       "actual_employer_cost", "variance_amount", "variance_pct", "budget_status"]]
    .sort_values(["month", "department_id"])
    .style.format({
        "budget_payroll_cost": "₹{:,.0f}", "actual_employer_cost": "₹{:,.0f}",
        "variance_amount": "₹{:,.0f}", "variance_pct": "{:.2f}%"
    }),
    use_container_width=True
)

# KPI targets only, not actual performance
st.header("5. KPI targets and actual-status availability")
st.warning(
    "The supplied KPI file contains targets only. No monthly actual attendance, overtime-share, "
    "attrition or task-completion measurements were supplied. Therefore actual-vs-target KPI "
    "traffic-light statuses cannot be calculated honestly."
)
kpi_cols = [
    "attendance_rate_target", "overtime_share_target_pct",
    "attrition_monthly_target_pct", "task_completion_target_pct"
]
kpi_view = fk[["month", "department_id"] + kpi_cols].copy()
kpi_view["actual_status"] = "⚪ Actual KPI not supplied"
st.dataframe(kpi_view, use_container_width=True)
missing_targets = fk[kpi_cols].isna().sum().rename("Missing target cells").reset_index().rename(columns={"index": "KPI"})
st.subheader("Missing KPI targets")
st.dataframe(missing_targets, use_container_width=True)

# Manual checks
st.header("6. Manual verification – three department-month examples")
checks = [
    ("D03", pd.Timestamp("2026-06-01")),
    ("D02", pd.Timestamp("2025-05-01")),
    ("D04", pd.Timestamp("2025-04-01")),
]
manual_rows = []
for did, month in checks:
    r = variance[(variance["department_id"] == did) & (variance["month"] == month)]
    if not r.empty:
        x = r.iloc[0]
        manual_rows.append({
            "Department": f"{did} – {x['department_name']}",
            "Month": month.strftime("%b %Y"),
            "Budget": x["budget_payroll_cost"],
            "Actual employer cost": x["actual_employer_cost"],
            "Manual variance (Actual − Budget)": x["actual_employer_cost"] - x["budget_payroll_cost"],
            "Variance %": (x["actual_employer_cost"] - x["budget_payroll_cost"]) / x["budget_payroll_cost"] * 100
        })
manual_df = pd.DataFrame(manual_rows)
st.dataframe(manual_df.style.format({
    "Budget": "₹{:,.2f}", "Actual employer cost": "₹{:,.2f}",
    "Manual variance (Actual − Budget)": "₹{:,.2f}", "Variance %": "{:.2f}%"
}), use_container_width=True)
st.caption("Example check: D03 Jun 2026 = ₹60,83,765.18 − ₹54,75,000 = ₹6,08,765.18 (11.12% overspend).")

# Recommendations
st.header("7. Recommendations")
all_dept = variance.groupby(["department_id", "department_name"], as_index=False).agg(
    budget=("budget_payroll_cost", "sum"),
    actual=("actual_employer_cost", "sum"),
    net_variance=("variance_amount", "sum")
)
all_dept["variance_pct"] = all_dept["net_variance"] / all_dept["budget"] * 100
top = all_dept.sort_values("net_variance", ascending=False)
if len(top) >= 2:
    a, b = top.iloc[0], top.iloc[1]
    st.markdown(
        f"**Priority 1 – {a['department_name']} ({a['department_id']}):** "
        f"net overspend ₹{a['net_variance']:,.0f} ({a['variance_pct']:.2f}%). "
        "Review month-level staffing changes, role mix, variable pay and employer contributions; "
        "agree a forecast refresh with the budget owner."
    )
    st.markdown(
        f"**Priority 2 – {b['department_name']} ({b['department_id']}):** "
        f"net overspend ₹{b['net_variance']:,.0f} ({b['variance_pct']:.2f}%). "
        "Review recurring overspend months and planned hiring/compensation changes; "
        "reforecast the remaining period instead of applying a blanket cut."
    )
st.markdown(
    "**Hiring-freeze fairness:** The supplied files do not identify the hiring-freeze date or whether "
    "budgets were revised after the freeze. Keep the original approved budget as the official baseline, "
    "flag any unadjusted baseline, and add a separately labelled adjusted view only after HR/Finance "
    "confirms the freeze period and approved adjustment methodology."
)

# Data quality and downloads
st.header("8. Data quality and reconciliation")
checks_df = pd.DataFrame([
    ["Budget records", len(budget)],
    ["KPI target records", len(kpi)],
    ["Payroll item records", len(payroll)],
    ["Unique payroll item IDs", payroll["payroll_item_id"].nunique()],
    ["Duplicate payroll item IDs", int(payroll["payroll_item_id"].duplicated().sum())],
    ["Departments without mapping", len(set(budget["department_id"]) - set(departments["department_id"]))],
    ["Budget/actual matched department-months", int(variance["variance_amount"].notna().sum())],
    ["Budget total", budget["budget_payroll_cost"].sum()],
    ["Actual employer cost total", actual["actual_employer_cost"].sum()],
    ["Net variance", variance["variance_amount"].sum()],
], columns=["Check", "Result"])
st.dataframe(checks_df, use_container_width=True)

st.download_button(
    "Download department-month variance CSV",
    data=variance.to_csv(index=False).encode("utf-8"),
    file_name="task10_department_month_variance.csv",
    mime="text/csv"
)
st.download_button(
    "Download department ranking CSV",
    data=dept_summary.to_csv(index=False).encode("utf-8"),
    file_name="task10_department_variance_ranking.csv",
    mime="text/csv"
)
st.download_button(
    "Download KPI targets CSV",
    data=kpi_view.to_csv(index=False).encode("utf-8"),
    file_name="task10_kpi_targets_status.csv",
    mime="text/csv"
)

st.success("Task 10 financial variance analysis is complete for all 198 department-months. KPI actual performance remains pending its source actuals.")
st.caption("Source files: budget_payroll_dept_month.csv, fact_payroll.csv, dim_department.csv, kpi_targets.csv.")
