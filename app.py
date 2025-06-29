# app.py

import streamlit as st
from input_sidebar import get_user_inputs
from lease_calculations import (
    generate_variable_payments,
    generate_lease_schedule,
    handle_lease_modification,
    DepreciationMethod,
)
# If you use exemption_handler or disclosures_tab, you can import them as needed

st.set_page_config("IFRS 16 Lease Model", layout="wide")
st.title("📘 IFRS 16 Lease Model Tool")
st.info("Use the form below to input lease details and generate IFRS 16 outputs. Modification/reassessment supported.")

# --- User Inputs ---
submitted, lease_inputs, enable_modification, modification_inputs = get_user_inputs()

if submitted:
    # --- Generate Payments Schedule ---
    payments = generate_variable_payments(
        lease_inputs["payment_amount"],
        lease_inputs["lease_term_months"],
        annual_cpi_percent=lease_inputs["cpi_rate"] if lease_inputs["cpi_escalation"] else 0
    )

    # --- Generate Initial Lease Schedule ---
    rou_asset = lease_inputs["payment_amount"] * lease_inputs["lease_term_months"]  # or your preferred initial ROU logic
    lease_df, lease_metrics = generate_lease_schedule(
        lease_inputs["start_date"],
        payments,
        lease_inputs["discount_rate"],
        lease_inputs["lease_term_months"],
        rou_asset=rou_asset,
        depreciation_method=DepreciationMethod.STRAIGHT_LINE,
        residual_value=0
    )

    # --- Handle Lease Modification / Reassessment ---
    if enable_modification:
        st.success("Modification detected! Calculating before/after impact...")

        # Generate new payment schedule for revised terms
        new_payments = [modification_inputs["new_payment_amount"]] * modification_inputs["new_lease_term_months"]

        mod_schedule = handle_lease_modification(
            original_schedule=lease_df,
            modification_date=modification_inputs["effective_date"],
            new_payments=new_payments,
            new_discount_rate=modification_inputs["new_discount_rate"],
            depreciation_method=DepreciationMethod.STRAIGHT_LINE
        )

        # --- Display After Modification Schedule ---
        st.subheader("Lease Amortization Schedule (After Modification)")
        st.dataframe(mod_schedule)

        st.markdown("**Modification Details:**")
        st.write(modification_inputs)
    else:
        st.subheader("Lease Amortization Schedule")
        st.dataframe(lease_df)

        st.markdown("**Lease Metrics:**")
        st.json(lease_metrics)

    # --- Download Option (optional) ---
    st.download_button(
        label="Download Lease Schedule (CSV)",
        data=lease_df.to_csv(index=False),
        file_name="lease_schedule.csv",
        mime="text/csv"
    )
