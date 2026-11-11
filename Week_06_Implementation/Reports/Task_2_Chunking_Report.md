# Task 2 — Chunking Design

I split supported text and source files into windows of up to 80 lines with a 15-line overlap. Line-based windows keep implementation and nearby context readable, while overlap reduces the chance that a method or explanation is cut off at a boundary. Each JSON chunk records its repository-relative path, line range, stable ID, and text. Git metadata, caches, virtual environments, and binary files are excluded.

Scripts: rag/chunk_repository.py