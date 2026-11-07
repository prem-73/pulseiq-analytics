import duckdb
import streamlit as st
import plotly.express as px
import pandas as pd

st.set_page_config(
    page_title="PulseIQ Team Productivity",
    layout="wide"
)

st.title("PulseIQ - Team Productivity Dashboard")
st.caption("Task 8 | Synthetic Sample Data | 16 Teams | 38 Sprints")

con = duckdb.connect("task8_sample.duckdb", read_only=True)

# Load team and sprint details
teams = con.execute(
    "SELECT * FROM dim_team ORDER BY team_name"
).fetchdf()

sprints = con.execute(
    "SELECT * FROM dim_sprint ORDER BY sprint_id"
).fetchdf()

# Load aggregated metrics
metrics = con.execute(
    "SELECT * FROM metric_team_sprint"
).fetchdf()

# Load task-level data for manual verification
tasks = con.execute(
    "SELECT * FROM fact_task"
).fetchdf()

con.close()

# ------------------------------------------------
# Rules
# ------------------------------------------------

st.header("1. Metric Definitions and Rules")

with st.expander("View metric calculation rules", expanded=True):
    st.markdown("""
    - **Velocity:** Total story points from completed tasks.
    - **Cycle Time:** Days between started_at and completed_at.
    - **On-time Rate:** Completed tasks finished on or before due_date,
      divided by all completed tasks.
    - **Blocked Work:** Tasks whose current status is Blocked.
    - **Reopened Work:** Tasks with reopen_count greater than zero.
    - **Cancelled Tasks:** Excluded from velocity and on-time calculations.
    - **Privacy:** Groups smaller than 5 are suppressed.
    """)

st.warning(
    "This dashboard uses synthetic sample data. "
    "It does not represent actual company team performance."
)

# ------------------------------------------------
# Filters
# ------------------------------------------------

st.header("2. Team and Sprint Selection")

col1, col2 = st.columns(2)

with col1:
    team_options = ["All Teams"] + teams["team_name"].tolist()
    selected_team = st.selectbox("Select Team", team_options)

with col2:
    sprint_options = ["All Sprints"] + sprints["sprint_name"].tolist()
    selected_sprint = st.selectbox("Select Sprint", sprint_options)

filtered = metrics.copy()

if selected_team != "All Teams":
    filtered = filtered[
        filtered["team_name"] == selected_team
    ]

if selected_sprint != "All Sprints":
    filtered = filtered[
        filtered["sprint_name"] == selected_sprint
    ]

# ------------------------------------------------
# KPI Cards
# ------------------------------------------------

st.header("3. Productivity KPIs")

total_tasks = int(filtered["total_tasks"].sum())
completed = int(filtered["completed_tasks"].sum())
velocity = int(filtered["velocity"].sum())
blocked = int(filtered["blocked_tasks"].sum())
reopened = int(filtered["reopened_tasks"].sum())

cycle_time = filtered["avg_cycle_time_days"].mean()

completed_rows = filtered["completed_tasks"].sum()

if completed_rows > 0:
    on_time = (
        filtered["on_time_rate_pct"].fillna(0)
        * filtered["completed_tasks"]
    ).sum() / completed_rows
else:
    on_time = 0

c1, c2, c3 = st.columns(3)
c4, c5, c6 = st.columns(3)

c1.metric("Total Tasks", f"{total_tasks:,}")
c2.metric("Completed Tasks", f"{completed:,}")
c3.metric("Velocity", f"{velocity:,} points")
c4.metric("Average Cycle Time", f"{cycle_time:.2f} days" if pd.notna(cycle_time) else "N/A")
c5.metric("On-time Rate", f"{on_time:.2f}%")
c6.metric("Blocked Tasks", f"{blocked:,}")

st.metric("Reopened Tasks", f"{reopened:,}")

# ------------------------------------------------
# Team comparison
# ------------------------------------------------

st.header("4. Team-wise Productivity")

team_summary = (
    metrics.groupby(["team_id", "team_name", "team_size"])
    .agg(
        total_velocity=("velocity", "sum"),
        completed_tasks=("completed_tasks", "sum"),
        blocked_tasks=("blocked_tasks", "sum"),
        reopened_tasks=("reopened_tasks", "sum"),
        cycle_time=("avg_cycle_time_days", "mean"),
        on_time_rate=("on_time_rate_pct", "mean")
    )
    .reset_index()
)

team_summary["velocity_per_member"] = (
    team_summary["total_velocity"] / team_summary["team_size"]
)

