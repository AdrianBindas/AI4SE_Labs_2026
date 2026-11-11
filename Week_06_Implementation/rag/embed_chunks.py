from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .common import (
    CHUNKS_PATH,
    EMBEDDING_DIMENSIONS,
    EMBEDDINGS_PATH,
    hashed_embedding,
    read_json,
    write_json,
)


def embed_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for chunk in chunks:
        content = f"{chunk['path']}\n{chunk['text']}"
        records.append({**chunk, "embedding": hashed_embedding(content)})
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Vectorize repository chunks.")
    parser.add_argument("--chunks", type=Path, default=CHUNKS_PATH)
    parser.add_argument("--output", type=Path, default=EMBEDDINGS_PATH)
    args = parser.parse_args()

    chunk_data = read_json(args.chunks)
    chunks = chunk_data.get("chunks")
    if not isinstance(chunks, list):
        raise ValueError(f"chunks list missing from {args.chunks}")
    records = embed_chunks(chunks)
    write_json(
        args.output,
        {
            "method": "384-dimensional signed feature hashing (tokens and adjacent pairs)",
            "dimensions": EMBEDDING_DIMENSIONS,
            "records": records,
        },
    )
    print(f"Wrote {len(records)} chunk/embedding pairs to {args.output}")


if __name__ == "__main__":
    main()
