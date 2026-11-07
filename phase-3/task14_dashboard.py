import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Task 14 | AI Signals", layout="wide")
st.title("Task 14 – AI Signals Dashboard")
st.caption("Anomalies, forecast ranges and attrition-risk signals. Model outputs require human review.")

FILES = {
    "anomaly": "fact_anomaly.csv",
    "forecast": "fact_forecast.csv",
    "attrition": "fact_attrition_risk.csv",
}
for label, path in FILES.items():
    if not os.path.exists(path):
        st.error(f"Missing {path}. Place all three Task 14 CSV files in the project root.")
        st.stop()

@st.cache_data
def load_data():
    anomaly = pd.read_csv(FILES["anomaly"])
    forecast = pd.read_csv(FILES["forecast"])
    attrition = pd.read_csv(FILES["attrition"])
    anomaly["period"] = pd.to_datetime(anomaly["period"], errors="coerce")
    forecast["forecast_month"] = pd.to_datetime(forecast["forecast_month"], errors="coerce")
    attrition["as_of_date"] = pd.to_datetime(attrition["as_of_date"], errors="coerce")
    for col in ["money_at_risk", "anomaly_score"]:
        anomaly[col] = pd.to_numeric(anomaly[col], errors="coerce")
    for col in ["forecast_value", "lower_80", "upper_80"]:
        forecast[col] = pd.to_numeric(forecast[col], errors="coerce")
    attrition["risk_score_12m"] = pd.to_numeric(attrition["risk_score_12m"], errors="coerce")
    return anomaly, forecast, attrition

anomaly, forecast, attrition = load_data()

st.info("AI outputs are decision-support signals, not confirmed losses, diagnoses, or promises. A human reviewer must validate each item.")

# Summary cards
flagged = anomaly[anomaly["flagged"].astype(str).str.upper().eq("Y")].copy()
money_known = flagged["money_at_risk"].notna()
total_money = flagged.loc[money_known, "money_at_risk"].sum()
risk_high = int(attrition["risk_band"].astype(str).str.lower().eq("high").sum())
c1, c2, c3, c4 = st.columns(4)
c1.metric("Flagged anomaly records", f"{len(flagged):,}")
c2.metric("Recorded money at risk", f"₹{total_money:,.2f}")
c3.metric("Anomalies without money estimate", f"{int((~money_known).sum()):,}")
c4.metric("High attrition-risk signals", f"{risk_high:,}")

# Anomaly ranking
st.subheader("1. Anomalies ranked by recorded money at risk")
st.markdown("**AI-generated, for human review**")
st.write("Plain-language note: This ranking sums only populated `money_at_risk` values. A missing estimate is not treated as zero loss; it means the source did not quantify the exposure.")
anomaly_rank = (flagged.groupby("reason_code", dropna=False)
                .agg(flagged_records=("result_id", "count"),
                     records_with_money=("money_at_risk", "count"),
                     money_at_risk=("money_at_risk", "sum"))
                .reset_index()
                .sort_values("money_at_risk", ascending=False))
if not anomaly_rank.empty:
    fig = go.Figure(go.Bar(
        x=anomaly_rank["money_at_risk"],
        y=anomaly_rank["reason_code"],
        orientation="h",
        customdata=anomaly_rank[["flagged_records", "records_with_money"]],
        hovertemplate="Type: %{y}<br>Recorded money at risk: ₹%{x:,.2f}<br>Flagged records: %{customdata[0]}<br>Records with money estimate: %{customdata[1]}<extra></extra>"
    ))
    fig.update_layout(height=max(400, 32 * len(anomaly_rank)), yaxis={"categoryorder": "total ascending"},
                      xaxis_title="Recorded money at risk (₹)", yaxis_title="Anomaly type")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(anomaly_rank.rename(columns={
        "reason_code": "Anomaly type", "flagged_records": "Flagged records",
        "records_with_money": "Records with money estimate", "money_at_risk": "Money at risk (₹)"
    }), use_container_width=True, hide_index=True)
else:
    st.warning("No flagged anomaly rows were found.")

st.caption(f"Across flagged rows: {int(money_known.sum())} have a money estimate; {int((~money_known).sum())} do not. Recorded amount: ₹{total_money:,.2f}. This is model-estimated exposure, not confirmed loss.")

# Forecast chart
st.subheader("2. Forecast vs actual with 80% confidence band")
st.markdown("**AI-generated, for human review**")
st.write("Plain-language note: The shaded area is the model's supplied 80% interval (`lower_80` to `upper_80`). It is a range, not a guarantee. Forecasts are grouped by metric and department.")
metrics = sorted(forecast["metric"].dropna().unique().tolist())
metric_choice = st.selectbox("Forecast metric", metrics, index=metrics.index("headcount_end") if "headcount_end" in metrics else 0)
f_metric = forecast[forecast["metric"] == metric_choice].copy()
departments = sorted(f_metric["department_id"].dropna().unique().tolist())
dept_choice = st.selectbox("Department", departments, index=departments.index("ALL") if "ALL" in departments else 0)
f_view = f_metric[f_metric["department_id"] == dept_choice].sort_values("forecast_month")

