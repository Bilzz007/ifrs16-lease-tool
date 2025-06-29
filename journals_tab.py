# journals_tab.py

import streamlit as st
import pandas as pd

def display_journals(tab, df, rou_asset, liability, direct_costs, incentives, lease_name,
                     modification_inputs=None, pre_mod_schedule=None, post_mod_schedule=None):
    with tab:
        st.subheader("Journal Entries")

        # --- Initial Recognition ---
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

        # --- Recurring Journal Entry Example ---
        st.markdown("#### Recurring Monthly Entries")
        sample_entry = df.iloc[0]
        st.code(
            f"Dr Depreciation Expense    ${sample_entry.get('Depreciation', sample_entry.get('Depreciation (num)',0)):,.2f}\n"
            f"Dr Interest Expense        ${sample_entry.get('Interest', sample_entry.get('Interest (num)',0)):,.2f}\n"
            f"Cr Lease Liability         ${sample_entry.get('Principal', sample_entry.get('Principal (num)',0)):,.2f}\n"
            f"Cr Cash/Bank               ${sample_entry.get('Payment', sample_entry.get('Payment (num)',0)):,.2f}"
        )

        # --- Modification Journal Entry ---
        if modification_inputs and pre_mod_schedule is not None and post_mod_schedule is not None:
            st.markdown("---")
            st.markdown("#### Modification / Reassessment Adjustment Entry")

            # Calculate adjustment at modification date
            # (You can refine logic per your detailed business needs)
            mod_date = modification_inputs.get("effective_date")
            pre_last = pre_mod_schedule.iloc[-1] if not pre_mod_schedule.empty else None
            post_first = post_mod_schedule.iloc[0] if not post_mod_schedule.empty else None

            old_liability = pre_last["Closing_Liability"] if pre_last is not None else 0
            new_liability = post_first["Closing_Liability"] if post_first is not None else 0
            old_rou = pre_last["ROU_Balance"] if pre_last is not None else 0
            new_rou = post_first["ROU_Balance"] if post_first is not None else 0

            liability_adj = new_liability - old_liability
            rou_adj = new_rou - old_rou

            adj_entries = []
            if rou_adj > 0:
                adj_entries.append({"Account": "Dr Right-of-use Asset (modification)", "Amount": f"${abs(rou_adj):,.2f}"})
            elif rou_adj < 0:
                adj_entries.append({"Account": "Cr Right-of-use Asset (modification)", "Amount": f"${abs(rou_adj):,.2f}"})

            if liability_adj > 0:
                adj_entries.append({"Account": "Cr Lease Liability (modification)", "Amount": f"${abs(liability_adj):,.2f}"})
            elif liability_adj < 0:
                adj_entries.append({"Account": "Dr Lease Liability (modification)", "Amount": f"${abs(liability_adj):,.2f}"})

            # If further adjustment is needed (e.g. gain/loss if ROU is written off)
            rou_zero = (rou_adj + old_rou) <= 0
            if rou_zero and liability_adj < 0:
                # Per IFRS 16: Gain/loss to P&L if ROU is zero and liability reduced further
                adj_entries.append({"Account": "Dr/Cr Gain or Loss (P&L)", "Amount": f"${abs(liability_adj):,.2f}"})

            if adj_entries:
                st.dataframe(pd.DataFrame(adj_entries), hide_index=True)
                st.markdown(f"**Modification Effective Date:** {mod_date}")
            else:
                st.info("No adjustment entry required at modification.")

            st.markdown("**Modification Reason:**")
            st.write(modification_inputs.get("modification_reason", ""))

        # --- Download Full Schedule ---
        st.download_button(
            label="Download Lease Schedule & Journals (CSV)",
            data=df.to_csv(index=False),
            file_name=f"{lease_name}_full_schedule.csv",
            mime="text/csv"
        )
