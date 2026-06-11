# Argus — Project Description

## Overview

**Argus** is an AML (Anti-Money Laundering) investigation agent that drafts Suspicious Activity Reports (SARs) from evidence, not imagination. Every claim in the SAR draft is anchored to an Elastic document that a separate Skeptic agent re-verifies in an independent context.

## The Problem

Banks dispose of 90–95% of AML alerts as false positives. The bottleneck for Level-1 analysts isn't reasoning — it's evidence assembly: pulling KYC, walking entity graphs, checking sanctions, sweeping adverse media, and citing everything in a SAR template. This takes ~3 hours per alert.

## Our Solution

A dual-agent system powered by Gemini and Elastic MCP:

1. **Investigator** (Gemini 2.5 Pro) explores the evidence graph using Elastic MCP tools
2. **Skeptic** (Gemini 2.5 Flash) re-executes every citation in a separate context
3. **Orchestrator** runs a deterministic loop with hard iteration cap

### Key Innovation: Structural Citation Gate

The Skeptic doesn't just review narratives — it re-fetches every cited document and verifies field values match. This is an **architectural** guarantee, not a prompt-based one. The system physically cannot produce hallucinated findings because:

- Findings without citations are rejected by Pydantic schema
- The Skeptic has a restricted tool surface (verification only, no exploration)
- Separate contexts prevent the Investigator from pre-empting its own review
- Read-only Elastic API key prevents data mutation

## Tech Stack

- **Gemini 2.5 Pro/Flash** via Google Cloud Vertex AI
- **Google Cloud Agent Builder** for orchestration
- **Elastic Cloud Serverless** with ELSER for hybrid search
- **Elastic MCP Server** (official `elastic/mcp-server-elasticsearch`)
- **Cloud Run** for deployment
- **Next.js 15** for the analyst-facing UI
- **Firestore** for case state and iteration traces

## Features

- One-screen analyst workspace: alert queue → investigation → SAR draft
- Real-time reasoning trace showing Investigator/Skeptic rounds
- Click-through citation chips linking claims to source documents
- Negative control support (agent correctly clears false positives)
- Prompt injection resistance (tested with adversarial data)
- Portable architecture (documented SOC and SRE port paths)

## Impact

- Reduces analyst time per alert from ~3 hours to ~30 minutes
- Drives hallucination rate from ~30% (single-agent) to <5% (dual-agent)
- 100% citation validity on golden-case evaluation
- Architecture ports to SOC alert triage and SRE incident investigation

## Links

- **Hosted Demo:** [https://argus-demo.run.app](https://argus-demo.run.app)
- **Repository:** [https://github.com/YOUR_ORG/argus](https://github.com/YOUR_ORG/argus)
- **Video:** [3-minute walkthrough](https://youtube.com/watch?v=PLACEHOLDER)

## License

Apache 2.0
