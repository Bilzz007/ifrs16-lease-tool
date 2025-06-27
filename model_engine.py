import streamlit as st
import pandas as pd
from typing import Dict
from lease_calculations import (
    calculate_right_of_use_asset,
    generate_variable_payments,
    calculate_lease_liability,
    generate_lease_schedule,
    calculate_lease_metrics,
)
from disclosures_tab import display_disclosures
from notes_tab import display_notes
from qa_tab import display_qa
from journals_tab import display_journals


def run_ifrs16_model(inputs: Dict):
    try:
        # === Handle IFRS 16 Exemptions ===
        if inputs["low_value_lease"]:
            st.warning("Lease qualifies as a **Low-value Lease Exemption** under IFRS 16. No ROU or Lease Liability recognized.")
            return

        if inputs["short_term_lease"]:
            st.warning("Lease qualifies as a **Short-term Lease Exemption** under IFRS 16. No ROU or Lease Liability recognized.")
            return

        # === Sanity Checks ===
        if inputs["residual_value"] >= inputs["payment"] * inputs["term_months"]:
            st.error("Residual value cannot exceed total lease payments")
            return

        # === Payments & Schedules ===
        payments = generate_variable_payments(
            inputs["payment"],
            inputs["term_months"],
            annual_cpi_percent=inputs["cpi"]
        )

        if inputs["residual_value"] > 0:
            payments[-1] += inputs["residual_value"]

        liability = calculate_lease_liability(payments, inputs["discount_rate"] / 100)
        rou_asset = calculate_right_of_use_asset(
            liability,
            inputs["direct_costs"],
            inputs["incentives"]
        )

        if inputs["residual_value"] >= rou_asset:
            st.error("Residual value must be less than right-of-use asset value")
            return

        df, _ = generate_lease_schedule(
            start_date=inputs["start_date"],
            payments=payments,
            discount_rate=inputs["discount_rate"] / 100,
            term_months=inputs["term_months"],
            rou_asset=rou_asset,
            residual_value=inputs["residual_value"]
        )

        # === Clean & Format Data ===
        numeric_cols = [
            "Interest",
            "Principal",
            "Depreciation",
            "Payment",
            "Closing_Liability",
            "ROU_Balance"
        ]

        for col in numeric_cols:
            if pd.api.types.is_string_dtype(df[col]):
                df[col + " (num)"] = df[col].str.replace(",", "").astype(float)
            else:
                df[col + " (num)"] = df[col]

        # Rename columns for display
        df.rename(columns=lambda col: col.replace("_", " "), inplace=True)
        df.rename(columns={"ROU Balance": "ROU_Balance"}, inplace=True)

        st.success("Model generated successfully!")

        # === Display Tabs ===
        tab1, tab2, tab3, tab4 = st.tabs(["Disclosures", "Notes", "QA", "Journals"])
        display_disclosures(tab1, df, pd.to_datetime(inputs["reporting_date"]))
        display_notes(tab2, df, payments)
        display_qa(tab3, df)
        display_journals(
            tab4,
            df,
            rou_asset,
            liability,
            inputs["direct_costs"],
            inputs["incentives"],
            inputs["lease_name"]
        )

    except Exception as e:
        st.error(f"Error generating lease model: {str(e)}")
