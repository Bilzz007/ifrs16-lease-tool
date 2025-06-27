# notes_tab.py
import streamlit as st

def display_notes(tab, df, payments):
    with tab:
        st.subheader("Descriptive Disclosures")

        st.text_area("59(a) - Leasing Activities", 
                     "The entity leases various assets including office space, vehicles, and equipment.", 
                     height=100)

        st.text_area("59(b) - Future Cash Outflows",
                     f"The entity has undiscounted lease payments totaling ${sum(payments):,.0f}.", 
                     height=100)

        st.text_area("Depreciation Policy",
                     "ROU assets are depreciated straight-line over the lease term in accordance with IFRS 16.31.", 
                     height=100)
