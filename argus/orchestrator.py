"""Orchestrator — the deterministic loop that coordinates Investigator and Skeptic."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from argus.investigator import Investigator
from argus.logging import log_agent_action, setup_logging
from argus.mcp.local_simulator import LocalElasticSimulator
from argus.models import Alert, Case, Finding, IterationTrace, SkepticVerdict
from argus.reporter import SARReporter
from argus.skeptic import Skeptic

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "4"))
INVESTIGATOR_MODEL = os.getenv("INVESTIGATOR_MODEL", "gemini-2.5-flash")
SKEPTIC_MODEL = os.getenv("SKEPTIC_MODEL", "gemini-2.5-flash")


class Orchestrator:
    """Deterministic loop owner: case lifecycle, iteration cap, report assembly."""

    def __init__(
        self,
        elastic_url: str | None = None,
        elastic_api_key: str | None = None,
        google_api_key: str | None = None,
    ):
        self.elastic_url = elastic_url or os.getenv("ELASTIC_URL", "")
        self.elastic_api_key = elastic_api_key or os.getenv("ELASTIC_API_KEY", "")
        self.google_api_key = google_api_key or os.getenv("GOOGLE_API_KEY", "")

        # Use local simulator when no Elastic URL configured
        self.mcp_client = LocalElasticSimulator()

        self.investigator = Investigator(
            model_name=INVESTIGATOR_MODEL,
            mcp_client=self.mcp_client,
            api_key=self.google_api_key,
        )
        self.skeptic = Skeptic(
            model_name=SKEPTIC_MODEL,
            mcp_client=self.mcp_client,
            api_key=self.google_api_key,
        )
        self.reporter = SARReporter()
        self.traces: list[IterationTrace] = []
        setup_logging()

    async def investigate(self, alert: Alert) -> Case:
        """Run the full Investigator-Skeptic loop on an alert."""
        case = Case(
            alert=alert,
            investigator_model=INVESTIGATOR_MODEL,
            skeptic_model=SKEPTIC_MODEL,
        )

        log_agent_action("orchestrator", "case_start", case.case_id, {
            "alert_id": alert.alert_id,
            "max_iterations": MAX_ITERATIONS,
        })

        await self.mcp_client.connect()

        try:
            # Initial investigation
            findings = await self.investigator.investigate(alert, case.case_id)

            self._record_trace(case.case_id, findings, "investigator_draft", 0)

            # Skeptic verification loop
            for iteration in range(MAX_ITERATIONS):
                case.iteration_count = iteration + 1
                verdicts: list[tuple[Finding, SkepticVerdict]] = []

                for finding in findings:
                    verdict = await self.skeptic.verify(finding, case.case_id)
                    verdicts.append((finding, verdict))
                    finding.iteration = iteration + 1

                self._record_trace(
                    case.case_id,
                    [{"finding": f.model_dump(), "verdict": v.model_dump()} for f, v in verdicts],
                    "skeptic_verdict",
                    iteration + 1,
                )

                # Process verdicts
                accepted: list[Finding] = []
                rejected: list[Finding] = []
                unverified: list[Finding] = []

                for finding, verdict in verdicts:
                    if verdict.verdict == "ACCEPT":
                        finding.skeptic_verdict = "accepted"
                        accepted.append(finding)
                    elif verdict.verdict == "REJECT":
                        finding.skeptic_verdict = "rejected"
                        rejected.append(finding)
                    else:
                        finding.skeptic_verdict = "unverified"
                        unverified.append(finding)

                log_agent_action("orchestrator", "iteration_summary", case.case_id, {
                    "iteration": iteration + 1,
                    "accepted": len(accepted),
                    "rejected": len(rejected),
                    "unverified": len(unverified),
                })

                # If no rejections, we're done
                if not rejected:
                    findings = accepted + unverified
                    break

                # Feed rejections back to Investigator
                if iteration < MAX_ITERATIONS - 1:
                    feedback = self._build_feedback(verdicts)
                    revised_findings = await self.investigator.investigate(
                        alert, case.case_id, feedback=feedback
                    )
                    self._record_trace(
                        case.case_id, revised_findings, "investigator_revision", iteration + 1
                    )
                    # Merge: keep accepted, replace rejected with revisions
                    findings = accepted + revised_findings
                else:
                    # Final iteration: move remaining rejects to unverified
                    for f in rejected:
                        f.skeptic_verdict = "unverified"
                    findings = accepted + rejected + unverified

            # Finalize case
            case.findings = findings
            case.sar_draft = self.reporter.generate_sar_draft(case)
            case.verdict = self._determine_verdict(findings)
            case.updated_at = datetime.now(timezone.utc).isoformat()

            self._record_trace(case.case_id, case.model_dump(), "final_state", case.iteration_count)

            log_agent_action("orchestrator", "case_complete", case.case_id, {
                "verdict": case.verdict,
                "findings_count": len(case.findings),
                "iterations": case.iteration_count,
            })

        finally:
            await self.mcp_client.close()

        return case

    def _determine_verdict(self, findings: list[Finding]) -> str:
        """Determine the overall case verdict from findings."""
        if not findings:
            return "clear"

        # If any high/critical confirmed findings → escalate
        for f in findings:
            if f.skeptic_verdict == "accepted" and f.severity in ("high", "critical"):
                if f.claim_type == "confirmed":
                    return "escalate"

        # If only low-severity or inferred → clear
        has_confirmed_med = any(
            f.skeptic_verdict == "accepted" and f.severity == "med" and f.claim_type == "confirmed"
            for f in findings
        )
        if has_confirmed_med:
            return "escalate"

        return "clear"

    def _build_feedback(
        self, verdicts: list[tuple[Finding, SkepticVerdict]]
    ) -> str:
        """Build feedback string from Skeptic rejections."""
        feedback_parts: list[str] = []
        for finding, verdict in verdicts:
            if verdict.verdict == "REJECT":
                feedback_parts.append(
                    f"### Finding: {finding.title}\n"
                    f"**Rejected.** Reasons:\n"
                    + "\n".join(f"- {r}" for r in verdict.reasons)
                )
                if verdict.missing_or_wrong_citations:
                    feedback_parts.append("**Problematic citations:**")
                    for c in verdict.missing_or_wrong_citations:
                        feedback_parts.append(
                            f"- {c.index}/{c.doc_id} field={c.field}: {c.excerpt}"
                        )
        return "\n\n".join(feedback_parts)

    def _record_trace(
        self,
        case_id: str,
        content: Any,
        phase: str,
        iteration: int,
    ) -> None:
        """Record an iteration trace."""
        # Normalize content for serialization
        if isinstance(content, list):
            serialized = [
                item.model_dump() if hasattr(item, "model_dump") else item
                for item in content
            ]
        elif hasattr(content, "model_dump"):
            serialized = content.model_dump()
        else:
            serialized = content

        trace = IterationTrace(
            case_id=case_id,
            finding_id="*",
            iteration=iteration,
            phase=phase,
            content=serialized if isinstance(serialized, dict) else {"data": serialized},
        )
        self.traces.append(trace)
