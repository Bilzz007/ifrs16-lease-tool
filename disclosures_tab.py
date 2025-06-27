# disclosures_tab.py
import streamlit as st
import pandas as pd
from typing import Dict

def display_disclosures(tab, df: pd.DataFrame, reporting_date):
    with tab:
        st.subheader("Financial Statement Disclosures")

        from lease_calculations import calculate_lease_metrics
        metrics: Dict[str, Dict[str, float]] = calculate_lease_metrics(df, reporting_date)

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

        st.markdown("#### Amortization Schedule")
        st.dataframe(df, hide_index=True, use_container_width=True)
