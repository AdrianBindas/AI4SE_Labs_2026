from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from Week_06_Implementation.rag.chunk_repository import (
    LINES_PER_CHUNK,
    OVERLAP_LINES,
    chunk_repository,
    chunk_text_file,
)
from Week_06_Implementation.rag.common import hashed_embedding
from Week_06_Implementation.rag.generate_code import replace_method_body
from Week_06_Implementation.rag.retrieve_chunks import cosine_similarity, retrieve


class ChunkingTests(unittest.TestCase):
    def test_chunks_overlap_and_keep_line_ranges(self) -> None:
        lines = [f"line {number}" for number in range(LINES_PER_CHUNK + 1)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.py"
            path.write_text("\n".join(lines), encoding="utf-8")
            chunks = chunk_text_file(path, "sample.py")

        self.assertEqual(len(chunks), 2)
        first, second = chunks
        self.assertEqual((first["start_line"], first["end_line"]), (1, 80))
        self.assertEqual(second["start_line"], 80 - OVERLAP_LINES + 1)
        self.assertEqual(second["end_line"], LINES_PER_CHUNK + 1)
        overlap = second["text"].splitlines()[:OVERLAP_LINES]
        self.assertEqual(first["text"].splitlines()[-OVERLAP_LINES:], overlap)

    def test_repository_chunking_skips_git_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git").mkdir()
            (root / ".git" / "config.txt").write_text("excluded", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "module.py").write_text("value = 1", encoding="utf-8")
            chunks = chunk_repository(root)

        self.assertEqual([chunk["path"] for chunk in chunks], ["src/module.py"])


class RetrievalTests(unittest.TestCase):
    def test_embedding_is_repeatable_and_unit_normalized(self) -> None:
        vector = hashed_embedding("InventoryLedger available stock")
        self.assertEqual(vector, hashed_embedding("InventoryLedger available stock"))
        self.assertAlmostEqual(sum(value * value for value in vector), 1.0)

    def test_retrieval_ranks_matching_chunk_first(self) -> None:
        records = [
            {
                "id": "inventory",
                "path": "inventory.py",
                "start_line": 1,
                "end_line": 1,
                "text": "InventoryLedger available stock",
                "embedding": hashed_embedding("inventory.py\nInventoryLedger available stock"),
            },
            {
                "id": "events",
                "path": "events.py",
                "start_line": 1,
                "end_line": 1,
                "text": "EventBus handlers",
                "embedding": hashed_embedding("events.py\nEventBus handlers"),
            },
        ]
        result = retrieve("InventoryLedger available stock", records)
        self.assertEqual(result[0]["id"], "inventory")

    def test_similarity_requires_equal_dimensions(self) -> None:
        with self.assertRaises(ValueError):
            cosine_similarity([1.0], [1.0, 0.0])


class CodeGenerationValidationTests(unittest.TestCase):
    def test_replaces_body_and_preserves_decorator_and_signature(self) -> None:
        source = (
            "class Sample:\n"
            "    @property\n"
            "    def ready(self) -> bool:\n"
            "        pass\n"
        )
        generated = (
            "def ready(self) -> bool:\n"
            '    """Report readiness."""\n'
            "    return True\n"
        )
        updated = replace_method_body(source, "Sample", "ready", generated)

        self.assertIn("    @property\n", updated)
        self.assertIn("    def ready(self) -> bool:\n", updated)
        self.assertIn('        """Report readiness."""', updated)
        self.assertIn("        return True", updated)

    def test_rejects_signature_changes(self) -> None:
        source = "class Sample:\n    def run(self, value: int) -> bool:\n        pass\n"
        generated = "def run(self) -> bool:\n    return True\n"
        with self.assertRaises(ValueError):
            replace_method_body(source, "Sample", "run", generated)

    def test_does_not_replace_implemented_method_without_force(self) -> None:
        source = "class Sample:\n    def run(self) -> bool:\n        return True\n"
        generated = "def run(self) -> bool:\n    return False\n"
        with self.assertRaises(ValueError):
            replace_method_body(source, "Sample", "run", generated)


if __name__ == "__main__":
    unittest.main()
