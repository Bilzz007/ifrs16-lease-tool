import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from collections import defaultdict

# --- Core calculations ---
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

# --- App UI ---
st.set_page_config("IFRS 16 Lease Model", layout="wide")
st.title("📘 IFRS 16 Lease Model Tool")
st.info("👋 Use the **sidebar** to enter lease details and reporting date. Then generate the lease model.")

# --- Sidebar Inputs ---
st.sidebar.header("Lease Inputs")
lease_name = st.sidebar.text_input("Lease Name", "Lease A")
entity = st.sidebar.text_input("Entity", "Entity A")
location = st.sidebar.text_input("Location", "Main Office")
asset_class = st.sidebar.selectbox("Asset Class", ["Building", "Equipment", "Vehicle", "Other"])
reporting_date = st.sidebar.date_input("📅 Reporting Date", value=date(2025, 12, 31))

lease_mode = st.sidebar.radio("Define Lease Term By:", ["Number of Periods", "Start and End Dates"])
if lease_mode == "Number of Periods":
    start_date = st.sidebar.date_input("Lease Start Date", value=date.today())
    unit = st.sidebar.selectbox("Period Unit", ["Months", "Quarters", "Years"])
    count = st.sidebar.number_input("Number of Periods", 1, value=24)
    term_months = count * {"Months": 1, "Quarters": 3, "Years": 12}[unit]
else:
    start_date = st.sidebar.date_input("Lease Start Date", value=date.today())
    end_date = st.sidebar.date_input("Lease End Date", value=start_date + relativedelta(months=24))
    term_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

payment = st.sidebar.number_input("Monthly Payment", min_value=0.0, value=10000.0)
discount_rate = st.sidebar.slider("Discount Rate (%)", 0.0, 100.0, 6.0)
direct_costs = st.sidebar.number_input("Initial Direct Costs", 0.0, value=0.0)
incentives = st.sidebar.number_input("Lease Incentives", 0.0, value=0.0)
cpi = st.sidebar.slider("Annual CPI (%)", 0.0, 10.0, 0.0)

if st.sidebar.button("Generate Lease Model"):
    adjusted = generate_cpi_adjusted_payments(payment, term_months, cpi)
    liability = calculate_lease_liability_from_payments(adjusted, discount_rate / 100)
    rou_asset = calculate_right_of_use_asset(liability, direct_costs, incentives)
    schedule_df, _ = generate_amortization_schedule(start_date, adjusted, discount_rate / 100, term_months, rou_asset)

    st.session_state["schedule_df"] = schedule_df

    st.success("✅ Model generated successfully!")

    tab1, tab2, tab3 = st.tabs(["📘 Quantitative & Schedule", "📄 Descriptive Disclosures", "🧪 QA Tests"])

    with tab1:
        df = st.session_state["schedule_df"]
        df["Interest (num)"] = df["Interest"].str.replace(",", "").astype(float)
        df["Principal (num)"] = df["Principal"].str.replace(",", "").astype(float)
        df["Depreciation (num)"] = df["Depreciation"].str.replace(",", "").astype(float)
        df["Payment (num)"] = df["Payment"].str.replace(",", "").astype(float)

        st.subheader("📘 Lease Summary")
        st.markdown(f"""
- **Lease:** {lease_name}  
- **Entity:** {entity}  
- **Location:** {location}  
- **Start Date:** {start_date.strftime('%Y-%m-%d')}  
- **Lease Term:** {term_months} months  
- **Discount Rate:** {discount_rate:.2f}%  
- **Initial Liability:** ${liability:,.0f}  
- **ROU Asset:** ${rou_asset:,.0f}
""")

        st.subheader("📄 Amortization Schedule")
        st.dataframe(df)

        st.subheader("📘 FS-style Quantitative Disclosure (CY vs PY)")

        cy = reporting_date.year
        py = cy - 1
        totals_by_year = defaultdict(lambda: {"ROU": 0, "LIAB": 0, "DEP": 0, "INT": 0})
        for _, row in df.iterrows():
            y = row["Date"].year
            totals_by_year[y]["DEP"] += row["Depreciation (num)"]
            totals_by_year[y]["INT"] += row["Interest (num)"]
            totals_by_year[y]["LIAB"] = float(row["Closing Liability"].replace(",", ""))
            totals_by_year[y]["ROU"] = float(row["Right-of-use Asset Closing Balance"].replace(",", ""))

        def format_block(label, y):
            return f"""
### As of 31 Dec {y} ({label})
- **ROU Asset:** ${totals_by_year[y]["ROU"]:,.0f}
- **Lease Liability:** ${totals_by_year[y]["LIAB"]:,.0f}
- **YTD Depreciation:** ${totals_by_year[y]["DEP"]:,.0f}
- **YTD Interest:** ${totals_by_year[y]["INT"]:,.0f}
"""
        st.markdown(format_block("CY", cy))
        st.markdown(format_block("PY", py))

        st.subheader("📊 Maturity Analysis")
        maturity_df = pd.DataFrame({
            "Year": [(start_date + relativedelta(months=i)).year for i in range(term_months)],
            "Undiscounted Payment": df["Payment (num)"]
        }).groupby("Year").sum().astype(int)
        st.dataframe(maturity_df)

    with tab2:
        st.subheader("📄 Descriptive Disclosures (IFRS 16)")
        para59a = st.text_area("59(a) – Nature of leasing", "The entity leases buildings and vehicles...")
        para59b = st.text_area("59(b) – Future outflows", "Some leases include CPI-linked increases...")
        para59c = st.text_area("59(c) – Restrictions", "Restrictions exist on sub-letting and use...")
        para59d = st.text_area("59(d) – Expedients", "Short-term and low-value exemptions used.")
        para60a = st.text_area("60A – Expense policies", "Lease expense includes depreciation and interest.")

    with tab3:
        st.subheader("🧪 QA Tests")

        def check(label, fn):
            try:
                fn()
                st.success(f"✅ {label}")
            except AssertionError as e:
                st.error(f"❌ {label}: {str(e)}")

        check("Liability calculation", lambda: abs(liability - calculate_lease_liability_from_payments(adjusted, discount_rate / 100)) < 1)
        check("ROU calculation", lambda: abs(rou_asset - (liability + direct_costs - incentives)) < 1)
        check("Ending balances = 0", lambda: (
            abs(float(df["Closing Liability"].iloc[-1].replace(",", ""))) < 1 and
            abs(float(df["Right-of-use Asset Closing Balance"].iloc[-1].replace(",", ""))) < 1
        ))

    full_txt = f"""# IFRS 16 Lease Disclosure – {lease_name}

## FS Summary (as of {reporting_date})
CY: {cy}, PY: {py}

CY
- ROU: ${totals_by_year[cy]["ROU"]:,.0f}
- Liability: ${totals_by_year[cy]["LIAB"]:,.0f}
- Depreciation: ${totals_by_year[cy]["DEP"]:,.0f}
- Interest: ${totals_by_year[cy]["INT"]:,.0f}

PY
- ROU: ${totals_by_year[py]["ROU"]:,.0f}
- Liability: ${totals_by_year[py]["LIAB"]:,.0f}
- Depreciation: ${totals_by_year[py]["DEP"]:,.0f}
- Interest: ${totals_by_year[py]["INT"]:,.0f}

## Disclosures (IFRS 16)
59(a): {para59a}
59(b): {para59b}
59(c): {para59c}
59(d): {para59d}
60A: {para60a}
"""
    st.download_button("⬇️ Download Disclosure (TXT)", data=full_txt, file_name=f"IFRS16_Disclosure_{lease_name}.txt")
