import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# ------------------- Core Calculations -------------------

def calculate_right_of_use_asset(liability, direct_costs=0, incentives=0):
    return round(liability + direct_costs - incentives, 2)

def generate_cpi_adjusted_payments(base_payment, term_months, annual_cpi_percent):
    cpi_rate = annual_cpi_percent / 100
    payments = []
    for month in range(term_months):
        year = month // 12
        adjusted_payment = round(base_payment * ((1 + cpi_rate) ** year), 2)
        payments.append(adjusted_payment)
    return payments

def calculate_lease_liability_from_payments(payments, rate):
    r = rate / 12
    if r == 0:
        return round(sum(payments), 2)
    return round(sum(p / ((1 + r) ** i) for i, p in enumerate(payments, start=1)), 2)

def generate_daily_depreciation_schedule(start_date, term_months, rou_asset):
    end_date = start_date + relativedelta(months=term_months)
    total_days = (end_date - start_date).days
    if total_days == 0:
        raise ValueError("Lease term must be at least one day.")
    daily_depreciation = rou_asset / total_days

    schedule = []
    cumulative_depr = 0
    for i in range(term_months):
        month_start = start_date + relativedelta(months=i)
        month_end = month_start + relativedelta(months=1)
        days_in_month = (month_end - month_start).days
        depreciation = round(daily_depreciation * days_in_month, 2)

        if i == term_months - 1:
            depreciation = round(rou_asset - cumulative_depr, 2)
            rou_balance = 0
        else:
            rou_balance = round(rou_asset - cumulative_depr - depreciation, 2)

        cumulative_depr += depreciation
        schedule.append((i + 1, month_start, depreciation, rou_balance))
    return schedule

def generate_amortization_schedule(start_date, payments, rate, term_months, rou_asset):
    schedule = []
    liability = calculate_lease_liability_from_payments(payments, rate)
    r = rate / 12
    depr_schedule = generate_daily_depreciation_schedule(start_date, term_months, rou_asset)

    for i in range(term_months):
        payment_used = payments[i]
        interest = round(liability * r, 2)
        principal = round(payment_used - interest, 2)
        liability -= principal
        liability = 0 if abs(liability) < 1 else round(liability, 2)

        period, date_, depreciation, rou_closing = depr_schedule[i]
        schedule.append({
            "Period": period,
            "Date": date_,
            "Payment": f"{payment_used:,.0f}",
            "Interest": f"{interest:,.0f}",
            "Principal": f"{principal:,.0f}",
            "Closing Liability": f"{liability:,.0f}",
            "Depreciation": f"{depreciation:,.0f}",
            "Right-of-use Asset Closing Balance": f"{rou_closing:,.0f}"
        })
    return pd.DataFrame(schedule), rou_asset

# ------------------- Streamlit UI -------------------

st.set_page_config(page_title="IFRS 16 - Leases", layout="wide")
st.title("📘 IFRS 16 – Leases")

st.info("""👋 **Welcome to the IFRS 16 – Leases Model Tool!**

Use the panel on the **left sidebar** to enter your lease details (like asset class, term, payments, discount rate, etc.).

Then, click the **'Generate Lease Model'** button to view amortization schedules, disclosures, and test results.
""")

st.sidebar.header("Lease Inputs")
lease_name = st.sidebar.text_input("Lease Name", "Lease A")
entity = st.sidebar.text_input("Entity", "Entity A")
location = st.sidebar.text_input("Location", "Main Office")
asset_class = st.sidebar.selectbox("Asset Class", ["Building", "Equipment", "Vehicle", "Other"])

lease_input_mode = st.sidebar.radio("Define Lease Term By:", ["Number of Periods", "Start and End Dates"])

if lease_input_mode == "Number of Periods":
    start_date = st.sidebar.date_input("Lease Start Date", value=date.today())
    period_unit = st.sidebar.selectbox("Period Unit", ["Months", "Quarters", "Years"])
    period_count = st.sidebar.number_input("Number of Periods", min_value=1, value=24)
    term_months = period_count * {"Months": 1, "Quarters": 3, "Years": 12}[period_unit]
else:
    start_date = st.sidebar.date_input("Lease Start Date", value=date.today())
    end_date = st.sidebar.date_input("Lease End Date", start_date + relativedelta(months=24))
    term_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

payment = st.sidebar.number_input("Monthly Payment", min_value=0.0, value=10000.0)

