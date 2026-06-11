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
│  https://argus-frontend-794755514339.us-central1.run.app              │
└──────┬───────────────────────────────────────────────────────────────┘
       │ HTTPS /api/invoke → proxy
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│              ORCHESTRATOR (FastAPI on Cloud Run)                       │
│  Deterministic loop: case lifecycle, iteration cap (MAX=4),           │
│  report assembly, local file persistence                              │
│  https://argus-backend-794755514339.us-central1.run.app               │
└──────┬─────────────────────────────────┬─────────────────────────────┘
       │                                 │
       ▼                                 ▼
  ┌─────────────┐                  ┌─────────────┐
  │ INVESTIGATOR│ ◄── feedback ──  │   SKEPTIC   │
  │ (Gemini 2.5 │ ──  finding  ──► │ (Gemini 2.5 │
  │  Flash)     │                  │  Flash)     │
  │ Vertex AI   │                  │ Vertex AI   │
  └─────┬───────┘                  └─────┬───────┘
        │ full MCP tool surface          │ verification-only (get_doc)
        │ (8 tools)                      │
        ▼                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│           LOCAL ELASTIC SIMULATOR (in-process)                        │
│  Implements Elastic-compatible search/get_document/count/semantic     │
│  Queries synthetic JSON dataset (~3,900 documents)                    │
│  Same interface as real elastic/mcp-server-elasticsearch              │
└──────┬───────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│        SYNTHETIC AML DATASET (6 indices, JSON files)                  │
│  argus-transactions (2500) · argus-entities (500)                     │
│  argus-adverse-media (500) · argus-sanctions (200)                    │
│  argus-prior-alerts (200) · argus-typology-playbooks (5)              │
│  Golden cases: GC-001 (shell-company) · GC-004 (false positive)       │
└──────────────────────────────────────────────────────────────────────┘
```

## Investigator Tool Surface (8 tools)

| Tool | Description | Size Cap |
|------|-------------|----------|
| `search` | Full Elastic DSL search (BM25 + bool) | 50 results |
| `get_document` | Fetch single doc by index + ID | 1 |
| `entity_neighbors` | Graph traversal via beneficial ownership | 50 |
| `transaction_history` | Windowed tx history for an entity | 50 |
| `adverse_media_search` | Semantic search over adverse media | 10 |
| `sanctions_check` | Fuzzy match against OFAC/EU/UN lists | 10 |
| `similar_prior_alerts` | kNN on alert embeddings | 5 |
| `typology_playbook` | FinCEN/FATF expected-evidence checklist | 3 |

## Skeptic Tool Surface (restricted)

| Tool | Description | Constraint |
|------|-------------|-----------|
| `get_document` | Re-fetch cited documents only | Only indices in finding citations |
| `search` | Verification search | Size capped at 5 |
| `count` | Existence checks | — |

## Trust Boundaries

| Boundary | Enforcement | Prevents |
|----------|-------------|----------|
| Data → Agent | Read-only simulator, no write methods | Data mutation |
| Tools → Skeptic | Code: restricted tool subset + index allowlist | Fishing/fabrication |
| Finding → SAR | Pydantic: non-empty `evidence[]` (min_length=1) | Uncited claims |
| Investigator → Skeptic | Separate Gemini sessions/contexts | Self-review bypass |
| Loop runaway | Hard cap: `MAX_ITERATIONS=4` | Infinite spirals |
| Query injection | DSL validator blocks `script`, `_source`, size caps | Elastic injection |

## Data Flow

```
Alert ─→ Orchestrator ─→ Investigator (gather evidence via tools)
                              │
                              ▼
                         Gemini 2.5 Flash (analyze evidence, produce findings)
                              │
                              ▼
                         Skeptic (re-fetch citations, verify)
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              ACCEPT → SAR         REJECT → feedback loop
                                        │
                                        ▼
                                   Investigator (revise)
                                        │
                                        ▼
                                   Skeptic (re-verify)
                                        │
                                   (up to 4 iterations)
                                        │
                                        ▼
                                   Case finalized
                                   SAR draft generated
```

1. Alert enters from queue (pre-seeded demo alerts)
2. Orchestrator creates Case, invokes Investigator
3. Investigator executes 8+ tool calls to gather evidence from all 6 indices
4. Evidence is formatted and sent to Gemini for analysis → structured Findings
5. For each Finding, Skeptic re-fetches cited documents and asks Gemini to verify
6. On REJECT: feedback with reasons → Investigator revises with new evidence
7. On ACCEPT: Finding promoted to final case
8. After convergence: SAR Markdown report assembled, Case persisted

## Deployment

| Component | Platform | URL |
|-----------|----------|-----|
| Backend | Cloud Run (1Gi, 300s timeout) | https://argus-backend-794755514339.us-central1.run.app |
| Frontend | Cloud Run (512Mi) | https://argus-frontend-794755514339.us-central1.run.app |
| Model | Vertex AI (Gemini 2.5 Flash) | us-central1 |
| Project | GCP | valiant-surfer-497305-j8 |

## Portability

The Investigator–Skeptic pattern ports to any analyst-triage workflow:
- **SOC alert triage** — swap indices for security events + threat intel
- **SRE incident investigation** — swap for logs/metrics + runbook corpus
- **Real Elastic Cloud** — set `ELASTIC_URL` + `ELASTIC_API_KEY` env vars to connect

See [docs/portability.md](docs/portability.md) for the full mapping.
