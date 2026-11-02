import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Task 11 | Profit & Loss", page_icon="📈", layout="wide")
st.title("Task 11: Profit & Loss and Expense Analytics")
st.caption("PulseIQ Analytics | Monthly management P&L | April 2025 – September 2026")

FILES = {
    "ledger": "fact_ledger.csv",
    "account": "dim_account.csv",
    "expense": "fact_expense.csv",
    "vendor": "dim_vendor.csv",
}

@st.cache_data
def load_data():
    missing = [f for f in FILES.values() if not Path(f).exists()]
    if missing:
        raise FileNotFoundError("Missing source file(s): " + ", ".join(missing) +
                                ". Keep all four CSV files beside task11_dashboard.py.")

    ledger = pd.read_csv(FILES["ledger"])
    account = pd.read_csv(FILES["account"])
    expense = pd.read_csv(FILES["expense"])
    vendor = pd.read_csv(FILES["vendor"])

    ledger["account_code"] = pd.to_numeric(ledger["account_code"], errors="coerce").astype("Int64")
    account["account_code"] = pd.to_numeric(account["account_code"], errors="coerce").astype("Int64")
    account["parent_code"] = pd.to_numeric(account["parent_code"], errors="coerce").astype("Int64")
    ledger["entry_date"] = pd.to_datetime(ledger["entry_date"], errors="coerce")
    ledger["posting_period"] = ledger["entry_date"].dt.to_period("M").astype(str)
    for c in ["debit", "credit"]:
        ledger[c] = pd.to_numeric(ledger[c], errors="coerce").fillna(0)

    # Critical control: only detail accounts are included. Group headings are never summed.
    detail_accounts = account[account["is_group"].astype(str).str.upper().isin(["N", "NO", "FALSE", "0"])]
    pnl_accounts = detail_accounts[detail_accounts["statement"].astype(str).str.lower().eq("profit & loss")]
    pnl = ledger.merge(
        pnl_accounts[["account_code", "account_name", "account_type", "normal_balance", "statement"]],
        on="account_code", how="inner", validate="many_to_one"
    )

    # Signed P&L values: income is credit less debit; expense is debit less credit.
    pnl["revenue"] = (pnl["credit"] - pnl["debit"]).where(pnl["account_type"].eq("INCOME"), 0)
    pnl["expenses"] = (pnl["debit"] - pnl["credit"]).where(pnl["account_type"].eq("EXPENSE"), 0)
    monthly = pnl.groupby("posting_period", as_index=False).agg(
        revenue=("revenue", "sum"), expenses=("expenses", "sum")
    )
    monthly["profit"] = monthly["revenue"] - monthly["expenses"]
    monthly["margin_pct"] = monthly.apply(
        lambda r: (r["profit"] / r["revenue"] * 100) if r["revenue"] else 0, axis=1
    )

    # Expense register is used for vendor/category analysis only; it is not added to ledger P&L.
    expense["expense_date"] = pd.to_datetime(expense["expense_date"], errors="coerce")
    expense["month"] = expense["expense_date"].dt.to_period("M").astype(str)
    for c in ["category_account", "amount_excl_gst", "gst_amount", "total_amount"]:
        expense[c] = pd.to_numeric(expense[c], errors="coerce")
    expense["category_account"] = expense["category_account"].astype("Int64")
    expense_detail = expense.merge(
        detail_accounts[["account_code", "account_name", "is_group"]],
        left_on="category_account", right_on="account_code", how="left",
        validate="many_to_one"
    )
    expense_detail = expense_detail.merge(
        vendor[["vendor_id", "vendor_name"]], on="vendor_id", how="left", validate="many_to_one"
    )
    return ledger, account, expense_detail, vendor, pnl, monthly, detail_accounts

try:
    ledger, accounts, expenses, vendors, pnl, monthly, detail_accounts = load_data()
except Exception as e:
    st.error(str(e))
    st.stop()

periods = sorted(monthly["posting_period"].dropna().unique())
if not periods:
    st.warning("No P&L detail-account postings were found.")
    st.stop()

