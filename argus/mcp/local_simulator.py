"""Local Elastic simulator — searches synthetic JSON data directly.

Used when ELASTIC_URL is not configured. Provides the same interface as the
real Elastic MCP client but queries the local synthetic dataset files.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from argus.logging import log_tool_call
from argus.mcp.guards import (
    ALLOWED_INDICES,
    MAX_SEARCH_SIZE,
    MAX_SEMANTIC_SEARCH_K,
    validate_dsl,
    validate_index,
    validate_size,
)
from argus.models import Citation, ToolResult

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "synthetic"


class LocalElasticSimulator:
    """Simulates Elastic search over local JSON files for development/demo."""

    def __init__(self):
        self._data: dict[str, list[dict]] = {}
        self._load_data()

    def _load_data(self) -> None:
        """Load all synthetic data into memory."""
        for index_name in ALLOWED_INDICES:
            filepath = DATA_DIR / f"{index_name}.json"
            if filepath.exists():
                self._data[index_name] = json.loads(filepath.read_text())
            else:
                self._data[index_name] = []

    async def connect(self) -> None:
        """No-op for local simulator."""
        pass

    async def close(self) -> None:
        """No-op for local simulator."""
        pass

    async def search(
        self,
        index: str,
        query_dsl: dict[str, Any],
        size: int = 10,
        case_id: str = "",
        source_filter: list[str] | None = None,
    ) -> ToolResult:
        """Search local data with basic query matching."""
        start = time.monotonic()
        validate_index("search", index)
        size = validate_size("search", size, MAX_SEARCH_SIZE)

        docs = self._data.get(index, [])
        matched = self._match_query(docs, query_dsl.get("query", {}))

        # Apply sort if present
        sort_spec = query_dsl.get("sort", [])
        if sort_spec:
            for sort_item in reversed(sort_spec):
                if isinstance(sort_item, dict):
                    for field, direction in sort_item.items():
                        reverse = direction == "desc" if isinstance(direction, str) else direction.get("order") == "desc"
                        matched.sort(key=lambda d: self._get_field(d, field) or "", reverse=reverse)

        # Cap results
        matched = matched[:size]

        # Generate doc IDs
        hits = []
        citations = []
        for i, doc in enumerate(matched):
            doc_id = doc.get("_id") or doc.get("entity_id") or doc.get("transaction_id") or doc.get("article_id") or doc.get("entry_id") or doc.get("alert_id") or doc.get("playbook_id") or f"{index}-{i}"
            hit = {**doc, "_id": doc_id}
            hits.append(hit)
            citations.append(Citation(index=index, doc_id=doc_id, score=1.0 - i * 0.05))

        elapsed = int((time.monotonic() - start) * 1000)
        result = ToolResult(
            tool_name="search",
            case_id=case_id,
            args={"index": index, "query_dsl": query_dsl, "size": size},
            index=index,
            hits=hits,
            citations=citations,
            truncated=len(matched) == size,
            execution_time_ms=elapsed,
        )
        result.compute_hash()
        log_tool_call("search", case_id, {"index": index, "size": size}, f"{len(hits)} hits", elapsed)
        return result

    async def get_document(
        self,
        index: str,
        doc_id: str,
        case_id: str = "",
    ) -> ToolResult:
        """Fetch a single document by ID."""
        start = time.monotonic()
        validate_index("get_document", index)

        docs = self._data.get(index, [])
        found = None
        for doc in docs:
            did = doc.get("_id") or doc.get("entity_id") or doc.get("transaction_id") or doc.get("article_id") or doc.get("entry_id") or doc.get("alert_id") or doc.get("playbook_id")
            if did == doc_id:
                found = doc
                break

        elapsed = int((time.monotonic() - start) * 1000)
        if found:
            hit = {**found, "_id": doc_id}
            result = ToolResult(
                tool_name="get_document",
                case_id=case_id,
                args={"index": index, "doc_id": doc_id},
                index=index,
                hits=[hit],
                citations=[Citation(index=index, doc_id=doc_id)],
                execution_time_ms=elapsed,
            )
        else:
            result = ToolResult(
                tool_name="get_document",
                case_id=case_id,
                args={"index": index, "doc_id": doc_id},
                index=index,
                hits=[],
                citations=[],
                execution_time_ms=elapsed,
            )
        result.compute_hash()
        log_tool_call("get_document", case_id, {"index": index, "doc_id": doc_id}, "1 doc" if found else "not found", elapsed)
        return result

    async def count(
        self,
        index: str,
        query_dsl: dict[str, Any],
        case_id: str = "",
    ) -> ToolResult:
        """Count matching documents."""
        start = time.monotonic()
        validate_index("count", index)

        docs = self._data.get(index, [])
        query = query_dsl.get("query", query_dsl)
        matched = self._match_query(docs, query)

        elapsed = int((time.monotonic() - start) * 1000)
        result = ToolResult(
            tool_name="count",
            case_id=case_id,
            args={"index": index, "query_dsl": query_dsl},
            index=index,
            hits=[{"count": len(matched)}],
            execution_time_ms=elapsed,
        )
        result.compute_hash()
        log_tool_call("count", case_id, {"index": index}, f"count={len(matched)}", elapsed)
        return result

    async def semantic_search(
        self,
        index: str,
        query_text: str,
        k: int = 10,
        case_id: str = "",
        filter_dsl: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Simulate semantic search with keyword matching."""
        start = time.monotonic()
        validate_index("semantic_search", index)
        k = validate_size("semantic_search", k, MAX_SEMANTIC_SEARCH_K)

        docs = self._data.get(index, [])
        # Simple keyword-based relevance scoring
        query_terms = [t.lower() for t in query_text.split() if len(t) > 2 and t.upper() != "OR"]
        scored: list[tuple[float, dict]] = []

        for doc in docs:
            doc_text = json.dumps(doc).lower()
            score = sum(1 for term in query_terms if term in doc_text)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        matched = [doc for _, doc in scored[:k]]

        hits = []
        citations = []
        for i, doc in enumerate(matched):
            doc_id = doc.get("_id") or doc.get("article_id") or doc.get("entity_id") or doc.get("alert_id") or f"{index}-{i}"
            hits.append({**doc, "_id": doc_id})
            citations.append(Citation(index=index, doc_id=doc_id, score=scored[i][0] if i < len(scored) else 0))

        elapsed = int((time.monotonic() - start) * 1000)
        result = ToolResult(
            tool_name="semantic_search",
            case_id=case_id,
            args={"index": index, "query_text": query_text, "k": k},
            index=index,
            hits=hits,
            citations=citations,
            truncated=len(matched) == k,
            execution_time_ms=elapsed,
        )
        result.compute_hash()
        log_tool_call("semantic_search", case_id, {"index": index, "query_text": query_text[:50]}, f"{len(hits)} hits", elapsed)
        return result

    async def list_indices(self, case_id: str = "") -> ToolResult:
        """Return allowlisted indices."""
        return ToolResult(
            tool_name="list_indices",
            case_id=case_id,
            args={},
            index="*",
            hits=[{"indices": sorted(ALLOWED_INDICES)}],
        )

    def _match_query(self, docs: list[dict], query: dict) -> list[dict]:
        """Match documents against a simplified Elastic query DSL."""
        if not query:
            return docs[:]

        if "match_all" in query:
            return docs[:]

        if "bool" in query:
            return self._match_bool(docs, query["bool"])

        if "term" in query:
            return self._match_term(docs, query["term"])

        if "match" in query:
            return self._match_text(docs, query["match"])

        if "range" in query:
            return self._match_range(docs, query["range"])

        if "semantic" in query:
            # Fall back to text search
            field_config = query["semantic"]
            query_text = field_config.get("query", "")
            return self._match_text_in_all(docs, query_text)

        # Default: return all
        return docs[:]

    def _match_bool(self, docs: list[dict], bool_query: dict) -> list[dict]:
        """Handle bool queries with must, should, must_not."""
        candidates = set(range(len(docs)))

        # must: all must match
        for clause in bool_query.get("must", []):
            clause_matches = {i for i, doc in enumerate(docs) if self._doc_matches(doc, clause)}
            candidates &= clause_matches

        # should: at least minimum_should_match (default 1)
        should_clauses = bool_query.get("should", [])
        min_should = bool_query.get("minimum_should_match", 1 if should_clauses and not bool_query.get("must") else 0)

        if should_clauses and min_should > 0:
            should_candidates = set()
            for i in candidates:
                doc = docs[i]
                match_count = sum(1 for clause in should_clauses if self._doc_matches(doc, clause))
                if match_count >= min_should:
                    should_candidates.add(i)
            candidates &= should_candidates

        # must_not: none must match
        for clause in bool_query.get("must_not", []):
            clause_matches = {i for i, doc in enumerate(docs) if self._doc_matches(doc, clause)}
            candidates -= clause_matches

        return [docs[i] for i in sorted(candidates)]

    def _doc_matches(self, doc: dict, clause: dict) -> bool:
        """Check if a single document matches a query clause."""
        if "term" in clause:
            for field, value in clause["term"].items():
                actual = self._get_field(doc, field)
                if isinstance(value, dict):
                    value = value.get("value", value)
                if actual == value:
                    return True
                # Check in lists
                if isinstance(actual, list):
                    return value in actual
            return False

        if "match" in clause:
            for field, config in clause["match"].items():
                query_text = config if isinstance(config, str) else config.get("query", "")
                actual = self._get_field(doc, field)
                if actual and query_text.lower() in str(actual).lower():
                    return True
            return False

        if "range" in clause:
            for field, conditions in clause["range"].items():
                actual = self._get_field(doc, field)
                if actual is None:
                    return False
                for op, val in conditions.items():
                    if op == "gte" and str(actual) < str(val):
                        return False
                    if op == "lte" and str(actual) > str(val):
                        return False
                    if op == "gt" and str(actual) <= str(val):
                        return False
                    if op == "lt" and str(actual) >= str(val):
                        return False
                return True

        if "bool" in clause:
            matched = self._match_bool([doc], clause["bool"])
            return len(matched) > 0

        # Nested or unknown
        return True

    def _match_term(self, docs: list[dict], term_query: dict) -> list[dict]:
        """Match term queries."""
        results = []
        for doc in docs:
            for field, value in term_query.items():
                actual = self._get_field(doc, field)
                if isinstance(value, dict):
                    value = value.get("value", value)
                if actual == value:
                    results.append(doc)
                    break
                if isinstance(actual, list) and value in actual:
                    results.append(doc)
                    break
        return results

    def _match_text(self, docs: list[dict], match_query: dict) -> list[dict]:
        """Match text queries with simple containment."""
        results = []
        for doc in docs:
            for field, config in match_query.items():
                query_text = config if isinstance(config, str) else config.get("query", "")
                actual = self._get_field(doc, field)
                if actual and query_text.lower() in str(actual).lower():
                    results.append(doc)
                    break
        return results

    def _match_text_in_all(self, docs: list[dict], query_text: str) -> list[dict]:
        """Match text anywhere in the document."""
        terms = [t.lower() for t in query_text.split() if len(t) > 2]
        results = []
        for doc in docs:
            doc_str = json.dumps(doc).lower()
            if any(term in doc_str for term in terms):
                results.append(doc)
        return results

    def _match_range(self, docs: list[dict], range_query: dict) -> list[dict]:
        """Match range queries."""
        results = []
        for doc in docs:
            matches = True
            for field, conditions in range_query.items():
                actual = self._get_field(doc, field)
                if actual is None:
                    matches = False
                    break
                for op, val in conditions.items():
                    if op == "gte" and str(actual) < str(val):
                        matches = False
                    elif op == "lte" and str(actual) > str(val):
                        matches = False
            if matches:
                results.append(doc)
        return results

    def _get_field(self, doc: dict, field_path: str) -> Any:
        """Get a nested field value using dot notation."""
        parts = field_path.split(".")
        current: Any = doc
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx] if idx < len(current) else None
                except (ValueError, IndexError):
                    # Try to find in list of dicts
                    results = [item.get(part) for item in current if isinstance(item, dict)]
                    current = results[0] if results else None
            else:
                return None
            if current is None:
                return None
        return current
