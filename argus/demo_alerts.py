"""Pre-seeded demo alerts for the Argus alert queue."""

from argus.models import Alert

# GC-001: Shell-company round-tripping (primary demo case)
GC_001_ALERT = Alert(
    alert_id="GC-001",
    transaction_id="TXN-2026-04-15-98500",
    originator="Acme Logistics LLC (Delaware, US)",
    beneficiary="Verde Holdings Ltd (BVI)",
    amount=98500.00,
    currency="USD",
    channel="wire",
    country_pair="US-VG",
    memo="Consulting services Q1 2026",
    timestamp="2026-04-15T14:23:00Z",
    risk_score=0.87,
    status="pending",
)

# GC-004: Negative control (false positive)
GC_004_ALERT = Alert(
    alert_id="GC-004",
    transaction_id="TXN-2026-04-20-250000",
    originator="Northern Industrial Corp (Ontario, CA)",
    beneficiary="Shenzhen MegaTech Electronics Co Ltd (CN)",
    amount=250000.00,
    currency="USD",
    channel="wire",
    country_pair="CA-CN",
    memo="PO-2026-1847 - Electronic components batch shipment",
    timestamp="2026-04-20T09:45:00Z",
    risk_score=0.62,
    status="pending",
)

# Additional demo alerts for queue variety
DEMO_ALERTS = [
    GC_001_ALERT,
    GC_004_ALERT,
    Alert(
        alert_id="ALERT-003",
        transaction_id="TXN-2026-04-22-45000",
        originator="Bright Star Trading FZE (Dubai, AE)",
        beneficiary="Pacific Rim Exports Inc (Panama, PA)",
        amount=45000.00,
        currency="USD",
        channel="wire",
        country_pair="AE-PA",
        memo="Trade finance - textiles",
        timestamp="2026-04-22T11:30:00Z",
        risk_score=0.74,
        status="pending",
    ),
    Alert(
        alert_id="ALERT-004",
        transaction_id="TXN-2026-04-25-12500",
        originator="Johannesburg Capital Partners (ZA)",
        beneficiary="Malta Investment Services Ltd (MT)",
        amount=12500.00,
        currency="EUR",
        channel="wire",
        country_pair="ZA-MT",
        memo="Investment advisory fees",
        timestamp="2026-04-25T16:15:00Z",
        risk_score=0.55,
        status="pending",
    ),
]
