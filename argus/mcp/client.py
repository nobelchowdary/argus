"""MCP client wrapper — async Elastic MCP client with guard layer."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from argus.logging import log_tool_call
from argus.mcp.guards import (
    ALLOWED_INDICES,
    MAX_SEARCH_SIZE,
    MAX_SEMANTIC_SEARCH_K,
    GuardError,
    validate_dsl,
    validate_index,
    validate_size,
    validate_skeptic_access,
)
from argus.models import Citation, ToolResult


class ElasticMCPClient:
    """Async client wrapping the Elastic MCP server with guard enforcement."""

    def __init__(
        self,
        elastic_url: str,
        api_key: str,
        timeout: float = 30.0,
    ):
        self.elastic_url = elastic_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self.elastic_url,
            headers={
                "Authorization": f"ApiKey {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._client

    async def search(
        self,
        index: str,
        query_dsl: dict[str, Any],
        size: int = 10,
        case_id: str = "",
        source_filter: list[str] | None = None,
    ) -> ToolResult:
        """Execute a search with full guard validation."""
        start = time.monotonic()
        validate_index("search", index)
        size = validate_size("search", size, MAX_SEARCH_SIZE)
        validate_dsl("search", query_dsl)

        body: dict[str, Any] = {**query_dsl, "size": size}
        if source_filter:
            body["_source"] = source_filter

        response = await self.client.post(f"/{index}/_search", json=body)
        response.raise_for_status()
        data = response.json()

        hits = [hit["_source"] | {"_id": hit["_id"]} for hit in data.get("hits", {}).get("hits", [])]
        citations = [
            Citation(
                index=index,
                doc_id=hit["_id"],
                score=hit.get("_score"),
            )
            for hit in data.get("hits", {}).get("hits", [])
        ]

        elapsed = int((time.monotonic() - start) * 1000)
        result = ToolResult(
            tool_name="search",
            case_id=case_id,
            args={"index": index, "query_dsl": query_dsl, "size": size},
            index=index,
            hits=hits,
            aggregations=data.get("aggregations"),
            citations=citations,
            truncated=len(hits) == size,
            execution_time_ms=elapsed,
        )
        result.compute_hash()
        log_tool_call("search", case_id, result.args, f"{len(hits)} hits", elapsed)
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

        response = await self.client.get(f"/{index}/_doc/{doc_id}")
        response.raise_for_status()
        data = response.json()

        hit = data.get("_source", {}) | {"_id": data.get("_id", doc_id)}
        elapsed = int((time.monotonic() - start) * 1000)

        result = ToolResult(
            tool_name="get_document",
            case_id=case_id,
            args={"index": index, "doc_id": doc_id},
            index=index,
            hits=[hit],
            citations=[Citation(index=index, doc_id=doc_id)],
            execution_time_ms=elapsed,
        )
        result.compute_hash()
        log_tool_call("get_document", case_id, result.args, "1 doc", elapsed)
        return result

    async def count(
        self,
        index: str,
        query_dsl: dict[str, Any],
        case_id: str = "",
    ) -> ToolResult:
        """Count documents matching a query."""
        start = time.monotonic()
        validate_index("count", index)
        validate_dsl("count", {"query": query_dsl.get("query", query_dsl)})

        body = {"query": query_dsl.get("query", query_dsl)}
        response = await self.client.post(f"/{index}/_count", json=body)
        response.raise_for_status()
        data = response.json()

        elapsed = int((time.monotonic() - start) * 1000)
        result = ToolResult(
            tool_name="count",
            case_id=case_id,
            args={"index": index, "query_dsl": query_dsl},
            index=index,
            hits=[{"count": data.get("count", 0)}],
            execution_time_ms=elapsed,
        )
        result.compute_hash()
        log_tool_call("count", case_id, result.args, f"count={data.get('count', 0)}", elapsed)
        return result

    async def semantic_search(
        self,
        index: str,
        query_text: str,
        k: int = 10,
        case_id: str = "",
        filter_dsl: dict[str, Any] | None = None,
    ) -> ToolResult:
        """Semantic search using ELSER/dense vectors."""
        start = time.monotonic()
        validate_index("semantic_search", index)
        k = validate_size("semantic_search", k, MAX_SEMANTIC_SEARCH_K)

        body: dict[str, Any] = {
            "size": k,
            "query": {
                "semantic": {
                    "field": "semantic_field",
                    "query": query_text,
                }
            },
        }
        if filter_dsl:
            body["post_filter"] = filter_dsl

        response = await self.client.post(f"/{index}/_search", json=body)
        response.raise_for_status()
        data = response.json()

        hits = [hit["_source"] | {"_id": hit["_id"]} for hit in data.get("hits", {}).get("hits", [])]
        citations = [
            Citation(index=index, doc_id=hit["_id"], score=hit.get("_score"))
            for hit in data.get("hits", {}).get("hits", [])
        ]

        elapsed = int((time.monotonic() - start) * 1000)
        result = ToolResult(
            tool_name="semantic_search",
            case_id=case_id,
            args={"index": index, "query_text": query_text, "k": k},
            index=index,
            hits=hits,
            citations=citations,
            truncated=len(hits) == k,
            execution_time_ms=elapsed,
        )
        result.compute_hash()
        log_tool_call("semantic_search", case_id, result.args, f"{len(hits)} hits", elapsed)
        return result

    async def list_indices(self, case_id: str = "") -> ToolResult:
        """Return only the allowlisted argus-* indices."""
        return ToolResult(
            tool_name="list_indices",
            case_id=case_id,
            args={},
            index="*",
            hits=[{"indices": sorted(ALLOWED_INDICES)}],
        )
