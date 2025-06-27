# qa_tab.py
import streamlit as st

def display_qa(tab, df):
    with tab:
        st.subheader("Quality Assurance Checks")

        liability_check = abs(df["Closing Liability (num)"].iloc[-1]) < 0.01
        rou_check = abs(df["ROU Balance (num)"].iloc[-1]) < 0.01
        depr_values = df["Depreciation (num)"][:-1]
        mean_depr = depr_values.mean()
        straight_line_check = all(abs(d - mean_depr) < 0.01 for d in depr_values)

        st.markdown("Liability amortizes to zero: " + ("✅ PASS" if liability_check else "❌ FAIL"))
        st.markdown("ROU asset depreciates to zero: " + ("✅ PASS" if rou_check else "❌ FAIL"))
        st.markdown("Straight-line depreciation verified: " + ("✅ PASS" if straight_line_check else "❌ FAIL"))
