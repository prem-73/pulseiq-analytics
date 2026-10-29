import duckdb
import streamlit as st

st.set_page_config(page_title="PulseIQ Attrition Analytics", layout="wide")
st.title("PulseIQ - Attrition Analytics")
st.caption("Task 7: Actual Attrition and Predicted Risk")

con = duckdb.connect("pulseiq.duckdb", read_only=True)

headcount = con.execute("SELECT * FROM metric_headcount_monthly ORDER BY month_end").fetchdf()
departments = con.execute("SELECT department, COUNT(*) AS employee_count FROM employees GROUP BY department ORDER BY department").fetchdf()
history = con.execute("SELECT employee_id, effective_from, effective_to, is_current FROM dim_employee").fetchdf()
con.close()

st.header("1. Actual Attrition")

col1, col2, col3 = st.columns(3)
col1.metric("Employee Records", len(history))
col2.metric("Non-current Records", int((history["is_current"] == False).sum()))
col3.metric("Confirmed Exits", "Unavailable")

st.warning("Actual exits cannot be calculated because verified exit records are unavailable.")

st.subheader("Monthly Exits")
st.info("Unavailable: verified employee exit dates are required.")

st.subheader("Current Employees by Department")
st.dataframe(departments, use_container_width=True, hide_index=True)
st.caption("These are current employee counts, not attrition counts.")

st.subheader("Monthly Headcount")
st.dataframe(headcount, use_container_width=True, hide_index=True)

st.header("2. Tenure at Exit and Exit Type")
st.info("Unavailable: confirmed exit dates and exit categories were not identified.")

st.header("3. Predicted, not certain")
st.warning("No validated attrition-risk prediction feed was identified. Predicted risk values are not displayed.")

st.write("Predictions are estimates, not confirmed future events. This dashboard does not claim to predict individual employees.")

st.header("4. Privacy Protection")
st.write("Minimum group size: 5 employees.")
st.info("For future group-level results with fewer than 5 employees, display: Suppressed — group too small.")

st.header("5. Three Biggest Findings")
st.markdown("**Finding 1:** 100 current employee records and zero non-current records.")
st.markdown("**Finding 2:** January, September and October 2026 headcount snapshots each report 100 employees. This does not prove that no exits occurred between snapshots.")
st.markdown("**Finding 3:** No validated attrition-risk prediction output was identified.")

st.header("6. Data Limitations")
st.markdown("""

* Verified employee exit dates are unavailable.
* Voluntary and other exit categories are unavailable.
* Tenure at exit cannot be calculated without exit dates.
* Validated prediction output is unavailable.
* Findings must be updated when reliable historical data becomes available.
  """)

st.success("Dashboard loaded using available data. Missing information is clearly disclosed.")
