from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = WORKSPACE_ROOT / "AI4SE_Playground"
DATA_DIR = Path(__file__).resolve().parent / "data"
CHUNKS_PATH = DATA_DIR / "chunks.json"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.json"
EMBEDDING_DIMENSIONS = 384
TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|\d+")
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    ".venv",
}
TEXT_SUFFIXES = {".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}


def hashed_embedding(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    """Create a normalized feature-hashing vector from tokens and adjacent pairs."""
    if dimensions < 1:
        raise ValueError("dimensions must be positive")

    tokens = [token.casefold() for token in TOKEN_PATTERN.findall(text)]
    features = tokens + [f"{left} {right}" for left, right in zip(tokens, tokens[1:])]
    vector = [0.0] * dimensions
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        index = value % dimensions
        vector[index] += -1.0 if value & (1 << 63) else 1.0

    norm = math.sqrt(sum(component * component for component in vector))
    if norm:
        vector = [component / norm for component in vector]
    return vector


def read_json(path: Path) -> dict[str, Any]:
    import json

    with path.open(encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def write_json(path: Path, value: object) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")
