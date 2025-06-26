import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from collections import defaultdict

# ---------------------- Lease Calculations ----------------------

from lease_calculations import (
    calculate_right_of_use_asset,
    generate_cpi_adjusted_payments,
    calculate_lease_liability_from_payments,
    generate_daily_depreciation_schedule,
    generate_amortization_schedule,
)

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
residual_value = st.sidebar.number_input("Guaranteed Residual Value", min_value=0.0, value=0.0)
cpi = st.sidebar.slider("Annual CPI (%)", 0.0, 10.0, 0.0)

# -------------------------- Exemption Detection --------------------------

LOW_VALUE_THRESHOLD = 5000  # Define low value threshold
is_short_term = term_months <= 12 and residual_value == 0
is_low_value = payment < LOW_VALUE_THRESHOLD and asset_class != 'Building'
is_exempt = is_short_term or is_low_value

# Optional: Show user what the app is detecting
st.write("Short-term lease:", is_short_term)
st.write("Low-value lease:", is_low_value)
st.write("Is exempt from IFRS 16?", is_exempt)

# -------------------------- Generate Model --------------------------

if st.sidebar.button("Generate Lease Model"):
    if is_exempt:
        st.warning("⚠️ This lease qualifies for a practical expedient under IFRS 16. No ROU asset or lease liability is recognized.")

        st.markdown("### 📒 Journal Entries (Expense-Only Treatment)")
        expense_entries = [{
            "Date": start_date + relativedelta(months=i),
            "Account": "Dr Lease Expense",
            "Amount": f"${payment:,.0f}"
        } for i in range(term_months)] + [{
            "Date": start_date + relativedelta(months=i),
            "Account": "Cr Bank / Payables",
            "Amount": f"${payment:,.0f}"
        } for i in range(term_months)]
        je_df = pd.DataFrame(expense_entries)
        st.dataframe(je_df)

        st.download_button(
            label="⬇️ Download Journal Entries (CSV)",
            data=je_df.to_csv(index=False),
            file_name=f"{lease_name}_journal_entries_expensed.csv"
        )

        st.markdown("### 📄 Descriptive Notes (IFRS 16)")
        st.text_area("59(d) – Practical expedients", "The entity has elected to apply IFRS 16 practical expedients for short-term or low-value leases, recognizing lease expense directly in profit or loss.")

    else:
        # Existing IFRS 16 logic
        payments = generate_cpi_adjusted_payments(payment, term_months, cpi)
        if residual_value > 0:
            payments[-1] += residual_value

        liability = calculate_lease_liability_from_payments(payments, discount_rate / 100)
        rou_asset = calculate_right_of_use_asset(liability, direct_costs, incentives)
        df, _ = generate_amortization_schedule(start_date, payments, discount_rate / 100, term_months, rou_asset)

        df["Interest (num)"] = df["Interest"].str.replace(",", "").astype(float)
        df["Principal (num)"] = df["Principal"].str.replace(",", "").astype(float)
        df["Depreciation (num)"] = df["Depreciation"].str.replace(",", "").astype(float)
        df["Payment (num)"] = df["Payment"].str.replace(",", "").astype(float)

        st.success("✅ Model generated successfully!")

    # ---------------------- Tab 1: Disclosures ----------------------

    with tab1:
        st.subheader("📄 Amortization Schedule")
        st.dataframe(df, use_container_width=True)
        if residual_value > 0:
            st.markdown(f"**✅ Residual Value Guarantee Included:** ${residual_value:,.0f}")

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

    # ---------------------- Tab 4: Journal Entries ----------------------

    with tab4:
        st.subheader("📒 Journal Entries (IFRS 16)")

        st.markdown("#### Initial Recognition")
        init_je_rows = [
            {"Date": start_date, "Account": "Dr Right-of-use Asset", "Amount": f"${rou_asset:,.0f}"},
            {"Date": start_date, "Account": "Cr Lease Liability (PV of lease payments incl. RVG)", "Amount": f"${liability:,.0f}"}
        ]
        if direct_costs > 0:
            init_je_rows.append({"Date": start_date, "Account": "Dr Initial Direct Costs", "Amount": f"${direct_costs:,.0f}"})
        if incentives > 0:
            init_je_rows.append({"Date": start_date, "Account": "Cr Lease Incentives", "Amount": f"${incentives:,.0f}"})
        if residual_value > 0:
            init_je_rows.append({"Date": start_date, "Account": "🔍 Note", "Amount": f"Includes RVG of ${residual_value:,.0f}"})

        init_je = pd.DataFrame(init_je_rows)
        st.dataframe(init_je, use_container_width=True)

        st.markdown("#### Monthly Lease Entries")
        monthly_entries = []
        for _, row in df.iterrows():
            entry_date = row["Date"]
            monthly_entries.extend([
                {"Date": entry_date, "Account": "Dr Depreciation Expense", "Amount": f"${row['Depreciation']}"},
                {"Date": entry_date, "Account": "Dr Interest Expense", "Amount": f"${row['Interest']}"},
                {"Date": entry_date, "Account": "Cr Bank / Payables", "Amount": f"${row['Payment']}"}
            ])
        journal_df = pd.DataFrame(monthly_entries)
        st.dataframe(journal_df, use_container_width=True)

        st.download_button(
            label="⬇️ Download Journal Entries (CSV)",
            data=journal_df.to_csv(index=False),
            file_name=f"{lease_name}_journal_entries.csv"
        )

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
