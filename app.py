
import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

st.set_page_config(page_title="IFRS 16 - Leases", layout="wide")
st.title("📘 IFRS 16 – Leases")

st.info("""👋 **Welcome to the IFRS 16 – Leases Model Tool!**

Use the panel on the **left sidebar** to enter your lease details (like asset class, term, payments, discount rate, etc.).

Then, click the **'Generate Lease Model'** button to view amortization schedules, journal entries, and summaries.
""")

# Checkbox to show full IFRS 16
show_standard = st.checkbox("📖 Show full IFRS 16 standard")
if show_standard:
    try:
        df = pd.read_csv("ifrs-16-sections.csv")  # This CSV must have three columns: Section, Paragraph, Text
        search = st.text_input("🔍 Search IFRS content").lower()
        for row in df.itertuples(index=False):
            row_data = list(row)
            if len(row_data) >= 3:
                section, paragraph, text = row_data[:3]
                if search in section.lower() or search in paragraph.lower() or search in text.lower():
                    with st.expander(f"{section} – {paragraph}"):
                        st.markdown(text)
    except Exception as e:
        st.error(f"Failed to load IFRS 16 content: {e}")
