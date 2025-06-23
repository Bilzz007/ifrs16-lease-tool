import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

def calculate_lease_liability(payment, rate, n_periods):
    r = rate / 12
    return round(payment * (1 - (1 + r) ** -n_periods) / r, 2)

def calculate_rou_asset(liability, direct_costs=0, incentives=0):
    return round(liability + direct_costs - incentives, 2)

def generate_amortization_schedule(start_date, payment, rate, n_periods, rou_asset):
    schedule = []
    liability = calculate_lease_liability(payment, rate, n_periods)
    r = rate / 12
    actual_day = start_date.day
    first_period_fraction = (30 - actual_day + 1) / 30 if actual_day > 1 else 1
    depreciation_full = rou_asset / n_periods
    depreciation_first = depreciation_full * first_period_fraction

    cumulative_depreciation = 0
    for i in range(n_periods):
        interest = liability * r
        principal = payment - interest
        liability -= principal

        depreciation = depreciation_first if i == 0 else depreciation_full
        cumulative_depreciation += depreciation
        rou_closing = round(max(0, rou_asset - cumulative_depreciation), 0)

        # Round liability and clean up "-0"
        liability_rounded = round(liability, 0)
        if abs(liability_rounded) < 1:
            liability_rounded = 0

        schedule.append({
            "Period": i + 1,
            "Date": start_date + relativedelta(months=i),
            "Payment": f"{payment:,.0f}",
            "Interest": f"{interest:,.0f}",
            "Principal": f"{principal:,.0f}",
            "Closing Liability": f"{liability_rounded:,.0f}",
            "Depreciation": f"{depreciation:,.0f}",
            "ROU Closing Balance": f"{rou_closing:,.0f}"
        })
    return pd.DataFrame(schedule), rou_asset

st.set_page_config(page_title="IFRS 16 Lease Model v2", layout="wide")
st.title("📘 IFRS 16 Lease Model Tool — v2")

st.sidebar.header("Lease Inputs")
lease_name = st.sidebar.text_input("Lease Name", "Lease A")
entity = st.sidebar.text_input("Entity", "Entity A")
location = st.sidebar.text_input("Location", "Main Office")
asset_class = st.sidebar.selectbox("Asset Class", ["Building", "Equipment", "Vehicle", "Other"])
start_date = st.sidebar.date_input("Lease Start Date", datetime.today())
term_months = st.sidebar.number_input("Lease Term (months)", min_value=1, value=24)
payment = st.sidebar.number_input("Monthly Payment", min_value=0.0, value=10000.0)

use_slider = st.sidebar.radio("Discount Rate Input Method", ["Slider", "Manual Entry"])
if use_slider == "Slider":
    discount_rate = st.sidebar.slider("Discount Rate (%)", 0.0, 100.0, 6.0, step=0.1)
else:
    discount_rate = st.sidebar.number_input("Discount Rate (%)", 0.0, 100.0, 6.0, step=0.1)

direct_costs = st.sidebar.number_input("Initial Direct Costs", min_value=0.0, value=0.0)
incentives = st.sidebar.number_input("Lease Incentives", min_value=0.0, value=0.0)
cpi = st.sidebar.slider("📈 Annual CPI Increase (%)", 0.0, 10.0, 0.0)

LOW_VALUE_THRESHOLD = 5000

if st.sidebar.button("Generate Lease Model"):
    is_short_term = term_months < 12
    is_low_value = payment < LOW_VALUE_THRESHOLD

    if is_short_term or is_low_value:
        reason = "short-term" if is_short_term else "low-value"
        st.warning(f"⚠️ Lease '{lease_name}' is automatically treated as **{reason}** and exempt from capitalization under IFRS 16.")
        st.subheader("📒 Non-Capitalized Lease Journal Entries")
        exempt_je = pd.DataFrame([{
            "Date": start_date + relativedelta(months=i),
            "Lease Name": lease_name,
            "JE Debit - Lease Expense": f"{payment:,.0f}",
            "JE Credit - Bank/Payables": f"{payment:,.0f}"
        } for i in range(term_months)])
        st.dataframe(exempt_je)
    else:
        liability = calculate_lease_liability(payment, discount_rate / 100, term_months)
        rou_asset = calculate_rou_asset(liability, direct_costs, incentives)
        st.write(f"**Initial Lease Liability:** ${liability:,.0f}  |  **Initial ROU Asset:** ${rou_asset:,.0f}")

        st.subheader("📄 Amortization Schedule")
        schedule_df, _ = generate_amortization_schedule(start_date, payment, discount_rate / 100, term_months, rou_asset)
        st.dataframe(schedule_df)

        st.subheader("📘 Summary")
        st.markdown(f"""
        - **Lease:** {lease_name}  
        - **Entity:** {entity}  
        - **Location:** {location}  
        - **Asset Class:** {asset_class}  
        - **Start Date:** {start_date.strftime('%Y-%m-%d')}  
        - **Term:** {term_months} months  
        - **Discount Rate:** {discount_rate}%  
        - **CPI Adjustment:** {cpi}% annually
        """)
