# Portability: AML → SOC → SRE

## Architectural Generality

The Investigator–Skeptic + structural-citation-gate pattern is not AML-specific. It ports line-for-line to any analyst-triage workflow whose bottleneck is **evidence assembly across heterogeneous data**.

## Mapping Table

| Argus for AML | SOC Alert Triage | SRE Incident Investigation |
|---------------|------------------|---------------------------|
| Suspicious transaction alert | Security alert (EDR/SIEM) | Pager alert (logs/metrics) |
| `entity_neighbors` | `process_tree` + `network_neighbors` | Service-dependency-graph |
| `adverse_media_search` | Threat-intel/IOC corpus search | Postmortem/runbook search |
| `sanctions_check` | `ioc_lookup` (threat-intel feeds) | `cve_match` (vuln DB) |
| `typology_playbook` | MITRE ATT&CK playbooks | SRE runbook library |
| SAR draft + citations | Incident report + citations | Postmortem draft + citations |

## What Carries Over Unchanged

- Orchestrator loop (investigator → skeptic → feedback)
- Investigator/Skeptic asymmetric tool surfaces
- Pydantic `Finding` + `Citation` schemas
- Citation re-execution gate
- Iteration traces
- Architectural guardrails (read-only, index allowlist, DSL validator)

## What Changes Per Domain

- Index names and mappings
- Convenience tool wrappers
- System prompt content
- Ground-truth definitions

## SOC Port Sketch

### Indices

| Index | Description |
|-------|-------------|
| `argus-events` | Security events (Sysmon, EDR telemetry) |
| `argus-threat-intel` | IOC feeds, MITRE ATT&CK mappings |
| `argus-assets` | Asset inventory, network topology |
| `argus-alerts-history` | Historical alert dispositions |
| `argus-playbooks` | MITRE ATT&CK response playbooks |

### Convenience Tools

- `process_tree(pid, host)` — process parent/child relationships
- `network_neighbors(ip, timerange)` — connection graph
- `ioc_lookup(indicator, type)` — check against threat-intel
- `mitre_playbook(technique_id)` — get response checklist

## SRE Port Sketch

### Indices

| Index | Description |
|-------|-------------|
| `argus-logs` | Application and infrastructure logs |
| `argus-metrics` | Time-series metrics (golden signals) |
| `argus-traces` | Distributed traces |
| `argus-runbooks` | SRE runbook library |
| `argus-postmortems` | Historical incident postmortems |

### Convenience Tools

- `service_dependencies(service_name)` — dependency graph
- `log_search(service, timerange, level)` — filtered log retrieval
- `metric_anomalies(service, metric, timerange)` — anomaly detection
- `cve_match(package, version)` — vulnerability lookup
- `similar_incidents(description, k)` — kNN on postmortems

## Why This Matters

AML compliance is slow to procure. SOC and SRE are higher-velocity adoption paths that share Elastic's customer base. The architecture as a portable pattern keeps both adjacencies open.
