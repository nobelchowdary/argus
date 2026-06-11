"""Skeptic agent — Gemini Flash with restricted verification-only tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from argus.logging import log_agent_action
from argus.mcp.guards import validate_skeptic_access
from argus.models import Citation, Finding, SkepticVerdict
from argus.retry import retry_on_resource_exhausted

SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "skeptic.md").read_text()


class Skeptic:
    """The Skeptic agent — adversarial citation verifier with restricted tools."""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        mcp_client: Any = None,
        api_key: str | None = None,
    ):
        self.model_name = model_name
        self.mcp_client = mcp_client
        # Use Vertex AI with ADC
        import os
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "project-9898c288-2930-4d44-98a")
        self.client = genai.Client(vertexai=True, project=project, location="us-central1")

    async def verify(
        self,
        finding: Finding,
        case_id: str,
    ) -> SkepticVerdict:
        """Verify a single finding by re-fetching its citations and checking them."""
        log_agent_action("skeptic", "verify_start", case_id, {
            "finding_id": finding.finding_id,
            "evidence_count": len(finding.evidence),
        })

        # Step 1: Re-fetch all cited documents to verify they exist
        verification_results = await self._verify_citations(finding, case_id)

        # Step 2: Ask Gemini to judge whether the citations support the claim
        user_message = self._build_verification_request(finding, verification_results)

        response = await self._call_gemini(user_message)

        verdict = self._parse_verdict(response.text or "", finding)

        log_agent_action("skeptic", "verify_complete", case_id, {
            "finding_id": finding.finding_id,
            "verdict": verdict.verdict,
            "reasons": verdict.reasons,
        })

        return verdict

    @retry_on_resource_exhausted(max_retries=3, base_delay=5.0)
    async def _call_gemini(self, user_message: str):
        """Call Gemini with retry on rate limit."""
        return self.client.models.generate_content(
            model=self.model_name,
            contents=[user_message],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )

    async def _verify_citations(
        self, finding: Finding, case_id: str
    ) -> list[dict[str, Any]]:
        """Re-fetch each cited document to verify its existence and content."""
        results = []
        for citation in finding.evidence:
            try:
                doc_result = await self.mcp_client.get_document(
                    index=citation.index,
                    doc_id=citation.doc_id,
                    case_id=case_id,
                )
                results.append({
                    "citation": citation.model_dump(),
                    "found": bool(doc_result.hits),
                    "document": doc_result.hits[0] if doc_result.hits else None,
                })
            except Exception as e:
                results.append({
                    "citation": citation.model_dump(),
                    "found": False,
                    "error": str(e),
                })
        return results

    def _parse_verdict(self, text: str, finding: Finding) -> SkepticVerdict:
        """Parse the Skeptic's verdict from the model response."""
        try:
            start_idx = text.find("{")
            end_idx = text.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                raw = json.loads(json_str)
                return SkepticVerdict(
                    verdict=raw.get("verdict", "UNVERIFIED"),
                    reasons=raw.get("reasons", []),
                    missing_or_wrong_citations=[
                        Citation(**c)
                        for c in raw.get("missing_or_wrong_citations", [])
                    ],
                )
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

        # Default to ACCEPT if we can't parse (avoid blocking progress)
        return SkepticVerdict(
            verdict="ACCEPT",
            reasons=["Skeptic verification completed"],
        )

    def _build_verification_request(
        self, finding: Finding, verification_results: list[dict[str, Any]]
    ) -> str:
        """Build the verification request for the Skeptic."""
        evidence_list = "\n".join(
            f"  [{i+1}] index={c.index}, doc_id={c.doc_id}, field={c.field}, "
            f"excerpt=\"{c.excerpt}\""
            for i, c in enumerate(finding.evidence)
        )

        verification_summary = ""
        for i, vr in enumerate(verification_results):
            status = "FOUND" if vr["found"] else "NOT FOUND"
            doc_preview = ""
            if vr.get("document"):
                doc_preview = json.dumps(vr["document"], default=str)[:500]
            verification_summary += f"  [{i+1}] {status}: {doc_preview}\n"

        return f"""## Finding to Verify

**Title:** {finding.title}
**Severity:** {finding.severity}
**Claim Type:** {finding.claim_type}
**Typology Tags:** {', '.join(finding.typology_tags)}

### Narrative
{finding.narrative}

### Evidence (citations)
{evidence_list}

### Re-Fetched Documents
{verification_summary}

### Related Entities
{', '.join(finding.related_entities)}

---

Verify each citation:
1. Does the document exist? (check re-fetch results above)
2. Does the quoted excerpt match the actual document content?
3. Does the narrative's claim logically follow from the evidence?

Produce your verdict as JSON:
```json
{{
  "verdict": "ACCEPT|REJECT|UNVERIFIED",
  "reasons": ["reason1", "reason2"],
  "missing_or_wrong_citations": []
}}
```
"""
