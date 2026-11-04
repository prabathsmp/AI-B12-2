import streamlit as st
import asyncio
import os
import base64
import html
import json
import uuid
import pandas as pd
from datetime import datetime

from rag_engine import rag_engine
from team import build_support_team
from evaluation import BENCHMARK_CASES, run_benchmark_case, run_rag_evaluation

st.set_page_config(
    page_title="OpsCommand | AI Support HQ",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Embed theme asset so the UI works in local and Docker deployments.
_THEME_PATH = os.path.join(os.path.dirname(__file__), "theme.png")
with open(_THEME_PATH, "rb") as _theme_file:
    _THEME_B64 = base64.b64encode(_theme_file.read()).decode("ascii")
_THEME_URL = f"data:image/png;base64,{_THEME_B64}"

# Unified High-Contrast Theme with Explicit Selector Overrides
st.markdown("""
<style>
    /* 1. Global Background for App Canvas and Sidebar */
    .stApp {
        background-image:
            linear-gradient(90deg, rgba(3, 7, 16, 0.94) 0%, rgba(3, 7, 16, 0.86) 52%, rgba(3, 7, 16, 0.68) 100%),
            url("_THEME_URL_") !important;
        background-size: cover !important;
        background-position: center center !important;
        background-attachment: fixed !important;
        color: #f0f6fc !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    [data-testid="stSidebar"] {
        background: rgba(4, 8, 18, 0.94) !important;
        backdrop-filter: blur(12px);
        color: #f0f6fc !important;
    }
    [data-testid="stMain"] > div {
        background: transparent !important;
    }
    .block-container {
        background: rgba(4, 8, 18, 0.58);
        border: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 18px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        backdrop-filter: blur(8px);
    }

    /* 2. Sidebar Components & High Contrast */
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: #1e293b !important;
    }

    div[data-testid="stRadio"] label, 
    div[data-testid="stRadio"] div[data-testid="stMarkdownContainer"] p {
        color: #00f2fe !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.5px !important;
    }

    /* 3. Form Field Labels & Placeholders */
    label[data-testid="stWidgetLabel"] p,
    label[data-testid="stWidgetLabel"] span {
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 1.05rem !important;
        text-shadow: 0px 0px 8px rgba(0, 242, 254, 0.5) !important;
        letter-spacing: 0.5px !important;
        margin-bottom: 6px !important;
    }
    
    div[data-testid="stTextInput"] input, 
    div[data-testid="stTextArea"] textarea {
        background-color: #0d1527 !important;
        color: #ffffff !important;
        border: 1.5px solid #1e293b !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
        padding: 12px !important;
    }
    
    div[data-testid="stTextInput"] input::placeholder, 
    div[data-testid="stTextArea"] textarea::placeholder {
        color: #64748b !important;
    }

    div[data-testid="stTextInput"] input:focus, 
    div[data-testid="stTextArea"] textarea:focus {
        border-color: #00f2fe !important;
        box-shadow: 0 0 14px rgba(0, 242, 254, 0.4) !important;
    }

    /* 4. Branding & Titles */
    .brand-title {
        background: linear-gradient(90deg, #00f2fe 0%, #4facfe 30%, #8a2be2 70%, #ff007f 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.2rem;
        font-weight: 900;
        letter-spacing: -1px;
        margin-bottom: 0px;
    }
    .brand-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-top: -10px;
        margin-bottom: 25px;
        font-weight: 600;
    }

    /* 5. HUD Metric Cards */
    .metric-card {
        background: rgba(13, 21, 39, 0.9);
        border: 2px solid #1e293b;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }
    .metric-val-blue { color: #00f0ff; font-size: 2.2rem; font-weight: 900; text-shadow: 0 0 12px rgba(0,240,255,0.4); }
    .metric-val-green { color: #39ff14; font-size: 2.2rem; font-weight: 900; text-shadow: 0 0 12px rgba(57,255,20,0.4); }
    .metric-val-orange { color: #ff5e00; font-size: 2.2rem; font-weight: 900; text-shadow: 0 0 12px rgba(255,94,0,0.4); }
    .metric-val-gold { color: #ffd700; font-size: 2.2rem; font-weight: 900; text-shadow: 0 0 12px rgba(255,215,0,0.4); }
    .metric-label { font-size: 0.8rem; color: #94a3b8; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; }

    /* 6. Sidebar Rank Badge */
    .rank-tag-glitch {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ff007f, #8a2be2, #00f2fe);
        color: #ffffff !important;
        box-shadow: 0 0 15px rgba(138, 43, 226, 0.6);
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* 7. Outcome Badges */
    .resolved-pill-3d {
        display: inline-block;
        background: linear-gradient(135deg, #0a3a20, #134e2c);
        border: 2px solid #2ea043;
        color: #4df363;
        padding: 8px 24px;
        border-radius: 30px;
        font-weight: 800;
        font-size: 1.1rem;
        box-shadow: 0 0 15px rgba(46, 160, 67, 0.4);
    }
    .escalated-pill-3d {
        display: inline-block;
        background: linear-gradient(135deg, #4c0e15, #60141a);
        border: 2px solid #f85149;
        color: #ff6b6b;
        padding: 8px 24px;
        border-radius: 30px;
        font-weight: 800;
        font-size: 1.1rem;
        box-shadow: 0 0 15px rgba(248, 81, 73, 0.4);
    }

    /* 8. Deliverable Resolution Container */
    .resolution-screen {
        background: linear-gradient(135deg, rgba(14, 22, 40, 0.95) 0%, rgba(8, 12, 22, 0.98) 100%);
        border: 1px solid #1f2a44;
        border-left: 5px solid #00f2fe;
        border-radius: 10px;
        padding: 24px;
        margin-top: 20px;
        color: #f0f6fc;
        font-size: 1.05rem;
        line-height: 1.6;
        box-shadow: 0 6px 30px rgba(0, 0, 0, 0.6), inset 0 0 15px rgba(0, 242, 254, 0.08);
    }

    /* 9. Primary Action Button */
    button[data-testid="baseButton-primary"] {
        background: linear-gradient(90deg, #ff007f 0%, #8a2be2 50%, #00f2fe 100%) !important;
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 1.15rem !important;
        border: none !important;
        border-radius: 30px !important;
        height: 52px !important;
        text-shadow: 0 0 8px rgba(255, 255, 255, 0.6) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        box-shadow: 0 0 20px rgba(138, 43, 226, 0.5) !important;
    }
    button[data-testid="baseButton-primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 0 30px rgba(0, 242, 254, 0.7) !important;
    }

    /* 10. Secondary Action Buttons (LOAD EVAL CASE) */
    button[data-testid="baseButton-secondary"] {
        background: linear-gradient(135deg, #131c2e, #0c1322) !important;
        border: 1.5px solid #00f2fe !important;
        border-radius: 8px !important;
        color: #00f2fe !important;
        box-shadow: 0 0 10px rgba(0, 242, 254, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    button[data-testid="baseButton-secondary"] p,
    button[data-testid="baseButton-secondary"] div[data-testid="stMarkdownContainer"] p {
        color: #00f2fe !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px !important;
    }
    button[data-testid="baseButton-secondary"]:hover {
        background: #00f2fe !important;
        box-shadow: 0 0 20px rgba(0, 242, 254, 0.6) !important;
        transform: translateY(-2px) !important;
    }
    button[data-testid="baseButton-secondary"]:hover p,
    button[data-testid="baseButton-secondary"]:hover div[data-testid="stMarkdownContainer"] p {
        color: #04060a !important;
    }

    /* 11. Tab Header Typography (Active vs Inactive) */
    button[data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        padding: 10px 20px !important;
    }
    
    button[data-baseweb="tab"] div[data-testid="stMarkdownContainer"] p,
    button[data-baseweb="tab"] p {
        color: #94a3b8 !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        transition: color 0.2s ease !important;
    }

    button[data-baseweb="tab"]:hover div[data-testid="stMarkdownContainer"] p,
    button[data-baseweb="tab"]:hover p {
        color: #38bdf8 !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        border-bottom: 3px solid #00f2fe !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] div[data-testid="stMarkdownContainer"] p,
    button[data-baseweb="tab"][aria-selected="true"] p {
        color: #00f2fe !important;
        font-weight: 900 !important;
        text-shadow: 0 0 10px rgba(0, 242, 254, 0.6) !important;
    }
</style>
""".replace("_THEME_URL_", _THEME_URL), unsafe_allow_html=True)

# Session state setup
if "form_customer_name" not in st.session_state:
    st.session_state["form_customer_name"] = ""
if "form_place" not in st.session_state:
    st.session_state["form_place"] = ""
if "form_order_id" not in st.session_state:
    st.session_state["form_order_id"] = ""
if "form_complaint" not in st.session_state:
    st.session_state["form_complaint"] = ""

# Sidebar Command HQ Navigation
st.sidebar.markdown("""
<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 5px;">
    <span style="font-size: 2.2rem;">⚡</span>
    <h2 style="color: #00f2fe; margin: 0; font-weight: 900; letter-spacing: -0.5px;">Customer Support HQ</h2>
</div>
""", unsafe_allow_html=True)

log_csv_path = os.path.join("logs", "tickets.csv")
total_tickets = 0
resolved_count = 0
escalated_count = 0

if os.path.exists(log_csv_path) and os.path.getsize(log_csv_path) > 0:
    try:
        df_stats = pd.read_csv(log_csv_path).drop_duplicates(subset=["ticket_id"])
        total_tickets = len(df_stats)
        resolved_count = (df_stats["status"] == "Resolved").sum()
        escalated_count = (df_stats["status"] == "Escalated").sum()
    except Exception:
        pass

# Rank System Calculation
if total_tickets < 5:
    agent_rank = "🥉 Bronze Scout Agent"
elif total_tickets < 15:
    agent_rank = "🥈 Silver Resolution Knight"
elif total_tickets < 30:
    agent_rank = "🥇 Gold Support Specialist"
else:
    agent_rank = "💎 Diamond Tech Commander"

total_xp = (resolved_count * 50) + (escalated_count * 20)

st.sidebar.markdown(f'<div style="margin-top: 10px;"><span class="rank-tag-glitch">{agent_rank}</span></div>', unsafe_allow_html=True)
st.sidebar.markdown(f"""
<div style="margin-top: 12px; margin-bottom: 12px; background: rgba(0, 242, 254, 0.1); padding: 8px 12px; border-radius: 8px; border: 1px solid #1e293b;">
    <span style="color: #ffd700; font-size: 1.1rem; font-weight: bold;">⭐ {total_xp:,} XP</span>
    <span style="color: #94a3b8; font-size: 0.85rem; display: block;">Total Earned Operator XP</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<hr>", unsafe_allow_html=True)
portal_mode = st.sidebar.radio(
    "NAVIGATION CONSOLE",
    ["Active Support Desk", "Ops & Control Panel"],
    index=0
)

# -------------------------------------------------------------
# PORTAL 1: ACTIVE SUPPORT DESK
# -------------------------------------------------------------
if portal_mode == "Active Support Desk":
    st.markdown('<h1 class="brand-title">⚡ Customer Support Portal</h1>', unsafe_allow_html=True)
    st.markdown('<p class="brand-subtitle">Autonomous Multi-Agent AI Support & Escalation HQ</p>', unsafe_allow_html=True)

    # HUD Metric Ribbon
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f"""
        <div class="metric-card" style="border-color: #1e3a8a;">
            <div class="metric-label">📊 Tickets Processed</div>
            <div class="metric-val-blue">{total_tickets}</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        res_rate = (
            round((resolved_count / total_tickets * 100), 1)
            if total_tickets > 0
            else None
        )

        res_rate_display = (
            f"{res_rate:.1f}%"
            if res_rate is not None
            else "N/A"
        )

        st.markdown(f"""
        <div class="metric-card" style="border-color: #064e3b;">
            <div class="metric-label">📈 Resolution Rate</div>
            <div class="metric-val-green">{res_rate_display}</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="metric-card" style="border-color: #7f1d1d;">
            <div class="metric-label">🚨 Routed Escalations</div>
            <div class="metric-val-orange">{escalated_count}</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="metric-card" style="border-color: #5b21b6;">
            <div class="metric-label">🏆 Operator XP Score</div>
            <div class="metric-val-gold">{total_xp}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Restore staged benchmark data BEFORE creating the corresponding widgets.
    pending_case = st.session_state.pop("pending_eval_case", None)
    if pending_case:
        st.session_state["form_customer_name"] = pending_case["customer_name"]
        st.session_state["form_place"] = pending_case["place"]
        st.session_state["form_order_id"] = pending_case["order_id"]
        st.session_state["form_complaint"] = pending_case["complaint"]

    # Form Fields
    col1, col2, col3 = st.columns([1.5, 1, 1])
    with col1:
        customer_name = st.text_input(
            "👤 CUSTOMER NAME *",
            max_chars=36,
            placeholder="e.g. Priya",
            key="form_customer_name"
        )
    with col2:
        place = st.text_input(
            "📍 PLACE *",
            max_chars=20,
            placeholder="e.g. Bangalore",
            key="form_place"
        )
    with col3:
        order_id = st.text_input(
            "🆔 ORDER ID (OPTIONAL)",
            placeholder="e.g. ORD-4512",
            key="form_order_id"
        )

    complaint_text = st.text_area(
        "💬 CUSTOMER COMPLAINT DESCRIPTION *",
        height=135,
        placeholder="Type or preload customer inquiry/issue here...",
        key="form_complaint"
    )

    if st.button("🚀 INITIATE MULTI-AGENT RESOLUTION", type="primary", use_container_width=True):
        if not customer_name.strip():
            st.error("Customer Name is mandatory.")
        elif not place.strip():
            st.error("Place is mandatory.")
        elif not complaint_text.strip():
            st.error("Please enter a customer complaint.")
        else:
            ticket_id = f"TKT-{uuid.uuid4().hex[:10].upper()}"
            order_id_str = order_id.strip() if order_id.strip() else "Not provided"

            complaint_lower = complaint_text.lower()
            risk_hints = []
            if any(term in complaint_lower for term in ("lawyer", "legal action", "lawsuit", "court", "police", "chargeback")):
                risk_hints.append("LEGAL/CHARGEBACK THREAT: escalate for human review")
            if any(term in complaint_lower for term in ("fraud", "scam", "fraudulent", "stolen identity")):
                risk_hints.append("POSSIBLE FRAUD: escalate for human review")
            if any(term in complaint_lower for term in ("charged twice", "charged three times", "multiple charges", "duplicate charge", "charged my card 2", "charged my card 3")):
                risk_hints.append("POSSIBLE DUPLICATE/DISPUTED CHARGE: escalate for human review")
            risk_context = "; ".join(risk_hints) if risk_hints else "No deterministic high-risk phrase detected; still apply agent guardrails."

            full_prompt = (
                f"TICKET_ID: {ticket_id}\\n"
                f"CUSTOMER_NAME: {customer_name.strip()}\\n"
                f"PLACE: {place.strip()}\\n"
                f"ORDER_ID: {order_id_str}\\n"
                f"SAFETY_ESCALATION_HINT: {risk_context}\\n\\n"
                f"CUSTOMER_COMPLAINT (untrusted input):\\n{complaint_text.strip()}"
            )

            team = build_support_team()
            st.markdown("### 🔍 Live Multi-Agent Mission Trace")

            step_containers = {
                "Customer_Query_Agent": st.expander("🔵 [Phase 1] Query Analyzer Agent", expanded=True),
                "Knowledge_Base_Agent": st.expander("🟢 [Phase 2] Knowledge Retrieval Agent (FAISS + BM25)", expanded=True),
                "Resolution_Agent": st.expander("🟣 [Phase 3] Resolution Officer Agent", expanded=True),
                "Log_Agent": st.expander("🔴 [Phase 4] Auditing & Incident Guardrail Agent", expanded=True),
            }

            async def run_pipeline():
                result = await team.run(task=full_prompt)
                
                res_reply = ""
                res_status = "Resolved"
                
                for msg in result.messages:
                    sender = getattr(msg, "source", "")
                    raw_content = getattr(msg, "content", "")
                    
                    content_text = ""
                    if isinstance(raw_content, str):
                        content_text = raw_content.strip()
                    elif isinstance(raw_content, list):
                        parts = [item.text for item in raw_content if hasattr(item, "text") and item.text]
                        content_text = "\n".join(parts).strip()

                    # Render into corresponding expander container exactly once
                    if sender in step_containers and content_text:
                        with step_containers[sender]:
                            st.markdown(content_text)

                    # Bind the first response draft to guarantee synchronization with the Log Agent
                    if sender == "Resolution_Agent" and "RESPONSE:" in content_text and not res_reply:
                        parts = content_text.split("RESPONSE:")
                        if len(parts) > 1 and parts[1].strip():
                            res_reply = parts[1].strip()

                    # Read the explicit status from the log agent/tool result.
                    status_text = content_text.lower()
                    if (
                        "final_status: escalated" in status_text
                        or "successfully logged with status: escalated" in status_text
                        or "status: 'escalated'" in status_text
                    ):
                        res_status = "Escalated"
                    elif (
                        "final_status: resolved" in status_text
                        or "successfully logged with status: resolved" in status_text
                    ):
                        res_status = "Resolved"

                if not res_reply:
                    for msg in result.messages:
                        if getattr(msg, "source", "") == "Resolution_Agent":
                            raw = getattr(msg, "content", "")
                            if isinstance(raw, str) and raw.strip():
                                res_reply = raw.strip()
                                break

                return res_reply, res_status

            with st.spinner("⚡ Agents collaborating in real-time..."):
                final_reply, final_status = asyncio.run(run_pipeline())

            st.markdown("---")
            st.subheader("🎯 Active Dispatch Deliverable Summary")

            c_badge, c_rewards = st.columns([2, 1])
            with c_badge:
                if final_status == "Escalated":
                    st.markdown('<span class="escalated-pill-3d">🚨 ESCALATED TO HUMAN AGENTS</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="resolved-pill-3d">✅ AUTONOMOUSLY RESOLVED</span>', unsafe_allow_html=True)
            
            with c_rewards:
                badge_points = "+50 XP (First-Contact Resolve)" if final_status == "Resolved" else "+20 XP (Manual Hand-Off)"
                st.markdown(f"**Earned Session Reward:** `{badge_points}`")

            if final_status == "Resolved":
                st.balloons()

            # Escape model-generated text before embedding it into HTML.
            safe_reply = html.escape(
                final_reply if final_reply else
                "Autonomous handling bypassed; ticket routed safely to manual Tier-2 intervention queue."
            ).replace("\\n", "<br>")
            st.markdown(f"""
            <div class="resolution-screen">
                <strong>[CONFIRMED OUTBOX MESSAGE]:</strong><br><br>
                {safe_reply}
            </div>
            """, unsafe_allow_html=True)

# -------------------------------------------------------------
# PORTAL 2: ADMIN & OPERATIONS CONTROL
# -------------------------------------------------------------
else:
    st.markdown('<h1 class="brand-title">⚙️ Admin & Operations Portal</h1>', unsafe_allow_html=True)
    st.markdown('<p class="brand-subtitle">Knowledge Base Management, Evaluation Benchmarks & Audit Logs</p>', unsafe_allow_html=True)

    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "📚 Knowledge Base Engine",
        "🎯 Benchmark Evaluation Suite",
        "🗄️ Master Ticket Audit Logs",
        "📊 RAG Evaluation Metrics"
    ])

    with admin_tab1:
        st.subheader("Interactive FAISS + BM25 Retrieval Engine")
        st.write("Construct, update, and manage semantic embeddings along with lexical indexes.")
        
        if st.button("🔄 RE-INDEX KNOWLEDGE BASE (FAISS + BM25 Okapi)", type="primary"):
            try:
                chunks_count, files_count = rag_engine.build_or_refresh_index()
                st.success(f"Success: Indexed {files_count} markdown guidelines into {chunks_count} vector and token searchable chunks.")
            except Exception as e:
                st.error(f"Failed to generate search index: {e}")

        st.markdown("---")
        st.subheader("Active Embedded Policy Guidelines")
        kb_path = "knowledge_base"
        if os.path.exists(kb_path):
            kb_files = [f for f in os.listdir(kb_path) if f.endswith(".md")]
            for filename in kb_files:
                file_full_path = os.path.join(kb_path, filename)
                with st.expander(f"📄 {filename.upper()}", expanded=False):
                    with open(file_full_path, "r", encoding="utf-8") as f:
                        st.markdown(f.read())

    with admin_tab2:
        st.subheader("Benchmark Evaluation Cases")
        st.caption("Click any 'LOAD EVAL CASE' button to prepopulate active support form inputs instantly.")

        test_cases = BENCHMARK_CASES

        run_col, judge_col = st.columns([2, 1])
        with judge_col:
            use_llm_judge = st.checkbox(
                "Use LLM-as-a-Judge (additional API cost)",
                value=True,
                key="eval_use_llm_judge",
                help="Adds a separate model call to score answer grounding, completeness, and empathy."
            )
        with run_col:
            run_all = st.button(
                "▶ RUN ALL 8 BENCHMARK CASES",
                type="primary",
                use_container_width=True,
                key="run_all_benchmarks"
            )

        if run_all:
            benchmark_results = []
            progress = st.progress(0, text="Starting benchmark evaluation...")
            for idx, case in enumerate(test_cases, start=1):
                progress.progress((idx - 1) / len(test_cases), text=f"Running benchmark case {idx}/{len(test_cases)}...")
                benchmark_results.append(run_benchmark_case(case, use_llm_judge=use_llm_judge))
            progress.progress(1.0, text="Benchmark run completed.")
            st.session_state["benchmark_results"] = benchmark_results
            st.session_state["benchmark_run_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        results = st.session_state.get("benchmark_results")
        if results:
            passed = sum(bool(item.get("passed")) for item in results)
            status_correct = sum(bool(item.get("status_pass")) for item in results)
            total = len(results)
            avg_latency = sum(item.get("latency_ms", 0) for item in results) / max(total, 1)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Overall Pass Rate", f"{passed}/{total}", f"{passed / max(total, 1) * 100:.1f}%")
            m2.metric("Status Accuracy", f"{status_correct}/{total}", f"{status_correct / max(total, 1) * 100:.1f}%")
            m3.metric("Avg. End-to-End Latency", f"{avg_latency / 1000:.1f}s")
            m4.metric("Run Timestamp", st.session_state.get("benchmark_run_timestamp", "—"))
            result_rows = []
            for item in results:
                judge_data = item.get("judge") or {}
                result_rows.append({
                    "Case": item.get("case_id"),
                    "Customer": item.get("customer"),
                    "Expected": item.get("expected_status"),
                    "Actual": item.get("actual_status"),
                    "Status Match": "✓" if item.get("status_pass") else "✗",
                    "Judge Score": judge_data.get("score", "N/A") if judge_data.get("available") else "N/A",
                    "Pass": "✓" if item.get("passed") else "✗",
                    "Latency (s)": round(item.get("latency_ms", 0) / 1000, 2),
                    "Error": item.get("error") or judge_data.get("error", ""),
                })
            results_df = pd.DataFrame(result_rows)
            st.dataframe(results_df, use_container_width=True, hide_index=True)

            # Export the complete benchmark run, including detailed LLM-as-a-Judge feedback.
            export_rows = []
            for item in results:
                judge_data = item.get("judge") or {}
                case_data = next(
                    (case for case in test_cases if case.get("id") == item.get("case_id")),
                    {}
                )
                export_rows.append({
                    "Case ID": item.get("case_id"),
                    "Customer": item.get("customer"),
                    "Complaint": case_data.get("complaint", ""),
                    "Expected Status": item.get("expected_status"),
                    "Actual Status": item.get("actual_status"),
                    "Status Match": bool(item.get("status_pass")),
                    "Benchmark Passed": bool(item.get("passed")),
                    "Agent Response": item.get("response", ""),
                    "Latency (ms)": item.get("latency_ms", 0),
                    "Judge Available": bool(judge_data.get("available")),
                    "Judge Score (0-5)": judge_data.get("score", ""),
                    "Judge Pass": judge_data.get("pass", ""),
                    "Policy Grounding (0-5)": judge_data.get("policy_grounding", ""),
                    "Completeness (0-5)": judge_data.get("completeness", ""),
                    "Empathy (0-5)": judge_data.get("empathy", ""),
                    "Judge Issues": "; ".join(judge_data.get("issues", []))
                        if isinstance(judge_data.get("issues"), list)
                        else judge_data.get("issues", ""),
                    "Judge Rationale / Feedback": judge_data.get("rationale", ""),
                    "Judge Error": judge_data.get("error", ""),
                    "Execution Error": item.get("error", ""),
                })

            export_df = pd.DataFrame(export_rows)
            export_json = {
                "run_timestamp": st.session_state.get("benchmark_run_timestamp"),
                "total_cases": len(results),
                "passed_cases": passed,
                "status_correct_cases": status_correct,
                "results": results,
            }
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                st.download_button(
                    label="📥 Download Benchmark Results + Judge Feedback (CSV)",
                    data=export_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="benchmark_evaluation_results.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_benchmark_results_csv",
                )
            with export_col2:
                st.download_button(
                    label="📥 Download Full Benchmark Results (JSON)",
                    data=json.dumps(export_json, ensure_ascii=False, indent=2, default=str).encode("utf-8"),
                    file_name="benchmark_evaluation_results.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_benchmark_results_json",
                )

            with st.expander("Inspect individual benchmark responses", expanded=False):
                for item in results:
                    st.markdown(f"#### Case #{item.get('case_id')} — {item.get('actual_status')}")
                    st.write(item.get("response") or item.get("error") or "No response captured.")
                    if item.get("judge"):
                        st.json(item["judge"])
            st.caption("Benchmark executions are logged separately under logs/benchmark_runs and do not count toward customer ticket/XP dashboard metrics.")

        for tc in test_cases:
            with st.container():
                c1, c2 = st.columns([4, 1.5])
                with c1:
                    st.markdown(f"**CASE #{tc['id']}:** *\"{tc['complaint']}\"*")
                    st.markdown(
                        f"<span style='color: #a5b4fc; font-size: 0.85rem;'>"
                        f"🔍 Expected: {tc['expected_status']} | {tc['customer']} "
                        f"({tc['place']}) | {tc['order_id']}</span>",
                        unsafe_allow_html=True
                    )
                with c2:
                    if st.button("LOAD EVAL CASE", key=f"btn_tc_{tc['id']}", use_container_width=True):
                        # Stage the benchmark data outside widget-owned session state.
                        # It survives while the Support Desk widgets are not rendered.
                        st.session_state["pending_eval_case"] = {
                            "customer_name": tc["customer"],
                            "place": tc["place"],
                            "order_id": tc["order_id"],
                            "complaint": tc["complaint"],
                        }
                        st.success(
                            f"Benchmark Test #{tc['id']} ready! "
                            "Go back to Active Support Desk."
                        )
                st.divider()

    with admin_tab4:
        st.subheader("Hybrid Retrieval Quality — FAISS vs BM25 vs RRF")
        st.caption(
            "Source-level relevance evaluation using benchmark complaint queries. "
            "Metrics are computed only for cases with known relevant knowledge-base sources."
        )
        rag_k = st.selectbox("Evaluate top-K retrieval", [1, 3, 5], index=1, key="rag_eval_k")
        if st.button("🔬 RUN RAG EVALUATION", type="primary", key="run_rag_eval"):
            with st.spinner("Running retrieval evaluation across benchmark queries..."):
                st.session_state["rag_eval_results"] = run_rag_evaluation(
                    rag_engine, cases=BENCHMARK_CASES, k=rag_k
                )
                st.session_state["rag_eval_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rag_eval = st.session_state.get("rag_eval_results")
        if rag_eval:
            st.caption(f"Last run: {st.session_state.get('rag_eval_timestamp', '—')}")
            st.info(
                f"Evaluated {rag_eval['evaluated_relevance_cases']} labeled queries; "
                f"{rag_eval['unsupported_or_no_exact_policy_cases']} cases are marked as requiring escalation "
                "or lacking an exact policy source. {rag_eval['note']}"
            )
            metric_rows = []
            labels = {
                "vector_results": "FAISS Vector",
                "bm25_results": "BM25",
                "fused_results": "Hybrid RRF",
            }
            for method, values in rag_eval["summary"].items():
                metric_rows.append({
                    "Retriever": labels.get(method, method),
                    f"Hit Rate@{rag_eval['k']}": f"{values['hit'] * 100:.1f}%",
                    f"Precision@{rag_eval['k']}": f"{values['precision'] * 100:.1f}%",
                    f"Recall@{rag_eval['k']}": f"{values['recall'] * 100:.1f}%",
                    f"MRR@{rag_eval['k']}": f"{values['mrr']:.3f}",
                })
            st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)

            detail_rows = []
            for item in rag_eval["details"]:
                detail_rows.append({
                    "Case": item.get("case_id"),
                    "Relevant Sources": ", ".join(item.get("expected_sources", [])) or "No exact source / escalation",
                    "FAISS": ", ".join(item.get("retrieved", {}).get("vector_results", [])),
                    "BM25": ", ".join(item.get("retrieved", {}).get("bm25_results", [])),
                    "RRF": ", ".join(item.get("retrieved", {}).get("fused_results", [])),
                    "Latency (ms)": item.get("latency_ms", "—"),
                    "Error": item.get("error", ""),
                })
            st.markdown("#### Per-case retrieval results")
            st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)
            st.download_button(
                "📥 Download RAG evaluation results (JSON)",
                data=json.dumps(rag_eval, indent=2, ensure_ascii=False),
                file_name="rag_evaluation_results.json",
                mime="application/json",
                key="download_rag_eval"
            )

    with admin_tab3:
        st.subheader("Audited System Logs Ledger")
        if os.path.exists(log_csv_path) and os.path.getsize(log_csv_path) > 0:
            df = pd.read_csv(log_csv_path)
            df = df.drop_duplicates(subset=["ticket_id"], keep="first")
            st.dataframe(df, use_container_width=True)

            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 EXPORT TICKET HISTORY (.CSV)",
                data=csv_data,
                file_name="tickets.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("System auditing log currently holds zero historical cases.")