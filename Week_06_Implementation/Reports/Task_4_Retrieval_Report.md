# Task 4 — Matching Design

I embed each input task with the same feature-hashing method and rank stored vectors by cosine similarity. The retrieval function accepts `n`, returns up to the `n` highest-scoring chunks, and uses path and chunk ID as deterministic tie-breakers. This keeps the implementation simple and reproducible.

Scripts: rag/retrieve_chunks.py