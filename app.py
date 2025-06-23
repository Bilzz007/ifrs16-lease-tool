
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

            lease_input_mode = st.radio("Define Lease Term By:", ["Number of Periods", "Start and End Dates"], key=f"input_mode_{i}")

            if lease_input_mode == "Number of Periods":
                start_date = st.date_input("Lease Start Date", key=f"start_date_{i}")
                period_unit = st.selectbox("Period Unit", ["Months", "Quarters", "Years"], key=f"period_unit_{i}")
                period_count = st.number_input("Number of Periods", min_value=1, value=24, key=f"period_count_{i}")
                term_months = period_count * {"Months": 1, "Quarters": 3, "Years": 12}[period_unit]
            else:
                start_date = st.date_input("Lease Start Date", key=f"start_date_range_{i}")
                end_date = st.date_input("Lease End Date", start_date + relativedelta(months=24), key=f"end_date_{i}")
                term_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)

            payment = st.number_input("Monthly Payment", min_value=0.0, value=10000.0, key=f"payment_{i}")
            use_slider = st.radio("Discount Rate Input Method", ["Slider", "Manual Entry"], key=f"rate_mode_{i}")
            if use_slider == "Slider":
                discount_rate = st.slider("Discount Rate (%)", 0.0, 100.0, 6.0, step=0.1, key=f"rate_slider_{i}")
            else:
                discount_rate = st.number_input("Discount Rate (%)", 0.0, 100.0, 6.0, step=0.1, key=f"rate_input_{i}")

            direct_costs = st.number_input("Initial Direct Costs", min_value=0.0, value=0.0, key=f"direct_{i}")
            incentives = st.number_input("Lease Incentives", min_value=0.0, value=0.0, key=f"incentive_{i}")
            cpi = st.slider("📈 Annual CPI Increase (%)", 0.0, 10.0, 0.0, key=f"cpi_{i}")
            payment_timing = st.radio("Payment Timing", ["Advance (Beginning of Period)", "Arrears (End of Period)"], key=f"payment_timing_{i}")

            submitted = st.form_submit_button("Generate Lease Model")

            if submitted:
                errors = []
                if not lease_name.strip():
                    errors.append("Lease Name is required.")
                if not start_date:
                    errors.append("Start Date is required.")
                if term_months <= 0:
                    errors.append("Lease Term must be greater than zero.")
                if payment <= 0:
                    errors.append("Monthly Payment must be greater than zero.")
                if discount_rate <= 0:
                    errors.append("Discount Rate must be greater than zero.")

                if errors:
                    st.error("Please fix the following before continuing:")
                    for e in errors:
                        st.markdown(f"- {e}")
                    continue

                is_short_term = term_months < 12
                is_low_value = payment < LOW_VALUE_THRESHOLD

                if is_short_term or is_low_value:
                    reason = "short-term" if is_short_term else "low-value"
                    st.warning(f"⚠️ Lease '{lease_name}' is exempt from capitalization under IFRS 16 due to being **{reason}**.")
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
                    st.subheader("📘 Summary (Before Change)")
                    st.markdown(f"- Lease: {lease_name}  
- Entity: {entity}  
- Term: {term_months} months  
- Discount Rate: {discount_rate}%  
- Initial Lease Liability: ${liability:,.0f}  
- Initial Right-of-use Asset: ${rou_asset:,.0f}")

                    st.subheader("📄 Schedule Before Change")
                    schedule_df, _ = generate_amortization_schedule(start_date, payment, discount_rate / 100, term_months, rou_asset, in_advance=(payment_timing == "Advance (Beginning of Period)"))
                    st.dataframe(schedule_df)

                    st.subheader("🔁 Reassessment or Modification (Optional)")
                    enable_change = st.checkbox("Enable Reassessment / Modification", key=f"enable_change_{i}")
                    if enable_change:
                        change_type = st.radio("Change Type", ["Reassessment", "Modification"], key=f"change_type_{i}")
                        effective_date = st.date_input("Effective Date of Change", key=f"effective_date_{i}")
                        revised_term_months = st.number_input("Revised Lease Term (months)", min_value=1, value=term_months, key=f"revised_term_{i}")
                        revised_payment = st.number_input("Revised Monthly Payment", min_value=0.0, value=payment, key=f"revised_payment_{i}")
                        revised_discount_rate = st.number_input("Revised Discount Rate (%)", 0.0, 100.0, value=discount_rate, key=f"revised_rate_{i}")

                        if effective_date <= start_date:
                            st.warning("Effective date must be after lease start.")
                        else:
                            original_schedule = generate_amortization_schedule(start_date, payment, discount_rate / 100, term_months, rou_asset, in_advance=(payment_timing == "Advance (Beginning of Period)"))[0]
                            liability_before = float(original_schedule[original_schedule["Date"] == effective_date]["Closing Liability"].replace(",", "").values[0]) if effective_date in original_schedule["Date"].values else liability
                            new_liability = calculate_lease_liability(revised_payment, revised_discount_rate / 100, revised_term_months)
                            rou_after = calculate_right_of_use_asset(new_liability)

                            impact_df = pd.DataFrame({
                                "Item": ["Lease Liability", "Right-of-use Asset", "Remaining Lease Term", "Monthly Payment", "Discount Rate"],
                                "Before Change": [liability_before, rou_asset, term_months, payment, discount_rate],
                                "After Change": [new_liability, rou_after, revised_term_months, revised_payment, revised_discount_rate],
                                "Impact (Δ)": [round(new_liability - liability_before, 2), round(rou_after - rou_asset, 2), revised_term_months - term_months, revised_payment - payment, round(revised_discount_rate - discount_rate, 2)]
                            })
                            st.subheader("📊 Before vs After Impact at Effective Date")
                            st.dataframe(impact_df)

                            st.subheader("📄 Revised Amortization Schedule After Change")
                            new_schedule_df, _ = generate_amortization_schedule(effective_date, revised_payment, revised_discount_rate / 100, revised_term_months, rou_after, in_advance=(payment_timing == "Advance (Beginning of Period)"))
                            st.dataframe(new_schedule_df)

                            if change_type == "Modification":
                                st.subheader("📘 Adjustment Entry (Modification)")
                                je = pd.DataFrame([{
                                    "Date": effective_date,
                                    "JE Debit - Right-of-use Asset": f"{round(rou_after - rou_asset):,.0f}",
                                    "JE Credit - Lease Liability": f"{round(new_liability - liability_before):,.0f}"
                                }])
                                st.dataframe(je)
