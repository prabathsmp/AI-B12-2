import streamlit as st
from group_chat_bot import run_support_chat, reset_chat_session

st.set_page_config(
    page_title="Intelligent Support Router",
    page_icon="🛍️",
    layout="wide"
)

with st.sidebar:
    st.title("Routing Architecture")
    st.markdown("""
    **Selector Specialists:**
    - `Order_Billing_Specialist`
    - `Payment_Specialist`
    - `Product_Catalog_Specialist`
    - `Warranty_Returns_Specialist`
    """)
    st.divider()
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        reset_chat_session()
        st.rerun()

st.title("🛍️ E-Commerce Multi-Agent Support Portal")
st.caption("Powered by AutoGen Dynamic Selector GroupChat")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display conversation
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        if "agent_name" in message:
            st.caption(f"Handled by: **{message['agent_name']}**")
        st.markdown(message["content"])

user_prompt = st.chat_input("Describe your issue...")

if user_prompt:
    st.session_state.chat_history.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            responses = run_support_chat(user_prompt)

            if responses:
                for resp in responses:
                    agent_name = resp["agent"]
                    agent_content = resp["content"]
                    st.caption(f"Handled by: **{agent_name}**")
                    st.markdown(agent_content)
                    
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "agent_name": agent_name,
                        "content": agent_content
                    })
            else:
                fallback_msg = "Your query was received, but no specialist generated a final resolution."
                st.warning(fallback_msg)
                st.session_state.chat_history.append({"role": "assistant", "content": fallback_msg})