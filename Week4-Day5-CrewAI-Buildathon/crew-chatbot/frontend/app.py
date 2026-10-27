import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

st.set_page_config(page_title="Multi-Agent Customer Support", layout="wide")
st.title("🤖 Multi-Agent Customer Support System")

user_query = st.text_input("Enter your support query or task:", placeholder="e.g., How do I reset my password?")

if st.button("Submit Query", type="primary"):
    if not user_query.strip():
        st.warning("Please provide a query first.")
    else:
        with st.spinner("Crew is processing: Assistant -> Web Search -> Logging..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/run-crew",
                    json={"query": user_query},
                    timeout=120
                )
                if response.status_code == 200:
                    data = response.json()
                    st.success("Completed and saved to answers.txt!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("1. Direct Assistant Answer")
                        st.info(data.get("direct_answer", "No response provided."))
                    
                    with col2:
                        st.subheader("2. Web Search Assistant Answer")
                        st.info(data.get("web_search_answer", "No response provided."))
                else:
                    st.error(f"Backend error ({response.status_code}): {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Failed to connect to backend: {e}")