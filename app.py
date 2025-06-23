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

# UI layout
st.set_page_config(page_title="IFRS 16 - Leases", layout="wide")
if "sidebar_expanded" not in st.session_state:
    st.session_state.sidebar_expanded = True

def collapse_sidebar():
    st.session_state.sidebar_expanded = False

st.title("📘 IFRS 16 – Lease Model with Reassessment")

st.info("Use the sidebar to enter lease details. After generating, you can optionally apply reassessment/modification.")

LOW_VALUE_THRESHOLD = 5000

if st.session_state.sidebar_expanded:
    st.sidebar.header("Lease Inputs")
    lease_name = st.sidebar.text_input("Lease Name", "Lease A")
    entity = st.sidebar.text_input("Entity", "Entity A")
    location = st.sidebar.text_input("Location", "Main Office")
    asset_class = st.sidebar.selectbox("Asset Class", ["Building", "Equipment", "Vehicle", "Other"])
    start_date = st.sidebar.date_input("Lease Start Date", datetime.today())

    lease_input_mode = st.sidebar.radio("Define Lease Term By:", ["Number of Periods", "Start and End Dates"])
    if lease_input_mode == "Number of Periods":
        period_unit = st.sidebar.selectbox("Period Unit", ["Months", "Quarters", "Years"])
        period_count = st.sidebar.number_input("Number of Periods", min_value=1, value=24)
        term_months = period_count * {"Months": 1, "Quarters": 3, "Years": 12}[period_unit]
    else:
        end_date = st.sidebar.date_input("Lease End Date", start_date + relativedelta(months=24))
        term_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

    payment = st.sidebar.number_input("Monthly Payment", min_value=0.0, value=10000.0)

    use_slider = st.sidebar.radio("Discount Rate Input Method", ["Slider", "Manual Entry"])
    if use_slider == "Slider":
        discount_rate = st.sidebar.slider("Discount Rate (%)", 0.0, 100.0, 6.0, step=0.1)
    else:
        discount_rate = st.sidebar.number_input("Discount Rate (%)", 0.0, 100.0, 6.0, step=0.1)

    direct_costs = st.sidebar.number_input("Initial Direct Costs", min_value=0.0, value=0.0)
    incentives = st.sidebar.number_input("Lease Incentives", min_value=0.0, value=0.0)
    cpi = st.sidebar.slider("📈 Annual CPI Increase (%)", 0.0, 10.0, 0.0)

    generate_model = st.sidebar.button("Generate Lease Model")
if generate_model:
    collapse_sidebar()
    is_short_term = term_months < 12
    is_low_value = payment < LOW_VALUE_THRESHOLD

    if is_short_term or is_low_value:
        reason = "short-term" if is_short_term else "low-value"
        st.warning(f"⚠️ Lease '{lease_name}' is automatically treated as **{reason}** and exempt from capitalization under IFRS 16.")
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

        # -----------------------------
        # 🔁 Reassessment Section
        # -----------------------------
        st.markdown("---")
        st.subheader("🔁 Reassessment or Modification")

        if st.checkbox("Apply reassessment or modification?"):
            effective_date = st.date_input("Effective Date of Change", start_date + relativedelta(months=12))
            new_payment = st.number_input("New Monthly Payment", min_value=0.0, value=payment)
            new_discount_rate = st.number_input("New Discount Rate (%)", min_value=0.0, value=discount_rate)
            new_end_date = st.date_input("New Lease End Date", start_date + relativedelta(months=36))

            new_term_months = (new_end_date.year - effective_date.year) * 12 + (new_end_date.month - effective_date.month)

            classification = "Modification" if (new_term_months != term_months or new_payment != payment) else "Reassessment"
            st.markdown(f"📌 This qualifies as a **{classification}** under IFRS 16.")

            new_liability = calculate_lease_liability(new_payment, new_discount_rate / 100, new_term_months)
            new_rou = calculate_right_of_use_asset(new_liability)

            st.markdown("### 📊 Before vs After (at Effective Date)")
            comparison_df = pd.DataFrame({
                "Metric": ["Lease Liability", "Right-of-use Asset", "Lease Term (months)", "Monthly Payment", "Discount Rate"],
                "Before": [f"${liability:,.0f}", f"${rou_asset:,.0f}", f"{term_months}", f"${payment:,.0f}", f"{discount_rate}%"],
                "After": [f"${new_liability:,.0f}", f"${new_rou:,.0f}", f"{new_term_months}", f"${new_payment:,.0f}", f"{new_discount_rate}%"]
            })
            st.dataframe(comparison_df)

            st.markdown("### 📅 Adjusted Amortization Schedule (Post-Change)")
            adjusted_schedule, _ = generate_amortization_schedule(effective_date, new_payment, new_discount_rate / 100, new_term_months, new_rou)
            st.dataframe(adjusted_schedule)
