"""Contract test: SC-007 — health endpoint must not issue Cypher mutations.

Static analysis via Python AST: inspects health_service.py and health_router.py
to assert that no Cypher string reachable from those modules contains mutation
keywords (CREATE, SET, MERGE, DELETE, DETACH DELETE, REMOVE).

This test does NOT require a running FalkorDB instance.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MUTATION_RE = re.compile(
    r"\b(CREATE|SET|MERGE|DELETE|DETACH\s+DELETE|REMOVE)\b",
    re.IGNORECASE,
)

# Files to inspect for Cypher mutations
_SOURCE_FILES = [
    _REPO_ROOT / "src" / "dashboard" / "health_service.py",
    _REPO_ROOT / "src" / "dashboard" / "health_router.py",
]


def _extract_string_literals(source: str) -> list[str]:
    """Extract all string constant values from Python source via AST parse."""
    tree = ast.parse(source)
    strings: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            # f-string — extract the constant parts
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    strings.append(sub.value)

    return strings


class TestHealthEndpointReadOnly:
    """SC-007: Static assertion — health service/router must contain no Cypher mutations."""

    @pytest.mark.parametrize("source_file", _SOURCE_FILES)
    def test_no_mutation_strings_in_source(self, source_file: Path):
        """Assert no string literal in source contains a Cypher mutation keyword."""
        assert source_file.exists(), f"Expected source file not found: {source_file}"
        source = source_file.read_text(encoding="utf-8")
        strings = _extract_string_literals(source)

        mutation_strings = [s for s in strings if _MUTATION_RE.search(s)]
        assert not mutation_strings, (
            f"SC-007 VIOLATION: {source_file.name} contains Cypher mutation keyword(s):\n"
            + "\n".join(f"  - {s!r}" for s in mutation_strings)
        )

    @pytest.mark.parametrize("source_file", _SOURCE_FILES)
    def test_no_execute_query_calls_with_mutations(self, source_file: Path):
        """Assert execute_query is never called with a mutation Cypher string."""
        assert source_file.exists(), f"Expected source file not found: {source_file}"
        source = source_file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Find all execute_query call expressions and check their string args
        mutation_calls: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            # Check if this is an execute_query call
            func = node.func
            is_execute_query = (
                (isinstance(func, ast.Name) and func.id == "execute_query")
                or (isinstance(func, ast.Attribute) and func.attr == "execute_query")
            )
            if not is_execute_query:
                continue
            # Inspect the first argument (the Cypher query string)
            if node.args and isinstance(node.args[0], ast.Constant):
                query_str = node.args[0].value
                if isinstance(query_str, str) and _MUTATION_RE.search(query_str):
                    mutation_calls.append(query_str)

        assert not mutation_calls, (
            f"SC-007 VIOLATION: {source_file.name} calls execute_query with mutation Cypher:\n"
            + "\n".join(f"  - {q!r}" for q in mutation_calls)
        )

    def test_mutation_detection_regex_works(self):
        """Sanity check: regex correctly identifies mutation keywords."""
        assert _MUTATION_RE.search("CREATE (n:MetaType)")
        assert _MUTATION_RE.search("SET n.health_score = 0.5")
        assert _MUTATION_RE.search("MERGE (n:MetaType {id: '1'})")
        assert _MUTATION_RE.search("DELETE n")
        assert _MUTATION_RE.search("DETACH DELETE n")
        assert _MUTATION_RE.search("REMOVE n.prop")
        # Reads must NOT match
        assert not _MUTATION_RE.search("MATCH (m:MetaType) WHERE m.domain_scope = $s RETURN m")
        assert not _MUTATION_RE.search("RETURN m.name, m.health_score")
