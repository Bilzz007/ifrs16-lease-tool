import streamlit as st
import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from lease_calculations import (
    calculate_right_of_use_asset,
    generate_variable_payments as generate_cpi_adjusted_payments,
    calculate_lease_liability as calculate_lease_liability_from_payments,
    generate_depreciation_schedule as generate_daily_depreciation_schedule,
    generate_lease_schedule as generate_amortization_schedule,
    calculate_lease_metrics
)

# -------------------------- Streamlit UI --------------------------
st.set_page_config("IFRS 16 Lease Model", layout="wide")
st.title("📘 IFRS 16 Lease Model Tool")
st.info("Use the sidebar to input lease details and generate IFRS 16 disclosures.")

# ------------------------ Sidebar Inputs ------------------------
with st.sidebar:
    st.header("Lease Inputs")

    # Basic lease info
    lease_name = st.text_input("Lease Name", "Lease A")
    entity = st.text_input("Entity", "Entity A")
    location = st.text_input("Location", "Main Office")
    asset_class = st.selectbox("Asset Class", ["Building", "Equipment", "Vehicle", "Other"])
    reporting_date = st.date_input("📅 Reporting Date", value=date(2025, 12, 31))

    # Exemptions
    st.subheader("IFRS 16 Exemptions")
    col1, col2 = st.columns(2)
    with col1:
        low_value_lease = st.checkbox("Low-value Lease")
    with col2:
        short_term_lease = st.checkbox("Short-term Lease")

    # Always ask for term inputs
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

    # Always collect financial terms
    st.subheader("Financial Terms")
    payment = st.number_input("Monthly Payment", min_value=0.0, value=10000.0)
    discount_rate = st.slider("Discount Rate (%)", 0.0, 20.0, 6.0, 0.1)
    direct_costs = st.number_input("Initial Direct Costs", 0.0, value=0.0)
    incentives = st.number_input("Lease Incentives", 0.0, value=0.0)
    residual_value = st.number_input("Guaranteed Residual Value", min_value=0.0, value=0.0,
                                     help="Must be less than ROU asset value")
    cpi = st.slider("Annual CPI Adjustment (%)", 0.0, 10.0, 0.0, 0.1)

