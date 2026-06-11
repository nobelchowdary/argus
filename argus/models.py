"""Pydantic models for Argus: Finding, Citation, ToolResult, Case, SkepticVerdict."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A citation anchoring a claim to an Elastic document."""

    index: str
    doc_id: str
    field: str | None = None
    excerpt: str | None = None
    score: float | None = None


class ToolResult(BaseModel):
    """Normalized result from any MCP tool call."""

    tool_name: str
    case_id: str
    args: dict
    index: str
    hits: list[dict] = Field(default_factory=list)
    aggregations: dict | None = None
    citations: list[Citation] = Field(default_factory=list)
    truncated: bool = False
    execution_time_ms: int = 0
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result_hash: str = ""

    def compute_hash(self) -> str:
        """SHA-256 of sorted hit IDs + aggregation keys for re-verification."""
        hit_ids = sorted(h.get("_id", "") for h in self.hits)
        agg_keys = sorted(self.aggregations.keys()) if self.aggregations else []
        payload = json.dumps({"hit_ids": hit_ids, "agg_keys": agg_keys}, sort_keys=True)
        self.result_hash = hashlib.sha256(payload.encode()).hexdigest()
        return self.result_hash


class Finding(BaseModel):
    """A single finding produced by the Investigator, validated by the Skeptic."""

    finding_id: str = Field(default_factory=lambda: str(uuid4()))
    case_id: str
    title: str
    severity: Literal["info", "low", "med", "high", "critical"]
    typology_tags: list[str] = Field(default_factory=list)
    fincen_advisory_refs: list[str] = Field(default_factory=list)
    narrative: str
    claim_type: Literal["confirmed", "inferred"]
    evidence: list[Citation] = Field(min_length=1)
    related_entities: list[str] = Field(default_factory=list)
    iteration: int = 0
    investigator_model: str = ""
    skeptic_verdict: Literal["accepted", "rejected", "unverified"] = "unverified"
    tool_call_ids: list[str] = Field(default_factory=list)


class SkepticVerdict(BaseModel):
    """The Skeptic's verdict on a single Finding."""

    verdict: Literal["ACCEPT", "REJECT", "UNVERIFIED"]
    reasons: list[str] = Field(default_factory=list)
    missing_or_wrong_citations: list[Citation] = Field(default_factory=list)


class Alert(BaseModel):
    """A flagged transaction alert that triggers an investigation."""

    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    transaction_id: str
    originator: str
    beneficiary: str
    amount: float
    currency: str = "USD"
    channel: str = "wire"
    country_pair: str = ""
    memo: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    risk_score: float = 0.0
    status: Literal["pending", "investigating", "cleared", "escalated"] = "pending"


class Case(BaseModel):
    """A full investigation case wrapping an alert, findings, and SAR draft."""

    case_id: str = Field(default_factory=lambda: str(uuid4()))
    alert: Alert
    findings: list[Finding] = Field(default_factory=list)
    sar_draft: str = ""
    verdict: Literal["clear", "escalate", "sar-filed"] | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    iteration_count: int = 0
    investigator_model: str = ""
    skeptic_model: str = ""


class IterationTrace(BaseModel):
    """One round of the Investigator-Skeptic loop."""

    case_id: str
    finding_id: str
    iteration: int
    phase: Literal["investigator_draft", "skeptic_verdict", "investigator_revision", "final_state"]
    content: dict
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