# Historical actuals are optional and are only joined if the reference summary has a matching month.
actuals = pd.DataFrame()
reference_candidates = [
    "unlock_PQ-13_reference_summary_dept_month.csv",
    os.path.join("data", "reference", "unlock_PQ-13_reference_summary_dept_month.csv"),
    os.path.join("data", "raw", "unlock_PQ-13_reference_summary_dept_month.csv"),
]
reference_path = next((p for p in reference_candidates if os.path.exists(p)), None)
actual_col = {"headcount_end": "headcount_end", "attrition_rate_monthly_pct": "attrition_rate_monthly_pct"}.get(metric_choice)
if reference_path and actual_col:
    ref = pd.read_csv(reference_path)
    ref["month"] = pd.to_datetime(ref["month"], errors="coerce")
    if dept_choice == "ALL":
        actuals = ref.groupby("month", as_index=False)[actual_col].sum() if metric_choice == "headcount_end" else ref.groupby("month", as_index=False)[actual_col].mean()
    else:
        # Reference uses department IDs; aggregate duplicate rows only if present.
        actuals = ref[ref["department_id"].astype(str) == str(dept_choice)].groupby("month", as_index=False)[actual_col].mean()
    actuals = actuals.rename(columns={"month": "forecast_month", actual_col: "actual_value"})

fig = go.Figure()
fig.add_trace(go.Scatter(x=f_view["forecast_month"], y=f_view["upper_80"], mode="lines",
                         line=dict(width=0), showlegend=False, hoverinfo="skip", name="Upper 80%"))
fig.add_trace(go.Scatter(x=f_view["forecast_month"], y=f_view["lower_80"], mode="lines",
                         line=dict(width=0), fill="tonexty", fillcolor="rgba(99,110,250,0.18)",
                         name="80% confidence band", hoverinfo="skip"))
fig.add_trace(go.Scatter(x=f_view["forecast_month"], y=f_view["forecast_value"], mode="lines+markers",
                         name="Forecast", line=dict(width=3)))
if not actuals.empty:
    merged = f_view.merge(actuals, on="forecast_month", how="left")
    if merged["actual_value"].notna().any():
        fig.add_trace(go.Scatter(x=merged["forecast_month"], y=merged["actual_value"],
                                 mode="lines+markers", name="Actual"))
fig.update_layout(xaxis_title="Month", yaxis_title=metric_choice, hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# Forecast error table only where actuals exist
st.subheader("3. Forecast error for months with known actuals")
if not actuals.empty:
    error_table = f_view.merge(actuals, on="forecast_month", how="inner")
    error_table = error_table[error_table["actual_value"].notna()].copy()
else:
    error_table = pd.DataFrame()

if not error_table.empty:
    error_table["absolute_error"] = (error_table["forecast_value"] - error_table["actual_value"]).abs()
    error_table["absolute_percentage_error"] = (
        error_table["absolute_error"] / error_table["actual_value"].abs().replace(0, pd.NA) * 100
    )
    st.dataframe(error_table[["forecast_month", "forecast_value", "actual_value", "absolute_error", "absolute_percentage_error"]]
                 .rename(columns={"forecast_month": "Month", "forecast_value": "Forecast",
                                  "actual_value": "Actual", "absolute_error": "Absolute error",
                                  "absolute_percentage_error": "Absolute percentage error (%)"}),
                 use_container_width=True, hide_index=True)
    st.caption("Absolute percentage error = |forecast − actual| / |actual| × 100. Zero actuals are not assigned a percentage error.")
else:
    st.warning("No overlapping forecast months and actual values are available in the supplied files. Forecast error is therefore not calculable yet.")
    if not f_view.empty:
        st.write(f"Forecast period: {f_view['forecast_month'].min():%b %Y} to {f_view['forecast_month'].max():%b %Y}.")
    if reference_path:
        st.write("The available reference summary ends before the forecast period begins; no same-month actuals can be compared.")
    else:
        st.write("No Task 13 reference summary CSV was found in the project folder.")

# Attrition risk
st.subheader("4. Attrition-risk signals")
st.markdown("**AI-generated, for human review**")
st.write("Plain-language note: These are baseline model risk bands for HR review, not confirmed future exits and not a basis for automated employment decisions.")
risk_summary = (attrition.groupby("risk_band", dropna=False)
                .agg(employees=("prediction_id", "count"),
                     average_risk_score=("risk_score_12m", "mean"))
                .reset_index())
risk_order = {"High": 0, "Medium": 1, "Low": 2}
risk_summary["_order"] = risk_summary["risk_band"].map(risk_order).fillna(3)
risk_summary = risk_summary.sort_values("_order").drop(columns="_order")
st.dataframe(risk_summary.rename(columns={"risk_band": "Risk band", "employees": "Employees",
                                          "average_risk_score": "Average 12-month risk score"}),
             use_container_width=True, hide_index=True)
dept_risk = attrition.groupby(["department_id", "risk_band"]).size().unstack(fill_value=0)
st.bar_chart(dept_risk)

with st.expander("Model metadata and limitations"):
    st.write("Anomaly model versions:", ", ".join(sorted(flagged["model_version"].dropna().astype(str).unique())))
    st.write("Forecast model versions:", ", ".join(sorted(forecast["model_version"].dropna().astype(str).unique())))
    st.write("Attrition model versions:", ", ".join(sorted(attrition["model_version"].dropna().astype(str).unique())))
    notes = attrition["model_note"].dropna().astype(str).unique().tolist()
    if notes:
        st.warning("Attrition model note: " + " | ".join(notes))
    st.write("Forecast method and training cutoff:")
    st.dataframe(forecast[["metric", "department_id", "method", "trained_through", "model_version"]]
                 .drop_duplicates(), use_container_width=True, hide_index=True)

# Evidence outputs
os.makedirs("outputs", exist_ok=True)
anomaly_rank.to_csv("outputs/task14_anomaly_ranking.csv", index=False)
if not error_table.empty:
    error_table.to_csv("outputs/task14_forecast_errors.csv", index=False)
else:
    pd.DataFrame(columns=["forecast_month", "forecast_value", "actual_value", "absolute_error", "absolute_percentage_error"]).to_csv(
        "outputs/task14_forecast_errors.csv", index=False
    )
st.success("Evidence files saved in outputs/: task14_anomaly_ranking.csv and task14_forecast_errors.csv.")
