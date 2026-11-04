import duckdb
import pandas as pd
import streamlit as st
import subprocess
import sys
from pathlib import Path

st.set_page_config(
    page_title="PulseIQ Executive Scorecard",
    page_icon="📊",
    layout="wide"
)

DB = "pulseiq.duckdb"

st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}
.kpi-card {
    border: 1px solid #555;
    border-radius: 8px;
    padding: 12px;
    min-height: 125px;
}
.kpi-label {
    font-size: 13px;
    color: #aaa;
}
.kpi-value {
    font-size: 25px;
    font-weight: bold;
    margin: 8px 0;
}
.kpi-detail {
    font-size: 11px;
    color: #aaa;
}
@media print {
    @page {
        size: A4 landscape;
        margin: 8mm;
    }
    header, footer, [data-testid="stSidebar"],
    [data-testid="stToolbar"], .stButton,
    [data-testid="stHeader"] {
        display: none !important;
    }
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    .kpi-card {
        break-inside: avoid;
    }
    h1 { font-size: 22px !important; }
    h2 { font-size: 17px !important; }
}
</style>
""", unsafe_allow_html=True)

st.title("📊 PulseIQ | Executive Company Health")
st.caption("Task 15 | Executive KPI Scorecard | Governed Metric Layer")

if not Path(DB).exists():
    st.error("pulseiq.duckdb not found.")
    st.stop()


@st.cache_data
def load_data():
    con = duckdb.connect(DB, read_only=True)

    metrics = {
        "Headcount": ("metric_headcount", "employee_count"),
        "Gross Payroll": ("metric_payroll_gross_total", "gross_pay_total"),
        "Net Payroll": ("metric_payroll_net_total", "net_pay_total"),
        "Attendance Rate": ("metric_attendance_rate", "attendance_rate_pct"),
        "Approved Leaves": ("metric_approved_leaves", "approved_leaves"),
        "Leave Requests": ("metric_leave_requests", "leave_requests"),
        "Salary Total": ("metric_salary_total", "salary_total"),
        "Hours Worked": ("metric_hours_worked_total", "total_hours_worked")
    }

    values = {}
    for name, (view, column) in metrics.items():
        values[name] = con.execute(
            f"SELECT {column} FROM {view}"
        ).fetchone()[0]

    headcount_monthly = con.execute("""
        SELECT month_end, employee_count
        FROM metric_headcount_monthly
        ORDER BY month_end
    """).df()

    payroll_monthly = con.execute("""
        SELECT pay_period, gross_pay, net_pay
        FROM metric_payroll_by_period
        ORDER BY pay_period
    """).df()

    targets = con.execute("""
        SELECT month, AVG(attendance_rate_target) AS target
        FROM kpi_targets
        GROUP BY month
        ORDER BY month
    """).df()

    con.close()
    return values, headcount_monthly, payroll_monthly, targets


try:
    values, headcount_monthly, payroll_monthly, targets = load_data()
except Exception as error:
    st.error(f"Metric loading failed: {error}")
    st.stop()


# Reporting month selector
months = sorted(
    set(payroll_monthly["pay_period"].astype(str))
    | set(pd.to_datetime(headcount_monthly["month_end"]).dt.strftime("%Y-%m"))
)

selected_month = st.selectbox(
    "Reporting month",
    months,
    index=len(months) - 1
) if months else None

# Monthly values, where available
monthly_headcount = headcount_monthly[
    pd.to_datetime(headcount_monthly["month_end"]).dt.strftime("%Y-%m")
    == selected_month
] if selected_month else pd.DataFrame()

monthly_payroll = payroll_monthly[
    payroll_monthly["pay_period"].astype(str) == selected_month
] if selected_month else pd.DataFrame()

# Attendance target
attendance_target = None
if selected_month and not targets.empty:
    match = targets[
        pd.to_datetime(targets["month"]).dt.strftime("%Y-%m")
        == selected_month
    ]
    if not match.empty:
        attendance_target = float(match.iloc[0]["target"]) * 100


def money(value):
    return f"₹{value:,.2f}" if pd.notna(value) else "N/A"


def number(value):
    return f"{value:,.0f}" if pd.notna(value) else "N/A"


def card(label, value, target, status, source, note):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-detail">Target: {target}</div>
        <div class="kpi-detail">Status: {status}</div>
        <div class="kpi-detail">Source: {source}</div>
        <div class="kpi-detail">{note}</div>
    </div>
    """, unsafe_allow_html=True)


st.markdown("### Eight Headline KPIs")

# Use selected-month data for metrics that support it.
headcount_value = (
    monthly_headcount.iloc[0]["employee_count"]
    if not monthly_headcount.empty else values["Headcount"]
)

gross_value = (
    monthly_payroll.iloc[0]["gross_pay"]
    if not monthly_payroll.empty else values["Gross Payroll"]
)

