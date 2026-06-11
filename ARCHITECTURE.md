# Argus — Architecture & Trust Boundaries

## System Overview

Argus is a dual-agent AML investigation system built on three principles:

1. **Architectural enforcement over prompt engineering** — all safety constraints are enforced in code
2. **Adversarial verification** — the Skeptic re-executes every citation in a separate context
3. **Read-only data access** — the agent cannot mutate evidence or downstream systems

## Component Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    WEB UI (Next.js on Cloud Run)                      │
│  Alert queue · Investigation workspace · SAR draft · Reasoning trace  │
└──────┬───────────────────────────────────────────────────────────────┘
       │ HTTPS (Cloud Run authn)
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│              ORCHESTRATOR (Python, Cloud Run service)                 │
│  Deterministic loop owner: case lifecycle, iteration cap, report      │
│  assembly, persistence of iteration traces to Firestore               │
└──────┬─────────────────────────────────┬─────────────────────────────┘
       │                                 │
       ▼                                 ▼
  ┌─────────────┐                  ┌─────────────┐
  │ INVESTIGATOR│ ◄── feedback ──  │   SKEPTIC   │
  │ (Gemini 2.5 │ ──  finding  ──► │ (Gemini 2.5 │
  │  Pro)       │                  │  Flash)     │
  └─────┬───────┘                  └─────┬───────┘
        │ full MCP tool surface          │ verification-only subset
        ▼                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│            ELASTIC MCP SERVER (sidecar container)                     │
│  Official elastic/mcp-server-elasticsearch, read-only API key         │
└──────┬───────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│        ELASTIC CLOUD SERVERLESS (Search project)                      │
│  argus-transactions · argus-entities · argus-adverse-media            │
│  argus-sanctions · argus-prior-alerts · argus-typology-playbooks      │
└──────────────────────────────────────────────────────────────────────┘
```

## Trust Boundaries

| Boundary | Enforcement | Prevents |
|----------|-------------|----------|
| Elastic → Agent | API key: read-only on `argus-*` | Data mutation |
| Tools → Skeptic | Code: restricted tool subset | Fishing/fabrication |
| Finding → SAR | Pydantic: non-empty `evidence[]` | Uncited claims |
| Investigator → Skeptic | Separate session/context | Self-review bypass |
| Loop runaway | Hard cap: `MAX_ITERATIONS=4` | Infinite spirals |

## Data Flow

1. Alert enters from queue (pre-seeded or API)
2. Orchestrator creates Case, invokes Investigator
3. Investigator explores via MCP tools, produces Findings
4. For each Finding, Skeptic re-executes citations
5. On REJECT: feedback loop, Investigator revises
6. On ACCEPT: Finding promoted to SAR draft
7. After convergence: SAR assembled, Case persisted

## Portability

The Investigator–Skeptic pattern ports to any analyst-triage workflow:
- **SOC alert triage** — swap indices for security events + threat intel
- **SRE incident investigation** — swap for logs/metrics + runbook corpus

See [docs/portability.md](docs/portability.md) for the full mapping.
