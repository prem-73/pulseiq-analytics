import json
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="PulseIQ Attrition Analytics",
    layout="wide"
)

st.title("PulseIQ - Attrition Analytics")
st.caption("Task 7: Actual Attrition and Predicted Risk")

MIN_GROUP_SIZE = 5

# --------------------------------------------------
# 1. Load actual project data
# --------------------------------------------------
st.header("1. Actual Company Data")

try:
    con = duckdb.connect("pulseiq.duckdb", read_only=True)

    headcount = con.execute(
        "SELECT * FROM metric_headcount_monthly ORDER BY month_end"
    ).fetchdf()

    departments = con.execute("""
        SELECT department, COUNT(*) AS employee_count
        FROM employees
        GROUP BY department
        ORDER BY department
    """).fetchdf()

    history = con.execute("""
        SELECT employee_id, effective_from, effective_to, is_current
        FROM dim_employee
    """).fetchdf()

    con.close()

    col1, col2, col3 = st.columns(3)

    col1.metric("Employee History Records", len(history))
    col2.metric(
        "Current Records",
        int(history["is_current"].fillna(False).astype(bool).sum())
    )
    col3.metric(
        "Non-current Records",
        int((~history["is_current"].fillna(False).astype(bool)).sum())
    )

    st.warning(
        "Verified employee exit records are unavailable. "
        "Current employee counts must not be interpreted as attrition counts."
    )

    st.subheader("Current Employees by Department")
    st.dataframe(departments, use_container_width=True, hide_index=True)

    st.subheader("Monthly Headcount")
    st.dataframe(headcount, use_container_width=True, hide_index=True)

except Exception as error:
    st.error(f"Could not load company data: {error}")
    st.stop()

# --------------------------------------------------
# 2. Actual attrition limitations
# --------------------------------------------------
st.header("2. Actual Attrition, Tenure at Exit and Exit Type")

st.info(
    "Monthly exits, tenure at exit, and voluntary/involuntary exit types "
    "cannot be calculated because verified exit dates and exit categories "
    "are unavailable in the current company dataset."
)

# --------------------------------------------------
# 3. External dataset analysis
# --------------------------------------------------
st.header("3. External Dataset Analysis")

external_path = Path("data/external/emp_attrition.csv")

