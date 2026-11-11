from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from .common import (
    CHUNKS_PATH,
    EXCLUDED_DIRECTORY_NAMES,
    REPOSITORY_ROOT,
    TEXT_SUFFIXES,
    write_json,
)

LINES_PER_CHUNK = 80
OVERLAP_LINES = 15


def chunk_text_file(path: Path, relative_path: str) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    chunks: list[dict[str, object]] = []
    start = 0
    while start < len(lines):
        end = min(start + LINES_PER_CHUNK, len(lines))
        content = "\n".join(lines[start:end])
        chunk_id = hashlib.sha1(
            f"{relative_path}:{start + 1}:{end}".encode("utf-8")
        ).hexdigest()[:16]
        chunks.append(
            {
                "id": chunk_id,
                "path": relative_path,
                "start_line": start + 1,
                "end_line": end,
                "text": content,
            }
        )
        if end == len(lines):
            break
        start = end - OVERLAP_LINES
    return chunks


def chunk_repository(root: Path) -> list[dict[str, object]]:
    if not root.is_dir():
        raise FileNotFoundError(f"repository directory does not exist: {root}")

    chunks: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative.parts):
            continue
        chunks.extend(chunk_text_file(path, relative.as_posix()))
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk the sample repository.")
    parser.add_argument("--repository", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--output", type=Path, default=CHUNKS_PATH)
    args = parser.parse_args()

    chunks = chunk_repository(args.repository)
    write_json(args.output, {"repository": str(args.repository), "chunks": chunks})
    print(f"Wrote {len(chunks)} chunks to {args.output}")


if __name__ == "__main__":
    main()
