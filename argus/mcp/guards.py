"""MCP guard layer — index allowlist, DSL validator, size caps."""

from __future__ import annotations

import re
from typing import Any

ALLOWED_INDICES: set[str] = {
    "argus-transactions",
    "argus-entities",
    "argus-adverse-media",
    "argus-sanctions",
    "argus-prior-alerts",
    "argus-typology-playbooks",
}

# Maximum result sizes
MAX_SEARCH_SIZE = 50
MAX_SEMANTIC_SEARCH_K = 10
MAX_SOURCE_BYTES = 1_048_576  # 1 MB

# DSL keys that are forbidden (prevent writes, scripts, etc.)
FORBIDDEN_DSL_KEYS: set[str] = {
    "script",
    "update_by_query",
    "delete_by_query",
    "reindex",
    "update",
    "delete",
    "index",
    "create",
    "bulk",
    "put_mapping",
    "put_settings",
}

# Allowed top-level DSL keys for search queries
ALLOWED_DSL_KEYS: set[str] = {
    "query",
    "aggs",
    "aggregations",
    "size",
    "sort",
    "_source",
    "runtime_mappings",
    "from",
    "highlight",
    "track_total_hits",
    "knn",
    "fields",
    "post_filter",
}


class GuardError(Exception):
    """Raised when a guard check fails."""

    def __init__(self, tool_name: str, reason: str):
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"Guard rejected {tool_name}: {reason}")


def validate_index(tool_name: str, index: str) -> str:
    """Validate that the index is in the allowlist."""
    if index not in ALLOWED_INDICES:
        raise GuardError(
            tool_name,
            f"Index '{index}' not in allowlist. Allowed: {sorted(ALLOWED_INDICES)}",
        )
    return index


def validate_size(tool_name: str, size: int, max_size: int = MAX_SEARCH_SIZE) -> int:
    """Validate that the requested size is within bounds."""
    if size < 0:
        raise GuardError(tool_name, f"Size must be non-negative, got {size}")
    if size > max_size:
        return max_size  # Silently cap rather than reject
    return size


def validate_dsl(tool_name: str, query_dsl: dict[str, Any]) -> dict[str, Any]:
    """Validate that the DSL query contains no forbidden operations."""
    _check_forbidden_keys(tool_name, query_dsl, path="")
    _check_top_level_keys(tool_name, query_dsl)
    return query_dsl


def _check_forbidden_keys(tool_name: str, obj: Any, path: str) -> None:
    """Recursively check for forbidden keys in the DSL."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            if key.lower() in FORBIDDEN_DSL_KEYS:
                raise GuardError(
                    tool_name,
                    f"Forbidden DSL key '{key}' at path '{current_path}'",
                )
            # Check for script-like patterns in string values
            if isinstance(value, str) and re.search(
                r"(ctx\._source|doc\[|params\.)", value, re.IGNORECASE
            ):
                raise GuardError(
                    tool_name,
                    f"Script-like pattern detected in value at '{current_path}'",
                )
            _check_forbidden_keys(tool_name, value, current_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_forbidden_keys(tool_name, item, f"{path}[{i}]")


def _check_top_level_keys(tool_name: str, query_dsl: dict[str, Any]) -> None:
    """Validate that only allowed top-level keys are present."""
    invalid_keys = set(query_dsl.keys()) - ALLOWED_DSL_KEYS
    if invalid_keys:
        raise GuardError(
            tool_name,
            f"Invalid top-level DSL keys: {sorted(invalid_keys)}. "
            f"Allowed: {sorted(ALLOWED_DSL_KEYS)}",
        )


def validate_skeptic_access(
    tool_name: str,
    index: str,
    allowed_indices_for_case: set[str],
    size: int | None = None,
) -> None:
    """Additional restrictions for the Skeptic's tool surface."""
    validate_index(tool_name, index)

    if index not in allowed_indices_for_case:
        raise GuardError(
            tool_name,
            f"Skeptic cannot access '{index}' — not referenced in finding citations. "
            f"Allowed for this case: {sorted(allowed_indices_for_case)}",
        )

    if size is not None and size > 5:
        raise GuardError(
            tool_name,
            f"Skeptic size cap is 5, got {size}",
        )
