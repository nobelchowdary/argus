# Argus — 3-Minute Demo Video Script

**Total runtime:** ~3:00  
**Style:** Screen recording with voiceover. No face cam needed.  
**Screen:** Browser showing the hosted demo at https://argus-frontend-712958901404.us-central1.run.app

---

## 0:00–0:15 — Title + Problem Statement

**[Screen: Title card — dark background, Argus logo/text, one-liner]**

**Say:**
> "Compliance analysts at banks dispose of 95 percent of anti-money laundering alerts as false positives. The bottleneck isn't reasoning — it's evidence assembly. Pulling KYC, walking entity graphs, checking sanctions, citing everything in a SAR template. That takes three hours per alert. Argus does it in under a minute."

**[Cut to: Browser opening the hosted demo URL]**

---

## 0:15–0:35 — Alert Queue + Kick Off Investigation

**[Screen: The alert queue on the left panel. Multiple alerts visible.]**

**Say:**
> "Here's the alert queue. We have a suspicious wire — $98,500 from Acme Logistics LLC in Delaware to Verde Holdings Ltd in the British Virgin Islands. Risk score 0.87 — flagged for potential shell-company round-tripping."

**[Action: Click the "Investigate" button on GC-001]**

**Say:**
> "I'll kick off an investigation. The dual-agent system will now analyze this transaction."

---

## 0:35–1:30 — Reasoning Trace (The Core Demo)

**[Screen: Right panel switches to "Reasoning Trace" tab. Trace entries stream in.]**

**Say:**
> "Watch the trace panel. The Investigator agent — powered by Gemini on Vertex AI — is gathering evidence. It's calling entity_neighbors, transaction_history, adverse_media_search, and sanctions_check against our synthetic Elastic dataset."

**[Pause as investigator_draft trace entries appear]**

**Say:**
> "It produced five findings. Now the Skeptic agent kicks in — this is what makes Argus different. The Skeptic has a restricted tool surface. It can only re-fetch cited documents and verify them. It cannot explore on its own."

**[Point to skeptic_verdict entries]**

**Say:**
> "Here — the Skeptic is verifying each citation. It re-executes the underlying lookup in a completely separate context. If the Investigator hallucinated a claim or cited a document that doesn't match, the Skeptic rejects it. This is a structural guarantee — not a prompt-based one."

**[If a rejection shows in the trace, highlight it:]**

**Say:**
> "See this rejection? The Skeptic found a citation that didn't match the source document. The Investigator had to go back, re-fetch the actual data, and correct its finding. This self-correction loop is the core innovation."

---

## 1:30–2:15 — SAR Draft + Findings

**[Action: Click on the "SAR Draft" tab in the right panel]**

**Say:**
> "The investigation is complete. Verdict: escalate. Here's the SAR draft — a structured Suspicious Activity Report with Subject Information, Suspicious Activity narrative, and Filing Recommendation."

**[Scroll through the SAR draft]**

**Say:**
> "Every claim in this narrative is backed by evidence from the dataset. The findings show beneficial-owner overlap, circular transaction patterns, and adverse media hits — all with citations pointing back to specific documents in the Elastic indices."

**[Point to findings in the center panel]**

**Say:**
> "Five findings, each with a severity level, typology tags, and cited evidence. The Skeptic accepted all of them after verification. Nothing gets into the SAR without passing the citation gate."

---

## 2:15–2:40 — Negative Control (GC-004)

**[Action: Click back to alert queue, select GC-004 ($250,000 CA→CN wire)]**

**Say:**
> "But here's the real test — Argus isn't biased toward escalation. This second alert is a $250,000 wire from Canada to China. Looks suspicious on the surface, but..."

**[Action: Click Investigate. Wait for completion.]**

**Say:**
> "Verdict: clear. The agent found legitimate purchase order references, established commercial history, and no adverse media. It correctly identifies this as a false positive and recommends no SAR filing. The Skeptic verified the clearing rationale just as rigorously."

---

## 2:40–2:55 — Architecture + What Makes This Different

**[Screen: Switch to show the architecture diagram or explain over the UI]**

**Say:**
> "Under the hood: Gemini 2.5 on Vertex AI, deployed on Google Cloud Run, with an Elastic-compatible MCP tool surface. The key architectural decisions — read-only data access, asymmetric tool surfaces between Investigator and Skeptic, separate contexts preventing self-review, and a hard iteration cap — these are all enforced in code, not in prompts. The system physically cannot hallucinate findings into the final report."

---

## 2:55–3:00 — Closing

**[Screen: Show the GitHub repo or closing card]**

**Say:**
> "Argus — an AML investigation agent that drafts SARs from evidence, not imagination. Built with Gemini and Google Cloud. The same Investigator-Skeptic pattern ports directly to SOC alert triage and SRE incident investigation. Apache 2.0, link below."

---

## Recording Tips

1. **Warm up Cloud Run** before recording — hit the frontend URL and run one investigation first so there's no cold-start delay during the video
2. **Use GC-001 first** (escalate case) — it shows the full investigation including Skeptic verification
3. **Use GC-004 second** (clear case) — proves the agent isn't biased
4. **If investigation takes time**, you can cut/speed-up the waiting portion and narrate over it
5. **Keep cursor visible** — point to trace entries, findings, and citations as you explain them
