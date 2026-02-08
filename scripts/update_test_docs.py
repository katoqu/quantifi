#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
DOC_PATH = ROOT / "docs" / "TESTING.md"

START = "<!-- TESTS:START -->"
END = "<!-- TESTS:END -->"


def _first_line(doc: str | None) -> str:
    if not doc:
        return ""
    doc = doc.strip()
    if not doc:
        return ""
    return doc.splitlines()[0].strip()


def collect_tests() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        rel = path.relative_to(ROOT).as_posix()
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in module.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                purpose = _first_line(ast.get_docstring(node)) or "—"
                rows.append((f"`{rel}`", f"`{node.name}`", purpose))
    return rows


def render_table(rows: list[tuple[str, str, str]]) -> str:
    lines = [
        "| File | Test | Purpose |",
        "|---|---|---|",
    ]
    for file_cell, test_cell, purpose in rows:
        lines.append(f"| {file_cell} | {test_cell} | {purpose} |")
    return "\n".join(lines) + "\n"


def update_doc(*, doc_path: Path, table: str) -> bool:
    text = doc_path.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit(
            f"Missing markers in {doc_path}: add {START} and {END} around the generated section."
        )

    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    new_text = before + START + "\n" + table + END + after

    if new_text == text:
        return False

    doc_path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    rows = collect_tests()
    table = render_table(rows)
    changed = update_doc(doc_path=DOC_PATH, table=table)
    print(f"{'Updated' if changed else 'No changes'}: {DOC_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
