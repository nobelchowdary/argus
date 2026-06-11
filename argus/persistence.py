"""Persistence layer — Firestore + Cloud Storage I/O for cases and traces."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from argus.models import Case, IterationTrace


class LocalPersistence:
    """Local file-based persistence for development. Swap for Firestore in production."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.cases_dir = self.data_dir / "cases"
        self.traces_dir = self.data_dir / "traces"
        self.cases_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)

    async def save_case(self, case: Case) -> None:
        """Save a case to local storage."""
        filepath = self.cases_dir / f"{case.case_id}.json"
        filepath.write_text(json.dumps(case.model_dump(), indent=2, default=str))

    async def load_case(self, case_id: str) -> Case | None:
        """Load a case from local storage."""
        filepath = self.cases_dir / f"{case_id}.json"
        if filepath.exists():
            data = json.loads(filepath.read_text())
            return Case(**data)
        return None

    async def list_cases(self) -> list[dict[str, Any]]:
        """List all cases (summary only)."""
        cases = []
        for filepath in self.cases_dir.glob("*.json"):
            data = json.loads(filepath.read_text())
            cases.append({
                "case_id": data["case_id"],
                "alert_id": data["alert"]["alert_id"],
                "originator": data["alert"]["originator"],
                "beneficiary": data["alert"]["beneficiary"],
                "amount": data["alert"]["amount"],
                "verdict": data.get("verdict"),
                "created_at": data["created_at"],
            })
        return sorted(cases, key=lambda x: x["created_at"], reverse=True)

    async def save_traces(self, traces: list[IterationTrace]) -> None:
        """Save iteration traces."""
        if not traces:
            return
        case_id = traces[0].case_id
        filepath = self.traces_dir / f"{case_id}.jsonl"
        with open(filepath, "a") as f:
            for trace in traces:
                f.write(json.dumps(trace.model_dump(), default=str) + "\n")

    async def save_traces_data(self, case_id: str, traces: list[dict]) -> None:
        """Save pre-serialized trace data."""
        if not traces:
            return
        filepath = self.traces_dir / f"{case_id}.jsonl"
        with open(filepath, "a") as f:
            for trace in traces:
                f.write(json.dumps(trace, default=str) + "\n")

    async def load_traces(self, case_id: str) -> list[dict]:
        """Load iteration traces for a case."""
        filepath = self.traces_dir / f"{case_id}.jsonl"
        if not filepath.exists():
            return []
        traces = []
        for line in filepath.read_text().strip().split("\n"):
            if line:
                traces.append(json.loads(line))
        return traces


class FirestorePersistence:
    """Firestore-based persistence for production."""

    def __init__(self, project_id: str | None = None):
        from google.cloud import firestore

        self.db = firestore.AsyncClient(project=project_id or os.getenv("GOOGLE_CLOUD_PROJECT"))

    async def save_case(self, case: Case) -> None:
        """Save a case to Firestore."""
        doc_ref = self.db.collection("cases").document(case.case_id)
        await doc_ref.set(case.model_dump())

    async def load_case(self, case_id: str) -> Case | None:
        """Load a case from Firestore."""
        doc_ref = self.db.collection("cases").document(case_id)
        doc = await doc_ref.get()
        if doc.exists:
            return Case(**doc.to_dict())
        return None

    async def list_cases(self) -> list[dict[str, Any]]:
        """List all cases."""
        cases = []
        async for doc in self.db.collection("cases").order_by(
            "created_at", direction="DESCENDING"
        ).limit(50).stream():
            data = doc.to_dict()
            cases.append({
                "case_id": data["case_id"],
                "alert_id": data["alert"]["alert_id"],
                "originator": data["alert"]["originator"],
                "beneficiary": data["alert"]["beneficiary"],
                "amount": data["alert"]["amount"],
                "verdict": data.get("verdict"),
                "created_at": data["created_at"],
            })
        return cases

    async def save_traces(self, traces: list[IterationTrace]) -> None:
        """Save iteration traces to Firestore."""
        if not traces:
            return
        batch = self.db.batch()
        for trace in traces:
            doc_ref = self.db.collection("traces").document()
            batch.set(doc_ref, trace.model_dump())
        await batch.commit()

    async def load_traces(self, case_id: str) -> list[dict]:
        """Load iteration traces for a case."""
        traces = []
        async for doc in self.db.collection("traces").where(
            "case_id", "==", case_id
        ).order_by("iteration").stream():
            traces.append(doc.to_dict())
        return traces
