"use client";

import type { Alert, Case, Finding } from "@/app/page";

interface InvestigationWorkspaceProps {
  alert: Alert | null;
  activeCase: Case | null;
  isInvestigating: boolean;
  error?: string | null;
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: "bg-red-500/20 text-red-300 border-red-500/40",
    high: "bg-orange-500/20 text-orange-300 border-orange-500/40",
    med: "bg-amber-500/20 text-amber-300 border-amber-500/40",
    low: "bg-blue-500/20 text-blue-300 border-blue-500/40",
    info: "bg-gray-500/20 text-gray-300 border-gray-500/40",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded border ${
        colors[severity] || colors.info
      }`}
    >
      {severity}
    </span>
  );
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const colors: Record<string, string> = {
    accepted: "bg-green-500/20 text-green-300",
    rejected: "bg-red-500/20 text-red-300",
    unverified: "bg-amber-500/20 text-amber-300",
  };
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded ${
        colors[verdict] || "bg-gray-500/20 text-gray-300"
      }`}
    >
      {verdict}
    </span>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--card-border)] rounded-lg p-4 mb-3">
      <div className="flex items-center gap-2 mb-2">
        <SeverityBadge severity={finding.severity} />
        <VerdictBadge verdict={finding.skeptic_verdict} />
        <span className="text-xs text-[var(--muted)]">
          iter {finding.iteration}
        </span>
      </div>
      <h3 className="text-sm font-semibold mb-2">{finding.title}</h3>
      <p className="text-xs text-[var(--muted)] leading-relaxed mb-3">
        {finding.narrative}
      </p>
      <div className="flex flex-wrap gap-1">
        {finding.typology_tags.map((tag) => (
          <span
            key={tag}
            className="text-[10px] px-2 py-0.5 bg-[var(--accent-muted)]/20 text-[var(--accent)] rounded"
          >
            {tag}
          </span>
        ))}
      </div>
      {/* Citation chips */}
      <div className="mt-3 flex flex-wrap gap-1">
        {finding.evidence.map((cit, i) => (
          <span
            key={i}
            className="text-[10px] px-2 py-0.5 bg-white/5 border border-white/10 rounded font-mono cursor-pointer hover:bg-white/10 transition-colors"
            title={`${cit.index}/${cit.doc_id}\n${cit.excerpt || ""}`}
          >
            [{i + 1}] {cit.index.replace("argus-", "")}
          </span>
        ))}
      </div>
    </div>
  );
}

export function InvestigationWorkspace({
  alert,
  activeCase,
  isInvestigating,
  error,
}: InvestigationWorkspaceProps) {
  if (!alert) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">🔍</div>
          <h2 className="text-lg font-semibold mb-2">Argus AML Agent</h2>
          <p className="text-sm text-[var(--muted)] max-w-sm">
            Select an alert from the queue to begin an investigation. The
            Investigator–Skeptic dual-agent loop will analyze the transaction and
            produce a citation-grounded SAR draft.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Alert Header */}
      <div className="p-4 border-b border-[var(--card-border)] bg-[var(--card)]">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold">
              Investigation: {alert.alert_id}
            </h2>
            <p className="text-xs text-[var(--muted)] mt-0.5">
              {alert.originator} → {alert.beneficiary}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-mono">
              ${alert.amount.toLocaleString()} {alert.currency}
            </span>
            {activeCase?.verdict && (
              <span
                className={`text-xs font-bold px-3 py-1 rounded ${
                  activeCase.verdict === "clear"
                    ? "bg-green-500/20 text-green-300"
                    : "bg-red-500/20 text-red-300"
                }`}
              >
                {activeCase.verdict === "clear"
                  ? "✓ CLEARED"
                  : "⚠ ESCALATE"}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Investigation Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {isInvestigating && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="relative w-16 h-16 mx-auto mb-6">
                <div className="absolute inset-0 border-4 border-[var(--accent)]/20 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-transparent border-t-[var(--accent)] rounded-full animate-spin"></div>
              </div>
              <p className="text-sm font-medium mb-2">
                Investigator–Skeptic loop running...
              </p>
              <div className="text-xs text-[var(--muted)] space-y-1.5 max-w-xs mx-auto">
                <p>⚡ Gathering evidence from 6 Elastic indices</p>
                <p>🔍 Gemini analyzing transaction patterns</p>
                <p>⚖️ Skeptic verifying citations</p>
                <p className="text-[var(--accent)] mt-3">This takes 30–90 seconds</p>
              </div>
            </div>
          </div>
        )}

        {error && !isInvestigating && (
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-sm font-medium text-red-300">Investigation Error</p>
            <p className="text-xs text-red-400 mt-1">{error}</p>
          </div>
        )}

        {activeCase && !isInvestigating && (
          <div>
            {/* Summary */}
            <div className="mb-4 p-3 bg-[var(--card)] border border-[var(--card-border)] rounded-lg">
              <div className="grid grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-lg font-bold">
                    {activeCase.findings.length}
                  </div>
                  <div className="text-[10px] text-[var(--muted)] uppercase">
                    Findings
                  </div>
                </div>
                <div>
                  <div className="text-lg font-bold">
                    {
                      activeCase.findings.filter(
                        (f) => f.skeptic_verdict === "accepted"
                      ).length
                    }
                  </div>
                  <div className="text-[10px] text-[var(--muted)] uppercase">
                    Accepted
                  </div>
                </div>
                <div>
                  <div className="text-lg font-bold">
                    {activeCase.iteration_count}
                  </div>
                  <div className="text-[10px] text-[var(--muted)] uppercase">
                    Iterations
                  </div>
                </div>
                <div>
                  <div className="text-lg font-bold text-[var(--accent)]">
                    {activeCase.investigator_model.split("-").slice(-1)}
                  </div>
                  <div className="text-[10px] text-[var(--muted)] uppercase">
                    Model
                  </div>
                </div>
              </div>
            </div>

            {/* Findings */}
            <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-3">
              Findings
            </h3>
            {activeCase.findings.map((finding) => (
              <FindingCard key={finding.finding_id} finding={finding} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
