"""SAR draft reporter — assembles findings into a structured SAR narrative."""

from __future__ import annotations

from argus.models import Case, Finding


class SARReporter:
    """Generates structured SAR draft from case findings."""

    def generate_sar_draft(self, case: Case) -> str:
        """Generate a Markdown SAR draft from the case."""
        accepted = [f for f in case.findings if f.skeptic_verdict == "accepted"]
        unverified = [f for f in case.findings if f.skeptic_verdict == "unverified"]

        if case.verdict == "clear":
            return self._generate_clearance_report(case, accepted, unverified)
        else:
            return self._generate_sar(case, accepted, unverified)

    def _generate_sar(
        self, case: Case, accepted: list[Finding], unverified: list[Finding]
    ) -> str:
        """Generate a SAR filing draft."""
        alert = case.alert

        sections = [
            "# Suspicious Activity Report (SAR) — DRAFT",
            "",
            "## 1. Subject Information",
            "",
            f"- **Originator:** {alert.originator}",
            f"- **Beneficiary:** {alert.beneficiary}",
            f"- **Transaction Amount:** {alert.amount:,.2f} {alert.currency}",
            f"- **Channel:** {alert.channel}",
            f"- **Country Pair:** {alert.country_pair}",
            f"- **Transaction Date:** {alert.timestamp}",
            "",
            "## 2. Suspicious Activity Description",
            "",
        ]

        # Narrative from findings
        for i, finding in enumerate(accepted, 1):
            sections.extend([
                f"### Finding {i}: {finding.title}",
                f"**Severity:** {finding.severity} | "
                f"**Type:** {finding.claim_type} | "
                f"**Typology:** {', '.join(finding.typology_tags)}",
                "",
                finding.narrative,
                "",
                "**Evidence:**",
            ])
            for j, citation in enumerate(finding.evidence, 1):
                sections.append(
                    f"  [{j}] `{citation.index}/{citation.doc_id}` "
                    f"— field: `{citation.field}` "
                    f'— "{citation.excerpt}"'
                )
            sections.append("")

        # Filing recommendation
        sections.extend([
            "## 3. Filing Recommendation",
            "",
            "**RECOMMEND FILING** — Evidence supports suspicious activity consistent with "
            f"typology: {', '.join(set(t for f in accepted for t in f.typology_tags))}.",
            "",
        ])

        # Unverified hypotheses appendix
        if unverified:
            sections.extend([
                "## Appendix: Unverified Hypotheses",
                "",
                "> ⚠️ The following findings could not be fully verified by the Skeptic. "
                "They are included for analyst review but should not form the basis of a filing.",
                "",
            ])
            for finding in unverified:
                sections.extend([
                    f"### {finding.title} (UNVERIFIED)",
                    finding.narrative,
                    "",
                ])

        # Investigation metadata
        sections.extend([
            "---",
            "",
            "## Investigation Metadata",
            "",
            f"- **Case ID:** {case.case_id}",
            f"- **Alert ID:** {alert.alert_id}",
            f"- **Investigator Model:** {case.investigator_model}",
            f"- **Skeptic Model:** {case.skeptic_model}",
            f"- **Iterations:** {case.iteration_count}",
            f"- **Accepted Findings:** {len(accepted)}",
            f"- **Unverified Findings:** {len(unverified)}",
            f"- **Generated:** {case.updated_at}",
        ])

        return "\n".join(sections)

    def _generate_clearance_report(
        self, case: Case, accepted: list[Finding], unverified: list[Finding]
    ) -> str:
        """Generate a clearance/no-SAR report."""
        alert = case.alert

        sections = [
            "# Alert Clearance Report",
            "",
            "## Disposition: NO SAR RECOMMENDED",
            "",
            "## 1. Alert Summary",
            "",
            f"- **Originator:** {alert.originator}",
            f"- **Beneficiary:** {alert.beneficiary}",
            f"- **Amount:** {alert.amount:,.2f} {alert.currency}",
            f"- **Channel:** {alert.channel}",
            f"- **Country Pair:** {alert.country_pair}",
            "",
            "## 2. Investigation Summary",
            "",
        ]

        if accepted:
            sections.append(
                "The following findings were confirmed but do not meet the threshold "
                "for suspicious activity:"
            )
            sections.append("")
            for finding in accepted:
                sections.extend([
                    f"- **{finding.title}** ({finding.severity}): {finding.narrative[:200]}...",
                    "",
                ])
        else:
            sections.extend([
                "No findings of concern were substantiated during investigation.",
                "",
            ])

        sections.extend([
            "## 3. Rationale for Clearance",
            "",
            "Based on the evidence reviewed, the activity is consistent with legitimate "
            "commercial purpose. No indicators of money laundering, terrorist financing, "
            "or other suspicious activity were confirmed.",
            "",
            "---",
            "",
            "## Investigation Metadata",
            "",
            f"- **Case ID:** {case.case_id}",
            f"- **Iterations:** {case.iteration_count}",
            f"- **Generated:** {case.updated_at}",
        ])

        return "\n".join(sections)
