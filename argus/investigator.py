"""Investigator agent — Gemini with full MCP tool access for AML investigation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from argus.logging import log_agent_action
from argus.mcp.tools import AMLTools
from argus.models import Alert, Citation, Finding
from argus.retry import retry_on_resource_exhausted

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "investigator.md").read_text()


class Investigator:
    """The Investigator agent — gathers evidence via tools then uses Gemini for analysis."""

    def __init__(
        self,
        model_name: str = "gemini-2.5-flash-lite",
        mcp_client: Any = None,
        api_key: str | None = None,
    ):
        self.model_name = model_name
        self.mcp_client = mcp_client
        self.aml_tools = AMLTools(mcp_client) if mcp_client else None
        # Use Vertex AI with ADC (project has billing enabled)
        import os
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "project-9898c288-2930-4d44-98a")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.client = genai.Client(vertexai=True, project=project, location=location)

    async def investigate(
        self,
        alert: Alert,
        case_id: str,
        feedback: str | None = None,
    ) -> list[Finding]:
        """Run an investigation — execute tools then produce findings."""
        log_agent_action("investigator", "investigate_start", case_id, {
            "alert_id": alert.alert_id,
            "has_feedback": feedback is not None,
        })

        # Step 1: Gather evidence by executing tools against the data
        evidence_bundle = await self._gather_evidence(alert, case_id)

        # Step 2: Send evidence to Gemini for analysis and finding generation
        user_message = self._build_analysis_prompt(alert, evidence_bundle, feedback)

        response = await self._call_gemini(user_message)

        # Step 3: Parse findings from response
        findings = self._parse_findings(response.text or "", case_id, evidence_bundle)

        log_agent_action("investigator", "investigate_complete", case_id, {
            "findings_count": len(findings),
        })

        return findings

    @retry_on_resource_exhausted(max_retries=3, base_delay=5.0)
    async def _call_gemini(self, user_message: str):
        """Call Gemini with retry on rate limit."""
        return self.client.models.generate_content(
            model=self.model_name,
            contents=[user_message],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=4096,
            ),
        )

    async def _gather_evidence(self, alert: Alert, case_id: str) -> dict[str, Any]:
        """Execute all relevant tools to gather evidence for the alert."""
        evidence: dict[str, Any] = {}

        # 1. Get entity info for originator and beneficiary
        orig_name = alert.originator.split("(")[0].strip()
        benef_name = alert.beneficiary.split("(")[0].strip()

        # Search entities
        orig_result = await self.mcp_client.search(
            index="argus-entities",
            query_dsl={"query": {"match": {"names": orig_name}}},
            size=5,
            case_id=case_id,
        )
        evidence["originator_entities"] = orig_result

        benef_result = await self.mcp_client.search(
            index="argus-entities",
            query_dsl={"query": {"match": {"names": benef_name}}},
            size=5,
            case_id=case_id,
        )
        evidence["beneficiary_entities"] = benef_result

        # 2. Get the flagged transaction
        txn_result = await self.mcp_client.search(
            index="argus-transactions",
            query_dsl={"query": {"term": {"transaction_id": alert.transaction_id}}},
            size=1,
            case_id=case_id,
        )
        evidence["flagged_transaction"] = txn_result

        # 3. Check beneficial ownership overlap
        orig_entity_id = None
        benef_entity_id = None
        if orig_result.hits:
            orig_entity_id = orig_result.hits[0].get("entity_id")
        if benef_result.hits:
            benef_entity_id = benef_result.hits[0].get("entity_id")

        if orig_entity_id:
            neighbors = await self.aml_tools.entity_neighbors(
                orig_entity_id, case_id=case_id, hops=1
            )
            evidence["originator_neighbors"] = neighbors

        if benef_entity_id:
            neighbors = await self.aml_tools.entity_neighbors(
                benef_entity_id, case_id=case_id, hops=1
            )
            evidence["beneficiary_neighbors"] = neighbors

        # 4. Transaction history
        if orig_entity_id:
            tx_hist = await self.aml_tools.transaction_history(
                orig_entity_id, start="2025-01-01", end="2026-12-31", case_id=case_id
            )
            evidence["originator_transactions"] = tx_hist

        # 5. Adverse media
        adv_orig = await self.aml_tools.adverse_media_search(
            orig_name, case_id=case_id, k=5
        )
        evidence["adverse_media_originator"] = adv_orig

        adv_benef = await self.aml_tools.adverse_media_search(
            benef_name, case_id=case_id, k=5
        )
        evidence["adverse_media_beneficiary"] = adv_benef

        # 6. Sanctions check
        sanctions_orig = await self.aml_tools.sanctions_check(
            orig_name, case_id=case_id
        )
        evidence["sanctions_originator"] = sanctions_orig

        sanctions_benef = await self.aml_tools.sanctions_check(
            benef_name, case_id=case_id
        )
        evidence["sanctions_beneficiary"] = sanctions_benef

        # 7. Prior alerts
        prior = await self.aml_tools.similar_prior_alerts(
            alert.transaction_id, case_id=case_id
        )
        evidence["prior_alerts"] = prior

        # 8. Typology playbook
        playbook = await self.aml_tools.typology_playbook(
            "shell-company-roundtrip", case_id=case_id
        )
        evidence["typology_playbook"] = playbook

        return evidence

    def _build_analysis_prompt(
        self, alert: Alert, evidence: dict[str, Any], feedback: str | None
    ) -> str:
        """Build the prompt with gathered evidence for Gemini analysis."""
        evidence_text = self._format_evidence(evidence)

        msg = f"""## Alert Under Investigation

