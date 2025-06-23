
import streamlit as st
import pandas as pd

st.set_page_config(page_title="IFRS 16 - Leases", layout="wide")
st.title("📘 IFRS 16 – Leases Reference")

st.info("""👋 **Welcome to the Full IFRS 16 Reference Viewer**

Use the checkbox below to expand the full standard with search functionality. This is ideal for management, auditors, and anyone working on IFRS 16 applications.
""")

if st.checkbox("📖 Show full IFRS 16 standard"):
    df = pd.read_csv("ifrs-16-full-structured.csv")
    search = st.text_input("🔍 Search by keyword, section, or paragraph").lower()
    for row in df.itertuples(index=False):
        if len(row) >= 3:
            section, paragraph, text = row
            if search in section.lower() or search in paragraph.lower() or search in text.lower():
                with st.expander(f"{section} – ¶{paragraph}"):
                    st.markdown(text)
