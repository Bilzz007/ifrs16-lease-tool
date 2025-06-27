# exemption_handler.py

import pandas as pd
import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta

def handle_ifrs16_exemption(
    start_date: date,
    term_months: int,
    payment: float,
    low_value_lease: bool,
    short_term_lease: bool
) -> None:
    """Displays outputs for IFRS 16 exempt leases (low-value or short-term)."""

    st.success("✔️ Lease qualifies for IFRS 16 exemption")

    exemption_reason = []
    if low_value_lease:
        exemption_reason.append("Low-value lease (IFRS 16.5)")
    if short_term_lease:
        exemption_reason.append("Short-term lease (IFRS 16.6)")

    with st.expander("Exemption Details"):
        st.markdown(f"""
        **Exemption Applied:**  
        {" and ".join(exemption_reason)}

        **Accounting Treatment:**  
        Lease payments are recognized as an expense on a straight-line basis over the lease term.
        """)
        exempt_schedule = pd.DataFrame({
            "Period": list(range(1, term_months + 1)),
            "Date": [start_date + relativedelta(months=i) for i in range(term_months)],
            "Lease Expense": [payment] * term_months
        })
        st.dataframe(exempt_schedule, hide_index=True)

    with st.expander("Journal Entries"):
        st.markdown("**Initial Recognition:** No ROU asset or liability recorded")
        st.markdown("**Monthly Entries:**")
        st.code(f"Dr Lease Expense      ${payment:,.2f}\nCr Cash/Bank          ${payment:,.2f}")