use_slider = st.sidebar.radio("Discount Rate Input Method", ["Slider", "Manual Entry"])
discount_rate = (
    st.sidebar.slider("Discount Rate (%)", 0.0, 100.0, 6.0, step=0.1)
    if use_slider == "Slider"
    else st.sidebar.number_input("Discount Rate (%)", 0.0, 100.0, 6.0, step=0.1)
)

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
        exempt_je = pd.DataFrame([{
            "Date": start_date + relativedelta(months=i),
            "Lease Name": lease_name,
            "JE Debit - Lease Expense": f"{payment:,.0f}",
            "JE Credit - Bank/Payables": f"{payment:,.0f}"
        } for i in range(term_months)])
        st.subheader("📒 Non-Capitalized Lease Journal Entries")
        st.dataframe(exempt_je)

    else:
        adjusted_payments = generate_cpi_adjusted_payments(payment, term_months, cpi)
        liability = calculate_lease_liability_from_payments(adjusted_payments, discount_rate / 100)
        rou_asset = calculate_right_of_use_asset(liability, direct_costs, incentives)

        st.session_state["model_generated"] = True
        st.session_state["liability"] = liability
        st.session_state["rou_asset"] = rou_asset
        st.session_state["start_date"] = start_date
        st.session_state["term_months"] = term_months
        st.session_state["adjusted_payments"] = adjusted_payments
        st.session_state["discount_rate"] = discount_rate / 100
        st.session_state["direct_costs"] = direct_costs
        st.session_state["incentives"] = incentives

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
        schedule_df, _ = generate_amortization_schedule(start_date, adjusted_payments, discount_rate / 100, term_months, rou_asset)
        st.dataframe(schedule_df)
        st.session_state["schedule_df"] = schedule_df

        st.subheader("📘 IFRS 16 Disclosures")

        df = schedule_df.copy()
        df["Interest (num)"] = df["Interest"].str.replace(",", "").astype(float)
        df["Principal (num)"] = df["Principal"].str.replace(",", "").astype(float)
        df["Depreciation (num)"] = df["Depreciation"].str.replace(",", "").astype(float)
        df["Payment (num)"] = df["Payment"].str.replace(",", "").astype(float)

        total_interest = df["Interest (num)"].sum()
        total_depreciation = df["Depreciation (num)"].sum()
        total_cash_outflow = df["Payment (num)"].sum()

        st.markdown(f"""
- **Opening Lease Liability:** ${liability:,.0f}  
- **Closing Lease Liability:** $0  
- **Total Interest Expense:** ${total_interest:,.0f}  
- **Total Depreciation of ROU Asset:** ${total_depreciation:,.0f}  
- **Total Lease Payments / Cash Outflows:** ${total_cash_outflow:,.0f}  
- **ROU Asset Reconciliation:**  
  - Opening: ${rou_asset:,.0f}  
  - Less: Depreciation: ${total_depreciation:,.0f}  
  - Closing: $0  
""")

        maturity_analysis = pd.DataFrame({
            "Year": [(start_date + relativedelta(months=i)).year for i in range(term_months)],
            "Payment": df["Payment (num)"]
        }).groupby("Year").sum().astype(int)

        st.markdown("### 📊 Maturity Analysis (Undiscounted Future Payments)")
        st.dataframe(maturity_analysis)

        st.subheader("🧪 Internal QA Test Suite")

        if st.button("Run QA Tests"):
            def try_assert(name, fn):
                try:
                    fn()
                    st.success(f"✅ {name}")
                except AssertionError as e:
                    st.error(f"❌ {name} failed: {str(e)}")

            def test_liability_from_adjusted():
                expected = calculate_lease_liability_from_payments(adjusted_payments, discount_rate / 100)
                assert abs(liability - expected) < 1, f"Expected {expected}, got {liability}"

            def test_right_of_use_asset():
                expected = calculate_right_of_use_asset(liability, direct_costs, incentives)
                assert abs(rou_asset - expected) < 1, f"Expected {expected}, got {rou_asset}"

            def test_depreciation_sum():
                schedule = generate_daily_depreciation_schedule(start_date, term_months, rou_asset)
                total = round(sum(item[2] for item in schedule), 2)
                assert abs(total - rou_asset) < 1, f"Depreciation sum {total} != ROU asset {rou_asset}"

            def test_final_balances():
                df, _ = generate_amortization_schedule(start_date, adjusted_payments, discount_rate / 100, term_months, rou_asset)
                liability_end = float(str(df["Closing Liability"].iloc[-1]).replace(",", ""))
                rou_end = float(str(df["Right-of-use Asset Closing Balance"].iloc[-1]).replace(",", ""))
                assert abs(liability_end) < 1, f"Ending liability not zero: {liability_end}"
                assert abs(rou_end) < 1, f"Ending ROU not zero: {rou_end}"

            try_assert("CPI-adjusted lease liability", test_liability_from_adjusted)
            try_assert("Right-of-use asset calculation", test_right_of_use_asset)
            try_assert("Depreciation matches asset value", test_depreciation_sum)
            try_assert("Final balances zero-out", test_final_balances)
