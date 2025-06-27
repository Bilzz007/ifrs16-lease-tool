import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta

def get_user_inputs():
    with st.sidebar:
        st.header("Lease Inputs")
        lease_name = st.text_input("Lease Name", "Lease A")
        entity = st.text_input("Entity", "Entity A")
        location = st.text_input("Location", "Main Office")
        asset_class = st.selectbox("Asset Class", ["Building", "Equipment", "Vehicle", "Other"])
        reporting_date = st.date_input(" Reporting Date", value=date(2025, 12, 31))

        st.subheader("Lease Terms")
        lease_mode = st.radio("Define Lease Term By:", ["Number of Periods", "Start and End Dates"])

        if lease_mode == "Number of Periods":
            start_date = st.date_input("Lease Start Date", value=date.today())
            unit = st.selectbox("Period Unit", ["Months", "Quarters", "Years"])
            count = st.number_input("Number of Periods", 1, value=24)
            term_months = count * {"Months": 1, "Quarters": 3, "Years": 12}[unit]
            end_date = start_date + relativedelta(months=term_months)
        else:
            start_date = st.date_input("Lease Start Date", value=date.today())
            end_date = st.date_input("Lease End Date", value=start_date + relativedelta(months=24))
            term_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

        st.subheader("Financial Terms")
        payment = st.number_input("Monthly Payment", min_value=0.0, value=10000.0)
        discount_rate = st.slider("Discount Rate (%)", 0.0, 20.0, 6.0, 0.1)
        direct_costs = st.number_input("Initial Direct Costs", 0.0, value=0.0)
        incentives = st.number_input("Lease Incentives", 0.0, value=0.0)
        residual_value = st.number_input("Guaranteed Residual Value", min_value=0.0, value=0.0)
        cpi = st.slider("Annual CPI Adjustment (%)", 0.0, 10.0, 0.0, 0.1)

    # === Auto-detect exemptions ===
    low_value_lease = payment < 5000
    short_term_lease = term_months < 12

    return {
        "lease_name": lease_name,
        "entity": entity,
        "location": location,
        "asset_class": asset_class,
        "reporting_date": reporting_date,
        "low_value_lease": low_value_lease,
        "short_term_lease": short_term_lease,
        "start_date": start_date,
        "end_date": end_date,
        "term_months": term_months,
        "payment": payment,
        "discount_rate": discount_rate,
        "direct_costs": direct_costs,
        "incentives": incentives,
        "residual_value": residual_value,
        "cpi": cpi,
    }
