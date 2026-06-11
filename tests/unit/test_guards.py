"""Unit tests for MCP guard layer."""

import pytest
from argus.mcp.guards import (
    GuardError,
    validate_dsl,
    validate_index,
    validate_size,
    validate_skeptic_access,
)


def test_validate_index_allowed():
    assert validate_index("search", "argus-transactions") == "argus-transactions"


def test_validate_index_rejected():
    with pytest.raises(GuardError, match="not in allowlist"):
        validate_index("search", "production-data")


def test_validate_index_partial_match():
    with pytest.raises(GuardError):
        validate_index("search", "argus-secret-stuff")


def test_validate_size_within_bounds():
    assert validate_size("search", 10) == 10


def test_validate_size_capped():
    assert validate_size("search", 100) == 50  # Capped silently


def test_validate_size_negative():
    with pytest.raises(GuardError, match="non-negative"):
        validate_size("search", -1)


def test_validate_dsl_valid():
    dsl = {"query": {"match": {"memo": "consulting"}}, "size": 10}
    assert validate_dsl("search", dsl) == dsl


def test_validate_dsl_forbidden_script():
    with pytest.raises(GuardError, match="Forbidden DSL key"):
        validate_dsl("search", {"query": {"match_all": {}}, "script": {"source": "..."}})


def test_validate_dsl_forbidden_nested():
    with pytest.raises(GuardError, match="Forbidden DSL key"):
        validate_dsl("search", {"query": {"bool": {"must": [{"script": {"source": "x"}}]}}})


def test_validate_dsl_invalid_top_level():
    with pytest.raises(GuardError, match="Invalid top-level"):
        validate_dsl("search", {"query": {"match_all": {}}, "unknown_key": True})


def test_validate_dsl_script_pattern_in_value():
    with pytest.raises(GuardError, match="Script-like pattern"):
        validate_dsl("search", {"query": {"match": {"field": "ctx._source.x"}}})


def test_skeptic_access_valid():
    validate_skeptic_access(
        "get_document", "argus-entities", {"argus-entities", "argus-transactions"}, size=3
    )


def test_skeptic_access_index_not_in_case():
    with pytest.raises(GuardError, match="not referenced in finding"):
        validate_skeptic_access(
            "search", "argus-adverse-media", {"argus-entities"}, size=3
        )


def test_skeptic_access_size_exceeded():
    with pytest.raises(GuardError, match="Skeptic size cap"):
        validate_skeptic_access(
            "search", "argus-entities", {"argus-entities"}, size=10
        )
