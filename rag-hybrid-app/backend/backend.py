import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

app = FastAPI(title="Hybrid Graph-Vector RAG Engine")

# -------------------------------------------------------------------
# Configuration & Constants
# -------------------------------------------------------------------
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100
RETRIEVER_K = 4

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "97f40310")

FAISS_DIR = Path("./faiss_storage")
FAISS_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# Singletons & Embeddings with Normalization
# -------------------------------------------------------------------
embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    encode_kwargs={"normalize_embeddings": True},
)
llm = ChatOpenAI(model=LLM_MODEL, temperature=0)

try:
    graph = Neo4jGraph(
        url=NEO4J_URI,
        username=NEO4J_USERNAME,
        password=NEO4J_PASSWORD,
        database=NEO4J_DATABASE,
        refresh_schema=False,
    )
    graph.query("RETURN 1 AS test")
    print(f"✅ Neo4j connected successfully to {NEO4J_DATABASE}")
except Exception as e:
    graph = None
    print(f"❌ Neo4j connection failure: {e}")

vector_store: Optional[FAISS] = None
if (FAISS_DIR / "index.faiss").exists():
    vector_store = FAISS.load_local(
        str(FAISS_DIR), embeddings, allow_dangerous_deserialization=True
    )

# -------------------------------------------------------------------
# Guardrails & Greetings Interceptors
# -------------------------------------------------------------------
ADVERSARIAL_PATTERNS = [
    r"system\s*prompt",
    r"developer\s*prompt",
    r"hidden\s*instructions",
    r"reveal\s*(your\s*)?(rules|prompt)",
    r"ignore\s*(all\s*)?(previous|above)\s*instructions",
    r"jailbreak",
    r"bypass\s*safety",
]

GREETING_PATTERNS = [
    r"^(hi|hello|hey|vanakkam|good\s*(morning|afternoon|evening)|namaste|greetings)(\s+.*)?[!.]*$"
]

REFUSAL_MESSAGE = (
    "I am designed to assist strictly within document knowledge constraints. "
    "I cannot share internal system configurations or process malicious queries."
)

FALLBACK_MESSAGE = (
    "The available documents and knowledge graph do not contain sufficient verified "
    "information to answer this request."
)


def is_greeting(text: str) -> bool:
    lowered = text.strip().lower()
    for pattern in GREETING_PATTERNS:
        if re.match(pattern, lowered):
            return True
    return False


def run_input_guardrail(query: str) -> bool:
    if len(query.strip()) == 0 or len(query) > 2000:
        return False
    lowered = query.lower()
    for pattern in ADVERSARIAL_PATTERNS:
        if re.search(pattern, lowered):
            return False
    return True


# -------------------------------------------------------------------
# Pydantic Schemas
# -------------------------------------------------------------------
class ChatHistoryItem(BaseModel):
    role: str
    content: str


class QueryRequest(BaseModel):
    query: str
    history: List[ChatHistoryItem] = []


class Citation(BaseModel):
    source: str
    page: int
    content: str
    type: str  # 'vector' or 'knowledge_graph'


class QueryResponse(BaseModel):
    answer: str
    citations: List[Citation]
    retrieval_mode: str
    guardrail_flag: bool


# -------------------------------------------------------------------
# Ingestion Pipeline
# -------------------------------------------------------------------
def ingest_pdf_to_vector_and_graph(file_path: Path, filename: str):
    global vector_store
    loader = PyPDFLoader(str(file_path))
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(pages)

    for c in chunks:
        c.metadata["source"] = filename

    # 1. FAISS Ingestion
    vector_store = FAISS.from_documents(chunks, embeddings)
    vector_store.save_local(str(FAISS_DIR))

    # 2. Neo4j Knowledge Graph Ingestion
    if graph:
        try:
            transformer = LLMGraphTransformer(llm=llm, ignore_tool_usage=False)
            graph_documents = transformer.convert_to_graph_documents(chunks)
            graph.add_graph_documents(graph_documents, include_source=True)
            print(f"--> Extracted and wrote {len(graph_documents)} graph docs to Neo4j.")
        except Exception as e:
            print(f"❌ Neo4j Graph Extraction Error: {e}")

    return len(chunks)


