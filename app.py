# Smarter QA Assistant and Auto Commentary with Model Summary

# Existing QA logic + extended rules
st.sidebar.markdown("---")
st.sidebar.subheader("🧠 AI QA Assistant")
st.sidebar.markdown("Checks for unusual assumptions or anomalies, missing fields, or unusual flags.")
qa_messages = []
auto_comments = []
summary_model = []

for lease in lease_data:
    notes = []
    if not lease['lease_name']:
        qa_messages.append("❌ Missing lease name.")
    if lease['discount_rate'] > 15:
        qa_messages.append(f"⚠️ Lease '{lease['lease_name']}' has a high discount rate: {lease['discount_rate']}%")
        notes.append("High discount rate — ensure alignment with incremental borrowing rate.")
    if lease['term_months'] < 6:
        qa_messages.append(f"⚠️ Lease '{lease['lease_name']}' has a very short lease term: {lease['term_months']} months")
        notes.append("Unusually short lease — check if short-term exemption applies.")
    if lease['payment'] == 0:
        qa_messages.append(f"❓ Lease '{lease['lease_name']}' has zero lease payments.")
        notes.append("Lease payment is zero — confirm if this is a concessional lease or an input error.")
    if lease['new_payment'] and lease['payment'] and lease['new_payment'] != lease['payment']:
        notes.append("Lease modified — payment has changed. Remeasurement likely required.")
    if lease['new_term'] and lease['new_term'] > lease['term_months']:
        notes.append("Lease term extended — confirm updated term assessment.")

    if notes:
        auto_comments.append(f"📌 {lease['lease_name']} ({lease['entity']}, {lease['location']}):\n- " + "\n- ".join(notes))

    # Model summary generation
    summary = f"Lease '{lease['lease_name']}' for a {lease['asset_class'].lower()} asset at {lease['location']} (Entity: {lease['entity']}) spans {lease['term_months']} months with a monthly payment of {lease['payment']:.2f}. "
    summary += f"The discount rate applied is {lease['discount_rate']}%. "
    if lease['mod_month']:
        summary += f"A modification is scheduled at month {lease['mod_month']}, adjusting the lease payment to {lease['new_payment']} and possibly extending the lease term to {lease['new_term']} months. "
    if lease['incentives'] > 0:
        summary += f"Lease incentives of {lease['incentives']:.2f} have been factored in. "
    if lease['direct_costs'] > 0:
        summary += f"Direct costs of {lease['direct_costs']:.2f} are included in the initial ROU measurement. "

    summary_model.append(summary.strip())

# Display QA and commentary
if qa_messages:
    st.warning("\n".join(qa_messages))
else:
    st.success("No obvious issues found in lease assumptions.")

if auto_comments:
    st.markdown("---")
    st.subheader("📝 Lease Commentary")
    for comment in auto_comments:
        st.markdown(comment)

if summary_model:
    st.markdown("---")
    st.subheader("📄 Lease Model Summary")
    for line in summary_model:
        st.markdown(f"- {line}")
