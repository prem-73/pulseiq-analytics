import streamlit as st

st.set_page_config(
    page_title="PulseIQ Workforce Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 PulseIQ Workforce Analytics")
st.write("Welcome to your HR analytics dashboard!")

st.success("Streamlit application is running successfully.")

st.markdown("### Available Dashboard")
st.write(
    "Select **Workforce Overview** from the left sidebar "
    "to view workforce metrics."
)
