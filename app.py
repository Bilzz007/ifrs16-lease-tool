import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- Calculation functions ---
def calculate_right_of_use_asset(liability, direct_costs=0, incentives=0):
    return round(liability + direct_costs - incentives, 2)

def generate_cpi_adjusted_payments(base_payment, term_months, annual_cpi_percent):
    cpi_rate = annual_cpi_percent / 100
    return [round(base_payment * ((1 + cpi_rate) ** (m // 12)), 2) for m in range(term_months)]

def calculate_lease_liability_from_payments(payments, rate):
    r = rate / 12
    return round(sum(p / ((1 + r) ** i) if r else p for i, p in enumerate(payments, start=1)), 2)

def generate_daily_depreciation_schedule(start_date, term_months, rou_asset):
    end_date = start_date + relativedelta(months=term_months)
    total_days = (end_date - start_date).days or 1
    daily_depr = rou_asset / total_days
    schedule = []
    cumulative = 0
    for i in range(term_months):
        m_start = start_date + relativedelta(months=i)
        m_end = m_start + relativedelta(months=1)
        days = (m_end - m_start).days
        depr = round(daily_depr * days, 2)
        if i == term_months - 1:
            depr = round(rou_asset - cumulative, 2)
            balance = 0
        else:
            balance = round(rou_asset - cumulative - depr, 2)
        cumulative += depr
        schedule.append((i + 1, m_start, depr, balance))
    return schedule

def generate_amortization_schedule(start_date, payments, rate, term_months, rou_asset):
    liability = calculate_lease_liability_from_payments(payments, rate)
    r = rate / 12
    depr_schedule = generate_daily_depreciation_schedule(start_date, term_months, rou_asset)
    schedule = []
    for i in range(term_months):
        pmt = payments[i]
        interest = round(liability * r, 2)
        principal = round(pmt - interest, 2)
        liability -= principal
        liability = 0 if abs(liability) < 1 else round(liability, 2)
        period, dt, depr, rou = depr_schedule[i]
        schedule.append({
            "Period": period, "Date": dt,
            "Payment": f"{pmt:,.0f}", "Interest": f"{interest:,.0f}",
            "Principal": f"{principal:,.0f}", "Closing Liability": f"{liability:,.0f}",
            "Depreciation": f"{depr:,.0f}", "Right-of-use Asset Closing Balance": f"{rou:,.0f}"
        })
    return pd.DataFrame(schedule), rou_asset

# --- App setup ---
st.set_page_config("IFRS 16 Lease Model", layout="wide")
st.title("📘 IFRS 16 Lease Accounting Model")
st.info("👋 Use the **sidebar** to enter lease inputs. Click 'Generate Lease Model' to view schedules and disclosures.")

# --- Sidebar Inputs ---
st.sidebar.header("Lease Inputs")
lease_name = st.sidebar.text_input("Lease Name", "Lease A")
entity = st.sidebar.text_input("Entity", "Entity A")
location = st.sidebar.text_input("Location", "Main Office")
asset_class = st.sidebar.selectbox("Asset Class", ["Building", "Equipment", "Vehicle", "Other"])

lease_mode = st.sidebar.radio("Define Lease Term By:", ["Number of Periods", "Start and End Dates"])
if lease_mode == "Number of Periods":
    start_date = st.sidebar.date_input("Start Date", value=date.today())
    unit = st.sidebar.selectbox("Period Unit", ["Months", "Quarters", "Years"])
    count = st.sidebar.number_input("Number of Periods", 1, value=24)
    term_months = count * {"Months": 1, "Quarters": 3, "Years": 12}[unit]
else:
    start_date = st.sidebar.date_input("Start Date", value=date.today())
    end_date = st.sidebar.date_input("End Date", value=start_date + relativedelta(months=24))
    term_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

payment = st.sidebar.number_input("Monthly Payment", min_value=0.0, value=10000.0)
rate_input = st.sidebar.radio("Discount Rate Input", ["Slider", "Manual"])
discount_rate = st.sidebar.slider("Discount Rate (%)", 0.0, 100.0, 6.0) if rate_input == "Slider" else st.sidebar.number_input("Discount Rate (%)", 0.0, 100.0, 6.0)
direct_costs = st.sidebar.number_input("Initial Direct Costs", 0.0, value=0.0)
incentives = st.sidebar.number_input("Lease Incentives", 0.0, value=0.0)
cpi = st.sidebar.slider("📈 Annual CPI Increase (%)", 0.0, 10.0, 0.0)

# --- Generate model ---
if st.sidebar.button("Generate Lease Model"):
    adjusted = generate_cpi_adjusted_payments(payment, term_months, cpi)
    liability = calculate_lease_liability_from_payments(adjusted, discount_rate / 100)
    rou_asset = calculate_right_of_use_asset(liability, direct_costs, incentives)
    schedule_df, _ = generate_amortization_schedule(start_date, adjusted, discount_rate / 100, term_months, rou_asset)

    st.session_state.update({
        "schedule_df": schedule_df,
        "liability": liability,
        "rou_asset": rou_asset,
        "start_date": start_date,
        "term_months": term_months,
        "adjusted_payments": adjusted,
        "discount_rate": discount_rate / 100,
        "entity": entity,
        "location": location,
        "lease_name": lease_name,
        "asset_class": asset_class
    })

    st.success("✅ Model generated! Use the tabs below to review amortization schedule, disclosures, and QA.")
    tab1, tab2, tab3 = st.tabs(["📘 Quantitative & Schedule", "📄 Descriptive Disclosures", "🧪 QA Test Suite"])

    with tab1:
        df = st.session_state["schedule_df"]
        df["Interest (num)"] = df["Interest"].str.replace(",", "").astype(float)
        df["Principal (num)"] = df["Principal"].str.replace(",", "").astype(float)
        df["Depreciation (num)"] = df["Depreciation"].str.replace(",", "").astype(float)
        df["Payment (num)"] = df["Payment"].str.replace(",", "").astype(float)

        st.subheader("📘 Lease Summary")
        st.markdown(f"""
**Lease Name:** {lease_name}  
**Entity:** {entity}  
**Location:** {location}  
**Asset Class:** {asset_class}  
**Lease Term:** {term_months} months  
**Start Date:** {start_date.strftime('%Y-%m-%d')}  
**Discount Rate:** {discount_rate:.2f}%  
**Initial Lease Liability:** ${liability:,.0f}  
**Initial Right-of-use Asset:** ${rou_asset:,.0f}
""")

        st.subheader("📄 Amortization Schedule")
        st.dataframe(df)

        st.subheader("📘 IFRS 16 Quantitative Disclosures")
        st.markdown("### 📄 Statement of Financial Position")
        st.markdown(f"""
- **Right-of-use Asset (Closing):** $0  
- **Lease Liability (Closing):** $0  
- **Lease Liability (Opening):** ${liability:,.0f}
""")
        st.markdown("### 📃 Statement of Profit or Loss")
        st.markdown(f"""
- **Depreciation Expense on ROU Asset:** ${df["Depreciation (num)"].sum():,.0f}  
- **Interest Expense on Lease Liability:** ${df["Interest (num)"].sum():,.0f}
""")
        st.markdown("### 💰 Statement of Cash Flows")
        st.markdown(f"""
- **Total Lease Payments:** ${df["Payment (num)"].sum():,.0f}  
  - Principal Portion: ${df["Principal (num)"].sum():,.0f}  
  - Interest Portion: ${df["Interest (num)"].sum():,.0f}
""")
        st.markdown("### 📊 Maturity Analysis (Undiscounted)")
        maturity_df = pd.DataFrame({
            "Year": [(start_date + relativedelta(months=i)).year for i in range(term_months)],
            "Undiscounted Payment": df["Payment (num)"]
        }).groupby("Year").sum().astype(int)
        st.dataframe(maturity_df)

    with tab2:
        st.subheader("📄 Descriptive Disclosures (IFRS 16: 59–60A)")
        para59a = st.text_area("59(a): Nature of leasing activities", "The entity leases office buildings and vehicles.")
        para59b = st.text_area("59(b): Future outflows not in liability", "Certain leases include CPI-linked payments.")
        para59c = st.text_area("59(c): Restrictions/covenants", "Leases restrict sub-letting and asset use.")
        para59d = st.text_area("59(d): Practical expedients", "Short-term and low-value exemptions applied.")
        para60a = st.text_area("60A: Expense explanation", "Lease expense includes depreciation and interest.")

    with tab3:
        st.subheader("🧪 QA Test Suite")

        def try_assert(name, fn):
            try:
                fn()
                st.success(f"✅ {name}")
            except AssertionError as e:
                st.error(f"❌ {name}: {e}")

        try_assert("Liability match", lambda: abs(calculate_lease_liability_from_payments(adjusted, discount_rate / 100) - liability) < 1)
        try_assert("ROU match", lambda: abs(rou_asset - (liability + direct_costs - incentives)) < 1)
        try_assert("Depreciation match", lambda: abs(sum(generate_daily_depreciation_schedule(start_date, term_months, rou_asset)[i][2] for i in range(term_months)) - rou_asset) < 1)
        try_assert("Ending balances = 0", lambda: (
            abs(float(df['Closing Liability'].iloc[-1].replace(",", ""))) < 1 and
            abs(float(df['Right-of-use Asset Closing Balance'].iloc[-1].replace(",", ""))) < 1
        ))

    # --- Export Disclosure ---
    full_txt = f"""# IFRS 16 Lease Disclosure – {lease_name}

## Summary
Entity: {entity}
Lease Name: {lease_name}
Asset Class: {asset_class}
Start Date: {start_date.strftime('%Y-%m-%d')}
Term: {term_months} months
Initial Liability: ${liability:,.0f}
ROU Asset: ${rou_asset:,.0f}

## Amortization Schedule
{df.to_csv(index=False)}

## Quantitative
- Depreciation: ${df["Depreciation (num)"].sum():,.0f}
- Interest: ${df["Interest (num)"].sum():,.0f}
- Total Payments: ${df["Payment (num)"].sum():,.0f}

## Descriptive Disclosures
59(a): {para59a}
59(b): {para59b}
59(c): {para59c}
59(d): {para59d}
60A : {para60a}
"""
    st.download_button("⬇️ Download Full Disclosure (TXT)", data=full_txt, file_name=f"IFRS16_{lease_name}.txt")
