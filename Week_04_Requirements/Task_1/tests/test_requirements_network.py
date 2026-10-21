import json
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

from requirements_network import (
    AnalystOutput,
    build_graph,
    DocumentCoverage,
    FinalRequirement,
    FeedbackOutput,
    SummaryOutput,
    _feedback_node,
    _analyst_node,
    _canonicalize_draft_sources,
    _canonicalize_source_ids,
    load_documents,
    render_markdown,
    route_after_feedback,
    run_pipeline,
    score_candidates,
)


def candidate(candidate_id: str, name: str = "Report queue visibility") -> dict:
    return {
        "candidate_id": candidate_id,
        "origin_agent": "functional",
        "name": name,
        "statement": (
            "The system shall display the report's queue position, submission time, "
            "and current status so that staff can determine whether it is waiting, "
            "running, completed, or failed."
        ),
        "category": "Reporting",
        "requirement_type": "functional",
        "priority": "High",
        "source_documents": ["survey.txt"],
        "evidence": ["Staff asked to see their report position and status."],
        "confidence": 0.9,
        "original_candidate_id": None,
        "uncertainty": "",
    }


class RequirementsNetworkTests(unittest.TestCase):
    def test_loads_text_and_email_recursively_with_relative_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nested = root / "nested"
            nested.mkdir()
            (nested / "notes.txt").write_text("A requirement.", encoding="utf-8")
            message = EmailMessage()
            message["Subject"] = "Queue status"
            message["Date"] = "Tue, 28 Jul 2009 09:00:00 -0500"
            message.set_content("Staff need report status.")
            (root / "thread.eml").write_bytes(message.as_bytes())

            documents = load_documents(root)

            self.assertEqual(
                [item.document_id for item in documents],
                ["nested/notes.txt", "thread.eml"],
            )
            self.assertIn("Queue status", documents[1].text)
            self.assertIn("Staff need report status.", documents[1].text)

    def test_rejects_missing_or_empty_input_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                load_documents(root)
            with self.assertRaises(NotADirectoryError):
                load_documents(root / "missing")

    def test_canonicalizes_source_title_to_exact_document_id(self) -> None:
        documents = [
            {
                "document_id": "email_report_features.eml",
                "text": "Subject: Report features and interface requirements\nSome evidence.",
            },
            {"document_id": "survey_results_2009.txt", "text": "Survey evidence."},
        ]

        result = _canonicalize_source_ids(
            ["report_features_and_interface_requirements"], documents, "functional"
        )

        self.assertEqual(result, ["email_report_features.eml"])

    def test_rejects_ambiguous_source_reference(self) -> None:
        documents = [
            {"document_id": "reports/notes.txt", "text": "Subject: Notes\nA"},
            {"document_id": "minutes/notes.txt", "text": "Subject: Notes\nB"},
        ]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            _canonicalize_source_ids(["notes"], documents, "functional")

    def test_rework_keeps_valid_original_citations_if_model_uses_instruction_as_source(self) -> None:
        from requirements_network import RequirementDraft

        draft = RequirementDraft(
            name="Revised requirement",
            statement=(
                "The system shall provide an updated, traceable workflow result "
                "that meets the needs recorded by the stakeholders in their source."
            ),
            category="Workflow",
            requirement_type="functional",
            priority="High",
            source_documents=["assignment_compliance_checklist"],
            evidence=["Stakeholders described the workflow in the source."],
            confidence=0.8,
            original_candidate_id="functional-0001",
        )
        original = candidate("functional-0001")

        result = _canonicalize_draft_sources(
            [draft],
            [{"document_id": "survey.txt", "text": "evidence"}],
            "functional",
            fallback_candidates=[original],
        )

        self.assertEqual(result[0].source_documents, ["survey.txt"])
        self.assertIn("original candidate's validated", result[0].uncertainty)

    def test_analyst_rejects_uncited_rework_and_keeps_existing_candidate(self) -> None:
        class StubStructuredModel:
            def with_structured_output(self, _schema: type) -> "StubStructuredModel":
                return self

            def invoke(self, _messages: list) -> AnalystOutput:
                return AnalystOutput(
                    requirements=[
                        {
                            "name": "Untraceable revised requirement",
                            "statement": (
                                "The system shall address this review finding with a "
                                "clear and consistent operational requirement statement."
                            ),
                            "category": "Workflow",
                            "requirement_type": "functional",
                            "priority": "Medium",
                            "source_documents": ["assignment_compliance_checklist"],
                            "evidence": ["No source was provided."],
                            "confidence": 0.8,
                        }
                    ]
                )

        original = candidate("functional-0001")
        node = _analyst_node("functional", lambda _model: StubStructuredModel(), rework=True)
        state = {
            "documents": [{"document_id": "survey.txt", "text": "evidence"}],
            "candidates": [original],
            "candidate_sequence": 1,
            "pending_feedback": {
                "candidate_ids": [],
                "target_agents": ["functional"],
                "instruction": "Add missing requirements.",
            },
            "unresolved_feedback": [],
        }

        result = node(state)

        self.assertEqual(result["candidates"], [original])
        self.assertEqual(len(result["unresolved_feedback"]), 1)
        self.assertIn(
            "assignment_compliance_checklist",
            result["unresolved_feedback"][0]["references"],
        )

    def test_deterministic_score_and_duplicate_flag(self) -> None:
        items = [candidate("one"), candidate("two")]
        valid_sources = {"survey.txt"}

        first = score_candidates(items, valid_sources)
        second = score_candidates(items, valid_sources)

        self.assertEqual(first, second)
        self.assertTrue(first["one"]["exact_duplicate"])
        self.assertIn("exact_duplicate_candidate", first["one"]["flags"])
        self.assertEqual(first["one"]["breakdown"]["source_traceability"], 25)
        self.assertEqual(first["one"]["score"], 79)

    def test_feedback_router_targets_origin_or_summary(self) -> None:
        self.assertEqual(
            route_after_feedback(
                {
                    "pending_feedback": {
                        "target_agents": ["technical"],
                        "candidate_ids": ["technical-0001"],
                    }
                }
            ),
            "rework_technical",
        )
        self.assertEqual(route_after_feedback({"pending_feedback": None}), "summary")

    def test_langgraph_compiles_without_invoking_models(self) -> None:
        graph = build_graph(lambda _model: object())
        self.assertIsNotNone(graph)

    def test_full_graph_runs_offline_with_structured_model_stubs(self) -> None:
        class StubStructuredModel:
            def __init__(self, model_name: str, schema: type) -> None:
                self.model_name = model_name
                self.schema = schema

            def invoke(self, messages: list) -> object:
                payload = json.loads(messages[1].content)
                if self.schema is AnalystOutput:
                    source_ids = ["notes.txt", "thread.eml"]
                    statement = (
                        f"The system shall support the {self.model_name} analyst's "
                        "evidence-backed requirement workflow and provide a clear, "
                        "traceable result that stakeholders can evaluate consistently."
                    )
                    return AnalystOutput(
                        requirements=[
                            {
                                "name": f"Analyst requirement {self.model_name}",
                                "statement": statement,
                                "category": "Workflow",
                                "requirement_type": "functional",
                                "priority": "Medium",
                                "source_documents": source_ids,
                                "evidence": ["Evidence from the input corpus."],
                                "confidence": 0.9,
                                "original_candidate_id": None,
                                "uncertainty": "",
                            }
                        ]
                    )
                if self.schema is FeedbackOutput:
                    return FeedbackOutput(findings=[], unresolved_conflicts=[])
                if self.schema is SummaryOutput:
                    return SummaryOutput(
                        executive_summary="The corpus describes requirements workflows.",
                        requirements=[
                            FinalRequirement(
                                name=item["name"],
                                statement=item["statement"],
                                category=item["category"],
                                requirement_type=item["requirement_type"],
                                priority=item["priority"],
                                source_documents=item["source_documents"],
                            )
                            for item in payload["candidates"]
                        ],
                        discarded_requirements=[],
                        unresolved_conflicts=[],
                        assumptions=[],
                        document_coverage=[
                            DocumentCoverage(
                                source_document=source_id,
                                disposition="requirements",
                                explanation="A structured analyst reviewed this file.",
                            )
                            for source_id in payload["source_document_ids"]
                        ],
                    )
                raise AssertionError(f"Unexpected schema: {self.schema}")

        class StubModel:
            def __init__(self, model_name: str) -> None:
                self.model_name = model_name

            def with_structured_output(self, schema: type) -> StubStructuredModel:
                return StubStructuredModel(self.model_name, schema)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            corpus = root / "corpus"
            corpus.mkdir()
            (corpus / "notes.txt").write_text("A supported request.", encoding="utf-8")
            message = EmailMessage()
            message["Subject"] = "Test input"
            message.set_content("A second source.")
            (corpus / "thread.eml").write_bytes(message.as_bytes())
            output = root / "requirements.md"

            result = run_pipeline(
                corpus,
                output,
                llm_factory=lambda model_name: StubModel(model_name),
            )

            rendered = result.read_text(encoding="utf-8")
            self.assertEqual(result, output)
            self.assertIn("### FR-001", rendered)
            self.assertIn("notes.txt", rendered)
            self.assertIn("thread.eml", rendered)

    def test_feedback_node_obeys_retry_limit(self) -> None:
        class StubStructuredModel:
            def __init__(self, schema: type) -> None:
                self.schema = schema

            def invoke(self, _messages: list) -> object:
                if self.schema is FeedbackOutput:
                    return FeedbackOutput(
                        findings=[
                            {
                                "issue_type": "conflict",
                                "severity": "High",
                                "candidate_ids": ["functional-0001"],
                                "target_agents": ["functional"],
                                "instruction": "Resolve this conflicting statement.",
                            }
                        ]
                    )
                raise AssertionError(f"Unexpected schema: {self.schema}")

        class StubModel:
            def with_structured_output(self, schema: type) -> StubStructuredModel:
                return StubStructuredModel(schema)

        node = _feedback_node(lambda _model: StubModel())
        state = {
            "documents": [{"document_id": "survey.txt", "text": "evidence"}],
            "candidates": [candidate("functional-0001")],
            "scores": {},
            "deterministic_flags": [],
            "revision_round": 3,
            "max_revisions": 3,
            "unresolved_conflicts": [],
            "unresolved_feedback": [],
        }

        result = node(state)

        self.assertIsNone(result["pending_feedback"])
        self.assertEqual(len(result["unresolved_feedback"]), 1)

    def test_feedback_node_records_invented_candidate_id_without_crashing(self) -> None:
        class StubStructuredModel:
            def __init__(self, schema: type) -> None:
                self.schema = schema

            def invoke(self, _messages: list) -> object:
                if self.schema is FeedbackOutput:
                    return FeedbackOutput(
                        findings=[
                            {
                                "issue_type": "conflict",
                                "severity": "High",
                                "candidate_ids": ["technical-9999"],
                                "target_agents": ["technical"],
                                "instruction": "Resolve this conflicting statement.",
                            }
                        ]
                    )
                raise AssertionError(f"Unexpected schema: {self.schema}")

        class StubModel:
            def with_structured_output(self, schema: type) -> StubStructuredModel:
                return StubStructuredModel(schema)

        node = _feedback_node(lambda _model: StubModel())
        state = {
            "documents": [{"document_id": "survey.txt", "text": "evidence"}],
            "candidates": [candidate("functional-0001")],
            "scores": {},
            "deterministic_flags": [],
            "revision_round": 0,
            "max_revisions": 3,
            "unresolved_conflicts": [],
            "unresolved_feedback": [],
        }

        result = node(state)

        self.assertIsNone(result["pending_feedback"])
        self.assertIn("unresolvable finding", result["unresolved_conflicts"][0])
        self.assertEqual(
            result["unresolved_feedback"][0]["candidate_ids"], ["technical-9999"]
        )

    def test_markdown_output_has_unique_ids_traceability_and_required_sections(self) -> None:
        summary = SummaryOutput(
            executive_summary="The system consolidates library reporting requirements.",
            requirements=[
                FinalRequirement(
                    name="Queue visibility",
                    statement=(
                        "The system shall show the report's queue position and current "
                        "processing state so staff can distinguish waiting work from "
                        "completed or failed reports."
                    ),
                    category="Reporting",
                    requirement_type="functional",
                    priority="High",
                    source_documents=["survey.txt"],
                ),
                FinalRequirement(
                    name="Accessible report output",
                    statement=(
                        "The system shall provide standards-compliant, accessible HTML "
                        "reports that work with assistive technologies and support staff "
                        "who rely on screen readers or magnification."
                    ),
                    category="Accessibility",
                    requirement_type="non-functional",
                    priority="Critical",
                    source_documents=["minutes.txt"],
                ),
            ],
            discarded_requirements=[],
            unresolved_conflicts=["Historical storage architecture remains unsettled."],
            assumptions=[],
            document_coverage=[
                DocumentCoverage(
                    source_document="survey.txt",
                    disposition="requirements",
                    explanation="Includes staff reporting requests.",
                ),
                DocumentCoverage(
                    source_document="minutes.txt",
                    disposition="requirements",
                    explanation="Includes accessibility constraints.",
                ),
            ],
        )

        rendered = render_markdown(
            summary,
            [
                {"document_id": "survey.txt", "text": "survey"},
                {"document_id": "minutes.txt", "text": "minutes"},
            ],
        )

        self.assertIn("### FR-001 — Queue visibility", rendered)
        self.assertIn("### NFR-001 — Accessible report output", rendered)
        self.assertIn("`survey.txt`", rendered)
        self.assertIn("## Priority scale", rendered)
        self.assertIn("## Discarded requirements", rendered)
        self.assertIn("## Unresolved conflicts", rendered)
        self.assertIn("## Source-document coverage", rendered)
        self.assertEqual(rendered.count("### FR-001"), 1)


if __name__ == "__main__":
    unittest.main()
