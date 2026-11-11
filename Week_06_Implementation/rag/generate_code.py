from __future__ import annotations

import argparse
import ast
import json
import os
import re
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .common import (
    EMBEDDINGS_PATH,
    REPOSITORY_ROOT,
    WORKSPACE_ROOT,
    read_json,
)
from .retrieve_chunks import retrieve

ASSIGNMENTS_PATH = (
    WORKSPACE_ROOT / "Week_06_Implementation" / "Assignments" / "missing_code.json"
)
ALLOWED_MODELS = {
    "gpt-6-luna",
    "gpt-5.6-luna",
    "gpt-5.4-nano",
    "gpt-5-nano",
    "gpt-5-mini",
    "gpt-4.1-nano",
    "gpt-4o-mini",
}
DEFAULT_MODEL = "gpt-5-mini"


def _extract_python(response: str) -> str:
    fenced = re.search(r"```(?:python)?\s*(.*?)```", response, flags=re.DOTALL | re.I)
    return textwrap.dedent(fenced.group(1) if fenced else response).strip()


def replace_method_body(
    source: str,
    class_name: str,
    method_name: str,
    generated_source: str,
    *,
    force: bool = False,
) -> str:
    """Replace only the target method body, preserving its original signature/decorators."""
    tree = ast.parse(source)
    target_class = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )
    if target_class is None:
        raise ValueError(f"class {class_name!r} not found")
    target = next(
        (
            node
            for node in target_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == method_name
        ),
        None,
    )
    if target is None:
        raise ValueError(f"method {class_name}.{method_name} not found")
    if not force and not (
        len(target.body) == 1 and isinstance(target.body[0], ast.Pass)
    ):
        raise ValueError(
            f"{class_name}.{method_name} is not a pass-only stub; "
            "use --force to replace it"
        )

    generated = ast.parse(_extract_python(generated_source))
    generated_functions = [
        node for node in generated.body if isinstance(node, ast.FunctionDef)
    ]
    if (
        len(generated.body) != 1
        or len(generated_functions) != 1
        or generated_functions[0].name != method_name
    ):
        raise ValueError(f"model response must contain only def {method_name}(...)")
    generated_function = generated_functions[0]
    if ast.dump(target.args, include_attributes=False) != ast.dump(
        generated_function.args, include_attributes=False
    ):
        raise ValueError("generated method signature does not match the target")
    if not generated_function.body:
        raise ValueError("generated method body is empty")

    source_lines = source.splitlines()
    generated_lines = _extract_python(generated_source).splitlines()
    body_start = generated_function.body[0].lineno - 1
    body_end = generated_function.end_lineno
    indent = " " * target.col_offset
    replacement_body = [
        f"{indent}{line}" if line else ""
        for line in generated_lines[body_start:body_end]
    ]
    source_lines[target.body[0].lineno - 1 : target.end_lineno] = replacement_body
    result = "\n".join(source_lines) + ("\n" if source.endswith("\n") else "")
    ast.parse(result)
    return result


def _call_model(prompt: str, model: str, timeout: int = 120) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set OPENAI_API_KEY in the environment or the Week 04 .env file "
            "to enable LLM generation."
        )
    base_url = os.environ.get("WEEK06_LLM_BASE_URL", "https://api.openai.com/v1")
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Implement exactly the requested Python method. Return only "
                        "its complete def statement and body, without explanation or "
                        "markdown. Preserve the supplied signature exactly."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 1,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM request failed with HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"LLM request failed: {error.reason}") from error

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("LLM response did not contain chat completion content") from error
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("LLM returned an empty or non-text completion")
    return content


def _method_source(source: str, class_name: str, method_name: str) -> str:
    tree = ast.parse(source)
    target_class = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )
    if target_class is None:
        raise ValueError(f"class {class_name!r} not found")
    target = next(
        (
            node
            for node in target_class.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == method_name
        ),
        None,
    )
    if target is None:
        raise ValueError(f"method {class_name}.{method_name} not found")
    lines = source.splitlines()
    return "\n".join(lines[target.lineno - 1 : target.end_lineno])


def generate_for_target(
    task: str,
    relative_file: str,
    class_name: str,
    method_name: str,
    records: list[dict[str, Any]],
    model: str = DEFAULT_MODEL,
    *,
    force: bool = False,
) -> None:
    if model not in ALLOWED_MODELS:
        raise ValueError(f"unsupported model {model!r}; choose from {sorted(ALLOWED_MODELS)}")
    source_path = (REPOSITORY_ROOT / relative_file).resolve()
    repository_root = REPOSITORY_ROOT.resolve()
    if not source_path.is_relative_to(repository_root):
        raise ValueError("target source file must be inside the cloned repository")
    source = source_path.read_text(encoding="utf-8")
    current_method = _method_source(source, class_name, method_name)
    matches = retrieve(task, records, limit=5)
    context = "\n\n".join(
        f"### {item['path']}:{item['start_line']}-{item['end_line']}\n{item['text']}"
        for item in matches
    )
    prompt = (
        f"Task: {task}\n\n"
        f"Target: {relative_file}, class {class_name}, method {method_name}\n"
        f"Current method (its signature must remain unchanged):\n"
        f"```python\n{current_method}\n```\n\n"
        f"Relevant repository context (top {len(matches)} retrieved chunks):\n"
        f"{context}"
    )
    completion = _call_model(prompt, model)
    updated = replace_method_body(
        source, class_name, method_name, completion, force=force
    )
    source_path.write_text(updated, encoding="utf-8", newline="\n")


def run_missing_code(
    model: str = DEFAULT_MODEL,
    *,
    assignments_path: Path = ASSIGNMENTS_PATH,
    embeddings_path: Path = EMBEDDINGS_PATH,
    force: bool = False,
) -> None:
    assignments = json.loads(assignments_path.read_text(encoding="utf-8"))
    if not isinstance(assignments, list):
        raise ValueError(f"expected a list in {assignments_path}")
    storage = read_json(embeddings_path)
    records = storage.get("records")
    if not isinstance(records, list):
        raise ValueError(f"embedding records missing from {embeddings_path}")

    for entry in assignments:
        task = (
            f"Implement {entry['class']}.{entry['method']} in {entry['file']}. "
            f"Required behavior: {entry['docstring'].strip()}"
        )
        generate_for_target(
            task,
            entry["file"],
            entry["class"],
            entry["method"],
            records,
            model,
            force=force,
        )
        print(f"Implemented {entry['class']}.{entry['method']} in {entry['file']}")


def main() -> None:
    load_dotenv(
        WORKSPACE_ROOT / "Week_06_Implementation" / ".env",
        override=False,
    )
    parser = argparse.ArgumentParser(description="Generate code with repository RAG.")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=sorted(ALLOWED_MODELS))
    parser.add_argument("--assignments", type=Path, default=ASSIGNMENTS_PATH)
    parser.add_argument("--embeddings", type=Path, default=EMBEDDINGS_PATH)
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow replacing methods that are no longer pass-only stubs",
    )
    args = parser.parse_args()
    run_missing_code(
        args.model,
        assignments_path=args.assignments,
        embeddings_path=args.embeddings,
        force=args.force,
    )


if __name__ == "__main__":
    main()
