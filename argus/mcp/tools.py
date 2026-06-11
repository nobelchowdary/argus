"""AML convenience tools — high-level wrappers over Elastic MCP queries."""

from __future__ import annotations

from typing import Any

from argus.models import ToolResult


class AMLTools:
    """AML-shaped convenience tools that wrap constrained Elastic queries."""

    def __init__(self, mcp_client: Any):
        self.mcp = mcp_client

    async def entity_neighbors(
        self,
        entity_id: str,
        case_id: str = "",
        hops: int = 1,
        kinds: list[str] | None = None,
    ) -> ToolResult:
        """Find related entities via transactions or beneficial-ownership edges."""
        query: dict[str, Any] = {
            "query": {
                "bool": {
                    "should": [
                        {"term": {"originator.entity_id": entity_id}},
                        {"term": {"beneficiary.entity_id": entity_id}},
                        {"term": {"beneficial_owners.entity_id": entity_id}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        }

        # Search across transactions and entities
        tx_result = await self.mcp.search(
            index="argus-transactions", query_dsl=query, size=50, case_id=case_id
        )
        entity_query: dict[str, Any] = {
            "query": {
                "bool": {
                    "should": [
                        {"term": {"entity_id": entity_id}},
                        {"nested": {
                            "path": "beneficial_owners",
                            "query": {"term": {"beneficial_owners.entity_id": entity_id}},
                        }} if False else {"term": {"beneficial_owners.entity_id": entity_id}},
                    ],
                    "minimum_should_match": 1,
                }
            }
        }
        ent_result = await self.mcp.search(
            index="argus-entities", query_dsl=entity_query, size=50, case_id=case_id
        )

        # Combine results
        all_hits = tx_result.hits + ent_result.hits
        all_citations = tx_result.citations + ent_result.citations

        if kinds:
            all_hits = [h for h in all_hits if h.get("kind") in kinds]

        return ToolResult(
            tool_name="entity_neighbors",
            case_id=case_id,
            args={"entity_id": entity_id, "hops": hops, "kinds": kinds},
            index="argus-entities",
            hits=all_hits,
            citations=all_citations,
            execution_time_ms=tx_result.execution_time_ms + ent_result.execution_time_ms,
        )

    async def transaction_history(
        self,
        entity_id: str,
        start: str,
        end: str,
        case_id: str = "",
        min_amount: float | None = None,
    ) -> ToolResult:
        """Get windowed transaction history for an entity."""
        must_clauses: list[dict] = [
            {
                "bool": {
                    "should": [
                        {"term": {"originator.entity_id": entity_id}},
                        {"term": {"beneficiary.entity_id": entity_id}},
                    ],
                    "minimum_should_match": 1,
                }
            },
            {"range": {"timestamp": {"gte": start, "lte": end}}},
        ]
        if min_amount is not None:
            must_clauses.append({"range": {"amount": {"gte": min_amount}}})

        query: dict[str, Any] = {
            "query": {"bool": {"must": must_clauses}},
            "sort": [{"timestamp": "asc"}],
        }

        return await self.mcp.search(
            index="argus-transactions", query_dsl=query, size=50, case_id=case_id
        )

    async def adverse_media_search(
        self,
        entity_name: str,
        case_id: str = "",
        aliases: list[str] | None = None,
        k: int = 10,
    ) -> ToolResult:
        """Semantic search over adverse media for an entity."""
        search_text = entity_name
        if aliases:
            search_text = f"{entity_name} OR {' OR '.join(aliases)}"

        return await self.mcp.semantic_search(
            index="argus-adverse-media",
            query_text=search_text,
            k=k,
            case_id=case_id,
        )

    async def sanctions_check(
        self,
        entity_name: str,
        case_id: str = "",
        aliases: list[str] | None = None,
        dob: str | None = None,
        country: str | None = None,
    ) -> ToolResult:
        """Fuzzy match against sanctions lists."""
        should_clauses: list[dict] = [
            {"match": {"entity_name": {"query": entity_name, "fuzziness": "AUTO"}}},
        ]
        if aliases:
            for alias in aliases:
                should_clauses.append(
                    {"match": {"aliases": {"query": alias, "fuzziness": "AUTO"}}}
                )

        must_clauses: list[dict] = []
        if country:
            must_clauses.append({"term": {"country": country}})

        query: dict[str, Any] = {
            "query": {
                "bool": {
                    "should": should_clauses,
                    "must": must_clauses,
                    "minimum_should_match": 1,
                }
            }
        }

        return await self.mcp.search(
            index="argus-sanctions", query_dsl=query, size=10, case_id=case_id
        )

    async def similar_prior_alerts(
        self,
        transaction_id: str,
        case_id: str = "",
        k: int = 5,
    ) -> ToolResult:
        """Find similar prior alerts using kNN on alert embeddings."""
        return await self.mcp.semantic_search(
            index="argus-prior-alerts",
            query_text=f"transaction:{transaction_id}",
            k=k,
            case_id=case_id,
        )

    async def typology_playbook(
        self,
        typology_name: str,
        case_id: str = "",
    ) -> ToolResult:
        """Fetch a typology playbook with expected evidence checklist."""
        query: dict[str, Any] = {
            "query": {
                "match": {"typology": {"query": typology_name, "fuzziness": "AUTO"}}
            }
        }

        return await self.mcp.search(
            index="argus-typology-playbooks", query_dsl=query, size=3, case_id=case_id
        )
