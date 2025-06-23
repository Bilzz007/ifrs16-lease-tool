import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta

# --- Core Functions ---

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

# --- App Setup ---

st.set_page_config("IFRS 16 Lease Model", layout="wide")
st.title("📘 IFRS 16 Lease Accounting Model")

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
discount_rate = st.sidebar.slider("Discount Rate (%)", 0.0, 100.0, 6.0) if rate_input == "Slider" \
    else st.sidebar.number_input("Discount Rate (%)", 0.0, 100.0, 6.0)

direct_costs = st.sidebar.number_input("Initial Direct Costs", 0.0, value=0.0)
incentives = st.sidebar.number_input("Lease Incentives", 0.0, value=0.0)
cpi = st.sidebar.slider("📈 Annual CPI Increase (%)", 0.0, 10.0, 0.0)

LOW_VALUE_THRESHOLD = 5000

if st.sidebar.button("Generate Lease Model"):
    short_term = term_months < 12
    low_value = payment < LOW_VALUE_THRESHOLD

    if short_term or low_value:
        reason = "short-term" if short_term else "low-value"
        st.warning(f"⚠️ Lease '{lease_name}' is **{reason}** and exempt from capitalization.")
    else:
        adjusted = generate_cpi_adjusted_payments(payment, term_months, cpi)
        liability = calculate_lease_liability_from_payments(adjusted, discount_rate / 100)
        rou_asset = calculate_right_of_use_asset(liability, direct_costs, incentives)
        schedule_df, _ = generate_amortization_schedule(start_date, adjusted, discount_rate / 100, term_months, rou_asset)

        # Save to session for tabs
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
# --- Welcome guidance ---
st.success("✅ Model generated successfully! Use the tabs below to review amortization schedule, disclosures, and tests.")
st.info("📌 Use the **left sidebar** to modify lease inputs and generate a new model.")

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📘 Quantitative & Schedule", "📄 Descriptive Disclosures", "🧪 QA Test Suite"])

# --- Tab 1: Quantitative + Amortization ---
with tab1:
    st.subheader("📘 Lease Summary")
    st.markdown(f"""
**Lease Name:** {lease_name}  
**Entity:** {entity}  
**Location:** {location}  
**Asset Class:** {asset_class}  
**Lease Term:** {term_months} months  
**Start Date:** {start_date.strftime('%Y-%m-%d')}  
**Discount Rate:** {discount_rate*100:.2f}%  
**Initial Lease Liability:** ${liability:,.0f}  
**Initial Right-of-use Asset:** ${rou_asset:,.0f}
""")

    st.subheader("📄 Amortization Schedule")
    st.dataframe(df)

    st.subheader("📘 Quantitative Disclosures (IFRS 16)")
    st.markdown(f"""
**Statement of Financial Position**  
- Right-of-use Asset ({asset_class}): ${rou_asset:,.0f}  
- Lease Liability (Opening): ${liability:,.0f}  
- Lease Liability (Closing): $0  

**Statement of Profit or Loss**  
- Depreciation Expense: ${total_depr:,.0f}  
- Interest Expense on Lease Liability: ${total_interest:,.0f}  

**Statement of Cash Flows**  
- Lease Payments (Total): ${total_cash:,.0f}  
- Principal: ${df["Principal (num)"].sum():,.0f}  
- Interest: ${total_interest:,.0f}  
""")

    maturity_df = pd.DataFrame({
        "Year": [(start_date + relativedelta(months=i)).year for i in range(term_months)],
        "Undiscounted Payment": df["Payment (num)"]
    }).groupby("Year").sum().astype(int)

    st.markdown("### 📊 Maturity Analysis (Undiscounted)")
    st.dataframe(maturity_df)

