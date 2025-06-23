
import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def calculate_lease_liability(payment, rate, n_periods):
    r = rate / 12
    return round(payment * (1 - (1 + r) ** -n_periods) / r, 2)

def calculate_right_of_use_asset(liability, direct_costs=0, incentives=0):
    return round(liability + direct_costs - incentives, 2)

def generate_daily_depreciation_schedule(start_date, term_months, rou_asset):
    end_date = start_date + relativedelta(months=term_months)
    total_days = (end_date - start_date).days
    daily_depreciation = rou_asset / total_days
    schedule = []
    cumulative_depr = 0
    for i in range(term_months):
        month_start = start_date + relativedelta(months=i)
        month_end = month_start + relativedelta(months=1)
        days_in_month = (month_end - month_start).days
        depreciation = round(daily_depreciation * days_in_month, 2)
        cumulative_depr += depreciation
        rou_balance = round(rou_asset - cumulative_depr, 2)
        if i == term_months - 1:
            rou_balance = 0
        schedule.append((i + 1, month_start, depreciation, rou_balance))
    return schedule

def generate_amortization_schedule(start_date, payment, rate, term_months, rou_asset, in_advance=True):
    schedule = []
    liability = calculate_lease_liability(payment, rate, term_months)
    r = rate / 12
    depr_schedule = generate_daily_depreciation_schedule(start_date, term_months, rou_asset)

    for i in range(term_months):
        if in_advance:
            principal = round(payment, 2) if i == 0 else round(payment - liability * r, 2)
            interest = 0 if i == 0 else round(liability * r, 2)
        else:
            interest = round(liability * r, 2)
            principal = round(payment - interest, 2)

        liability -= principal
        liability = 0 if abs(liability) < 1 else round(liability, 2)
        period, date, depreciation, rou_closing = depr_schedule[i]

        schedule.append({
            "Period": period,
            "Date": date,
            "Payment": f"{payment:,.0f}",
            "Interest": f"{interest:,.0f}",
            "Principal": f"{principal:,.0f}",
            "Closing Liability": f"{liability:,.0f}",
            "Depreciation": f"{depreciation:,.0f}",
            "Right-of-use Asset Closing Balance": f"{rou_closing:,.0f}"
        })

    return pd.DataFrame(schedule), rou_asset

st.set_page_config(page_title="IFRS 16 - Leases", layout="wide")
st.title("📘 IFRS 16 – Lease Model")

# Sidebar expand/collapse control
if "sidebar_expanded" not in st.session_state:
    st.session_state.sidebar_expanded = True

def collapse_sidebar():
    st.session_state.sidebar_expanded = False

if st.session_state.sidebar_expanded:
    st.sidebar.header("Lease Inputs")
    lease_name = st.sidebar.text_input("Lease Name", "Lease 1")
    entity = st.sidebar.text_input("Entity", "Entity A")
    location = st.sidebar.text_input("Location", "Main Office")
    asset_class = st.sidebar.selectbox("Asset Class", ["Building", "Equipment", "Vehicle", "Other"])
    start_date = st.sidebar.date_input("Lease Start Date")
    term_months = st.sidebar.number_input("Lease Term (months)", min_value=1, value=24)
    payment = st.sidebar.number_input("Monthly Payment", min_value=0.0, value=10000.0)
    discount_rate = st.sidebar.number_input("Discount Rate (%)", 0.0, 100.0, 6.0, step=0.1)
    direct_costs = st.sidebar.number_input("Initial Direct Costs", min_value=0.0, value=0.0)
    incentives = st.sidebar.number_input("Lease Incentives", min_value=0.0, value=0.0)
    payment_timing = st.sidebar.radio("Payment Timing", ["Advance (Beginning of Period)", "Arrears (End of Period)"])
    generate = st.sidebar.button("Generate Lease Model")

    if generate:
        collapse_sidebar()

        is_short_term = term_months < 12
        is_low_value = payment < 5000

        if is_short_term or is_low_value:
            reasons = []
            if is_short_term:
                reasons.append("short-term")
            if is_low_value:
                reasons.append("low-value")
            reason_text = " and ".join(reasons)
            st.warning(f"⚠️ Lease '{lease_name}' is treated as {reason_text} and exempt from capitalization under IFRS 16.")
            exempt_je = pd.DataFrame([{
                "Date": start_date + relativedelta(months=i),
                "Lease Name": lease_name,
                "JE Debit - Lease Expense": f"{payment:,.0f}",
                "JE Credit - Bank/Payables": f"{payment:,.0f}"
            } for i in range(term_months)])
            st.subheader("📒 Non-Capitalized Lease Journal Entries")
            st.dataframe(exempt_je)
        else:
            liability = calculate_lease_liability(payment, discount_rate / 100, term_months)
            rou_asset = calculate_right_of_use_asset(liability, direct_costs, incentives)

            st.subheader("📘 Summary")
            st.markdown(f"- **Lease:** {lease_name}")
            st.markdown(f"- **Entity:** {entity}")
            st.markdown(f"- **Location:** {location}")
            st.markdown(f"- **Asset Class:** {asset_class}")
            st.markdown(f"- **Start Date:** {start_date.strftime('%Y-%m-%d')}")
            st.markdown(f"- **Term:** {term_months} months")
            st.markdown(f"- **Discount Rate:** {discount_rate}%")
            st.markdown(f"- **Initial Lease Liability:** ${liability:,.0f}")
            st.markdown(f"- **Initial Right-of-use Asset:** ${rou_asset:,.0f}")

            schedule_df, _ = generate_amortization_schedule(
                start_date, payment, discount_rate / 100,
                term_months, rou_asset,
                in_advance=(payment_timing == "Advance (Beginning of Period)")
            )

            st.subheader("📄 Amortization Schedule")
            st.dataframe(schedule_df)
