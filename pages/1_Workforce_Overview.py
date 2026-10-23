import streamlit as st
import duckdb
import plotly.express as px
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="PulseIQ Workforce Overview", layout="wide")

DB_PATH = Path(__file__).resolve().parents[1] / "pulseiq.duckdb"

st.title("PulseIQ - Workforce Overview")
st.caption("Workforce and headcount analytics")


@st.cache_data
def load_metrics(db_path):
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        headcount = con.execute("SELECT employee_count FROM metric_headcount").fetchdf()
        departments = con.execute("SELECT department, employee_count FROM metric_headcount_by_department ORDER BY employee_count DESC").fetchdf()
        department_count = con.execute("SELECT department_count FROM metric_department_count").fetchdf()
        monthly = con.execute("SELECT month_end, employee_count FROM metric_headcount_monthly ORDER BY month_end").fetchdf()
        return headcount, departments, department_count, monthly
    finally:
        con.close()


if not DB_PATH.exists():
    st.error(f"Database not found: {DB_PATH}")
    st.stop()

try:
    headcount, departments, department_count, monthly = load_metrics(str(DB_PATH))

    total_employees = int(headcount.iloc[0]["employee_count"]) if not headcount.empty else 0
    total_departments = int(department_count.iloc[0]["department_count"]) if not department_count.empty else 0

    col1, col2 = st.columns(2)
    col1.metric("Current Headcount", total_employees)
    col2.metric("Departments", total_departments)

    st.divider()
    st.subheader("Department Workforce Distribution")

    if not departments.empty:
        department_options = departments["department"].dropna().tolist()
        selected = st.multiselect("Filter by department", department_options, default=department_options)
        filtered = departments[departments["department"].isin(selected)]

        if not filtered.empty:
            fig = px.bar(filtered, x="department", y="employee_count", title="Employee Count by Department", labels={"department": "Department", "employee_count": "Employees"})
            st.plotly_chart(fig, use_container_width=True)

            largest = filtered.sort_values("employee_count", ascending=False).iloc[0]
            st.info(f"Insight: {largest['department']} has {int(largest['employee_count'])} employees among the selected departments.")
        else:
            st.warning("Select at least one department.")
    else:
        st.warning("No department data available.")

    st.divider()
    st.subheader("Monthly Headcount Trend")

    if not monthly.empty:
        monthly["month_end"] = pd.to_datetime(monthly["month_end"])
        min_date = monthly["month_end"].min().date()
        max_date = monthly["month_end"].max().date()

        date_range = st.date_input(
            "Select date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="headcount_date_range"
        )

        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_monthly = monthly[
                (monthly["month_end"].dt.date >= start_date)
                & (monthly["month_end"].dt.date <= end_date)
            ]

            if not filtered_monthly.empty:
                fig = px.line(filtered_monthly, x="month_end", y="employee_count", markers=True, title="Monthly Employee Headcount", labels={"month_end": "Month End", "employee_count": "Employees"})
                st.plotly_chart(fig, use_container_width=True)
                latest = int(filtered_monthly.iloc[-1]["employee_count"])
                st.info(f"Insight: Headcount was {latest} employees in the latest month within the selected date range.")
            else:
                st.warning("No headcount data for the selected date range.")
        else:
            st.info("Select both a start date and an end date.")
    else:
        st.warning("No monthly headcount data available.")

    st.caption("Data source: governed metric views.")

except Exception as exc:
    st.error(f"Dashboard error: {exc}")
