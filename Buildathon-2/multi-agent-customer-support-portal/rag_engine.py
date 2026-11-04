"""Hybrid retrieval engine: normalized FAISS cosine search + BM25 + Reciprocal Rank Fusion.

FAISS stores normalized embeddings (inner product == cosine similarity).
BM25 scores are not directly comparable to cosine scores, so they are fused
by rank using RRF rather than adding raw scores.
"""
from __future__ import annotations

import glob
import json
import os
import re
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

INDEX_DIR = os.getenv("RAG_INDEX_DIR", "faiss_index")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
RRF_K = 60
TOKEN_RE = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)*", re.IGNORECASE)


def tokenize(text: str) -> List[str]:
    """Simple normalized tokenizer shared by corpus and query."""
    return TOKEN_RE.findall(text.lower())


class HybridRAGEngine:
    def __init__(self, kb_dir: str = "knowledge_base", index_dir: str = INDEX_DIR):
        self.kb_dir = kb_dir
        self.index_dir = index_dir
        self.encoder = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.chunks: List[Dict[str, str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.index: Optional[faiss.Index] = None
        self.is_indexed = False

    @staticmethod
    def _chunk_text(
        text: str, source_file: str, chunk_size: int = 700, overlap: int = 100
    ) -> List[Dict[str, str]]:
        """Chunk by characters, preserving paragraph boundaries where possible."""
        if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
            raise ValueError("chunk_size must be > overlap >= 0")

        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        if not text:
            return []

        chunks: List[Dict[str, str]] = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                # Prefer a nearby paragraph/sentence boundary without making tiny chunks.
                boundary = max(text.rfind("\n\n", start, end),
                               text.rfind(". ", start, end),
                               text.rfind("\n", start, end))
                if boundary > start + int(chunk_size * 0.60):
                    end = boundary + (2 if text[boundary:boundary + 2] == "\n\n" else 1)

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"source": source_file, "text": chunk_text})

            if end >= len(text):
                break
            start = max(end - overlap, start + 1)

        return chunks

    def _rebuild_bm25(self) -> None:
        tokenized = [tokenize(chunk["text"]) for chunk in self.chunks]
        if not tokenized or not any(tokenized):
            raise ValueError("Knowledge base contains no searchable text.")
        self.bm25 = BM25Okapi(tokenized)

    def build_or_refresh_index(self):
        md_files = sorted(glob.glob(os.path.join(self.kb_dir, "**", "*.md"), recursive=True))
        if not md_files:
            raise FileNotFoundError(f"No markdown documents found in '{self.kb_dir}'.")

        all_chunks: List[Dict[str, str]] = []
        for file_path in md_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            source = os.path.relpath(file_path, self.kb_dir).replace(os.sep, "/")
            all_chunks.extend(self._chunk_text(content, source))

        if not all_chunks:
            raise ValueError("Markdown files were found, but no non-empty chunks were produced.")

        embeddings = self.encoder.encode(
            [chunk["text"] for chunk in all_chunks],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=len(all_chunks) > 100,
        ).astype(np.float32)

        # Keep corpus/index assignment aligned: row i always represents chunks[i].
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        os.makedirs(self.index_dir, exist_ok=True)
        faiss.write_index(index, os.path.join(self.index_dir, "vectors.faiss"))
        with open(os.path.join(self.index_dir, "chunks.json"), "w", encoding="utf-8") as f:
            json.dump(
                {"model": EMBEDDING_MODEL_NAME, "chunks": all_chunks},
                f, ensure_ascii=False, indent=2
            )

        self.chunks = all_chunks
        self.index = index
        self._rebuild_bm25()
        self.is_indexed = True
        return len(self.chunks), len(md_files)

    def load_index(self) -> bool:
        index_path = os.path.join(self.index_dir, "vectors.faiss")
        metadata_path = os.path.join(self.index_dir, "chunks.json")
        if not (os.path.exists(index_path) and os.path.exists(metadata_path)):
            return False

        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        if metadata.get("model") != EMBEDDING_MODEL_NAME:
            # Avoid comparing embeddings generated by a different encoder.
            return False

        chunks = metadata.get("chunks", [])
        index = faiss.read_index(index_path)
        if not chunks or index.ntotal != len(chunks):
            return False

        self.chunks = chunks
        self.index = index
        self._rebuild_bm25()
        self.is_indexed = True
        return True

    def _ensure_index(self) -> None:
        if self.is_indexed and self.index is not None and self.bm25 is not None:
            return
        if not self.load_index():
            self.build_or_refresh_index()

    @staticmethod
    def _rrf(rank_lists: List[List[int]], rrf_k: int = RRF_K) -> Dict[int, float]:
        """Fuse ranked document IDs using 1/(k + rank), ranks are 1-based."""
        scores: Dict[int, float] = {}
        for ranked_ids in rank_lists:
            seen = set()
            for rank, doc_id in enumerate(ranked_ids, start=1):
                if doc_id in seen:
                    continue
                seen.add(doc_id)
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank)
        return scores

    def hybrid_search(self, query: str, top_k: int = 3, candidate_k: Optional[int] = None) -> Dict[str, Any]:
        if not query or not query.strip():
            return {"query": query, "vector_results": [], "bm25_results": [], "fused_results": []}
        if top_k < 1:
            raise ValueError("top_k must be >= 1")

        self._ensure_index()
        n = len(self.chunks)
        candidate_k = min(n, max(candidate_k or top_k * 3, top_k))

        # Vector search: embeddings are unit-normalized, so IP is cosine similarity.
        q_embedding = self.encoder.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        ).astype(np.float32)
        vector_scores, vector_ids = self.index.search(q_embedding, candidate_k)
        vector_ranked = [int(i) for i in vector_ids[0] if i >= 0]

        # BM25 lexical retrieval (tokenization consistent with corpus).
        bm25_scores = self.bm25.get_scores(tokenize(query))
        bm25_ranked = [
            int(i) for i in np.argsort(bm25_scores)[::-1][:candidate_k]
            if float(bm25_scores[i]) > 0.0
        ]

        fused_scores = self._rrf([vector_ranked, bm25_ranked])

        def result_for(doc_id: int, score: float, rank: int) -> Dict[str, Any]:
            chunk = self.chunks[doc_id]
            return {
                "source": chunk["source"],
                "text": chunk["text"],
                "score": float(score),
                "rank": rank,
                "chunk_id": doc_id,
            }

        vector_results = [
            result_for(doc_id, vector_scores[0][rank], rank + 1)
            for rank, doc_id in enumerate(vector_ranked[:top_k])
        ]
        bm25_results = [
            result_for(doc_id, bm25_scores[doc_id], rank + 1)
            for rank, doc_id in enumerate(bm25_ranked[:top_k])
        ]
        fused_ranked = sorted(fused_scores.items(), key=lambda item: (-item[1], item[0]))
        fused_results = [
            result_for(doc_id, score, rank + 1)
            for rank, (doc_id, score) in enumerate(fused_ranked[:top_k])
        ]

        return {
            "query": query,
            "vector_results": vector_results,
            "bm25_results": bm25_results,
            "fused_results": fused_results,
            "fusion": f"Reciprocal Rank Fusion (RRF k={RRF_K})",
        }


rag_engine = HybridRAGEngine()