# --- Tab 2: Descriptive Disclosures ---
with tab2:
    st.subheader("📄 General Descriptive Disclosures (IFRS 16: 59–60A)")

    para59a = st.text_area("📌 Nature of leasing activities (IFRS 16:59a)", 
        "The entity leases office buildings, vehicles, and IT equipment under non-cancellable lease contracts.")

    para59b = st.text_area("📌 Expected future cash outflows not included in liabilities (IFRS 16:59b)",
        "Certain leases contain variable payment clauses linked to CPI or usage. Extension and termination options exist but are not reasonably certain.")

    para59c = st.text_area("📌 Restrictions or covenants (IFRS 16:59c)", 
        "Some leases impose restrictions on subleasing, modifications, or use of the leased asset.")

    para59d = st.text_area("📌 Practical expedients applied (IFRS 16:59d)", 
        "The company elected the short-term lease exemption for leases under 12 months and the low-value exemption for IT accessories.")

    para60a = st.text_area("📌 Expense breakdown and policy explanation (IFRS 16:60A)", 
        "Total lease expense includes depreciation of right-of-use assets and interest on lease liabilities. Variable and exempt leases are recognized on a straight-line basis.")

# --- Tab 3: QA Test Suite ---
with tab3:
    st.subheader("🧪 Internal QA Test Suite")

    def try_assert(name, fn):
        try:
            fn()
            st.success(f"✅ {name}")
        except AssertionError as e:
            st.error(f"❌ {name} failed: {str(e)}")

    def test_liability():
        expected = calculate_lease_liability_from_payments(adjusted_payments, discount_rate)
        assert abs(liability - expected) < 1, f"Expected {expected}, got {liability}"

    def test_rou_asset():
        expected = calculate_right_of_use_asset(liability)
        assert abs(rou_asset - expected) < 1, f"Expected {expected}, got {rou_asset}"

    def test_depr_sum():
        schedule = generate_daily_depreciation_schedule(start_date, term_months, rou_asset)
        total = round(sum(row[2] for row in schedule), 2)
        assert abs(total - rou_asset) < 1, f"Depreciation sum {total} != ROU asset {rou_asset}"

    def test_balances():
        df2, _ = generate_amortization_schedule(start_date, adjusted_payments, discount_rate, term_months, rou_asset)
        end_liab = float(df2["Closing Liability"].iloc[-1].replace(",", ""))
        end_rou = float(df2["Right-of-use Asset Closing Balance"].iloc[-1].replace(",", ""))
        assert abs(end_liab) < 1, f"Ending liability not zero: {end_liab}"
        assert abs(end_rou) < 1, f"Ending ROU not zero: {end_rou}"

    try_assert("Lease liability calculation", test_liability)
    try_assert("ROU asset calculation", test_rou_asset)
    try_assert("Depreciation sum", test_depr_sum)
    try_assert("Final balances = 0", test_balances)

# --- Export Button ---
full_disclosure = f"""# IFRS 16 Lease Disclosure – {lease_name}

## Summary
- **Entity:** {entity}
- **Lease Name:** {lease_name}
- **Location:** {location}
- **Asset Class:** {asset_class}
- **Start Date:** {start_date.strftime('%Y-%m-%d')}
- **Term:** {term_months} months
- **Discount Rate:** {discount_rate * 100:.2f}%
- **Initial Liability:** ${liability:,.0f}
- **ROU Asset:** ${rou_asset:,.0f}

## Amortization Table (Summary)
{df.to_csv(index=False)}

## Quantitative Disclosures
- ROU Asset: ${rou_asset:,.0f}
- Lease Liability (Opening): ${liability:,.0f}
- Depreciation: ${total_depr:,.0f}
- Interest: ${total_interest:,.0f}
- Total Lease Payments: ${total_cash:,.0f}

## Descriptive Disclosures
### IFRS 16:59(a) – Nature of Leasing
{para59a}

### IFRS 16:59(b) – Future Cash Outflows Not Included
{para59b}

### IFRS 16:59(c) – Restrictions / Covenants
{para59c}

### IFRS 16:59(d) – Practical Expedients
{para59d}

### IFRS 16:60A – Expense Breakdown
{para60a}
"""

st.download_button(
    label="⬇️ Download Full Disclosure as TXT",
    file_name=f"IFRS16_Disclosure_{lease_name.replace(' ', '_')}.txt",
    mime="text/plain",
    data=full_disclosure
)