st.sidebar.header("P&L filters")
selected_month = st.sidebar.selectbox("Select month", periods, index=len(periods)-1)
month_row = monthly.loc[monthly["posting_period"].eq(selected_month)].iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Revenue", f"₹{month_row.revenue:,.2f}")
c2.metric("Expenses", f"₹{month_row.expenses:,.2f}")
c3.metric("Profit", f"₹{month_row.profit:,.2f}")
c4.metric("Profit margin", f"{month_row.margin_pct:,.2f}%")

st.subheader("Monthly P&L")
st.dataframe(monthly.rename(columns={
    "posting_period":"Month", "revenue":"Revenue", "expenses":"Expenses",
    "profit":"Profit", "margin_pct":"Profit Margin (%)"
}).style.format({
    "Revenue":"₹{:,.2f}", "Expenses":"₹{:,.2f}", "Profit":"₹{:,.2f}",
    "Profit Margin (%)":"{:.2f}%"
}), use_container_width=True, hide_index=True)

fig = px.line(monthly, x="posting_period", y=["revenue", "expenses", "profit"],
              markers=True, title="Revenue, Expenses and Profit by Month",
              labels={"posting_period":"Month", "value":"Amount (₹)", "variable":"Measure"})
st.plotly_chart(fig, use_container_width=True)
margin_fig = px.line(monthly, x="posting_period", y="margin_pct", markers=True,
                     title="Profit Margin Trend", labels={"posting_period":"Month","margin_pct":"Margin (%)"})
st.plotly_chart(margin_fig, use_container_width=True)

st.subheader(f"Expense category and vendor analysis – {selected_month}")
month_exp = expenses[expenses["month"].eq(selected_month)].copy()
if month_exp.empty:
    st.info("No expense-register rows for the selected month.")
else:
    cat = month_exp.groupby("account_name", dropna=False, as_index=False)["amount_excl_gst"].sum()
    cat = cat.sort_values("amount_excl_gst", ascending=False)
    st.plotly_chart(px.bar(cat, x="account_name", y="amount_excl_gst",
                           title="Expense by Category (excluding GST)",
                           labels={"account_name":"Category","amount_excl_gst":"Amount (₹)"}),
                    use_container_width=True)
    top_vendors = month_exp.groupby("vendor_name", dropna=False, as_index=False)["amount_excl_gst"].sum()
    top_vendors = top_vendors.sort_values("amount_excl_gst", ascending=False).head(10)
    st.plotly_chart(px.bar(top_vendors, x="amount_excl_gst", y="vendor_name", orientation="h",
                           title="Top 10 Vendors (excluding GST)",
                           labels={"vendor_name":"Vendor","amount_excl_gst":"Amount (₹)"}),
                    use_container_width=True)
    st.dataframe(top_vendors.rename(columns={"vendor_name":"Vendor","amount_excl_gst":"Spend excl. GST"})
                 .style.format({"Spend excl. GST":"₹{:,.2f}"}), use_container_width=True, hide_index=True)

st.subheader("Account classification control")
account_check = accounts[["account_code","account_name","account_type","parent_code","is_group","statement"]].copy()
account_check["included_in_pnl"] = (
    account_check["is_group"].astype(str).str.upper().isin(["N","NO","FALSE","0"]) &
    account_check["statement"].astype(str).str.lower().eq("profit & loss")
)
st.caption("P&L totals use only Profit & Loss detail accounts (is_group = N). Group headings are excluded to prevent double counting.")
st.dataframe(account_check, use_container_width=True, hide_index=True)

