
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
st.title("📘 IFRS 16 – Leases")

st.info("You can now model up to **10 leases**, with full support for reassessments or modifications.")

num_leases = st.number_input("How many leases do you want to add?", min_value=1, max_value=10, value=1, step=1)
LOW_VALUE_THRESHOLD = 5000

for i in range(num_leases):
    with st.expander(f"Lease {i+1}", expanded=(i == 0)):
        with st.form(f"lease_form_{i}"):
            lease_name = st.text_input("Lease Name", f"Lease {i+1}", key=f"lease_name_{i}")
            entity = st.text_input("Entity", "Entity A", key=f"entity_{i}")
            location = st.text_input("Location", "Main Office", key=f"location_{i}")
            asset_class = st.selectbox("Asset Class", ["Building", "Equipment", "Vehicle", "Other"], key=f"asset_class_{i}")
            start_date = st.date_input("Lease Start Date", key=f"start_date_{i}")
            term_months = st.number_input("Lease Term (months)", min_value=1, value=24, key=f"term_months_{i}")
            payment = st.number_input("Monthly Payment", min_value=0.0, value=10000.0, key=f"payment_{i}")
            discount_rate = st.number_input("Discount Rate (%)", 0.0, 100.0, 6.0, step=0.1, key=f"rate_input_{i}")
            direct_costs = st.number_input("Initial Direct Costs", min_value=0.0, value=0.0, key=f"direct_{i}")
            incentives = st.number_input("Lease Incentives", min_value=0.0, value=0.0, key=f"incentive_{i}")
            payment_timing = st.radio("Payment Timing", ["Advance (Beginning of Period)", "Arrears (End of Period)"], key=f"payment_timing_{i}")

            submitted = st.form_submit_button("Generate Lease Model")

            if submitted:
                if not lease_name or term_months <= 0 or payment <= 0 or discount_rate <= 0:
                    st.warning("Please fill all mandatory fields correctly.")
                    continue

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
