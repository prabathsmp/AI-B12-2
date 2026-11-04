# ⚡ OpsCommand: Multi-Agent AI Customer Support Desk

An enterprise-ready, autonomous customer support and incident routing system powered by **AutoGen (v0.4+)**, **Hybrid RAG (FAISS + BM25 Okapi)**, and a gamified **Streamlit** operator console.

---

## 🌟 Key Architecture & Capabilities

1. **Autonomous 4-Agent Pipeline**:
   - **Customer Query Agent**: Parses raw tickets, sanitizes fields, extracts categorization, urgency, and customer sentiment.
   - **Knowledge Base Agent**: Queries Markdown policies using a Hybrid Vector & Lexical retriever (FAISS inner product + BM25 scoring).
   - **Resolution Agent**: Synthesizes grounded, policy-compliant resolution drafts without hallucinations.
   - **Log Agent**: Applies strict safety guardrails, makes decisive escalation decisions (Human Hand-off vs. Autonomously Resolved), and writes idempotent ticket records to `logs/tickets.csv`.

2. **Gamified Operator Console**:
   - Live HUD tracking Resolution Rate %, Escalation Counts, and Operator Support XP.
   - Dynamic Rank Progression from *Bronze Scout* to *Diamond Commander*.
   - 8 Benchmark Test Suite with one-click evaluation preloading.
   - Integrated Admin Portal with real-time Knowledge Base re-indexing and CSV log exports.

---

## 📂 Repository Structure

```text
multi-agent-customer-support/
├── agents/
│   ├── __init__.py
│   ├── query_agent.py
│   ├── knowledge_agent.py
│   ├── resolution_agent.py
│   └── log_agent.py
├── knowledge_base/
│   ├── account_and_login.md
│   ├── product_faq.md
│   ├── refund_policy.md
│   └── shipping_policy.md
├── logs/
│   └── tickets.csv
├── app.py
├── rag_engine.py
├── team.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
└── README.md
```

---

## 🐳 Docker Deployment Guide

The application is containerized using multi-stage Python 3.11 images with volume mounts for continuous log persistence and dynamic policy hot-reloading.

### Prerequisites
- **Local**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- **VPS**: Any cloud provider (AWS EC2, DigitalOcean, Hetzner, Linode, etc.) running Ubuntu 22.04/24.04 with Docker and Docker Compose installed.
- **OpenAI API Key**: Access to `gpt-4o-mini` or `gpt-4o`.

---

### Option A: Local Deployment (Docker Desktop)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/multi-agent-customer-support.git
   cd multi-agent-customer-support
   ```

2. **Configure Environment Variables**:
   Create a `.env` file in the project root:
   ```env
   OPENAI_API_KEY=sk-proj-yourActualOpenAiKeyHere
   MODEL_NAME=gpt-4o-mini
   ```

3. **Build & Launch Container**:
   ```bash
   docker compose up -d --build
   ```

4. **Access the Console**:
   Open your browser and navigate to:
   ```text
   http://localhost:8501
   ```

5. **Stop Container**:
   ```bash
   docker compose down
   ```

---

### Option B: Remote VPS Deployment (Ubuntu Linux)

1. **SSH into your VPS**:
   ```bash
   ssh root@<your-vps-ip>
   ```

2. **Install Docker Engine & Compose (if not already installed)**:
   ```bash
   sudo apt update
   sudo apt install -y ca-certificates curl gnupg lsb-release
   sudo mkdir -p /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
   ```

3. **Clone the Repository**:
   ```bash
   git clone https://github.com/<your-username>/multi-agent-customer-support.git
   cd multi-agent-customer-support
   ```

4. **Configure Secrets**:
   Create your production `.env` file securely on the server:
   ```bash
   nano .env
   ```
   Add your variables:
   ```env
   OPENAI_API_KEY=sk-proj-yourActualOpenAiKeyHere
   MODEL_NAME=gpt-4o-mini
   ```
   *(Save and exit via `CTRL+O`, `ENTER`, `CTRL+X`)*.

5. **Configure Firewall (Port 8501)**:
   Allow inbound traffic on port 8501:
   ```bash
   sudo ufw allow 8501/tcp
   sudo ufw reload
   ```

6. **Build and Run in Detached Mode**:
   ```bash
   docker compose up -d --build
   ```

7. **Verify Deployment & Monitoring**:
   - Check container running state:
     ```bash
     docker compose ps
     ```
   - Stream container agent logs in real time:
     ```bash
     docker compose logs -f --tail=100
     ```

8. **Access via Public IP**:
   Navigate to `http://<your-vps-ip>:8501` in your browser.

---

## 💾 Data Persistence & Live Re-indexing

- **Audited Ticket Logs (`logs/tickets.csv`)**: 
  The `docker-compose.yml` mounts `./logs` as a persistent volume. Whenever tickets are logged or escalated, they are directly recorded on the host machine's disk, surviving container restarts and image updates.
- **Knowledge Base Policies (`knowledge_base/`)**:
  Mounted directly into `/app/knowledge_base`. You can edit existing `.md` policies or drop new ones directly on your server host without rebuilding the container. Navigate to the **Admin & Operations Portal** and click **Re-Index Knowledge Base Documents**.
- **Hybrid retrieval index (`faiss_index/`)**:
  FAISS vectors and chunk metadata are persisted on the host. BM25 is rebuilt from the saved chunk corpus at startup, avoiding repeated embedding generation after container recreation. Re-index after editing policy documents.

---

## 🛠️ Local Python Development (Without Docker)

If you prefer testing directly on your local Python environment:

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate    # On Windows: .\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup .env
cp .env.example .env  # Add your OPENAI_API_KEY

# 4. Run Streamlit application
streamlit run app.py
```

---

## 🧪 Benchmark Testing

The application comes pre-loaded with the standard 8 benchmark queries covering:
- Regular policy retrieval (Shipping delays, 30-day return windows, Warranty coverage)
- Account self-service workflows (Password reset procedures)
- Guardrail escalations (Angry sentiment, 3x billing dispute charges, explicit legal threats)
- Out-of-domain rejection (B2B corporate gift card inquiries with no policy match)

Load any benchmark scenario directly from the **Admin & Operations Portal -> Benchmark Evaluation Suite** tab.

## Buildathon Evaluation (Benchmark + RAG)

The Admin Portal now includes:

- **Benchmark Evaluation Suite:** runs all 8 customer scenarios through the actual multi-agent team. It checks expected final status deterministically and optionally uses an LLM judge to assess response quality (grounding, completeness, empathy). Enable/disable the judge in the UI; it makes additional model calls.
- **RAG Evaluation Metrics:** compares FAISS vector retrieval, BM25, and RRF using source-level relevance labels for the benchmark cases. It reports Hit Rate@K, Precision@K, Recall@K, MRR@K, and per-query retrieval latency.
- Benchmark tickets are written to `logs/benchmark_runs/benchmark_tickets.csv`, separate from production `logs/tickets.csv` so evaluation does not affect customer ticket/XP counts.

Run the app and open **Ops & Control Panel**:
1. Run all 8 benchmark cases in the Benchmark Evaluation Suite.
2. Run RAG Evaluation Metrics separately to compare retrieval strategies.
3. Download the RAG results JSON for evidence in your Buildathon presentation.

Note: The RAG relevance labels are source-document-level labels manually mapped to the current benchmark questions. Unsupported/escalation cases are tracked separately and excluded from the labeled-source average. LLM-as-a-Judge results are model-based assessments, not ground truth.
