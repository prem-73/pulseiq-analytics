import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Task 12 | Receivables & Cash", page_icon="💰", layout="wide")
st.title("Task 12: Invoices, Receivables and Cash Flow")
st.caption("PulseIQ Analytics | Invoice and collection analysis")

FILES = {
    "invoice": "fact_invoice.csv",
    "payment": "fact_invoice_payment.csv",
    "client": "dim_client.csv",
}

@st.cache_data
def load_data():
    missing = [f for f in FILES.values() if not Path(f).exists()]
    if missing:
        raise FileNotFoundError("Missing source file(s): " + ", ".join(missing) +
                                ". Keep all three CSV files beside task12_dashboard.py.")
    invoice = pd.read_csv(FILES["invoice"])
    payment = pd.read_csv(FILES["payment"])
    client = pd.read_csv(FILES["client"])

    for c in ["invoice_date", "due_date", "last_payment_date"]:
        invoice[c] = pd.to_datetime(invoice[c], errors="coerce")
    payment["payment_date"] = pd.to_datetime(payment["payment_date"], errors="coerce")
    for c in ["total_amount", "amount_paid", "balance_due", "days_past_due_at_cutoff", "days_to_pay"]:
        invoice[c] = pd.to_numeric(invoice[c], errors="coerce")
    payment["amount"] = pd.to_numeric(payment["amount"], errors="coerce").fillna(0)

    invoice["status"] = invoice["status"].astype(str).str.strip().str.upper()
    # Open statuses are exactly those specified in the task brief.
    open_statuses = ["SENT", "OVERDUE", "PARTIALLY_PAID"]
    open_inv = invoice[invoice["status"].isin(open_statuses)].copy()
    # Use the supplied source cutoff ageing field, preserving the dataset's own as-of date.
    # "Not yet due" is included in the 0-30/current bucket so all open balances reconcile.
    days = open_inv["days_past_due_at_cutoff"].fillna(0)
    open_inv["ageing_bucket"] = np.select(
        [days.le(30), days.le(60), days.le(90)],
        ["0-30 days (including not yet due)", "31-60 days", "61-90 days"],
        default="90+ days"
    )
    open_inv["balance_due"] = open_inv["balance_due"].fillna(0)
    open_inv = open_inv.merge(
        client[["client_id", "client_name", "payment_terms_days", "payment_behaviour"]],
        on="client_id", how="left", validate="many_to_one"
    )
    invoice_client = invoice.merge(
        client[["client_id", "client_name", "payment_terms_days", "payment_behaviour"]],
        on="client_id", how="left", validate="many_to_one"
    )
    return invoice, payment, client, open_inv, invoice_client

try:
    invoice, payment, clients, open_inv, invoice_client = load_data()
except Exception as exc:
    st.error(str(exc))
    st.stop()

st.info("Open invoice statuses used: SENT, OVERDUE and PARTIALLY_PAID. PAID, CANCELLED and DRAFT are excluded.")

# Dataset's own ageing cutoff is represented by days_past_due_at_cutoff.
cutoff_days = pd.to_numeric(invoice["days_past_due_at_cutoff"], errors="coerce")
st.caption("Ageing uses days_past_due_at_cutoff supplied in fact_invoice.csv. Not-yet-due open invoices are grouped with the 0–30/current bucket so the four displayed buckets reconcile to total open receivables.")

total_open = float(open_inv["balance_due"].sum())
bucket_order = ["0-30 days (including not yet due)", "31-60 days", "61-90 days", "90+ days"]
bucket = (open_inv.groupby("ageing_bucket", as_index=False)["balance_due"].sum()
          .set_index("ageing_bucket").reindex(bucket_order, fill_value=0).reset_index())
bucket_total = float(bucket["balance_due"].sum())
difference = bucket_total - total_open

c1, c2, c3, c4 = st.columns(4)
c1.metric("Open receivables", f"₹{total_open:,.2f}")
c2.metric("Open invoices", f"{len(open_inv):,}")
c3.metric("Payments received", f"₹{payment['amount'].sum():,.2f}")
c4.metric("Ageing bucket difference", f"₹{difference:,.2f}", delta="PASS" if abs(difference) < 0.01 else "CHECK")

st.subheader("Receivables ageing")
st.plotly_chart(px.bar(bucket, x="ageing_bucket", y="balance_due", text_auto=".2s",
                       title="Open receivables by ageing bucket",
                       labels={"ageing_bucket":"Ageing bucket","balance_due":"Outstanding (₹)"}),
                use_container_width=True)
st.dataframe(bucket.rename(columns={"ageing_bucket":"Ageing bucket","balance_due":"Outstanding"})
             .style.format({"Outstanding":"₹{:,.2f}"}), use_container_width=True, hide_index=True)
st.success(f"Bucket check: ₹{bucket_total:,.2f} = total open receivables ₹{total_open:,.2f}. Difference ₹{difference:,.2f}.")

