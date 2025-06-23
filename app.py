import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# --- Core Calculations ---

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

def generate_amortization_schedule(start_date, payment, rate, term_months, rou_asset):
    schedule = []
    liability = calculate_lease_liability(payment, rate, term_months)
    r = rate / 12
    depr_schedule = generate_daily_depreciation_schedule(start_date, term_months, rou_asset)
    for i in range(term_months):
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

# --- UI Setup ---

st.set_page_config(page_title="IFRS 16 - Leases", layout="wide")
st.title("📘 IFRS 16 – Leases")

st.info("""👋 **Welcome to the IFRS 16 – Leases Model Tool!**

You can add and generate models for **multiple leases** below. Each lease will have its own tab with inputs and schedules.
""")

num_leases = st.number_input("How many leases do you want to add?", min_value=1, value=1, step=1)
tabs = st.tabs([f"Lease {i+1}" for i in range(num_leases)])
LOW_VALUE_THRESHOLD = 5000

# --- Loop through each Lease ---
for i, tab in enumerate(tabs):
    with tab:
        st.header(f"Lease {i+1} Inputs")
        lease_name = st.text_input(f"Lease Name {i+1}", f"Lease {i+1}", key=f"lease_name_{i}")
        entity = st.text_input(f"Entity {i+1}", "Entity A", key=f"entity_{i}")
        location = st.text_input(f"Location {i+1}", "Main Office", key=f"location_{i}")
        asset_class = st.selectbox(f"Asset Class {i+1}", ["Building", "Equipment", "Vehicle", "Other"], key=f"asset_class_{i}")

        lease_input_mode = st.radio(f"Define Lease Term By {i+1}:", ["Number of Periods", "Start and End Dates"], key=f"input_mode_{i}")

        if lease_input_mode == "Number of Periods":
            start_date = st.date_input(f"Lease Start Date {i+1}", key=f"start_date_{i}")
            period_unit = st.selectbox(f"Period Unit {i+1}", ["Months", "Quarters", "Years"], key=f"period_unit_{i}")
            period_count = st.number_input(f"Number of Periods {i+1}", min_value=1, value=24, key=f"period_count_{i}")
            term_months = period_count * {"Months": 1, "Quarters": 3, "Years": 12}[period_unit]
        else:
            start_date = st.date_input(f"Lease Start Date {i+1}", key=f"start_date_range_{i}")
            end_date = st.date_input(f"Lease End Date {i+1}", start_date + relativedelta(months=24), key=f"end_date_{i}")
            term_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

        payment = st.number_input(f"Monthly Payment {i+1}", min_value=0.0, value=10000.0, key=f"payment_{i}")

        use_slider = st.radio(f"Discount Rate Input Method {i+1}", ["Slider", "Manual Entry"], key=f"rate_mode_{i}")
        if use_slider == "Slider":
            discount_rate = st.slider(f"Discount Rate (%) {i+1}", 0.0, 100.0, 6.0, step=0.1, key=f"rate_slider_{i}")
        else:
            discount_rate = st.number_input(f"Discount Rate (%) {i+1}", 0.0, 100.0, 6.0, step=0.1, key=f"rate_input_{i}")

        direct_costs = st.number_input(f"Initial Direct Costs {i+1}", min_value=0.0, value=0.0, key=f"direct_{i}")
        incentives = st.number_input(f"Lease Incentives {i+1}", min_value=0.0, value=0.0, key=f"incentive_{i}")
        cpi = st.slider(f"📈 Annual CPI Increase (%) {i+1}", 0.0, 10.0, 0.0, key=f"cpi_{i}")

        if st.button(f"Generate Lease Model {i+1}", key=f"generate_button_{i}"):
            is_short_term = term_months < 12
            is_low_value = payment < LOW_VALUE_THRESHOLD

            if is_short_term or is_low_value:
                reason = "short-term" if is_short_term else "low-value"
                st.warning(f"⚠️ Lease '{lease_name}' is automatically treated as **{reason}** and exempt from capitalization under IFRS 16.")
                st.subheader("📒 Non-Capitalized Lease Journal Entries")
                exempt_je = pd.DataFrame([{
                    "Date": start_date + relativedelta(months=j),
                    "Lease Name": lease_name,
                    "JE Debit - Lease Expense": f"{payment:,.0f}",
                    "JE Credit - Bank/Payables": f"{payment:,.0f}"
                } for j in range(term_months)])
                st.dataframe(exempt_je)
            else:
                liability = calculate_lease_liability(payment, discount_rate / 100, term_months)
                rou_asset = calculate_right_of_use_asset(liability, direct_costs, incentives)

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
- **Initial Lease Liability:** ${liability:,.0f}  
- **Initial Right-of-use Asset:** ${rou_asset:,.0f}
""")

                st.subheader("📄 Schedule for Lease Liability and Depreciation")
                schedule_df, _ = generate_amortization_schedule(start_date, payment, discount_rate / 100, term_months, rou_asset)
                st.dataframe(schedule_df)

                st.subheader("🔍 Model QA Assistant")

                def run_qa_checks(df):
                    errors = []
                    if df["Right-of-use Asset Closing Balance"].iloc[-1] != "0":
                        errors.append("❌ Right-of-use asset should reduce to 0 by end of lease.")
                    if df["Closing Liability"].iloc[-1] != "0":
                        errors.append("❌ Lease liability should be zero at the end.")
                    if not errors:
                        return ["✅ All basic checks passed."]
                    return errors

                test_results = run_qa_checks(schedule_df)
                for result in test_results:
                    st.markdown(f"- {result}")
