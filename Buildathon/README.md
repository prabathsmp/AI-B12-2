<div align="center">

# 🌾 Vivasai 2.0 — Farmer Assistant
**AI-Powered Grounded RAG Platform for Tamil Nadu Agricultural Schemes & Subsidies**

[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/Orchestration-LangChain-1C3C3C)](https://python.langchain.com/)
[![FAISS](https://img.shields.io/badge/Vector%20Store-FAISS-00599C)](https://github.com/facebookresearch/faiss)
[![Playwright](https://img.shields.io/badge/Scraper-Playwright-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/)
[![Embeddings](https://img.shields.io/badge/Embeddings-MiniLM--L6--v2-orange)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)

</div>

---

## 📌 Executive Summary

**Vivasai 2.0** is an agricultural knowledge engine developed for the **AI-B12-2 Buildathon**. The platform connects farmers across Tamil Nadu with verified, real-time government agricultural welfare programs.

Government portals frequently display scheme details across fragmented data tables and interactive endpoints. Vivasai 2.0 provides an end-to-end automated pipeline that captures live portal data, generates reference scheme documentation, creates hybrid vector-keyword indexes, and provides a dual-engine chat interface (OpenAI Cloud or Local Ollama) designed specifically for farmers.

---

## 🌟 Key Capabilities

- **Automated Scheme Ingestion**: Headless browser automation via Playwright queries the Tamil Nadu Uzhavan Portal (`tnagrisnet.tn.gov.in/people_app/GoScheme`), triggers official `getSchemeDet(ID)` POST endpoints, and compiles structured bilingual (English and Tamil) PDFs.
- **Hybrid Dense-Sparse Retrieval**: Combines semantic search (**FAISS**) with lexical exact-match search (**BM25**). An L2 distance cutoff threshold (`1.35`) triggers automatic BM25 fallback for specialized scheme names and agricultural acronyms.
- **Dual Runtime Engines**:
  - **Cloud Pipeline (`openapi-vivasai-app.py`)**: Uses OpenAI's `gpt-4.1-mini` for fast response generation and multi-turn conversational reasoning.
  - **Local & Offline Pipeline (`ollama-vivasai-app.py`)**: Uses local LLMs (`qwen2.5:latest`) via Ollama for air-gapped, zero-cost inference.
- **Query History Reformulation**: Integrates a conversational rewrite chain that reconstructs ambiguous follow-ups into standalone retrieval queries based on chat context.
- **Two-Tier Guardrails & System Security**: Upstream regex filters block jailbreaks and prompt extraction attacks. The system prompt enforces strict verifiability—refusing to hallucinate and redirecting farmers to local extension officers when documents lack answers.
- **Evidence Drawer & Citations**: Every generated response links directly to the specific source PDF and page number, enabling full auditability.

---

## 🏗️ Architecture & Data Pipeline

```text
       [ Tamil Nadu Uzhavan Portal ]
                     │
                     ▼ (download_uzhavan_schemes.py)
      [ Async Playwright Data Extraction ]
                     │
                     ├── Extract Listing: Dept, Description, Beneficiaries, Documents
                     └── POST /getSchemeDet/{id}: Input Types, Classes, Subsidy Patterns
                     │
                     ▼
       [ uzhavan_scheme_pdfs/*.pdf ]
                     │
                     ▼ (PyPDFLoader & RecursiveCharacterTextSplitter)
          [ Chunks: 500 chars / 50 overlap ]
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
[ FAISS Vector Store ]  [ BM25 Retriever ]
(all-MiniLM-L6-v2)      (Lexical Keyword Index)
         └───────────┬───────────┘
                     ▼
          [ Manifest Tracking: pdf_manifest.json ]
                     │
                     ▼
      [ User Query via Streamlit UI ]
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
  [ Intent Filter ]      [ Query Rewriter ]
  (Regex Guardrails)    (Conversation Context)
         │                       │
         └───────────┬───────────┘
                     ▼
      [ Hybrid Retrieval: FAISS + BM25 Fallback ]
                     │
                     ▼
         [ LLM Generation Chain ]
         (OpenAI GPT-4.1-mini / Ollama Qwen 2.5)
                     │
                     ▼
       [ Verified Answer + Source Citations ]
```

---

## 📂 Project Structure

```text
Buildathon/
├── download_uzhavan_schemes.py   # Playwright automation script to extract portal schemes
├── openapi-vivasai-app.py        # Streamlit RAG application powered by OpenAI models
├── ollama-vivasai-app.py         # Streamlit RAG application powered by local Ollama models
├── requirements.txt              # Production dependencies and library requirements
├── uzhavan_scheme_pdfs/          # Generated directory for extracted scheme PDFs
│   └── download_report.csv       # Status log of fetched schemes and error traces
└── faiss_index/                  # Persisted vector database and document manifests
    ├── index.faiss               # FAISS binary vector index
    ├── index.pkl                 # Document chunk metadata store
    └── pdf_manifest.json         # Fingerprint registry tracking file sizes and timestamps
```

---

## 🛠️ Technical Specifications

| Component | Implementation | Details |
|---|---|---|
| **Web Scraping & Extraction** | Playwright (Async Chromium) | Intercepts JSON responses from `/people_app/goScheme/getSchemeDet/{id}` |
| **Document Processing** | PyPDFLoader & RecursiveCharacterTextSplitter | Chunks: 500 tokens, Overlap: 50 tokens |
| **Vector Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | 384-dimensional dense semantic vectors |
| **Vector Store** | FAISS (`faiss-cpu`) | Indexing with dynamic rebuilding on manifest mismatch |
| **Lexical Search** | BM25Retriever | Top-$K=4$ keyword retrieval used as fallback when FAISS distance $> 1.35$ |
| **Cloud LLM Engine** | ChatOpenAI (`gpt-4.1-mini`) | Low temperature ($T=0$), streaming token support |
| **Local LLM Engine** | ChatOllama (`qwen2.5:latest`) | Context window: 4096 tokens, temperature: $0.1$ |
| **Web Interface** | Streamlit | Custom CSS styling, responsive quick-prompt action cards |

---

## ⚙️ Installation & Prerequisites

### Prerequisites
- **Python**: Version 3.10 or higher
- **Node/Chromium runtime**: Managed by Playwright
- **Ollama**: (Optional) Required only when running the local model stack

### 1. Repository Setup

```bash
git clone https://github.com/prabathsmp/AI-B12-2.git
cd AI-B12-2/Buildathon
```

### 2. Virtual Environment Configuration

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies & Browser Binaries

```bash
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure Environment Variables

Create a `.env` file in the `Buildathon` directory:

```env
# Cloud Model Configuration (openapi-vivasai-app.py)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini

# Local Model Configuration (ollama-vivasai-app.py)
OLLAMA_MODEL=qwen2.5:latest
OLLAMA_BASE_URL=http://localhost:11434
```

---

## 🚀 Step-by-Step Execution Guide

### Step 1: Scrape & Build Scheme Database

Run the automated ingestion script to populate the local document repository with official Tamil Nadu government schemes:

```bash
# Download 30 schemes in headless mode
python download_uzhavan_schemes.py --target 30

# Optional: Run with visual browser UI enabled
python download_uzhavan_schemes.py --target 30 --headed
```

The script saves formatted PDFs to `uzhavan_scheme_pdfs/` and writes extraction summaries to `download_report.csv`.

---

### Step 2: Launch the Assistant

#### Option A: OpenAI Cloud Interface
```bash
streamlit run openapi-vivasai-app.py
```

#### Option B: Local Ollama Interface
Ensure Ollama is running and has the target model pulled:
```bash
ollama pull qwen2.5:latest
streamlit run ollama-vivasai-app.py
```

Access the web interface at `http://localhost:8501`.

---

## 🛡️ Guardrails & Safety Architecture

1. **Adversarial Interception**: Regex detectors inspect inbound queries for instruction override tokens (`ignore previous instructions`, `system prompt`, `developer prompt`, `jailbreak`), immediately terminating evaluation before LLM execution.
2. **System Prompt Obfuscation**: The system explicitly forbids disclosure of runtime variables, directory routes, API keys, or embedded prompts.
3. **Strict Verifiability Standard**: If a question cannot be resolved using the retrieved context, the assistant outputs a standard disclaimer:
   > *"The available documents do not contain information to verify this. Please check with your local agricultural officer or the official department portal."*
4. **Cache & Manifest Invalidation**: Every session launch compares file size and modification timestamps against `pdf_manifest.json`. Adding or removing PDFs automatically triggers an index rebuild.

---

## 👥 Authors & Acknowledgments

- **Prabath** ([@prabathsmp](https://github.com/prabathsmp))
- Created as part of the **AI-B12-2 Buildathon**.