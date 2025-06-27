import streamlit as st
from input_sidebar import get_user_inputs
from exemption_handler import handle_ifrs16_exemption
from model_engine import run_ifrs16_model

st.set_page_config("IFRS 16 Lease Model", layout="wide")
st.title("📘 IFRS 16 Lease Model Tool")
st.info("Use the sidebar to input lease details and generate IFRS 16 disclosures.")

inputs = get_user_inputs()

if st.sidebar.button("Generate Lease Model"):
    if inputs["low_value_lease"] or inputs["short_term_lease"]:
        handle_ifrs16_exemption(
            start_date=inputs["start_date"],
            term_months=inputs["term_months"],
            payment=inputs["payment"],
            low_value_lease=inputs["low_value_lease"],
            short_term_lease=inputs["short_term_lease"]
        )
        st.stop()

    run_ifrs16_model(inputs)
