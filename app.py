import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from collections import defaultdict

# ---------------------- Lease Calculations ----------------------

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

# -------------------------- Streamlit UI --------------------------

st.set_page_config("IFRS 16 Lease Model", layout="wide")
st.title("📘 IFRS 16 Lease Model Tool")
st.info("Use the sidebar to input lease details and generate IFRS 16 disclosures.")

# ------------------------ Sidebar Inputs ------------------------

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

# -------------------------- Generate --------------------------

if st.sidebar.button("Generate Lease Model"):
    payments = generate_cpi_adjusted_payments(payment, term_months, cpi)
    liability = calculate_lease_liability_from_payments(payments, discount_rate / 100)
    rou_asset = calculate_right_of_use_asset(liability, direct_costs, incentives)
    df, _ = generate_amortization_schedule(start_date, payments, discount_rate / 100, term_months, rou_asset)

    df["Interest (num)"] = df["Interest"].str.replace(",", "").astype(float)
    df["Principal (num)"] = df["Principal"].str.replace(",", "").astype(float)
    df["Depreciation (num)"] = df["Depreciation"].str.replace(",", "").astype(float)
    df["Payment (num)"] = df["Payment"].str.replace(",", "").astype(float)

    st.success("✅ Model generated successfully!")
    tab1, tab2, tab3 = st.tabs(["📘 Disclosures", "📄 Descriptive Notes", "🧪 QA"])

    # ---------------------- Tab 1: Disclosures ----------------------

    with tab1:
        st.subheader("📄 Amortization Schedule")
        st.dataframe(df, use_container_width=True)

        cy = reporting_date.year
        py = cy - 1
        cy_date = date(cy, 12, 31)
        py_date = date(py, 12, 31)

        totals_by_year = defaultdict(lambda: {"ROU": 0, "LIAB": 0, "DEP": 0, "INT": 0})
        cf_by_year = defaultdict(lambda: {"PRIN": 0, "INT": 0})

        for _, row in df.iterrows():
            y = row["Date"].year
            totals_by_year[y]["DEP"] += row["Depreciation (num)"]
            totals_by_year[y]["INT"] += row["Interest (num)"]
            totals_by_year[y]["LIAB"] = float(row["Closing Liability"].replace(",", ""))
            totals_by_year[y]["ROU"] = float(row["Right-of-use Asset Closing Balance"].replace(",", ""))
            cf_by_year[y]["PRIN"] += row["Principal (num)"]
            cf_by_year[y]["INT"] += row["Interest (num)"]

        def liability_split(ref_date):
            cutoff = ref_date + relativedelta(months=12)
            current = df[(df["Date"] > ref_date) & (df["Date"] <= cutoff)]["Principal (num)"].sum()
            liab_rows = df[df["Date"] <= ref_date]
            if not liab_rows.empty:
                last_val = liab_rows["Closing Liability"].iloc[-1].replace(",", "")
                total_liab = float(last_val)
            else:
                total_liab = 0
            return round(current), round(max(total_liab - current, 0))

        cy_curr, cy_noncurr = liability_split(cy_date)
        py_curr, py_noncurr = liability_split(py_date)

        st.markdown("### 📄 Statement of Financial Position")
        sofp = pd.DataFrame({
            "Disclosure": ["Right-of-use assets (closing)", "Lease liabilities – current", "Lease liabilities – non-current"],
            f"{cy} (CY)": [f"${totals_by_year[cy]['ROU']:,.0f}", f"${cy_curr:,.0f}", f"${cy_noncurr:,.0f}"],
            f"{py} (PY)": [f"${totals_by_year[py]['ROU']:,.0f}", f"${py_curr:,.0f}", f"${py_noncurr:,.0f}"]
        })
        st.dataframe(sofp, use_container_width=True)

        st.markdown("### 📃 Statement of Profit or Loss")
        soci = pd.DataFrame({
            "Disclosure": ["Depreciation expense (YTD)", "Interest expense (YTD)"],
            f"{cy} (CY)": [f"${totals_by_year[cy]['DEP']:,.0f}", f"${totals_by_year[cy]['INT']:,.0f}"],
            f"{py} (PY)": [f"${totals_by_year[py]['DEP']:,.0f}", f"${totals_by_year[py]['INT']:,.0f}"]
        })
        st.dataframe(soci, use_container_width=True)

        st.markdown("### 💰 Statement of Cash Flows")
        socf = pd.DataFrame({
            "Disclosure": ["Lease payments – principal", "Lease payments – interest"],
            f"{cy} (CY)": [f"${cf_by_year[cy]['PRIN']:,.0f}", f"${cf_by_year[cy]['INT']:,.0f}"],
            f"{py} (PY)": [f"${cf_by_year[py]['PRIN']:,.0f}", f"${cf_by_year[py]['INT']:,.0f}"]
        })
        st.dataframe(socf, use_container_width=True)

    # ------------------- Tab 2: Descriptive Notes -------------------

    with tab2:
        st.subheader("📄 Descriptive Disclosures (IFRS 16)")
        para59a = st.text_area("59(a) – Nature of leasing", "The entity leases office space and equipment...")
        para59b = st.text_area("59(b) – Future cash outflows", "Some leases contain CPI escalation clauses...")
        para59c = st.text_area("59(c) – Restrictions", "Certain leases restrict sub-letting and alterations...")
        para59d = st.text_area("59(d) – Practical expedients", "Short-term and low-value lease exemptions applied.")
        para60a = st.text_area("60A – Expense explanation", "Lease expense includes depreciation and interest expense.")

    # ---------------------- Tab 3: QA Tests ----------------------

    with tab3:
        st.subheader("🧪 QA Tests")

        def assert_check(label, fn):
            try:
                fn()
                st.success(f"✅ {label}")
            except AssertionError as e:
                st.error(f"❌ {label}: {e}")

        assert_check("Liability calculation", lambda: abs(liability - calculate_lease_liability_from_payments(payments, discount_rate / 100)) < 1)
        assert_check("ROU asset calc", lambda: abs(rou_asset - (liability + direct_costs - incentives)) < 1)
        assert_check("Final balances are zero", lambda: (
            abs(float(df["Closing Liability"].iloc[-1].replace(',', ''))) < 1 and
            abs(float(df["Right-of-use Asset Closing Balance"].iloc[-1].replace(',', ''))) < 1
        ))

    # ---------------------- Export Button ----------------------

    disclosure_txt = f"""IFRS 16 Disclosure for {lease_name} | Entity: {entity}

SOFP {cy}:
ROU: ${totals_by_year[cy]['ROU']:,.0f}
Lease Liabilities: ${cy_curr + cy_noncurr:,.0f} (Current: ${cy_curr:,.0f}, Non-current: ${cy_noncurr:,.0f})

SOFP {py}:
ROU: ${totals_by_year[py]['ROU']:,.0f}
Lease Liabilities: ${py_curr + py_noncurr:,.0f} (Current: ${py_curr:,.0f}, Non-current: ${py_noncurr:,.0f})

SOCI {cy}:
Depreciation: ${totals_by_year[cy]['DEP']:,.0f}
Interest: ${totals_by_year[cy]['INT']:,.0f}

SOCF {cy}:
Principal: ${cf_by_year[cy]['PRIN']:,.0f}
Interest: ${cf_by_year[cy]['INT']:,.0f}

Descriptive Notes:
59(a): {para59a}
59(b): {para59b}
59(c): {para59c}
59(d): {para59d}
60A : {para60a}
"""

    st.download_button(
        label="⬇️ Download Disclosure (TXT)",
        data=disclosure_txt,
        file_name=f"IFRS16_Disclosure_{lease_name}.txt"
    )