fig = px.bar(
    team_summary,
    x="team_name",
    y="total_velocity",
    title="Team-wise Velocity",
    labels={
        "team_name": "Team",
        "total_velocity": "Velocity (Story Points)"
    }
)

st.plotly_chart(fig, use_container_width=True)

fig = px.bar(
    team_summary,
    x="team_name",
    y="on_time_rate",
    title="Team-wise On-time Delivery Rate",
    labels={
        "team_name": "Team",
        "on_time_rate": "On-time Rate (%)"
    }
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------
# Sprint comparison
# ------------------------------------------------

st.header("5. Sprint-wise Performance")

sprint_summary = (
    metrics.groupby(["sprint_id", "sprint_name"])
    .agg(
        velocity=("velocity", "sum"),
        completed_tasks=("completed_tasks", "sum"),
        blocked_tasks=("blocked_tasks", "sum"),
        reopened_tasks=("reopened_tasks", "sum")
    )
    .reset_index()
    .sort_values("sprint_id")
)

fig = px.line(
    sprint_summary,
    x="sprint_name",
    y="velocity",
    markers=True,
    title="Velocity Across 38 Sprints"
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------
# Blocked and reopened work
# ------------------------------------------------

st.header("6. Blocked and Reopened Work")

risk_summary = team_summary[
    ["team_name", "blocked_tasks", "reopened_tasks"]
]

fig = px.bar(
    risk_summary,
    x="team_name",
    y=["blocked_tasks", "reopened_tasks"],
    barmode="group",
    title="Blocked vs Reopened Tasks by Team"
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------
# Manual verification
# ------------------------------------------------

st.header("7. Manual Verification - Two Teams")

verification_teams = teams["team_name"].head(2).tolist()

verification = []

for team_name in verification_teams:
    team_id = int(
        teams.loc[
            teams["team_name"] == team_name,
            "team_id"
        ].iloc[0]
    )

    team_tasks = tasks[tasks["team_id"] == team_id]

    completed_tasks = team_tasks[
        team_tasks["status"] == "Completed"
    ]

    manual_velocity = int(
        completed_tasks["story_points"].sum()
    )

    manual_blocked = int(
        (team_tasks["status"] == "Blocked").sum()
    )

    manual_reopened = int(
        (team_tasks["reopen_count"] > 0).sum()
    )

    metric_row = team_summary[
        team_summary["team_name"] == team_name
    ].iloc[0]

    verification.append({
        "Team": team_name,
        "Manual Velocity": manual_velocity,
        "Dashboard Velocity": int(metric_row["total_velocity"]),
        "Manual Blocked": manual_blocked,
        "Dashboard Blocked": int(metric_row["blocked_tasks"]),
        "Manual Reopened": manual_reopened,
        "Dashboard Reopened": int(metric_row["reopened_tasks"])
    })

verification_df = pd.DataFrame(verification)

st.dataframe(
    verification_df,
    use_container_width=True,
    hide_index=True
)

st.success(
    "Manual verification compares task-level calculations "
    "with dashboard team aggregates."
)

# ------------------------------------------------
# Findings
# ------------------------------------------------

st.header("8. Three Team Health Findings")

highest_velocity = team_summary.loc[
    team_summary["total_velocity"].idxmax()
]

highest_blocked = team_summary.loc[
    team_summary["blocked_tasks"].idxmax()
]

highest_reopened = team_summary.loc[
    team_summary["reopened_tasks"].idxmax()
]

st.markdown(
    f"**Finding 1:** {highest_velocity['team_name']} has the "
    f"highest total velocity: {int(highest_velocity['total_velocity'])} points."
)

st.markdown(
    f"**Finding 2:** {highest_blocked['team_name']} has the "
    f"highest blocked workload: {int(highest_blocked['blocked_tasks'])} tasks."
)

st.markdown(
    f"**Finding 3:** {highest_reopened['team_name']} has the "
    f"highest reopened workload: {int(highest_reopened['reopened_tasks'])} tasks."
)

st.header("9. Fair Team Comparison")

st.write("""
A team with the highest velocity is not automatically the healthiest team.
Team size, work type, sprint duration, blocked work, and reopened tasks
must also be considered.

Velocity per team member provides additional context, but does not
fully adjust for work complexity.
""")

st.header("10. Team Performance Table")

st.dataframe(
    team_summary,
    use_container_width=True,
    hide_index=True
)

st.success("Task 8 Team Productivity Dashboard loaded successfully.")

