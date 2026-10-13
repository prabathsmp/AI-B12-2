import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import streamlit as st
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from neo4j import GraphDatabase

# -------------------------------------------------------------------------
# Load Environment Variables
# -------------------------------------------------------------------------
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

PDF_DIR = os.getenv("PDF_DIR", "./pdf_docs")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

st.set_page_config(
    page_title="Vivasai 2.0 — Graph RAG Assistant",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------------------------------------------------------------
# Custom Styling (Green Rural Theme)
# -------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    .stApp {
        background-color: #f7faf7;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b3d2c 0%, #082d20 100%);
        color: #ffffff;
        padding-top: 1.5rem;
    }

    .sidebar-brand {
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-bottom: 20px;
    }

    .brand-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #ffffff;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .brand-subtitle {
        font-size: 0.85rem;
        color: #a7f3d0;
        line-height: 1.35;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #115e43;
        border: 1px solid #10b981;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #ecfdf5;
        margin-bottom: 20px;
    }

    .status-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background-color: #34d399;
        box-shadow: 0 0 8px #34d399;
    }

    .metric-container {
        display: flex;
        gap: 10px;
        margin-bottom: 22px;
    }

    .metric-box {
        background: #ffffff;
        border-radius: 12px;
        padding: 10px 14px;
        flex: 1;
        display: flex;
        flex-direction: column;
        color: #0b3d2c;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }

    .metric-box-label {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #64748b;
    }

    .metric-box-val {
        font-size: 1.05rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 4px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    section[data-testid="stSidebar"] .stButton > button {
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 10px !important;
        padding: 10px 16px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: rgba(239, 68, 68, 0.2) !important;
        border-color: #ef4444 !important;
        color: #fca5a5 !important;
    }

    .hero-banner {
        background: linear-gradient(180deg, rgba(235, 245, 235, 0.85) 0%, rgba(247, 250, 247, 0.95) 100%),
                    url('https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1600&q=80') center/cover;
        border-radius: 18px;
        padding: 34px 40px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(13, 59, 46, 0.05);
        border: 1px solid #d1fae5;
    }

    .hero-tamil {
        font-size: 2.2rem;
        font-weight: 800;
        color: #064e3b;
        margin-bottom: 2px;
        letter-spacing: -0.02em;
    }

    .hero-english {
        font-size: 2.5rem;
        font-weight: 800;
        color: #064e3b;
        margin-bottom: 8px;
        letter-spacing: -0.02em;
    }

    .hero-tagline {
        font-size: 1.05rem;
        color: #1e3a2f;
        font-weight: 500;
        margin-bottom: 18px;
    }

    .hero-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        font-size: 0.92rem;
        color: #064e3b;
        font-weight: 600;
    }

    .qp-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 12px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        min-height: 85px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .qp-icon-box {
        font-size: 1.8rem;
        min-width: 40px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .qp-text-box {
        flex: 1;
        text-align: left;
    }
    .qp-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 2px;
    }
    .qp-sub {
        font-size: 0.78rem;
        color: #64748b;
        line-height: 1.25;
    }
    .qp-arrow {
        color: #059669;
        font-weight: 800;
        font-size: 1.1rem;
    }

    .qp-btn-row .stButton > button {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        color: #047857 !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        padding: 4px 10px !important;
        margin-top: 6px !important;
        width: 100% !important;
    }
    .qp-btn-row .stButton > button:hover {
        border-color: #10b981 !important;
        background-color: #f0fdf4 !important;
    }

    .chat-bubble-user {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 14px 20px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }

    .chat-bubble-assistant {
        background-color: #f2f8f4;
        border: 1px solid #d1fae5;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }

    .warning-callout {
        background-color: #fef9c3;
        border-left: 4px solid #eab308;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 14px 0;
        color: #713f12;
        font-size: 0.88rem;
        line-height: 1.45;
    }

    .graph-evidence-card {
        background-color: #ffffff;
        border-left: 3px solid #10b981;
        padding: 8px 12px;
        border-radius: 0 8px 8px 0;
        margin-top: 6px;
        font-family: monospace;
        font-size: 0.82rem;
        color: #0f172a;
        background: #f8fafc;
    }

    div[data-testid="stChatInput"] {
        background: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 9999px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05) !important;
        padding: 4px 12px !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #0f172a !important;
        background: transparent !important;
        font-size: 0.92rem !important;
    }
    div[data-testid="stChatInput"] button {
        color: #059669 !important;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# Prompts
# -------------------------------------------------------------------------
EXTRACTION_SYSTEM_PROMPT = """
You are a precision knowledge graph extraction engine for agricultural schemes and training programs.
Analyze the text chunk and extract entities and directed relationships.

Output format MUST be strictly a single JSON object with two keys:
1. "nodes": A list of entities. Each object must have:
   - "id": Normalized identifier in lowercase (e.g., "training-to-farmers", "pm-kisan", "paddy")
   - "name": Clean display name (e.g., "Training to Farmers", "PM-Kisan", "Paddy")
   - "type": One of [Scheme, Training, Crop, Document, Eligibility, Benefit, Authority, Concept]
   - "description": A concise 1-sentence summary of what this entity is or provides based on the chunk.

2. "relationships": A list of directed edges. Each object must have:
   - "source": The "id" of the head entity
   - "target": The "id" of the tail entity
   - "type": Explicit uppercase relationship:
     [OFFERS_TRAINING, COVERS_TOPIC, IMPLEMENTED_BY, ELIGIBLE_FOR, REQUIRES_DOCUMENT, 
      PROVIDES_BENEFIT, APPLIES_TO_CROP, MANAGED_BY]

Rules:
- Extract ONLY facts explicitly stated in the text.
- Do not classify training programs or welfare services as crops.
- Every "source" and "target" MUST match an "id" present in "nodes".
- Return pure JSON only without markdown wrapping or explanations.
"""

CYPHER_GENERATION_PROMPT = """
You are an expert Neo4j Cypher developer.
Given a user's question, write a Cypher query to retrieve relevant facts from the graph.

Graph Schema:
- Nodes: (:Entity {{id: String, name: String, type: String, description: String}})
- Relationships: (src:Entity)-[rel:RELATED_TO {{type: String}}]->(tgt:Entity)

Rules:
1. Always bind the relationship variable: `[rel:RELATED_TO]`
2. Match bidirectionally: `-(rel:RELATED_TO)-`
3. Use case-insensitive matching with `toLower(...) CONTAINS toLower('...')` across names and descriptions.
4. Always project:
   RETURN src.name AS source, 
          coalesce(src.description, '') AS source_desc,
          rel.type AS relationship, 
          tgt.name AS target,
          coalesce(tgt.description, '') AS target_desc
5. Output ONLY the raw Cypher query. Do NOT use markdown code blocks or explanations.

Example:
Question: what are trainings available for farmers
Cypher:
MATCH (src:Entity)-[rel:RELATED_TO]-(tgt:Entity)
WHERE toLower(src.name) CONTAINS 'train' OR toLower(tgt.name) CONTAINS 'train'
   OR toLower(src.type) CONTAINS 'training' OR toLower(tgt.type) CONTAINS 'training'
RETURN src.name AS source, coalesce(src.description, '') AS source_desc, rel.type AS relationship, tgt.name AS target, coalesce(tgt.description, '') AS target_desc
"""

ANSWER_SYNTHESIS_PROMPT = """
You are an agricultural advisor for farmers in Tamil Nadu.
Synthesize a clear, professional, and structured answer using the provided graph facts.

Graph Facts:
{context}

User Question:
{question}

Guidelines:
1. Identify all relevant programs, schemes, or training sessions mentioned.
2. Clearly state the organizing/managing authority (e.g., Department of Agriculture - Farmers Welfare).
3. Detail any eligible categories (e.g., small/marginal farmers), benefits (grants, stipends, subsidies), and required paperwork.
4. Present the response using clear bullet points and bold headers.
5. If details are minimal, explain what is recorded in the system and advise checking with the local Block Agricultural Extension Officer or the Uzhavan App.
6. If the graph facts are empty, state: "The information was not found in the knowledge graph."
"""

# -------------------------------------------------------------------------
# Intent Detection Utilities
# -------------------------------------------------------------------------
ADVERSARIAL_PATTERNS = [
    r"system\s*prompt",
    r"developer\s*prompt",
    r"hidden\s*instructions",
    r"initial\s*prompt",
    r"reveal\s*(your\s*)?(rules|prompt|instructions)",
    r"repeat\s*(the\s*words\s*)?above",
    r"ignore\s*(all\s*)?(previous|above)\s*instructions",
    r"jailbreak",
    r"bypass\s*rules",
    r"print\s*system",
]

GREETINGS_PATTERN = r"^(hi|hello|hey|vanakkam|வணக்கம்|good\s*(morning|afternoon|evening)|namaste)(\s+.*)?[!.]*$"

REFUSAL_OR_FALLBACK_PHRASES = [
    "information was not found in the knowledge graph",
    "cannot share system configurations",
    "cannot share internal prompts",
]

def is_adversarial(text: str) -> bool:
    return any(re.search(p, text.lower()) for p in ADVERSARIAL_PATTERNS)

def is_greeting(text: str) -> bool:
    return bool(re.match(GREETINGS_PATTERN, text.strip().lower()))

# -------------------------------------------------------------------------
# Knowledge Graph Backend Engine
# -------------------------------------------------------------------------
class GraphRAGEngine:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        self.extraction_llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            format="json",
            num_ctx=4096,
        )
        self.qa_llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            num_ctx=4096,
        )
        
        self.extract_chain = (
            ChatPromptTemplate.from_messages([
                ("system", EXTRACTION_SYSTEM_PROMPT),
                ("human", "Text Chunk:\n<chunk>\n{text}\n</chunk>\n\nJSON:"),
            ])
            | self.extraction_llm
        )
        self.cypher_chain = (
            ChatPromptTemplate.from_messages([
                ("system", CYPHER_GENERATION_PROMPT),
                ("human", "Question: {question}\n\nCypher query:"),
            ])
            | self.qa_llm
        )
        self.answer_chain = (
            ChatPromptTemplate.from_messages([
                ("system", ANSWER_SYNTHESIS_PROMPT)
            ])
            | self.qa_llm
        )

    def close(self):
        self.driver.close()

    def get_graph_counts(self) -> Tuple[int, int]:
        try:
            with self.driver.session() as session:
                node_res = session.run("MATCH (n:Entity) RETURN count(n) AS count").single()
                rel_res = session.run("MATCH ()-[r:RELATED_TO]->() RETURN count(r) AS count").single()
                return (node_res["count"] if node_res else 0, rel_res["count"] if rel_res else 0)
        except Exception:
            return (0, 0)

    def setup_constraints(self):
        query = """
        CREATE CONSTRAINT entity_id_unique IF NOT EXISTS
        FOR (e:Entity) REQUIRE e.id IS UNIQUE
        """
        with self.driver.session() as session:
            session.run(query)

    def ingest_folder(self, folder_path: str = PDF_DIR, progress_callback=None) -> int:
        folder = Path(folder_path)
        folder.mkdir(parents=True, exist_ok=True)
        loader = PyPDFDirectoryLoader(str(folder))
        docs = loader.load()
        if not docs:
            return 0

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        chunks = splitter.split_documents(docs)
        self.setup_constraints()

        total = len(chunks)
        for idx, chunk in enumerate(chunks, 1):
            if progress_callback:
                progress_callback(idx / total, f"Extracting chunk {idx}/{total}...")
            try:
                res = self.extract_chain.invoke({"text": chunk.page_content})
                data = json.loads(res.content)
                nodes = data.get("nodes", [])
                rels = data.get("relationships", [])
                source = chunk.metadata.get("source", "document")
                self._write_graph(nodes, rels, source)
            except Exception:
                pass

        return total

    def _write_graph(self, nodes: List[Dict], rels: List[Dict], source: str):
        node_query = """
        UNWIND $nodes AS n
        MERGE (e:Entity {id: n.id})
        ON CREATE SET e.name = n.name, 
                      e.type = n.type, 
                      e.description = coalesce(n.description, '')
        ON MATCH SET e.name = coalesce(e.name, n.name),
                     e.description = CASE WHEN e.description IS NULL OR e.description = '' 
                                          THEN coalesce(n.description, '') 
                                          ELSE e.description END
        """
        rel_query = """
        UNWIND $relationships AS r
        MATCH (src:Entity {id: r.source})
        MATCH (tgt:Entity {id: r.target})
        MERGE (src)-[rel:RELATED_TO {type: r.type}]->(tgt)
        ON CREATE SET rel.source_doc = $source
        """
        with self.driver.session() as session:
            session.run(node_query, nodes=nodes)
            session.run(rel_query, relationships=rels, source=source)

    def clean_cypher(self, cypher: str) -> str:
        return re.sub(r"```(cypher)?", "", cypher).strip("` \n")

    def execute_cypher(self, cypher: str) -> List[Dict[str, Any]]:
        try:
            with self.driver.session() as session:
                res = session.run(cypher)
                return [r.data() for r in res]
        except Exception:
            return []

    def format_records(self, records: List[Dict[str, Any]]) -> str:
        if not records:
            return "No matching relationships found in graph."
        
        seen = set()
        lines = []
        for r in records:
            src = r.get("source", "")
            rel = r.get("relationship", "")
            tgt = r.get("target", "")
            src_desc = r.get("source_desc", "")
            tgt_desc = r.get("target_desc", "")

            edge_key = tuple(sorted([src, tgt])) + (rel,)
            if edge_key in seen:
                continue
            seen.add(edge_key)

            entry = f"- ({src}) -[{rel}]-> ({tgt})"
            details = []
            if src_desc:
                details.append(f"{src}: {src_desc}")
            if tgt_desc:
                details.append(f"{tgt}: {tgt_desc}")
            if details:
                entry += f" | Context: {'; '.join(details)}"
            lines.append(entry)

        return "\n".join(lines)

    def query_graph(self, question: str) -> Tuple[str, str, str]:
        # 1. Text-to-Cypher
        raw_cypher = self.cypher_chain.invoke({"question": question}).content
        cypher = self.clean_cypher(raw_cypher)

        # 2. Query execution with keyword fallback
        records = self.execute_cypher(cypher)
        used_cypher = cypher

        if not records:
            terms = [w.lower() for w in re.findall(r"\b\w[\w-]*\b", question) if len(w) > 3]
            for term in terms:
                fb_query = f"""
                MATCH (src:Entity)-[rel:RELATED_TO]-(tgt:Entity)
                WHERE toLower(src.name) CONTAINS '{term}' 
                   OR toLower(tgt.name) CONTAINS '{term}'
                   OR toLower(coalesce(src.description, '')) CONTAINS '{term}'
                   OR toLower(coalesce(tgt.description, '')) CONTAINS '{term}'
                RETURN src.name AS source, 
                       coalesce(src.description, '') AS source_desc,
                       rel.type AS relationship, 
                       tgt.name AS target,
                       coalesce(tgt.description, '') AS target_desc
                LIMIT 25
                """
                fb_records = self.execute_cypher(fb_query)
                if fb_records:
                    records = fb_records
                    used_cypher = fb_query
                    break

        # 3. Formulate structured response
        context = self.format_records(records)
        answer = self.answer_chain.invoke({
            "context": context,
            "question": question,
        }).content

        return answer, context, used_cypher

