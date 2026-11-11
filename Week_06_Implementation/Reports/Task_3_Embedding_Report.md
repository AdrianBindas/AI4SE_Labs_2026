# Task 3 — Embedding and Storage Design

I represented each chunk with a normalized 384-dimensional signed feature-hashing vector, using identifier/word tokens and adjacent-token pairs from its path and text. This deterministic local method needs no model download, API key, or external service and produces numeric vectors suitable for cosine ranking; unlike a trained embedding model, it captures lexical rather than deep semantic similarity. I store each vector beside its source chunk in `rag/data/embeddings.json`.

Scripts: rag/embed_chunks.py