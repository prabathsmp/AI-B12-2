import os
import streamlit as st
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate


# --------------------------------------------------
# Configuration
# --------------------------------------------------

load_dotenv()

PDF_FOLDER = "documents"
FAISS_DB_PATH = "faiss_index"

st.set_page_config(
    page_title="Multi-PDF RAG",
    page_icon="📚"
)

st.title("Multi-PDF RAG Application")


# --------------------------------------------------
# Embeddings
# --------------------------------------------------

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


# --------------------------------------------------
# Create FAISS index from all PDFs
# --------------------------------------------------

def create_vector_db():

    chunks = []

    # Split each PDF into chunks.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    pdf_files = [
        filename
        for filename in os.listdir(PDF_FOLDER)
        if filename.lower().endswith(".pdf")
    ]

    if not pdf_files:
        raise ValueError(
            f"No PDF files found in '{PDF_FOLDER}'."
        )

    for filename in sorted(pdf_files):

        pdf_path = os.path.join(PDF_FOLDER, filename)

        st.write(f"Processing: {filename}")

        loader = PyPDFLoader(pdf_path)
        documents = loader.load()

        # Preserve the original filename.
        # PyPDFLoader already supplies the page number.
        for document in documents:
            document.metadata["source"] = filename

        pdf_chunks = splitter.split_documents(documents)

        chunks.extend(pdf_chunks)

    if not chunks:
        raise ValueError(
            "No text chunks were extracted from the PDFs."
        )

    # Create ONE FAISS database for all PDFs.
    vector_db = FAISS.from_documents(
        chunks,
        embeddings
    )

    # Persist the index to disk.
    vector_db.save_local(FAISS_DB_PATH)

    return vector_db, len(chunks), len(pdf_files)


# --------------------------------------------------
# Load FAISS index
# --------------------------------------------------

def load_vector_db():

    index_file = os.path.join(
        FAISS_DB_PATH,
        "index.faiss"
    )

    metadata_file = os.path.join(
        FAISS_DB_PATH,
        "index.pkl"
    )

    # Reuse the existing index if available.
    if (
        os.path.exists(index_file)
        and os.path.exists(metadata_file)
    ):

        vector_db = FAISS.load_local(
            FAISS_DB_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

        return vector_db, None, None

    # Otherwise, build the index.
    return create_vector_db()


# --------------------------------------------------
# Initialize the vector database
# --------------------------------------------------

if "store" not in st.session_state:

    try:

        with st.spinner(
            "Loading or building FAISS index..."
        ):

            store, chunk_count, pdf_count = load_vector_db()

            st.session_state.store = store

        if chunk_count is not None:

            st.success(
                f"Indexed {chunk_count} chunks "
                f"from {pdf_count} PDFs."
            )

        else:

            st.info(
                "Loaded the existing FAISS index from disk."
            )

    except Exception as exc:

        st.error(f"Failed to initialize RAG: {exc}")


# --------------------------------------------------
# Ask questions
# --------------------------------------------------

if "store" in st.session_state:

    st.subheader("Ask a question")

    question = st.text_input(
        "Enter your question"
    )

    if st.button("Get Answer") and question.strip():

        # Retrieve the three most relevant chunks.
        docs = st.session_state.store.as_retriever(
            search_kwargs={"k": 3}
        ).invoke(question)

        # Combine retrieved text.
        context = "\n\n".join(
            doc.page_content for doc in docs
        )

        # Short prompt to reduce token usage.
        prompt = ChatPromptTemplate.from_template("""
Answer using only the context. If unavailable, say
"I don't know from the provided documents."

Context:
{context}

Question: {question}

Answer:
""")

        llm = ChatOpenAI(
            model="gpt-4.1-mini",
            temperature=0
        )

        chain = prompt | llm

        response = chain.invoke({
            "context": context,
            "question": question
        })

        st.subheader("Answer")
        st.write(response.content)

        # Display source filenames and page numbers.
        st.subheader("Sources")

        for doc in docs:

            filename = doc.metadata.get(
                "source",
                "Unknown file"
            )

            # PyPDFLoader uses zero-based page numbers.
            page = doc.metadata.get("page", 0) + 1

            st.caption(
                f"{filename} - page {page}"
            )

            # with st.expander(
            #     f"View excerpt: {filename}, page {page}"
            # ):
            #     st.write(doc.page_content)
