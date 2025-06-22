import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px

# -- Helper Functions --
def calculate_lease_liability(payment, rate, n_periods):
    r = rate / 12
    return round(payment * (1 - (1 + r) ** -n_periods) / r, 2)

def calculate_rou_asset(liability, direct_costs=0, incentives=0):
    return round(liability + direct_costs - incentives, 2)

def generate_amortization_schedule(start_date, payment, rate, n_periods, rou_asset, mod_month=None, new_payment=None, new_term=None, new_rate=None):
    schedule = []
    liability = calculate_lease_liability(payment, rate, n_periods)
    r = rate / 12
    depreciation = rou_asset / n_periods
    total_periods = new_term if mod_month and new_term else n_periods

    if mod_month and new_term and new_payment and new_rate:
        modified_liability = calculate_lease_liability(new_payment, new_rate, new_term - mod_month + 1)
        rou_asset += modified_liability
        depreciation = rou_asset / total_periods

    for i in range(total_periods):
        current_payment = payment
        current_rate = r
        if mod_month and i + 1 >= mod_month:
            if new_payment: current_payment = new_payment
            if new_rate: current_rate = new_rate / 12

        interest = liability * current_rate
        principal = current_payment - interest
        liability -= principal

        schedule.append({
            "Period": i + 1,
            "Date": start_date + timedelta(days=30 * i),
            "Payment": round(current_payment, 2),
            "Interest": round(interest, 2),
            "Principal": round(principal, 2),
            "Closing Liability": round(liability, 2),
            "Depreciation": round(depreciation, 2),
            "ROU Closing Balance": round(rou_asset - depreciation * (i + 1), 2),
            "JE Debit - Interest Expense": round(interest, 2),
            "JE Debit - Depreciation": round(depreciation, 2),
            "JE Credit - Lease Liability": round(principal, 2)
        })

    return pd.DataFrame(schedule), rou_asset

# -- Streamlit Interface --
st.set_page_config(page_title="IFRS 16 Lease Model", layout="wide")
st.title("📘 IFRS 16 Lease Model Tool")

# Sidebar Input
st.sidebar.header("Lease Portfolio")
num_leases = st.sidebar.number_input("Number of Leases", min_value=1, max_value=10, value=1)

lease_data = []
asset_classes = ["Building", "Equipment", "Vehicle", "Other"]

for i in range(num_leases):
    st.sidebar.markdown(f"---\n### Lease {i+1}")
    lease_name = st.sidebar.text_input(f"Lease Name {i+1}", f"Lease {i+1}")
    asset_class = st.sidebar.selectbox(f"Asset Class {i+1}", asset_classes, index=0, key=f"class{i}")
    entity = st.sidebar.text_input(f"Entity {i+1}", "Entity A")
    location = st.sidebar.text_input(f"Location {i+1}", "Head Office")
    start_date = st.sidebar.date_input(f"Start Date {i+1}", datetime.today(), key=f"date{i}")
    term_months = st.sidebar.number_input(f"Lease Term {i+1}", 1, 240, 60, key=f"term{i}")
    payment = st.sidebar.number_input(f"Monthly Payment {i+1}", 0.0, value=10000.0, key=f"payment{i}")
    discount_rate = st.sidebar.slider(f"Discount Rate % {i+1}", 0.0, 20.0, 6.0, key=f"rate{i}")
    direct_costs = st.sidebar.number_input(f"Direct Costs {i+1}", 0.0, value=0.0, key=f"dc{i}")
    incentives = st.sidebar.number_input(f"Incentives {i+1}", 0.0, value=0.0, key=f"inc{i}")
    mod = st.sidebar.checkbox(f"Modification for Lease {i+1}?")
    mod_month, new_payment, new_term, new_rate = None, None, None, None
    if mod:
        mod_month = st.sidebar.number_input(f"Mod Month {i+1}", 1, term_months, 13, key=f"modm{i}")
        new_payment = st.sidebar.number_input(f"New Payment {i+1}", 0.0, value=9000.0, key=f"modpay{i}")
        new_term = st.sidebar.number_input(f"New Term {i+1}", 1, 240, 60, key=f"modterm{i}")
        new_rate = st.sidebar.slider(f"New Rate % {i+1}", 0.0, 20.0, 5.0, key=f"modrate{i}")

    lease_data.append({
        "lease_name": lease_name,
        "asset_class": asset_class,
        "entity": entity,
        "location": location,
        "start_date": start_date,
        "term_months": term_months,
        "payment": payment,
        "discount_rate": discount_rate,
        "direct_costs": direct_costs,
        "incentives": incentives,
        "mod_month": mod_month,
        "new_payment": new_payment,
        "new_term": new_term,
        "new_discount_rate": new_rate
    })