# -------------------------------------------------------------------------
# State & Resource Initialization
# -------------------------------------------------------------------------
@st.cache_resource
def get_graph_engine():
    return GraphRAGEngine()

try:
    engine = get_graph_engine()
except Exception as e:
    st.error(f"Failed to connect to Neo4j or Ollama: {e}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

if "quick_prompt" not in st.session_state:
    st.session_state.quick_prompt = None

node_count, rel_count = engine.get_graph_counts()

# -------------------------------------------------------------------------
# Sidebar
# -------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="brand-title">🌾 Vivasai Graph</div>
        <div class="brand-subtitle">Knowledge Graph RAG for Tamil Nadu Agriculture</div>
    </div>
    <div class="status-badge">
        <span class="status-dot"></span> Neo4j + Ollama Active
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-box">
            <span class="metric-box-label">ENTITIES (NODES)</span>
            <span class="metric-box-val">🏷️ {node_count}</span>
        </div>
        <div class="metric-box">
            <span class="metric-box-label">RELATIONSHIPS</span>
            <span class="metric-box-val">🕸️ {rel_count}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("##### 📁 Ingestion Control")
    st.caption(f"Target folder: `{PDF_DIR}`")
    if st.button("🔄 Ingest / Sync PDFs to Graph", use_container_width=True):
        progress_bar = st.progress(0, text="Reading PDFs...")
        def update_p(ratio, txt):
            progress_bar.progress(ratio, text=txt)
        
        chunks_done = engine.ingest_folder(PDF_DIR, progress_callback=update_p)
        progress_bar.empty()
        st.success(f"Ingested {chunks_done} chunks into Neo4j!")
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.quick_prompt = None
        st.rerun()

# -------------------------------------------------------------------------
# Hero Banner
# -------------------------------------------------------------------------
st.markdown("""
<div class="hero-banner">
    <div class="hero-tamil">வணக்கம்!</div>
    <div class="hero-english">Welcome to Vivasai 2.0 (Graph RAG)</div>
    <div class="hero-tagline">Navigating complex scheme dependencies, farmer eligibilities, and agricultural benefits through structured Graph Traversal.</div>
    <div class="hero-pills">
        <div class="hero-pill-item">🕸️ Neo4j Knowledge Graph</div>
        <span>|</span>
        <div class="hero-pill-item">⚙️ Local Qwen 2.5 Cypher Engine</div>
        <span>|</span>
        <div class="hero-pill-item">📍 For farmers in Tamil Nadu</div>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# Quick Prompt Suggestions
# -------------------------------------------------------------------------
st.markdown("##### 💡 Suggested Graph Queries")
c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class="qp-card">
        <div class="qp-icon-box">🎓</div>
        <div class="qp-text-box">
            <div class="qp-title">Farmer Trainings</div>
            <div class="qp-sub">What are trainings available for farmers?</div>
        </div>
        <div class="qp-arrow">›</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="qp-btn-row">', unsafe_allow_html=True)
    if st.button("Ask this question", key="btn_qp_1"):
        st.session_state.quick_prompt = "What are trainings available for farmers?"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="qp-card">
        <div class="qp-icon-box">📋</div>
        <div class="qp-text-box">
            <div class="qp-title">Document Requirements</div>
            <div class="qp-sub">What documents are required for PM-Kisan?</div>
        </div>
        <div class="qp-arrow">›</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="qp-btn-row">', unsafe_allow_html=True)
    if st.button("Ask this question", key="btn_qp_2"):
        st.session_state.quick_prompt = "What documents are required for PM-Kisan?"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="qp-card">
        <div class="qp-icon-box">🚜</div>
        <div class="qp-text-box">
            <div class="qp-title">Equipment & Subsidies</div>
            <div class="qp-sub">What subsidies are provided for plant protection equipment?</div>
        </div>
        <div class="qp-arrow">›</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="qp-btn-row">', unsafe_allow_html=True)
    if st.button("Ask this question", key="btn_qp_3"):
        st.session_state.quick_prompt = "What subsidies are provided for plant protection equipment?"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<hr style='margin: 18px 0 22px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# Chat Feed
# -------------------------------------------------------------------------
for msg in st.session_state.messages:
    timestamp = msg.get("timestamp", datetime.now().strftime("%I:%M %p"))

    if msg["role"] == "user":
        st.markdown(f"""
        <div class="chat-bubble-user">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-weight: 700; color: #1e293b;">👤 Farmer</span>
                <span style="font-size: 0.75rem; color: #94a3b8;">{timestamp}</span>
            </div>
            <div style="color: #334155; font-size: 0.95rem;">{msg['content']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-bubble-assistant">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 700; color: #064e3b;">🌾 Vivasai Graph Assistant</span>
                <span style="font-size: 0.75rem; color: #64748b;">{timestamp}</span>
            </div>
            <div style="color: #1e293b; font-size: 0.95rem; line-height: 1.6;">
                {msg['content']}
            </div>
            <div class="warning-callout">
                ⚠️ <strong>Note:</strong> Scheme criteria and subsidies are derived from Neo4j knowledge graph relationships. For official sanction orders, consult your local Block Agricultural Extension Officer.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Graph Evidence Drawer
        if msg.get("graph_facts"):
            with st.expander("🕸️ View Retrieved Graph Relationships (Cypher Evidence)", expanded=False):
                st.caption(f"**Generated Cypher Query:**\n```cypher\n{msg.get('cypher', '')}\n```")
                st.markdown("**Matched Knowledge Triples:**")
                for line in msg["graph_facts"].splitlines():
                    if line.strip():
                        st.markdown(f"<div class='graph-evidence-card'>{line}</div>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# Input & Execution Handling
# -------------------------------------------------------------------------
user_input = st.chat_input("Ask about schemes, eligible beneficiaries, trainings, or documents...")

active_query = None
if user_input:
    active_query = user_input
elif st.session_state.quick_prompt:
    active_query = st.session_state.quick_prompt
    st.session_state.quick_prompt = None

if active_query:
    current_time = datetime.now().strftime("%I:%M %p")
    st.session_state.messages.append({
        "role": "user",
        "content": active_query,
        "timestamp": current_time,
    })

    # Guard 1: Adversarial
    if is_adversarial(active_query):
        refusal = (
            "I am designed to assist strictly with agricultural schemes, crops, and farmer welfare queries. "
            "I cannot share internal system configurations or prompts."
        )
        st.session_state.messages.append({
            "role": "assistant",
            "content": refusal,
            "graph_facts": "",
            "cypher": "",
            "timestamp": current_time,
        })
        st.rerun()

    # Guard 2: Friendly Greetings
    elif is_greeting(active_query):
        greeting = (
            "வணக்கம்! Welcome to Vivasai 2.0 (Knowledge Graph Edition). 🌾\n\n"
            "I can traverse relationships across Tamil Nadu agricultural schemes, training initiatives, "
            "and subsidies. How can I assist you today?"
        )
        st.session_state.messages.append({
            "role": "assistant",
            "content": greeting,
            "graph_facts": "",
            "cypher": "",
            "timestamp": current_time,
        })
        st.rerun()

    # Graph RAG Execution
    else:
        with st.spinner("Traversing knowledge graph & analyzing relationships..."):
            answer, facts, cypher = engine.query_graph(active_query)

            # Approach 1: Suppress evidence drawer if the response is an empty refusal
            is_unverified = any(phrase in answer.lower() for phrase in REFUSAL_OR_FALLBACK_PHRASES)
            valid_facts = "" if is_unverified else facts

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "graph_facts": valid_facts,
                "cypher": cypher,
                "timestamp": current_time,
            })
            st.rerun()