if external_path.exists():
    try:
        external = pd.read_csv(external_path)

        required_columns = {
            "Attrition",
            "Department",
            "YearsAtCompany"
        }

        if not required_columns.issubset(external.columns):
            st.error(
                "External dataset is missing one or more required columns."
            )
        else:
            total_records = len(external)
            attrition_yes = (
                external["Attrition"].astype(str).str.strip().str.lower()
                == "yes"
            )
            attrition_count = int(attrition_yes.sum())
            attrition_rate = (
                attrition_count / total_records * 100
                if total_records else 0
            )

            st.warning(
                "The following results come from an external IBM HR dataset, "
                "not from actual company employees. They are for demonstration "
                "and analysis only."
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("External Dataset Records", total_records)
            col2.metric("Attrition-Labelled Records", attrition_count)
            col3.metric("External Dataset Attrition Rate", f"{attrition_rate:.2f}%")

            st.subheader("Attrition by Department")

            dept_summary = (
                external.assign(attrition_yes=attrition_yes)
                .groupby("Department")
                .agg(
                    group_size=("Attrition", "size"),
                    attrition_records=("attrition_yes", "sum")
                )
                .reset_index()
            )

            dept_summary["attrition_rate_pct"] = (
                dept_summary["attrition_records"]
                / dept_summary["group_size"] * 100
            )

            dept_summary["display_result"] = dept_summary.apply(
                lambda row: (
                    f"{row['attrition_rate_pct']:.2f}%"
                    if row["group_size"] >= MIN_GROUP_SIZE
                    else "Suppressed - group too small"
                ),
                axis=1
            )

            st.dataframe(
                dept_summary[
                    ["Department", "group_size", "attrition_records",
                     "display_result"]
                ].rename(columns={
                    "group_size": "Group Size",
                    "attrition_records": "Attrition-Labelled Records",
                    "display_result": "Attrition Rate"
                }),
                use_container_width=True,
                hide_index=True
            )

            st.subheader("Attrition by Years at Company")

            tenure_data = external.copy()
            tenure_data["tenure_years"] = pd.to_numeric(
                tenure_data["YearsAtCompany"], errors="coerce"
            )
            tenure_data = tenure_data.dropna(subset=["tenure_years"])
            tenure_data["tenure_band"] = pd.cut(
                tenure_data["tenure_years"],
                bins=[-1, 1, 3, 5, 10, float("inf")],
                labels=["0-1 years", "2-3 years", "4-5 years",
                        "6-10 years", "Over 10 years"]
            )
            tenure_data["attrition_yes"] = (
                tenure_data["Attrition"].astype(str).str.strip().str.lower()
                == "yes"
            )

            tenure_summary = (
                tenure_data.groupby("tenure_band", observed=False)
                .agg(
                    group_size=("Attrition", "size"),
                    attrition_records=("attrition_yes", "sum")
                )
                .reset_index()
            )

            tenure_summary["attrition_rate_pct"] = (
                tenure_summary["attrition_records"]
                / tenure_summary["group_size"].replace(0, pd.NA) * 100
            )

            tenure_summary["display_result"] = tenure_summary.apply(
                lambda row: (
                    f"{row['attrition_rate_pct']:.2f}%"
                    if row["group_size"] >= MIN_GROUP_SIZE
                    else "Suppressed - group too small"
                ),
                axis=1
            )

            st.dataframe(
                tenure_summary[
                    ["tenure_band", "group_size", "attrition_records",
                     "display_result"]
                ].rename(columns={
                    "tenure_band": "Years at Company",
                    "group_size": "Group Size",
                    "attrition_records": "Attrition-Labelled Records",
                    "display_result": "Attrition Rate"
                }),
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                "These are external dataset attrition labels grouped by "
                "department and years at company. Exact exit dates and "
                "exit categories are not available."
            )

    except Exception as error:
        st.error(f"Could not analyze the external dataset: {error}")
else:
    st.warning(
        "External dataset not found at data/external/emp_attrition.csv."
    )

# --------------------------------------------------
# 4. Model evaluation metrics
# --------------------------------------------------
st.header("4. Attrition Model Evaluation")

metrics_path = Path("models/attrition_model_metrics.json")

if metrics_path.exists():
    try:
        with metrics_path.open("r", encoding="utf-8") as file:
            metrics = json.load(file)

        st.warning(
            "These evaluation metrics are based on an external IBM HR dataset. "
            "They do not establish model performance on actual company employees."
        )

        st.caption(
            f"Dataset: {metrics.get('dataset', 'Not specified')} | "
            f"Test records: {metrics.get('test_rows', 'N/A')}"
        )

        col1, col2, col3, col4, col5 = st.columns(5)

        col1.metric("Accuracy", f"{metrics['accuracy']:.2%}")
        col2.metric("Precision", f"{metrics['precision']:.2%}")
        col3.metric("Recall", f"{metrics['recall']:.2%}")
        col4.metric("F1-score", f"{metrics['f1_score']:.2%}")
        col5.metric("ROC-AUC", f"{metrics['roc_auc']:.2%}")

        st.subheader("Model Limitations")

        for limitation in metrics.get("limitations", []):
            st.markdown(f"- {limitation}")

        st.info(
            "Predictions are estimates, not certainties. The model has not "
            "been validated for the company's actual workforce."
        )

    except Exception as error:
        st.error(f"Could not load model metrics: {error}")
else:
    st.warning(
        "Model metrics file not found. Run train_attrition_model.py first."
    )

# --------------------------------------------------
# 5. Findings and privacy
# --------------------------------------------------
st.header("5. Key Findings")

st.markdown(
    "**Finding 1:** The current employee history contains 100 records, "
    "with no non-current records in the inspected dataset."
)
st.markdown(
    "**Finding 2:** The available January, September and October 2026 "
    "headcount snapshots each report 100 employees. This does not prove "
    "that no exits occurred between snapshots."
)
st.markdown(
    "**Finding 3:** An external dataset and model evaluation are available, "
    "but neither establishes attrition rates or prediction performance "
    "for the company's actual employees."
)

st.header("6. Privacy Protection")
st.write(f"Minimum group size: {MIN_GROUP_SIZE} employees.")
st.write(
    "Groups with fewer than five records are suppressed in group-level "
    "attrition-rate displays."
)

st.header("7. Data Limitations")

st.markdown("""
- Verified employee exit dates are unavailable.
- Voluntary and involuntary exit categories are unavailable.
- Exact tenure at exit cannot be calculated without verified exit dates.
- External dataset analysis is not actual company workforce analysis.
- Model evaluation on an external test set does not guarantee company-level performance.
- Predictions must not be treated as certain outcomes or used alone for employment decisions.
""")

st.success("Dashboard loaded. Data sources and limitations are disclosed.")

