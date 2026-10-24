import os
from datetime import datetime
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Advanced Hybrid RAG Studio",
    page_icon="🕸️",
    layout="wide",
)

# Custom Clean CSS
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .chat-bubble-user {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 18px;
        margin-bottom: 10px;
    }
    .chat-bubble-assistant {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 12px;
        padding: 14px 18px;
        margin-bottom: 10px;
    }
    .citation-block {
        border-left: 3px solid #10b981;
        background-color: #ffffff;
        padding: 8px 12px;
        border-radius: 4px;
        margin-top: 6px;
        font-size: 0.85rem;
    }
    .graph-block {
        border-left: 3px solid #6366f1;
        background-color: #ffffff;
        padding: 8px 12px;
        border-radius: 4px;
        margin-top: 6px;
        font-size: 0.85rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------
# State Management
# -------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# -------------------------------------------------------------------
# Sidebar: PDF Ingestion & Engine Status
# -------------------------------------------------------------------
with st.sidebar:
    st.title("⚙️ Engine Controls")

    # Backend Connection Check
    try:
        health_resp = requests.get(f"{BACKEND_URL}/health", timeout=2)
        if health_resp.status_code == 200:
            health_data = health_resp.json()
            st.success("FastAPI Backend: Online")
            st.caption(
                f"Vector Index: {'Ready' if health_data['vector_ready'] else 'Empty'} | "
                f"Neo4j Graph: {'Connected' if health_data['graph_ready'] else 'Disconnected'}"
            )
        else:
            st.warning("Backend returning non-200 status.")
    except Exception:
        st.error("FastAPI Backend Offline. Please run backend.py")

    st.markdown("---")
    st.subheader("📄 Knowledge Ingestion")
    uploaded_file = st.file_uploader("Upload PDF Document", type=["pdf"])

    if uploaded_file is not None:
        if st.button("Index PDF into Vector + Graph", use_container_width=True):
            with st.spinner("Extracting text, embedding & constructing graph..."):
                files = {
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        "application/pdf",
                    )
                }
                try:
                    res = requests.post(
                        f"{BACKEND_URL}/upload-pdf", files=files, timeout=800
                    )
                    if res.status_code == 200:
                        payload = res.json()
                        st.success(
                            f"Indexed {payload['chunks_indexed']} chunks successfully!"
                        )
                    else:
                        st.error(f"Error {res.status_code}: {res.text}")
                except Exception as e:
                    st.error(f"Upload failed: {e}")

    st.markdown("---")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# -------------------------------------------------------------------
# Main UI
# -------------------------------------------------------------------
st.title("🕸️ Advanced Hybrid RAG (Vector + Graph)")
st.caption(
    "Query official documents using synchronized FAISS dense vector search and Neo4j entity graphs."
)

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"""
        <div class="chat-bubble-user">
            <div style="font-size: 0.8rem; font-weight: 600; color: #64748b; margin-bottom: 4px;">User ({msg['time']})</div>
            <div>{msg['content']}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
        <div class="chat-bubble-assistant">
            <div style="font-size: 0.8rem; font-weight: 600; color: #047857; margin-bottom: 4px;">
                Assistant ({msg['time']}) — <span style="color:#2563eb;">{msg.get('mode', 'Hybrid')}</span>
            </div>
            <div style="line-height: 1.6;">{msg['content']}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Citations drawer
        citations = msg.get("citations", [])
        if citations:
            with st.expander("📚 Matched References & Knowledge Graph Evidence"):
                for cit in citations:
                    if cit["type"] == "vector":
                        st.markdown(
                            f"""
                        <div class="citation-block">
                            <strong>📄 Doc Source:</strong> {cit['source']} (Page {cit['page']})<br>
                            <em>"{cit['content']}"</em>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"""
                        <div class="graph-block">
                            <strong>🕸️ Graph Relation:</strong> {cit['source']}<br>
                            <code>{cit['content']}</code>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

# -------------------------------------------------------------------
# Chat Input & Request Execution
# -------------------------------------------------------------------
query_input = st.chat_input("Ask a question about your indexed documents...")

if query_input:
    curr_time = datetime.now().strftime("%I:%M %p")
    st.session_state.messages.append(
        {"role": "user", "content": query_input, "time": curr_time}
    )

    history_payload = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
    ]

    with st.spinner("Synthesizing vector passages and graph nodes..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/query",
                json={"query": query_input, "history": history_payload},
                timeout=60,
            )
            if response.status_code == 200:
                result = response.json()
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": result["answer"],
                        "citations": result["citations"],
                        "mode": result["retrieval_mode"],
                        "time": curr_time,
                    }
                )
            else:
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"Backend Error: {response.status_code} - {response.text}",
                        "citations": [],
                        "mode": "Error",
                        "time": curr_time,
                    }
                )
        except Exception as e:
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"Connection error: {e}",
                    "citations": [],
                    "mode": "Error",
                    "time": curr_time,
                }
            )

    st.rerun()