st.subheader("Data quality and tie-out checks")
unmapped = int(expenses["account_name"].isna().sum())
missing_vendor = int(expenses["vendor_name"].isna().sum())
group_included = int(pnl["account_code"].isin(
    accounts.loc[accounts["is_group"].astype(str).str.upper().isin(["Y","YES","TRUE","1"]), "account_code"]
).sum())
debit_credit_diff = float((ledger["debit"].sum() - ledger["credit"].sum()))
q1, q2, q3, q4 = st.columns(4)
q1.metric("Ledger rows", f"{len(ledger):,}")
q2.metric("Expense rows", f"{len(expenses):,}")
q3.metric("Unmapped expense categories", f"{unmapped:,}")
q4.metric("Unmapped vendors", f"{missing_vendor:,}")
st.write(f"Ledger debit-credit difference across all account types: ₹{debit_credit_diff:,.2f} (this is a trial-balance check, not the P&L tie-out).")
st.write(f"Group accounts included in P&L calculation: {group_included} (expected 0).")

st.info("README tie-out: the uploaded README.md is a Validation Vault instruction file, not a P&L headline-number sheet. Enter/compare the official headline figures only after locating the correct README workbook/sheet. Do not open any unlock_TASK_11 answer-key file until your own calculations are complete.")

st.subheader("Findings to complete after reviewing results")
st.markdown("""
1. **Margin movement:** identify the months where revenue increased but margin fell; check whether expense growth exceeded revenue growth.
2. **Expense concentration:** identify the largest expense categories and whether their share of total expense is increasing.
3. **Vendor concentration:** identify the top vendors and check for repeated high-value bills, changes in spend, and payment timing.
""")
st.caption("Think-for-yourself checks: test pricing / revenue mix, payroll or operating-cost growth, and one-off / non-recurring expenses. Validate each cause using invoice, payroll, headcount, contract and ledger detail before stating it as a finding.")

st.download_button("Download monthly P&L CSV", monthly.to_csv(index=False).encode("utf-8"),
                   "task11_monthly_pnl.csv", "text/csv")
st.download_button("Download expense detail with vendor/category", expenses.to_csv(index=False).encode("utf-8"),
                   "task11_expense_analysis.csv", "text/csv")


# Automatically calculated business findings and internal ledger tie-out
st.divider()
st.header("Task 11 – Findings and reconciliation evidence")

findings = monthly.copy().sort_values("posting_period")
findings["revenue_growth_pct"] = findings["revenue"].pct_change() * 100
findings["margin_change_pp"] = findings["margin_pct"].diff()

st.subheader("Three data-backed findings")
growth_margin_drop = findings[
    (findings["revenue_growth_pct"] > 0) & (findings["margin_change_pp"] < 0)
]
if not growth_margin_drop.empty:
    worst = growth_margin_drop.sort_values("margin_change_pp").iloc[0]
    st.markdown(
        f"**1. Revenue growth did not always improve profitability.** "
        f"In {worst['posting_period']}, revenue increased by "
        f"{worst['revenue_growth_pct']:.2f}% from the previous month, while "
        f"profit margin fell by {abs(worst['margin_change_pp']):.2f} percentage points "
        f"to {worst['margin_pct']:.2f}%. Check expense growth, pricing and revenue mix "
        f"for that month."
    )
else:
    st.markdown("**1. Revenue and margin:** No month with rising revenue and falling margin was detected in the current ledger period.")

all_expenses = expenses.groupby("account_name", dropna=False, as_index=False)["amount_excl_gst"].sum()
all_expenses = all_expenses.sort_values("amount_excl_gst", ascending=False)
if len(all_expenses):
    top_cat = all_expenses.iloc[0]
    cat_total = all_expenses["amount_excl_gst"].sum()
    cat_share = (top_cat["amount_excl_gst"] / cat_total * 100) if cat_total else 0
    st.markdown(
        f"**2. Expense concentration:** {top_cat['account_name']} is the largest expense-register "
        f"category at ₹{top_cat['amount_excl_gst']:,.2f} excluding GST "
        f"({cat_share:.2f}% of expense-register spend). Review rent contracts, locations "
        f"and occupancy before concluding that this spend can be reduced."
    )