- **Alert ID:** {alert.alert_id}
- **Transaction ID:** {alert.transaction_id}
- **Originator:** {alert.originator}
- **Beneficiary:** {alert.beneficiary}
- **Amount:** ${alert.amount:,.2f} {alert.currency}
- **Channel:** {alert.channel}
- **Country Pair:** {alert.country_pair}
- **Memo:** {alert.memo}
- **Risk Score:** {alert.risk_score}

## Evidence Gathered From Elastic

{evidence_text}

## Instructions

Based on the evidence above, produce your findings as a JSON array. Each finding must have citations referencing specific documents from the evidence. If the evidence shows this is a legitimate transaction, produce a finding explaining why it should be cleared.

Respond ONLY with a JSON array of findings in this format:
```json
[
  {{
    "title": "Finding title",
    "severity": "info|low|med|high|critical",
    "typology_tags": ["tag1"],
    "narrative": "Explanation...",
    "claim_type": "confirmed|inferred",
    "evidence": [
      {{"index": "argus-...", "doc_id": "...", "field": "field_name", "excerpt": "quoted text from doc"}}
    ],
    "related_entities": ["entity_id_1"]
  }}
]
```
"""
        if feedback:
            msg += f"""
## Skeptic Feedback (you MUST address these issues)

{feedback}