if st.sidebar.button("Generate Lease Models"):
    disclosure_data, monthly_cashflows, qa_messages, auto_comments, summaries = [], [], [], [], []

    for lease in lease_data:
        liability = calculate_lease_liability(lease["payment"], lease["discount_rate"]/100, lease["term_months"])
        rou_asset = calculate_rou_asset(liability, lease["direct_costs"], lease["incentives"])
        sched_df, adjusted_rou = generate_amortization_schedule(
            lease["start_date"], lease["payment"], lease["discount_rate"]/100, lease["term_months"], rou_asset,
            lease["mod_month"], lease["new_payment"], lease["new_term"], lease["new_discount_rate"]/100 if lease["new_discount_rate"] else None
        )

        st.subheader(f"📄 {lease['lease_name']} ({lease['entity']} – {lease['asset_class']})")
        st.write(f"**Initial Lease Liability:** ${liability:,.2f} | **Initial ROU Asset:** ${rou_asset:,.2f}")
        st.code(f"Dr ROU Asset ${rou_asset:,.2f}\nCr Lease Liability ${liability:,.2f}")

        st.dataframe(sched_df)
        csv = sched_df.to_csv(index=False).encode("utf-8")
        st.download_button(f"📥 Download Schedule - {lease['lease_name']}", csv, f"{lease['lease_name']}_schedule.csv", "text/csv")

        disclosure_data.append({
            "Lease Name": lease["lease_name"],
            "Entity": lease["entity"],
            "Location": lease["location"],
            "Asset Class": lease["asset_class"],
            "Start Date": lease["start_date"],
            "Lease Term": lease["term_months"],
            "Monthly Payment": lease["payment"],
            "Rate (%)": lease["discount_rate"],
            "Initial Liability": liability,
            "Initial ROU": rou_asset
        })

        for row in sched_df.itertuples():
            monthly_cashflows.append({
                "Lease Name": lease["lease_name"], "Entity": lease["entity"], "Location": lease["location"],
                "Asset Class": lease["asset_class"], "Date": row.Date, "Payment": row.Payment,
                "Interest": row.Interest, "Principal": row.Principal
            })

        notes = []
        if not lease['lease_name']:
            qa_messages.append("❌ Missing lease name.")
        if lease['discount_rate'] > 15:
            qa_messages.append(f"⚠️ {lease['lease_name']} has a high discount rate ({lease['discount_rate']}%)")
            notes.append("High discount rate — confirm borrowing rate.")
        if lease['term_months'] < 6:
            qa_messages.append(f"⚠️ {lease['lease_name']} has a very short term ({lease['term_months']} months)")
            notes.append("Possible short-term lease exemption.")
        if lease['payment'] == 0:
            qa_messages.append(f"❓ {lease['lease_name']} has zero payments.")
            notes.append("Check for input error or concession.")
        if lease['new_payment'] and lease['new_payment'] != lease['payment']:
            notes.append("Modified payment — check if remeasurement is needed.")
        if lease['new_term'] and lease['new_term'] > lease['term_months']:
            notes.append("Extended term — reassess lease term.")

        if notes:
            auto_comments.append(f"📌 {lease['lease_name']} ({lease['entity']}):\n- " + "\n- ".join(notes))

        summaries.append(f"{lease['lease_name']} at {lease['location']} spans {lease['term_months']} months, rate {lease['discount_rate']}%, paying {lease['payment']}/mo.")

    if qa_messages:
        st.warning("\n".join(qa_messages))
    if auto_comments:
        st.subheader("📝 AI Review Comments")
        for comment in auto_comments:
            st.markdown(comment)
    if summaries:
        st.subheader("📋 Lease Summary")
        for s in summaries:
            st.markdown(f"- {s}")

    st.subheader("📊 Disclosure Table")
    df_disclose = pd.DataFrame(disclosure_data)
    st.dataframe(df_disclose)

    st.subheader("📆 Monthly Cash Flows")
    df_cashflow = pd.DataFrame(monthly_cashflows)
    st.dataframe(df_cashflow)

    chart = px.bar(df_disclose.groupby("Asset Class")[["Initial Liability", "Initial ROU"]].sum().reset_index(),
                   x="Asset Class", y=["Initial Liability", "Initial ROU"],
                   title="Initial Liability vs ROU by Asset Class", barmode="group")
    st.plotly_chart(chart)
