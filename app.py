import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from fpdf import FPDF

# Helper functions
def calculate_lease_liability(payment, rate, n_periods):
    r = rate / 12
    return round(payment * (1 - (1 + r) ** -n_periods) / r, 2)

def calculate_rou_asset(liability, direct_costs=0, incentives=0):
    return round(liability + direct_costs - incentives, 2)

def generate_amortization_schedule(start_date, payment, rate, n_periods, rou_asset, mod_month=None, new_payment=None, new_term=None, new_rate=None):
    schedule = []
    liability = calculate_lease_liability(payment, rate, n_periods)
    r = rate / 12
    actual_day = start_date.day
    first_period_fraction = (30 - actual_day + 1) / 30 if actual_day > 1 else 1
    depreciation_full = rou_asset / n_periods
    depreciation_first = depreciation_full * first_period_fraction
    total_periods = new_term if mod_month and new_term else n_periods

    for i in range(total_periods):
        current_payment = payment
        current_rate = r
        if mod_month and i + 1 >= mod_month:
            if new_payment: current_payment = new_payment
            if new_rate: current_rate = new_rate / 12
        interest = liability * current_rate
        principal = current_payment - interest
        liability -= principal
        current_depreciation = depreciation_first if i == 0 else depreciation_full
        schedule.append({
            "Period": i + 1,
            "Date": start_date + relativedelta(months=i),
            "Payment": round(current_payment, 2),
            "Interest": round(interest, 2),
            "Principal": round(principal, 2),
            "Closing Liability": round(liability, 2),
            "Depreciation": round(current_depreciation, 2),
            "ROU Closing Balance": round(rou_asset - depreciation_full * i, 2),
            "JE Debit - Interest Expense": round(interest, 2),
            "JE Debit - Depreciation": round(current_depreciation, 2),
            "JE Credit - Lease Liability": round(principal, 2)
        })
    return pd.DataFrame(schedule), rou_asset

# UI
st.set_page_config(page_title="IFRS 16 Lease Model", layout="wide")
st.title("📘 IFRS 16 Lease Model Tool")

st.sidebar.header("Lease Inputs")
lease_name = st.sidebar.text_input("Lease Name", "Lease A")
entity = st.sidebar.text_input("Entity", "Entity A")
location = st.sidebar.text_input("Location", "Main Office")
asset_class = st.sidebar.selectbox("Asset Class", ["Building", "Equipment", "Vehicle", "Other"])
start_date = st.sidebar.date_input("Lease Start Date", datetime.today())
term_months = st.sidebar.number_input("Lease Term (months)", min_value=1, value=24)
payment = st.sidebar.number_input("Monthly Payment", min_value=0.0, value=10000.0)
discount_rate = st.sidebar.slider("Discount Rate (%)", min_value=0.0, max_value=15.0, value=6.0)
direct_costs = st.sidebar.number_input("Initial Direct Costs", min_value=0.0, value=0.0)
incentives = st.sidebar.number_input("Lease Incentives", min_value=0.0, value=0.0)
short_term = st.sidebar.checkbox("⏱️ Short-Term Lease (<12 months)")
low_value = st.sidebar.checkbox("💸 Low-Value Lease")
cpi = st.sidebar.slider("📈 Annual CPI Increase (%)", 0.0, 10.0, 0.0)

if st.sidebar.button("Generate Lease Model"):
    if short_term or low_value:
        st.warning(f"Lease '{lease_name}' is exempt from IFRS 16 capitalization due to {'short-term' if short_term else 'low-value'} classification.")
        st.write("This lease is treated as an operating expense.")
        st.subheader("📒 Non-Capitalized Lease Journal Entries")
        exempt_je = pd.DataFrame([{
            "Date": start_date + relativedelta(months=i),
            "Lease Name": lease_name,
            "JE Debit - Lease Expense": payment,
            "JE Credit - Bank/Payables": payment
        } for i in range(term_months)])
        st.dataframe(exempt_je)
    else:
        payments = []
        current_payment = payment
        for m in range(term_months):
            if m > 0 and m % 12 == 0:
                current_payment *= (1 + cpi / 100)
            payments.append(round(current_payment, 2))

        liability = sum([p / ((1 + discount_rate / 100 / 12) ** (i + 1)) for i, p in enumerate(payments)])
        rou_asset = calculate_rou_asset(liability, direct_costs, incentives)
        st.write(f"**Initial Lease Liability:** ${liability:,.2f}  |  **Initial ROU Asset:** ${rou_asset:,.2f}")

        st.subheader("📄 Amortization Schedule")
        schedule_df, rou_final = generate_amortization_schedule(start_date, payment, discount_rate / 100, term_months, rou_asset)
        st.dataframe(schedule_df)

        st.subheader("📝 CPI-Adjusted Monthly Payments")
        payment_df = pd.DataFrame({"Month": list(range(1, term_months + 1)), "Payment": payments})
        st.dataframe(payment_df)

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