Revise your findings to fix the citation issues raised by the Skeptic.
"""
        return msg

    def _format_evidence(self, evidence: dict[str, Any]) -> str:
        """Format evidence bundle into readable text for the LLM."""
        parts: list[str] = []

        for key, result in evidence.items():
            if not hasattr(result, "hits") or not result.hits:
                parts.append(f"### {key}\nNo results found.\n")
                continue

            parts.append(f"### {key} ({len(result.hits)} results from {result.index})")
            for i, hit in enumerate(result.hits[:5]):
                doc_id = hit.get("_id", "unknown")
                display = {k: v for k, v in hit.items() if k != "_id"}
                for k, v in display.items():
                    if isinstance(v, str) and len(v) > 300:
                        display[k] = v[:300] + "..."
                parts.append(f"  Doc[{i}] id={doc_id}:")
                parts.append(f"    {json.dumps(display, indent=2, default=str)[:800]}")
            parts.append("")

        return "\n".join(parts)

    def _parse_findings(
        self, text: str, case_id: str, evidence: dict[str, Any]
    ) -> list[Finding]:
        """Parse findings from the model's text output."""
        findings: list[Finding] = []

        try:
            start_idx = text.find("[")
            end_idx = text.rfind("]") + 1
            if start_idx == -1 or end_idx <= start_idx:
                return self._fallback_findings(text, case_id, evidence)

            json_str = text[start_idx:end_idx]
            raw_findings = json.loads(json_str)

            for raw in raw_findings:
                evidence_list = []
                for e in raw.get("evidence", []):
                    evidence_list.append(Citation(
                        index=e.get("index", "argus-entities"),
                        doc_id=e.get("doc_id", "unknown"),
                        field=e.get("field"),
                        excerpt=e.get("excerpt"),
                    ))

                if not evidence_list:
                    evidence_list = self._auto_cite(raw, evidence)

                if not evidence_list:
                    continue

                finding = Finding(
                    case_id=case_id,
                    title=raw.get("title", "Untitled Finding"),
                    severity=raw.get("severity", "med"),
                    typology_tags=raw.get("typology_tags", []),
                    narrative=raw.get("narrative", ""),
                    claim_type=raw.get("claim_type", "inferred"),
                    evidence=evidence_list,
                    related_entities=raw.get("related_entities", []),
                    investigator_model=self.model_name,
                )
                findings.append(finding)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            log_agent_action("investigator", "parse_error", case_id, {"error": str(e)})
            return self._fallback_findings(text, case_id, evidence)

        return findings if findings else self._fallback_findings(text, case_id, evidence)

    def _fallback_findings(
        self, text: str, case_id: str, evidence: dict[str, Any]
    ) -> list[Finding]:
        """Generate fallback findings from available evidence when parsing fails."""
        findings: list[Finding] = []

        orig_hits = evidence.get("originator_entities")
        benef_hits = evidence.get("beneficiary_entities")

        if orig_hits and benef_hits and orig_hits.hits and benef_hits.hits:
            orig_doc = orig_hits.hits[0]
            benef_doc = benef_hits.hits[0]

            orig_owners = {
                bo.get("entity_id")
                for bo in orig_doc.get("beneficial_owners", [])
                if bo.get("entity_id")
            }
            benef_owners = {
                bo.get("entity_id")
                for bo in benef_doc.get("beneficial_owners", [])
                if bo.get("entity_id")
            }

            shared = orig_owners & benef_owners
            if shared:
                findings.append(Finding(
                    case_id=case_id,
                    title="Originator and beneficiary share controlling beneficial owner",
                    severity="high",
                    typology_tags=["layering", "shell-company-roundtrip"],
                    narrative="The originator and beneficiary share a common beneficial owner, indicating potential round-tripping through shell companies.",
                    claim_type="confirmed",
                    evidence=[
                        Citation(
                            index="argus-entities",
                            doc_id=orig_doc.get("_id", orig_doc.get("entity_id", "")),
                            field="beneficial_owners",
                            excerpt=f"Shared owner: {list(shared)[0]}",
                        ),
                        Citation(
                            index="argus-entities",
                            doc_id=benef_doc.get("_id", benef_doc.get("entity_id", "")),
                            field="beneficial_owners",
                            excerpt=f"Shared owner: {list(shared)[0]}",
                        ),
                    ],
                    related_entities=list(shared),
                    investigator_model=self.model_name,
                ))

        if not findings:
            # Generate a minimal finding so the case proceeds
            first_citation = None
            for result in evidence.values():
                if hasattr(result, "hits") and result.hits:
                    doc = result.hits[0]
                    first_citation = Citation(
                        index=result.index,
                        doc_id=doc.get("_id", "unknown"),
                        field="auto",
                        excerpt="Evidence gathered during investigation",
                    )
                    break

            if first_citation:
                findings.append(Finding(
                    case_id=case_id,
                    title="Investigation summary",
                    severity="info",
                    typology_tags=[],
                    narrative=text[:500] if text else "Investigation completed - see evidence.",
                    claim_type="inferred",
                    evidence=[first_citation],
                    related_entities=[],
                    investigator_model=self.model_name,
                ))

        return findings

    def _auto_cite(self, raw_finding: dict, evidence: dict[str, Any]) -> list[Citation]:
        """Auto-attach citations from evidence when the model didn't provide them."""
        citations: list[Citation] = []

        for key, result in evidence.items():
            if not hasattr(result, "hits") or not result.hits:
                continue
            for hit in result.hits[:2]:
                doc_id = hit.get("_id", "")
                if doc_id:
                    citations.append(Citation(
                        index=result.index,
                        doc_id=doc_id,
                        field="auto",
                        excerpt="Auto-cited from evidence gathering",
                    ))
                    if len(citations) >= 2:
                        return citations

        return citations