net_value = (
    monthly_payroll.iloc[0]["net_pay"]
    if not monthly_payroll.empty else values["Net Payroll"]
)

attendance_status = "N/A"
attendance_target_text = "Not configured"

if attendance_target is not None:
    attendance_status = (
        "On Target"
        if values["Attendance Rate"] >= attendance_target
        else "Below Target"
    )
    attendance_target_text = f"{attendance_target:.1f}%"


kpi_rows = [
    (
        "Headcount", number(headcount_value),
        "Not configured", "N/A",
        "metric_headcount_monthly" if not monthly_headcount.empty else "metric_headcount",
        "Selected month" if not monthly_headcount.empty else "Overall snapshot"
    ),
    (
        "Gross Payroll", money(gross_value),
        "Not configured", "N/A",
        "metric_payroll_by_period" if not monthly_payroll.empty else "metric_payroll_gross_total",
        "Selected month" if not monthly_payroll.empty else "Overall snapshot"
    ),
    (
        "Net Payroll", money(net_value),
        "Not configured", "N/A",
        "metric_payroll_by_period" if not monthly_payroll.empty else "metric_payroll_net_total",
        "Selected month" if not monthly_payroll.empty else "Overall snapshot"
    ),
    (
        "Attendance Rate", f'{values["Attendance Rate"]:.2f}%',
        attendance_target_text, attendance_status,
        "metric_attendance_rate", "Aggregate metric"
    ),
    (
        "Approved Leaves", number(values["Approved Leaves"]),
        "Not configured", "N/A",
        "metric_approved_leaves", "Aggregate metric"
    ),
    (
        "Leave Requests", number(values["Leave Requests"]),
        "Not configured", "N/A",
        "metric_leave_requests", "Aggregate metric"
    ),
    (
        "Salary Total", money(values["Salary Total"]),
        "Not configured", "N/A",
        "metric_salary_total", "Aggregate metric"
    ),
    (
        "Hours Worked", f'{values["Hours Worked"]:,.1f}',
        "Not configured", "N/A",
        "metric_hours_worked_total", "Aggregate metric"
    )
]

for start in (0, 4):
    cols = st.columns(4)
    for col, item in zip(cols, kpi_rows[start:start + 4]):
        with col:
            card(*item)

st.caption(
    "Important: Aggregate metrics are not month-filtered. "
    "Only headcount and payroll use selected-month values where available."
)

st.divider()

# Compact trends
st.markdown("### Monthly Trends")

trend1, trend2 = st.columns(2)

with trend1:
    st.markdown("**Headcount trend**")
    if not headcount_monthly.empty:
        st.line_chart(
            headcount_monthly.set_index("month_end")["employee_count"],
            height=170
        )
    else:
        st.info("No monthly headcount data.")

with trend2:
    st.markdown("**Payroll trend**")
    if not payroll_monthly.empty:
        st.bar_chart(
            payroll_monthly.set_index("pay_period")[["gross_pay", "net_pay"]],
            height=170
        )
    else:
        st.info("No monthly payroll data.")

st.divider()

# Detailed dashboard links: launch each dashboard on its own port
st.markdown("### Detailed Dashboard Navigation")

dashboard_files = [
    ("Task 11 – Workforce Overview", "task11_dashboard.py", 8511),
    ("Task 12 – Receivables", "task12_dashboard.py", 8512),
    ("Task 13 – Department Impact", "task13_dashboard.py", 8513),
    ("Task 14 – AI Signals", "task14_dashboard.py", 8514)
]

nav_cols = st.columns(4)

for col, (label, filename, port) in zip(nav_cols, dashboard_files):
    with col:
        st.markdown(f"**{label}**")
        if st.button(f"Open {label}", key=f"open_{port}"):
            if not Path(filename).exists():
                st.error(f"{filename} not found.")
            else:
                subprocess.Popen([
                    sys.executable, "-m", "streamlit", "run",
                    filename, "--server.port", str(port)
                ])
                st.success(f"Dashboard started: http://localhost:{port}")
                st.link_button(
                    "Go to dashboard",
                    f"http://localhost:{port}"
                )

with st.expander("KPI definitions and rationale"):
    definitions = [
        ("Headcount", "Measures the size of the current workforce."),
        ("Gross Payroll", "Measures payroll before deductions."),
        ("Net Payroll", "Measures payroll after deductions."),
        ("Attendance Rate", "Measures the percentage of attendance records marked present."),
        ("Approved Leaves", "Shows approved leave requests."),
        ("Leave Requests", "Shows the total number of recorded leave requests."),
        ("Salary Total", "Shows the governed total salary metric."),
        ("Hours Worked", "Measures total recorded working hours.")
    ]

    for name, description in definitions:
        st.markdown(f"**{name}:** {description}")

st.caption(
    "Targets are displayed only when available in the target table. "
    "No target or trend is invented for unsupported KPIs."
)

st.caption("PulseIQ Workforce Analytics | Task 15 | Executive Scorecard")
