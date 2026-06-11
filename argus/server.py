"""FastAPI server — the orchestrator's HTTP interface."""

from __future__ import annotations

import os
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from argus.models import Alert, Case
from argus.orchestrator import Orchestrator
from argus.persistence import LocalPersistence

# Load .env from project root (optional — Cloud Run uses env vars directly)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
    print(f"[argus] Loaded .env from: {_env_path}")

print(f"[argus] GOOGLE_API_KEY set: {bool(os.getenv('GOOGLE_API_KEY'))}")
print(f"[argus] GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', 'not set')}")

persistence = LocalPersistence()
orchestrator: Orchestrator | None = None


def _get_orchestrator() -> Orchestrator:
    """Lazy-init the orchestrator."""
    global orchestrator
    if orchestrator is None:
        try:
            orchestrator = Orchestrator()
            print("[argus] Orchestrator initialized successfully")
        except Exception as e:
            print(f"[argus] Orchestrator init failed: {e}")
            traceback.print_exc()
            raise
    return orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _get_orchestrator()
    except Exception as e:
        print(f"[argus] Warning: {e}")
    yield


app = FastAPI(
    title="Argus AML Investigation Agent",
    description="An AML investigation agent that drafts SARs from evidence, not imagination.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvestigateRequest(BaseModel):
    alert_id: str | None = None
    transaction_id: str = ""
    originator: str = ""
    beneficiary: str = ""
    amount: float = 0.0
    currency: str = "USD"
    channel: str = "wire"
    country_pair: str = ""
    memo: str = ""


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "argus-orchestrator"}


@app.post("/api/investigate")
async def investigate(request: InvestigateRequest) -> dict:
    """Kick off an investigation on an alert."""
    try:
        orch = _get_orchestrator()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    alert = Alert(
        transaction_id=request.transaction_id,
        originator=request.originator,
        beneficiary=request.beneficiary,
        amount=request.amount,
        currency=request.currency,
        channel=request.channel,
        country_pair=request.country_pair,
        memo=request.memo,
    )

    case = await orch.investigate(alert)
    await persistence.save_case(case)
    await persistence.save_traces(orch.traces)

    return case.model_dump()


@app.get("/api/cases")
async def list_cases():
    """List all investigation cases."""
    cases = await persistence.list_cases()
    return {"cases": cases}


@app.get("/api/cases/{case_id}")
async def get_case(case_id: str):
    """Get a specific case with full details."""
    case = await persistence.load_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case.model_dump()


@app.get("/api/cases/{case_id}/traces")
async def get_traces(case_id: str):
    """Get iteration traces for a case."""
    traces = await persistence.load_traces(case_id)
    return {"traces": traces}


@app.get("/api/alerts")
async def get_alerts():
    """Get pre-seeded alerts for the demo queue."""
    from argus.demo_alerts import DEMO_ALERTS
    return {"alerts": [a.model_dump() for a in DEMO_ALERTS]}
