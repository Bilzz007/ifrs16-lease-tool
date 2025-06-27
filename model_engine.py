import streamlit as st
import pandas as pd
from typing import Dict
from lease_calculations import (
    calculate_right_of_use_asset,
    generate_variable_payments,
    calculate_lease_liability,
    generate_lease_schedule,
    calculate_lease_metrics
)
from disclosures_tab import display_disclosures
from notes_tab import display_notes
from qa_tab import display_qa
from journals_tab import display_journals


def run_ifrs16_model(inputs: Dict):
    try:
        if inputs["residual_value"] >= inputs["payment"] * inputs["term_months"]:
            st.error("Residual value cannot exceed total lease payments")
            return

        payments = generate_variable_payments(
            inputs["payment"],
            inputs["term_months"],
            annual_cpi_percent=inputs["cpi"]
        )

        if inputs["residual_value"] > 0:
            payments[-1] += inputs["residual_value"]

        liability = calculate_lease_liability(
            payments, inputs["discount_rate"] / 100
        )
        rou_asset = calculate_right_of_use_asset(
            liability, inputs["direct_costs"], inputs["incentives"]
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

        # Rename columns to match UI naming convention
        df.rename(columns=lambda col: col.replace("_", " "), inplace=True)

        # Convert numeric columns to float if needed
        numeric_cols = [
            "Interest", "Principal", "Depreciation", "Payment",
            "Closing Liability", "ROU Balance"
        ]
        for col in numeric_cols:
            if pd.api.types.is_string_dtype(df[col]):
                df[col + " (num)"] = df[col].str.replace(",", "").astype(float)
            else:
                df[col + " (num)"] = df[col]

        st.success("Model generated successfully!")

        tab1, tab2, tab3, tab4 = st.tabs(["Disclosures", "Notes", "QA", "Journals"])
        display_disclosures(tab1, df, pd.to_datetime(inputs["reporting_date"]))  # FIXED: date type error
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
