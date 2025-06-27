# journals_tab.py
import streamlit as st
import pandas as pd

def display_journals(tab, df, rou_asset, liability, direct_costs, incentives, lease_name):
    with tab:
        st.subheader("Journal Entries")

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

        st.markdown("#### Recurring Monthly Entries")
        sample_entry = df.iloc[0]
        st.code(
            f"Dr Depreciation Expense    ${sample_entry['Depreciation (num)']:,.2f}\n"
            f"Dr Interest Expense        ${sample_entry['Interest (num)']:,.2f}\n"
            f"Cr Lease Liability         ${sample_entry['Principal (num)']:,.2f}\n"
            f"Cr Cash/Bank               ${sample_entry['Payment (num)']:,.2f}"
        )

        st.download_button(
            label="Download Journal Entries (CSV)",
            data=df.to_csv(index=False),
            file_name=f"{lease_name}_journal_entries.csv",
            mime="text/csv"
        )