st.subheader("Client-wise average days to pay")
paid = invoice_client[(invoice_client["status"] == "PAID") & invoice_client["days_to_pay"].notna()].copy()
client_pay = paid.groupby(["client_id","client_name"], as_index=False).agg(
    avg_days_to_pay=("days_to_pay","mean"),
    paid_invoice_count=("invoice_id","nunique"),
    paid_invoice_value=("total_amount","sum")
)
client_pay = client_pay.sort_values(["avg_days_to_pay","paid_invoice_count"], ascending=[False,False])
st.plotly_chart(px.bar(client_pay.head(15).sort_values("avg_days_to_pay"),
                       x="avg_days_to_pay", y="client_name", orientation="h",
                       title="Slowest-paying clients (average days to pay)",
                       labels={"avg_days_to_pay":"Average days to pay","client_name":"Client"}),
                use_container_width=True)
st.dataframe(client_pay.rename(columns={
    "client_id":"Client ID","client_name":"Client","avg_days_to_pay":"Average days to pay",
    "paid_invoice_count":"Paid invoices","paid_invoice_value":"Paid invoice value"
}).style.format({"Average days to pay":"{:.1f} days","Paid invoice value":"₹{:,.2f}"}),
use_container_width=True, hide_index=True)

st.subheader("Clients with the most overdue money")
overdue_clients = (open_inv.groupby(["client_id","client_name"], as_index=False)
                   .agg(outstanding=("balance_due","sum"),
                        overdue_days_max=("days_past_due_at_cutoff","max"),
                        open_invoice_count=("invoice_id","nunique"))
                   .sort_values("outstanding", ascending=False))
st.plotly_chart(px.bar(overdue_clients.head(10).sort_values("outstanding"),
                       x="outstanding", y="client_name", orientation="h",
                       title="Top 10 clients by open receivables",
                       labels={"outstanding":"Outstanding (₹)","client_name":"Client"}),
                use_container_width=True)
st.dataframe(overdue_clients.head(10).rename(columns={
    "client_id":"Client ID","client_name":"Client","outstanding":"Outstanding",
    "overdue_days_max":"Maximum days past due","open_invoice_count":"Open invoices"
}).style.format({"Outstanding":"₹{:,.2f}"}), use_container_width=True, hide_index=True)

st.subheader("Cash received by month")
cash_in = payment.dropna(subset=["payment_date"]).copy()
cash_in["month"] = cash_in["payment_date"].dt.to_period("M").astype(str)
cash_month = cash_in.groupby("month", as_index=False).agg(cash_in=("amount","sum"))
st.plotly_chart(px.bar(cash_month, x="month", y="cash_in", title="Cash in – customer payments received",
                       labels={"month":"Month","cash_in":"Cash received (₹)"}),
                use_container_width=True)

st.warning("Cash out is not present in the three supplied Task 12 files. Invoice and payment data prove customer cash receipts, but do not prove supplier/payroll/operating cash payments. Upload an approved cash-disbursement or bank-transaction source to complete cash-in versus cash-out; do not treat expense accruals as cash outflows.")

st.subheader("Invoice status summary")
status_summary = invoice.groupby("status", as_index=False).agg(
    invoice_count=("invoice_id","nunique"),
    invoice_value=("total_amount","sum"),
    outstanding=("balance_due","sum")
)
st.dataframe(status_summary.rename(columns={
    "status":"Status","invoice_count":"Invoices","invoice_value":"Invoice value",
    "outstanding":"Outstanding"
}).style.format({"Invoice value":"₹{:,.2f}","Outstanding":"₹{:,.2f}"}),
use_container_width=True, hide_index=True)

st.subheader("Data quality checks")
payment_invoice_ids = set(payment["invoice_id"].dropna())
invoice_ids = set(invoice["invoice_id"].dropna())
unmatched_payments = len(payment[~payment["invoice_id"].isin(invoice_ids)])
duplicate_invoice_ids = int(invoice["invoice_id"].duplicated().sum())
duplicate_payment_ids = int(payment["payment_id"].duplicated().sum())
payment_sum = float(payment["amount"].sum())
invoice_paid_sum = float(invoice["amount_paid"].sum())
d1, d2, d3, d4 = st.columns(4)
d1.metric("Invoice rows", f"{len(invoice):,}")
d2.metric("Payment rows", f"{len(payment):,}")
d3.metric("Unmatched payments", f"{unmatched_payments:,}")
d4.metric("Duplicate invoice IDs", f"{duplicate_invoice_ids:,}")
st.write(f"Payment total: ₹{payment_sum:,.2f} | Invoice amount_paid total: ₹{invoice_paid_sum:,.2f} | Difference: ₹{payment_sum-invoice_paid_sum:,.2f}")
st.write(f"Duplicate payment IDs: {duplicate_payment_ids:,}")

st.subheader("Finance discussion: a client that always pays in 75 days")
st.markdown("""
A predictable 75-day payment pattern can still create working-capital risk if agreed terms are 30 or 45 days.
Ask Finance:
1. Are 75 days contractually agreed, or is the client routinely late?
2. What is the outstanding exposure and concentration as a share of total receivables?
3. Are there disputed invoices, credit notes, or collection promises?
4. Should credit limits, deposits, milestone billing or collection escalation change?
""")

st.download_button("Download ageing bucket check", bucket.to_csv(index=False).encode("utf-8"),
                   "task12_ageing_bucket_check.csv", "text/csv")
st.download_button("Download client payment behaviour", client_pay.to_csv(index=False).encode("utf-8"),
                   "task12_client_days_to_pay.csv", "text/csv")
st.download_button("Download overdue client list", overdue_clients.to_csv(index=False).encode("utf-8"),
                   "task12_overdue_clients.csv", "text/csv")
