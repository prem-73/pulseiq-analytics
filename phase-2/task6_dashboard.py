import duckdb
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="PulseIQ - Attendance & Leave",
    page_icon="📊",
    layout="wide"
)

st.title("PulseIQ Analytics")
st.subheader("Task 6: Attendance and Leave Trends")

con = duckdb.connect("pulseiq.duckdb", read_only=True)

# Load attendance records
attendance = con.execute("""
    SELECT
        TRY_CAST(attendance_id AS BIGINT) AS attendance_id,
        TRY_CAST(employee_id AS BIGINT) AS employee_id,
        TRY_CAST(attendance_date AS DATE) AS attendance_date,
        status,
        TRY_CAST(hours_worked AS DOUBLE) AS hours_worked
    FROM attendance
""").fetchdf()

# Load current employee department mapping
employees = con.execute("""
    SELECT
        employee_id,
        employee_name,
        department_key
    FROM dim_employee
    WHERE is_current = TRUE
""").fetchdf()

departments = con.execute("""
    SELECT department_key, department_name
    FROM dim_department
""").fetchdf()

# Load leave records
leaves = con.execute("""
    SELECT
        TRY_CAST(employee_id AS BIGINT) AS employee_id,
        TRY_CAST(start_date AS DATE) AS start_date,
        TRY_CAST(end_date AS DATE) AS end_date,
        leave_type,
        status
    FROM "leave"
""").fetchdf()

con.close()

# Join department information
attendance = attendance.merge(
    employees[["employee_id", "department_key"]],
    on="employee_id",
    how="left"
)

attendance = attendance.merge(
    departments,
    on="department_key",
    how="left"
)

leaves = leaves.merge(
    employees[["employee_id", "department_key"]],
    on="employee_id",
    how="left"
)

leaves = leaves.merge(
    departments,
    on="department_key",
    how="left"
)

attendance["attendance_date"] = pd.to_datetime(
    attendance["attendance_date"], errors="coerce"
)

attendance["month"] = attendance["attendance_date"].dt.to_period(
    "M"
).astype(str)

# Sidebar filters
st.sidebar.header("Filters")

department_options = sorted(
    attendance["department_name"].dropna().unique().tolist()
)

selected_departments = st.sidebar.multiselect(
    "Department",
    department_options,
    default=department_options
)

filtered = attendance[
    attendance["department_name"].isin(selected_departments)
].copy()

if filtered.empty:
    st.warning("No attendance records for the selected department.")
    st.stop()

# KPI calculations
total_records = len(filtered)

present_count = (
    filtered["status"].str.lower() == "present"
).sum()

absent_count = (
    filtered["status"].str.lower() == "absent"
).sum()

leave_count = (
    filtered["status"].str.lower() == "leave"
).sum()

# This is a record-based rate, not yet a validated working-day rate.
attendance_rate = (
    present_count / total_records * 100
    if total_records else 0
)

total_hours = filtered["hours_worked"].sum()

col1, col2, col3, col4 = st.columns(4)

col1.metric("Attendance Records", total_records)
col2.metric("Present Records", int(present_count))
col3.metric("Absent Records", int(absent_count))
col4.metric("Record-Based Present Rate", f"{attendance_rate:.1f}%")

st.caption(
    "The present rate above uses present records divided by all attendance "
    "records. Validate scheduled working days and holidays before reporting "
    "it as the official attendance rate."
)

st.metric("Total Recorded Hours", f"{total_hours:,.1f}")

# Monthly attendance chart
st.subheader("Monthly Attendance by Department")

monthly = (
    filtered.groupby(["month", "department_name", "status"])
    .size()
    .reset_index(name="records")
)

present_monthly = monthly[
    monthly["status"].str.lower() == "present"
]

fig = px.bar(
    present_monthly,
    x="month",
    y="records",
    color="department_name",
    barmode="group",
    title="Present Records by Month and Department"
)

st.plotly_chart(fig, use_container_width=True)

# Department status comparison
st.subheader("Attendance Status by Department")

department_status = (
    filtered.groupby(["department_name", "status"])
    .size()
    .reset_index(name="records")
)

fig2 = px.bar(
    department_status,
    x="department_name",
    y="records",
    color="status",
    barmode="group",
    title="Present, Absent and Leave Records"
)

st.plotly_chart(fig2, use_container_width=True)

# Leave trends
st.subheader("Leave Patterns by Type")

filtered_leaves = leaves[
    leaves["department_name"].isin(selected_departments)
].copy()

if not filtered_leaves.empty:
    leave_summary = (
        filtered_leaves.groupby(["leave_type", "status"])
        .size()
        .reset_index(name="requests")
    )

    fig3 = px.bar(
        leave_summary,
        x="leave_type",
        y="requests",
        color="status",
        barmode="group",
        title="Leave Requests by Type and Status"
    )

    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No leave records found for the selected departments.")

# Overtime and late-arrival limitations
st.subheader("Late Arrivals and Overtime")

st.info(
    "The current attendance table contains status and hours_worked, "
    "but no arrival timestamp or explicit overtime field. "
    "Late arrivals and overtime cannot be reliably calculated until "
    "the relevant source fields and business rules are available."
)

# Data table
with st.expander("View filtered attendance records"):
    st.dataframe(filtered, use_container_width=True)

st.success("Attendance and leave dashboard loaded successfully.")