"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from argus.models import Alert, Case, Citation, Finding, ToolResult


def test_citation_creation():
    c = Citation(index="argus-transactions", doc_id="doc123")
    assert c.index == "argus-transactions"
    assert c.doc_id == "doc123"
    assert c.field is None


def test_finding_requires_evidence():
    with pytest.raises(ValidationError):
        Finding(
            case_id="test",
            title="Test",
            severity="med",
            narrative="Test narrative",
            claim_type="confirmed",
            evidence=[],  # Must have at least 1
        )


def test_finding_valid():
    f = Finding(
        case_id="test",
        title="Test Finding",
        severity="high",
        narrative="The evidence shows [1]...",
        claim_type="confirmed",
        evidence=[Citation(index="argus-entities", doc_id="ent-001", field="name", excerpt="Acme")],
        related_entities=["ent-001"],
    )
    assert f.title == "Test Finding"
    assert len(f.evidence) == 1
    assert f.finding_id  # Auto-generated


def test_tool_result_hash():
    tr = ToolResult(
        tool_name="search",
        case_id="test",
        args={"index": "argus-transactions"},
        index="argus-transactions",
        hits=[{"_id": "doc1"}, {"_id": "doc2"}],
    )
    h1 = tr.compute_hash()
    assert h1
    # Same hits should produce same hash
    h2 = tr.compute_hash()
    assert h1 == h2


def test_alert_defaults():
    a = Alert(
        transaction_id="txn-001",
        originator="Test Originator",
        beneficiary="Test Beneficiary",
        amount=10000.0,
    )
    assert a.status == "pending"
    assert a.currency == "USD"
    assert a.alert_id  # Auto-generated


def test_case_creation():
    alert = Alert(
        transaction_id="txn-001",
        originator="Org",
        beneficiary="Ben",
        amount=50000.0,
    )
    case = Case(alert=alert)
    assert case.case_id
    assert case.findings == []
    assert case.verdict is None