# -------------------------- Generate Model --------------------------
if st.sidebar.button("Generate Lease Model"):
    if low_value_lease or short_term_lease:
        st.success("✅ Lease qualifies for IFRS 16 exemption")

        with st.expander("Exemption Details"):
            st.markdown(f"""
            **Exemption Applied:**  
            {'Low-value lease (IFRS 16.5)' if low_value_lease else 'Short-term lease (IFRS 16.6)'}
            
            **Accounting Treatment:**  
            Lease payments are recognized as an expense on a straight-line basis over the lease term.
            """)

            exempt_payments = pd.DataFrame({
                "Period": range(1, term_months + 1),
                "Date": [start_date + relativedelta(months=i) for i in range(term_months)],
                "Lease Expense": [payment] * term_months
            })
            st.dataframe(exempt_payments, hide_index=True)

        with st.expander("Journal Entries"):
            st.markdown("**Initial Recognition:** No ROU asset or liability recorded")
            st.markdown("**Monthly Entries:**")
            st.code("Dr Lease Expense      ${:,.2f}\nCr Cash/Bank          ${:,.2f}".format(payment, payment))
            
    else:
        # Full IFRS 16 accounting
        try:
            # Validate residual value
            if residual_value >= payment * term_months:
                st.error("Residual value cannot exceed total lease payments")
                st.stop()

            # Generate payments
            payments = generate_cpi_adjusted_payments(payment, term_months, cpi)
            if residual_value > 0:
                payments[-1] += residual_value

            # Calculate liability and ROU asset
            liability = calculate_lease_liability_from_payments(payments, discount_rate / 100)
            rou_asset = calculate_right_of_use_asset(liability, direct_costs, incentives)
            
            if residual_value >= rou_asset:
                st.error("Residual value must be less than right-of-use asset value")
                st.stop()

            # Generate schedules
            df, metrics = generate_amortization_schedule(
                start_date=start_date,
                payments=payments,
                discount_rate=discount_rate / 100,
                term_months=term_months,
                rou_asset=rou_asset,
                residual_value=residual_value
            )

            # Convert formatted strings to numbers for calculations
            numeric_cols = ["Interest", "Principal", "Depreciation", "Payment", "Closing Liability", "ROU Balance"]
            for col in numeric_cols:
                df[col+" (num)"] = df[col].str.replace(",", "").astype(float)

            st.success("✅ Model generated successfully!")
            
            # Display results in tabs
            tab1, tab2, tab3, tab4 = st.tabs(["📘 Disclosures", "📄 Notes", "🧪 QA", "📒 Journals"])
            
            with tab1:
                st.subheader("Financial Statement Disclosures")
                
                # Calculate year-end metrics
                metrics = calculate_lease_metrics(df, reporting_date)
                
                # SOFP
                st.markdown("#### Statement of Financial Position")
                sofp_data = {
                    "Description": [
                        "Right-of-use assets",
                        "Lease liabilities - current",
                        "Lease liabilities - non-current"
                    ],
                    f"{reporting_date.year}": [
                        f"${metrics['current_year']['rou_balance']:,.0f}",
                        f"${metrics['current_year']['liability_current']:,.0f}",
                        f"${metrics['current_year']['liability_noncurrent']:,.0f}"
                    ]
                }
                if reporting_date.year - 1 in [d.year for d in df['Date']]:
                    sofp_data[f"{reporting_date.year-1}"] = [
                        f"${metrics['prior_year']['rou_balance']:,.0f}",
                        f"${metrics['prior_year']['liability_current']:,.0f}",
                        f"${metrics['prior_year']['liability_noncurrent']:,.0f}"
                    ]
                st.dataframe(pd.DataFrame(sofp_data), hide_index=True)
                
                # SOCI
                st.markdown("#### Statement of Comprehensive Income")
                soci_data = {
                    "Description": ["Depreciation expense", "Interest expense"],
                    f"{reporting_date.year}": [
                        f"${metrics['current_year']['depreciation']:,.0f}",
                        f"${metrics['current_year']['interest']:,.0f}"
                    ]
                }
                if reporting_date.year - 1 in [d.year for d in df['Date']]:
                    soci_data[f"{reporting_date.year-1}"] = [
                        f"${metrics['prior_year']['depreciation']:,.0f}",
                        f"${metrics['prior_year']['interest']:,.0f}"
                    ]
                st.dataframe(pd.DataFrame(soci_data), hide_index=True)
                
                # Amortization schedule
                st.markdown("#### Amortization Schedule")
                st.dataframe(df, hide_index=True, use_container_width=True)
            
            with tab2:
                st.subheader("Descriptive Disclosures")
                
                st.text_area("59(a) - Leasing Activities",
                            "The entity leases various assets including office space, vehicles, and equipment. "
                            "Leases are classified as operating leases under IFRS 16.", height=100)
                
                st.text_area("59(b) - Future Cash Outflows",
                            f"The entity has undiscounted lease payments totaling ${sum(payments):,.0f} "
                            "over the lease term, with payments subject to CPI adjustments.", height=100)
                
                st.text_area("Depreciation Policy",
                            "Right-of-use assets are depreciated on a straight-line basis over the shorter of "
                            "the lease term or the asset's useful life in accordance with IFRS 16.31.", height=100)
            
            with tab3:
                st.subheader("Quality Assurance Checks")
                
                # Liability check
                liability_check = abs(df["Closing Liability (num)"].iloc[-1]) < 0.01
                st.markdown(f"{"✅" if liability_check else "❌"} Liability amortizes to zero")
                
                # ROU asset check
                rou_check = abs(df["ROU Balance (num)"].iloc[-1]) < 0.01
                st.markdown(f"{"✅" if rou_check else "❌"} ROU asset depreciates to zero")
                
                # Straight-line check
                depr_values = df["Depreciation (num)"][:-1]  # Exclude last period adjustment
                straight_line_check = all(abs(d - depr_values.mean()) < 0.01 for d in depr_values)
                st.markdown(f"{"✅" if straight_line_check else "❌"} Straight-line depreciation verified")
            
            with tab4:
                st.subheader("Journal Entries")
                
                # Initial recognition
                st.markdown("#### Initial Recognition")
                init_entries = [
                    {"Account": "Dr Right-of-use Asset", "Amount": f"${rou_asset:,.2f}"},
                    {"Account": "Cr Lease Liability", "Amount": f"${liability:,.2f}"}
                ]
                if direct_costs > 0:
                    init_entries.append({"Account": "Dr Initial Direct Costs", "Amount": f"${direct_costs:,.2f}"})
                if incentives > 0:
                    init_entries.append({"Account": "Cr Lease Incentives Received", "Amount": f"${incentives:,.2f}"})
                st.dataframe(pd.DataFrame(init_entries), hide_index=True)
                
                # Monthly entries
                st.markdown("#### Recurring Monthly Entries")
                sample_entry = df.iloc[0]
                st.code(
                    f"Dr Depreciation Expense    ${sample_entry['Depreciation (num)']:,.2f}\n"
                    f"Dr Interest Expense        ${sample_entry['Interest (num)']:,.2f}\n"
                    f"Cr Lease Liability         ${sample_entry['Principal (num)']:,.2f}\n"
                    f"Cr Cash/Bank               ${sample_entry['Payment (num)']:,.2f}"
                )
                
                # Download option
                st.download_button(
                    label="📥 Download Journal Entries (CSV)",
                    data=df.to_csv(index=False),
                    file_name=f"{lease_name}_journal_entries.csv",
                    mime="text/csv"
                )
                
        except Exception as e:
            st.error(f"Error generating lease model: {str(e)}")
            st.stop()

# -------------------------- Documentation --------------------------
with st.expander("ℹ️ IFRS 16 Reference"):
    st.markdown("""
    **Key Requirements:**
    - All leases > 12 months and > $5k USD must be capitalized (IFRS 16.9)
    - Right-of-use assets depreciated straight-line (IFRS 16.31)
    - Lease liabilities amortized using effective interest method (IFRS 16.36)
    
    **Exemptions:**
    - Short-term leases (≤ 12 months) - IFRS 16.6
    - Low-value assets (≤ $5k USD) - IFRS 16.5
    """)
