from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

from .common import EMBEDDINGS_PATH, hashed_embedding, read_json


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("embedding dimensions do not match")
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def retrieve(
    query: str, records: list[dict[str, Any]], limit: int = 5
) -> list[dict[str, Any]]:
    if isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")
    query_embedding = hashed_embedding(query)
    ranked = [
        {
            **record,
            "similarity": cosine_similarity(query_embedding, record["embedding"]),
        }
        for record in records
    ]
    ranked.sort(key=lambda record: (-record["similarity"], record["path"], record["id"]))
    return ranked[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve relevant repository chunks.")
    parser.add_argument("query", help="Textual programming task")
    parser.add_argument("-n", "--limit", type=int, default=5)
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS_PATH)
    args = parser.parse_args()

    storage = read_json(args.embeddings)
    records = storage.get("records")
    if not isinstance(records, list):
        raise ValueError(f"embedding records missing from {args.embeddings}")
    for record in retrieve(args.query, records, args.limit):
        print(f"{record['path']}:{record['start_line']}-{record['end_line']} "
              f"(similarity={record['similarity']:.3f})")


if __name__ == "__main__":
    main()