all_vendors = expenses.groupby("vendor_name", dropna=False, as_index=False)["amount_excl_gst"].sum()
all_vendors = all_vendors.sort_values("amount_excl_gst", ascending=False)
if len(all_vendors):
    top_vendor = all_vendors.iloc[0]
    vendor_total = all_vendors["amount_excl_gst"].sum()
    vendor_share = (top_vendor["amount_excl_gst"] / vendor_total * 100) if vendor_total else 0
    top5_share = (all_vendors.head(5)["amount_excl_gst"].sum() / vendor_total * 100) if vendor_total else 0
    st.markdown(
        f"**3. Vendor concentration:** {top_vendor['vendor_name']} is the highest-spend vendor "
        f"at ₹{top_vendor['amount_excl_gst']:,.2f} excluding GST ({vendor_share:.2f}% of "
        f"expense-register spend). The top five vendors account for {top5_share:.2f}%; "
        f"review contracts, invoice duplication, service usage and payment terms."
    )

st.subheader("Revenue growth but margin decline – possible causes and proof")
st.dataframe(pd.DataFrame([
    {"Possible cause": "Higher operating costs (payroll, rent, cloud, marketing)",
     "Data that would prove it": "Monthly account-level expense ledger; compare expense growth with revenue growth."},
    {"Possible cause": "Lower-margin revenue mix or discounting",
     "Data that would prove it": "Revenue by service/product, customer, contract, unit price and discount."},
    {"Possible cause": "One-off or timing-related charges",
     "Data that would prove it": "Journal descriptions, invoice dates, accruals, reversals and non-recurring expense flags."},
]), use_container_width=True, hide_index=True)

st.subheader("Internal ledger P&L tie-out")
tieout = monthly[["posting_period", "revenue", "expenses", "profit", "margin_pct"]].copy()
grand = pd.DataFrame([{
    "posting_period": "ALL PERIODS",
    "revenue": tieout["revenue"].sum(),
    "expenses": tieout["expenses"].sum(),
    "profit": tieout["profit"].sum(),
    "margin_pct": (tieout["profit"].sum() / tieout["revenue"].sum() * 100)
        if tieout["revenue"].sum() else 0
}])
tieout_display = pd.concat([tieout, grand], ignore_index=True)
st.dataframe(tieout_display.rename(columns={
    "posting_period": "Month", "revenue": "Revenue", "expenses": "Expenses",
    "profit": "Profit", "margin_pct": "Profit Margin (%)"
}).style.format({
    "Revenue": "₹{:,.2f}", "Expenses": "₹{:,.2f}",
    "Profit": "₹{:,.2f}", "Profit Margin (%)": "{:.2f}%"
}), use_container_width=True, hide_index=True)

st.caption(
    "Important: this is an internal tie-out calculated from fact_ledger using P&L detail accounts only. "
    "The uploaded README.md contains Validation Vault instructions, not headline P&L figures. "
    "Therefore the official README headline reconciliation remains pending until the correct README "
    "sheet/workbook or headline totals are supplied. Expense-register category/vendor totals are "
    "shown separately and are not added again to ledger expenses."
)
st.download_button(
    "Download P&L tie-out table",
    tieout_display.to_csv(index=False).encode("utf-8"),
    "task11_pnl_tieout.csv",
    "text/csv"
)
st.download_button(
    "Download calculated findings",
    pd.DataFrame([
        {"Finding": "Revenue grew but margin fell", "Evidence": (
            f"{worst['posting_period']}: revenue growth {worst['revenue_growth_pct']:.2f}%, "
            f"margin change {worst['margin_change_pp']:.2f} percentage points."
        ) if not growth_margin_drop.empty else "No such month found."},
        {"Finding": "Largest expense category", "Evidence": (
            f"{top_cat['account_name']}: ₹{top_cat['amount_excl_gst']:,.2f} excl. GST."
        ) if len(all_expenses) else "No category data."},
        {"Finding": "Largest vendor", "Evidence": (
            f"{top_vendor['vendor_name']}: ₹{top_vendor['amount_excl_gst']:,.2f} excl. GST."
        ) if len(all_vendors) else "No vendor data."},
    ]).to_csv(index=False).encode("utf-8"),
    "task11_findings.csv",
    "text/csv"
)
