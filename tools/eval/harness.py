"""Evaluation harness — run agent against golden cases and compute metrics."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from argus.demo_alerts import GC_001_ALERT, GC_004_ALERT
from argus.models import Case, Finding
from argus.orchestrator import Orchestrator


GOLDEN_CASES_DIR = Path(__file__).parent.parent / "dataset" / "golden_cases"


def load_ground_truth(case_id: str) -> dict:
    """Load ground truth for a golden case."""
    gt_path = GOLDEN_CASES_DIR / case_id / "ground_truth.json"
    if gt_path.exists():
        return json.loads(gt_path.read_text())
    return {}


def compute_metrics(case: Case, ground_truth: dict) -> dict:
    """Compute evaluation metrics for a case against ground truth."""
    accepted = [f for f in case.findings if f.skeptic_verdict == "accepted"]
    expected = ground_truth.get("expected_findings", [])
    known_negatives = ground_truth.get("known_negatives", [])
    should_clear = ground_truth.get("should_be_cleared", False)

    # Match findings to expected
    matched = 0
    for exp in expected:
        if exp.get("must_be_found"):
            for finding in accepted:
                title_match = _fuzzy_title_match(finding.title, exp["title"])
                evidence_match = any(
                    c.index in exp.get("required_evidence_indices", [])
                    for c in finding.evidence
                )
                if title_match or evidence_match:
                    matched += 1
                    break

    total_expected = sum(1 for e in expected if e.get("must_be_found"))
    precision = matched / len(accepted) if accepted else 1.0
    recall = matched / total_expected if total_expected > 0 else 1.0
    hallucination_rate = (len(accepted) - matched) / len(accepted) if accepted else 0.0

    # Citation validity (all citations should re-execute)
    citation_valid = all(
        all(c.doc_id and c.index for c in f.evidence) for f in accepted
    )

    # Verdict accuracy
    actual_clear = case.verdict == "clear"
    verdict_correct = actual_clear == should_clear

    return {
        "case_id": case.case_id,
        "alert_id": case.alert.alert_id,
        "precision": precision,
        "recall": recall,
        "hallucination_rate": hallucination_rate,
        "citation_validity": 1.0 if citation_valid else 0.0,
        "verdict_correct": verdict_correct,
        "verdict": case.verdict,
        "expected_clear": should_clear,
        "total_findings": len(case.findings),
        "accepted_findings": len(accepted),
        "iterations": case.iteration_count,
    }


def _fuzzy_title_match(actual: str, expected: str) -> bool:
    """Check if finding title roughly matches expected."""
    actual_lower = actual.lower()
    # Check if key terms from expected appear in actual
    key_terms = [w for w in expected.lower().split() if len(w) > 4]
    matches = sum(1 for term in key_terms if term in actual_lower)
    return matches >= len(key_terms) * 0.5


async def run_evaluation() -> dict:
    """Run full evaluation against golden cases."""
    orchestrator = Orchestrator()
    results = []

    # GC-001
    print("\n" + "=" * 60)
    print("Running GC-001: Shell-company round-tripping")
    print("=" * 60)

    start = time.monotonic()
    gc001_case = await orchestrator.investigate(GC_001_ALERT)
    gc001_time = time.monotonic() - start

    gc001_gt = load_ground_truth("GC-001")
    gc001_metrics = compute_metrics(gc001_case, gc001_gt)
    gc001_metrics["wall_clock_s"] = round(gc001_time, 1)
    results.append(gc001_metrics)
    print(f"  Verdict: {gc001_case.verdict}")
    print(f"  Findings: {len(gc001_case.findings)}")
    print(f"  Time: {gc001_time:.1f}s")

    # GC-004
    print("\n" + "=" * 60)
    print("Running GC-004: Negative control")
    print("=" * 60)

    start = time.monotonic()
    gc004_case = await orchestrator.investigate(GC_004_ALERT)
    gc004_time = time.monotonic() - start

    gc004_gt = load_ground_truth("GC-004")
    gc004_metrics = compute_metrics(gc004_case, gc004_gt)
    gc004_metrics["wall_clock_s"] = round(gc004_time, 1)
    results.append(gc004_metrics)
    print(f"  Verdict: {gc004_case.verdict}")
    print(f"  Findings: {len(gc004_case.findings)}")
    print(f"  Time: {gc004_time:.1f}s")

    # Summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    for r in results:
        print(f"\n  {r['alert_id']}:")
        print(f"    Precision:       {r['precision']:.1%}")
        print(f"    Recall:          {r['recall']:.1%}")
        print(f"    Hallucination:   {r['hallucination_rate']:.1%}")
        print(f"    Citation Valid:  {r['citation_validity']:.1%}")
        print(f"    Verdict Correct: {'✓' if r['verdict_correct'] else '✗'}")
        print(f"    Wall Clock:      {r['wall_clock_s']}s")

    return {"results": results}


if __name__ == "__main__":
    asyncio.run(run_evaluation())
