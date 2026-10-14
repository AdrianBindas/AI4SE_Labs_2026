"""Score each prompt's predictions per question to obtain paired binary outcomes.

This re-uses the exact grading rule of the Task 2 evaluation script
(`data/evaluate_retrieval_predictions.py`): build an in-memory SQLite database
from the schema + dump, execute each predicted query, and compare the result
multiset to the labelled expected multiset.

The difference from the Task 2 script is that we DO NOT abort on the first bad
query. A query that fails to execute, or whose result does not match, is simply
scored 0 for that question. This yields, for every prompt, a 0/1 vector over the
155 questions -- the paired data Task 4 needs for McNemar's test.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter, defaultdict, deque
from pathlib import Path


TASK2_DIR = Path(__file__).resolve().parents[1] / "Task_2"
DATA_DIR = TASK2_DIR / "data"
LABELS_PATH = DATA_DIR / "restaurants_dataset.csv"
SCHEMA_PATH = DATA_DIR / "restaurants-schema.csv"
DATABASE_PATH = DATA_DIR / "restaurants-db.txt"

PREDICTION_FILES = {
    "OODA": TASK2_DIR / "Task_2_1" / "restaurants_dataset_predictions.csv",
    "ICIO": TASK2_DIR / "Task_2_2" / "restaurants_dataset_predictions.csv",
    "RISEN": TASK2_DIR / "Task_2_3" / "restaurants_dataset_predictions.csv",
}


def _sqlite_type(schema_type: str) -> str:
    t = schema_type.strip().lower()
    if t.startswith("int"):
        return "INTEGER"
    if t.startswith("decimal") or t.startswith("float"):
        return "REAL"
    return "TEXT"


def load_database() -> sqlite3.Connection:
    tables: dict[str, list[tuple[str, str, bool]]] = {}
    with SCHEMA_PATH.open(encoding="utf-8", newline="") as fh:
        for table, field, primary_key, _fk, col_type in csv.reader(
            fh, skipinitialspace=True
        ):
            table = table.strip()
            field = field.strip()
            if table == "-":
                continue
            tables.setdefault(table, []).append(
                (field, _sqlite_type(col_type), primary_key.strip().lower() == "y")
            )

    conn = sqlite3.connect(":memory:")
    for table, columns in tables.items():
        defs = []
        for field, col_type, pk in columns:
            d = f'"{field}" {col_type}'
            if pk:
                d += " PRIMARY KEY"
            defs.append(d)
        conn.execute(f'CREATE TABLE "{table}" ({", ".join(defs)})')

    with DATABASE_PATH.open(encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            m = re.fullmatch(r"([A-Z_]+)\((.*)\)", line.rstrip("\r\n"))
            if m is None:
                raise ValueError(f"Invalid database record on line {n}")
            table, values_text = m.groups()
            if table not in tables:
                raise ValueError(f"Unknown table {table!r} on line {n}")
            values = next(csv.reader([values_text], skipinitialspace=True))
            columns = tables[table]
            converted = []
            for value, (_f, col_type, _pk) in zip(values, columns):
                if col_type == "INTEGER":
                    converted.append(int(value))
                elif col_type == "REAL":
                    converted.append(float(value))
                else:
                    converted.append(value)
            placeholders = ", ".join("?" for _ in columns)
            conn.execute(f'INSERT INTO "{table}" VALUES ({placeholders})', converted)
    return conn


def _row_multiset(rows) -> Counter:
    return Counter(tuple(r) for r in rows)


def load_labels() -> defaultdict[str, deque]:
    csv.field_size_limit(1_000_000_000)
    labels: defaultdict[str, deque] = defaultdict(deque)
    with LABELS_PATH.open(encoding="utf-8", newline="") as fh:
        for n, row in enumerate(csv.DictReader(fh), start=2):
            result = json.loads(row["result"])
            labels[row["question"]].append(result)
    return labels


def score_prompt(prompt: str, conn: sqlite3.Connection) -> list[int]:
    """Return a 0/1 correctness vector over the questions for one prompt."""
    labels = load_labels()
    outcomes: list[int] = []
    path = PREDICTION_FILES[prompt]
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            question = row["question"]
            if not labels[question]:
                # Prediction for a question not in labels -> treat as wrong.
                outcomes.append(0)
                continue
            expected = labels[question].popleft()
            try:
                predicted = conn.execute(row["predicted_sql"]).fetchall()
            except sqlite3.Error:
                outcomes.append(0)
                continue
            outcomes.append(1 if _row_multiset(predicted) == _row_multiset(expected) else 0)
    return outcomes


def score_all() -> dict[str, list[int]]:
    conn = load_database()
    try:
        return {prompt: score_prompt(prompt, conn) for prompt in PREDICTION_FILES}
    finally:
        conn.close()


if __name__ == "__main__":
    results = score_all()
    for prompt, vec in results.items():
        print(f"{prompt:6s} correct={sum(vec):3d}/{len(vec):3d}  acc={sum(vec)/len(vec):.4f}")
