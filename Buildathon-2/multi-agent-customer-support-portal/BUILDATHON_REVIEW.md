# Buildathon Code Review & Change Log

## Summary
This is a good demo concept: a Streamlit operator dashboard, four AutoGen agents, policy retrieval, escalation, and CSV audit history. The original implementation had several correctness and demo-reliability issues. The current revision addresses the most impactful ones.

## Important fixes applied
- Implemented actual Reciprocal Rank Fusion (RRF) over FAISS and BM25 ranks. Previously the engine returned two independent lists and did **not** fuse them.
- Replaced paragraph-only splitting (the `chunk_size` and `overlap` parameters were ignored) with bounded overlapping chunks.
- Added consistent lexical tokenization for BM25 instead of `lower().split()`.
- Persisted FAISS vectors and chunk metadata under `faiss_index/`; BM25 is rebuilt from metadata on load. Docker Compose now persists this directory.
- Verified FAISS configuration: unit-normalized sentence embeddings + `IndexFlatIP` correctly approximate cosine similarity.
- Made benchmark case preload work by using the same Streamlit widget keys as session state.
- Replaced collision-prone microsecond-derived ticket IDs with UUID-based IDs.
- Added a missing OpenAI API-key validation with a clear error.
- Added explicit final-status parsing so the UI can display Escalated when the Log Agent emits its status.
- Added basic deterministic risk hints for legal threats, fraud, and duplicate/disputed charges.
- Escaped model-generated response text before embedding it in HTML to reduce HTML/script injection risk.
- Applied `theme.png` as a full-page Streamlit background with a dark readability overlay.
- Added `.env.example` because README referred to it but the original archive did not include it.
- Added prompt-injection warnings for user complaint text.

## RAG correctness notes
- FAISS: `normalize_embeddings=True` plus inner product is the standard cosine-similarity approach for normalized vectors.
- BM25: lexical score magnitudes are not comparable with cosine scores. RRF correctly fuses by rank:
  `RRF(d) = sum(1 / (k + rank_i(d)))`, with ranks starting at 1 and `k=60`.
- The engine exposes vector, BM25, and fused result lists for diagnostics.
- Re-index the knowledge base after policy edits from the Admin panel.

## Remaining recommendations before final submission
1. **Run end-to-end tests with a valid API key.** This environment did not have Streamlit, FAISS, Sentence Transformers, or AutoGen installed, so live app execution and provider calls could not be verified here.
2. Add automated regression assertions for all eight benchmark scenarios (expected category, match/no-match, and escalation status). Current benchmark cases are preloaded but are not a true automated evaluation harness.
3. Replace CSV with SQLite/Postgres if multiple users or concurrent ticket processing are expected. CSV append/dedup is not transaction-safe under concurrent writes.
4. Add authentication/authorization to the Admin portal before exposing it publicly. Streamlit's current UI has no admin access control.
5. Keep `.env` and logs out of source control. Never use a real API key in screenshots or demo recordings.
6. Add rate limiting, timeout/retry handling, and a user-visible failure state for API errors.
7. Avoid describing this as fully autonomous/enterprise-ready unless you add human approval, monitoring, auth, and persistent database controls.

## Manual smoke test
- Run `pip install -r requirements.txt`.
- Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
- Start `streamlit run app.py`.
- Load benchmark cases 1, 5, 6, and 8; verify form fields populate and expected resolved/escalated badge is displayed.
- Re-index policies; verify Admin panel reports chunks/files.
- Restart app/container; verify saved FAISS index loads without re-embedding.
- Review `logs/tickets.csv` and export it from Admin.
