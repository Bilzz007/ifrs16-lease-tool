# input_sidebar.py

import streamlit as st
from datetime import date

def get_user_inputs():
    st.header("Lease Details")

    with st.form("lease_input_form"):
        # --- Main lease fields ---
        lease_description = st.text_input("Lease Description", value="Office Rent")
        start_date = st.date_input("Lease Start Date", value=date.today())
        lease_term_months = st.number_input("Lease Term (months)", min_value=1, value=36)
        payment_amount = st.number_input("Lease Payment Amount", min_value=0.0, value=10000.0, step=1.0)
        payment_frequency = st.selectbox("Payment Frequency", ["Monthly", "Quarterly", "Annually"], index=0)
        discount_rate = st.number_input("Discount Rate (%)", min_value=0.0, max_value=100.0, value=5.0, step=0.01)
        initial_direct_costs = st.number_input("Initial Direct Costs", min_value=0.0, value=0.0, step=1.0)
        lease_incentives = st.number_input("Lease Incentives", min_value=0.0, value=0.0, step=1.0)
        prepayments = st.number_input("Prepayments", min_value=0.0, value=0.0, step=1.0)
        cpi_escalation = st.checkbox("Is lease payment CPI/index-linked?", value=False)
        cpi_rate = 0.0
        if cpi_escalation:
            cpi_rate = st.number_input("Expected Annual CPI/Index Increase (%)", min_value=0.0, value=3.0, step=0.01)

        # --- Exemptions ---
        st.markdown("### Recognition Exemptions")
        is_short_term = st.checkbox("Short-term lease exemption (< 12 months total)?", value=False)
        is_low_value = st.checkbox("Low-value asset exemption?", value=False)

        # --- Lease Modification / Reassessment section ---
        st.markdown("---")
        st.subheader("Lease Modification / Reassessment")
        enable_modification = st.checkbox("Has a lease modification/reassessment event occurred?", value=False)
        modification_inputs = {}
        if enable_modification:
            modification_inputs["effective_date"] = st.date_input("Modification Effective Date", value=date.today())
            modification_inputs["new_lease_term_months"] = st.number_input("Revised Remaining Lease Term (months)", min_value=1, value=12)
            modification_inputs["new_payment_amount"] = st.number_input("Revised Lease Payment Amount", min_value=0.0, value=payment_amount, step=0.01)
            modification_inputs["new_discount_rate"] = st.number_input("Revised Discount Rate (%)", min_value=0.0, max_value=100.0, value=discount_rate, step=0.01)
            modification_inputs["modification_reason"] = st.text_area("Modification Reason (for audit trail)", value="")

        submitted = st.form_submit_button("Submit")

    lease_inputs = {
        "lease_description": lease_description,
        "start_date": start_date,
        "lease_term_months": lease_term_months,
        "payment_amount": payment_amount,
        "payment_frequency": payment_frequency,
        "discount_rate": discount_rate,
        "initial_direct_costs": initial_direct_costs,
        "lease_incentives": lease_incentives,
        "prepayments": prepayments,
        "cpi_escalation": cpi_escalation,
        "cpi_rate": cpi_rate,
        "is_short_term": is_short_term,
        "is_low_value": is_low_value,
    }

    return submitted, lease_inputs, enable_modification, modification_inputs