# -------------------------------------------------------------------
# Retrieval Pipeline
# -------------------------------------------------------------------
def retrieve_hybrid(query: str):
    citations: List[Citation] = []
    vector_context = []
    graph_context = []

    # 1. Vector Search (Retrieves top K chunks reliably)
    if vector_store:
        matched_docs = vector_store.similarity_search(query, k=RETRIEVER_K)
        for doc in matched_docs:
            vector_context.append(doc.page_content)
            citations.append(
                Citation(
                    source=doc.metadata.get("source", "PDF Document"),
                    page=int(doc.metadata.get("page", 0)) + 1,
                    content=doc.page_content,
                    type="vector",
                )
            )

    # 2. Knowledge Graph Entity & Triple Retrieval
    if graph:
        try:
            entity_extraction_prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "Extract 1 to 3 key technical terms, entities, or concepts from the query "
                        "as a comma-separated list. Output only the terms.",
                    ),
                    ("human", "{query}"),
                ]
            )
            extracted = (
                (entity_extraction_prompt | llm)
                .invoke({"query": query})
                .content.strip()
            )
            entities = [e.strip() for e in extracted.split(",") if len(e.strip()) > 1]

            for entity in entities:
                cypher_query = """
                MATCH (n)-[r]->(m)
                WHERE n.id =~ $pattern OR m.id =~ $pattern OR type(r) =~ $pattern
                RETURN n.id AS source, type(r) AS rel, m.id AS target
                LIMIT 6
                """
                pattern = f"(?i).*{re.escape(entity)}.*"
                records = graph.query(cypher_query, params={"pattern": pattern})

                for rec in records:
                    fact = f"({rec['source']}) -[:{rec['rel']}]-> ({rec['target']})"
                    graph_context.append(fact)
                    citations.append(
                        Citation(
                            source="Neo4j KnowledgeGraph",
                            page=1,
                            content=fact,
                            type="knowledge_graph",
                        )
                    )
        except Exception as e:
            print(f"Graph retrieval issue: {e}")

    return vector_context, graph_context, citations


# -------------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "vector_ready": vector_store is not None,
        "graph_ready": graph is not None,
    }


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = Path(tmp.name)

    try:
        chunks_count = ingest_pdf_to_vector_and_graph(temp_path, file.filename)
    finally:
        if temp_path.exists():
            temp_path.unlink()

    return {
        "message": f"Successfully ingested {file.filename}",
        "chunks_indexed": chunks_count,
    }


@app.post("/query", response_model=QueryResponse)
def handle_rag_query(payload: QueryRequest):
    query = payload.query

    # Step 1: Upstream Safety Guardrail
    if not run_input_guardrail(query):
        return QueryResponse(
            answer=REFUSAL_MESSAGE,
            citations=[],
            retrieval_mode="Guardrail Refusal",
            guardrail_flag=True,
        )

    # Step 2: Greeting Interceptor
    if is_greeting(query):
        return QueryResponse(
            answer="Hello! How may I assist you with your uploaded documents today?",
            citations=[],
            retrieval_mode="Conversational",
            guardrail_flag=False,
        )

    # Step 3: Hybrid Retrieval (FAISS + Neo4j)
    vector_texts, graph_facts, citations = retrieve_hybrid(query)
    combined_context_parts = []

    if vector_texts:
        combined_context_parts.append(
            "=== Document Context ===\n" + "\n\n".join(vector_texts)
        )
    if graph_facts:
        combined_context_parts.append(
            "=== Knowledge Graph Triples ===\n" + "\n".join(graph_facts)
        )

    augmented_context = "\n\n".join(combined_context_parts)

    if not augmented_context.strip():
        return QueryResponse(
            answer=FALLBACK_MESSAGE,
            citations=[],
            retrieval_mode="Hybrid (No Context)",
            guardrail_flag=False,
        )

    # Step 4: History Resolution
    history_messages = []
    for item in payload.history[-4:]:
        if item.role == "user":
            history_messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            history_messages.append(AIMessage(content=item.content))

    # Step 5: Grounded Augmentation & Generation
    rag_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert technical documentation assistant. Answer the user's question "
                "thoroughly and accurately based ONLY on the provided document context and Knowledge Graph facts.\n"
                "- Extract exact bullet points, tools, libraries, and frameworks mentioned.\n"
                "- If the context does not contain the answer, state: "
                f"'{FALLBACK_MESSAGE}'.",
            ),
            MessagesPlaceholder("chat_history"),
            (
                "human",
                "Context:\n{context}\n\nQuestion: {query}\n\nStructured Answer:",
            ),
        ]
    )

    generation_chain = rag_prompt | llm
    generated_text = generation_chain.invoke(
        {
            "context": augmented_context,
            "query": query,
            "chat_history": history_messages,
        }
    ).content.strip()

    mode_str = "Hybrid (FAISS + Neo4j)" if (vector_texts and graph_facts) else (
        "Vector Only (FAISS)" if vector_texts else "Graph Only (Neo4j)"
    )

    return QueryResponse(
        answer=generated_text,
        citations=citations,
        retrieval_mode=mode_str,
        guardrail_flag=False,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)