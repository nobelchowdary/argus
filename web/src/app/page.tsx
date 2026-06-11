"use client";

import { useState, useCallback } from "react";
import { AlertQueue } from "@/components/AlertQueue";
import { InvestigationWorkspace } from "@/components/InvestigationWorkspace";
import { RightPanel } from "@/components/RightPanel";

export interface Alert {
  alert_id: string;
  transaction_id: string;
  originator: string;
  beneficiary: string;
  amount: number;
  currency: string;
  channel: string;
  country_pair: string;
  memo: string;
  timestamp: string;
  risk_score: number;
  status: string;
}

export interface Citation {
  index: string;
  doc_id: string;
  field: string | null;
  excerpt: string | null;
  score: number | null;
}

export interface Finding {
  finding_id: string;
  case_id: string;
  title: string;
  severity: string;
  typology_tags: string[];
  narrative: string;
  claim_type: string;
  evidence: Citation[];
  related_entities: string[];
  iteration: number;
  skeptic_verdict: string;
}

export interface Case {
  case_id: string;
  alert: Alert;
  findings: Finding[];
  sar_draft: string;
  verdict: string | null;
  created_at: string;
  updated_at: string;
  iteration_count: number;
  investigator_model: string;
  skeptic_model: string;
}

export interface TraceEntry {
  case_id: string;
  finding_id: string;
  iteration: number;
  phase: string;
  content: Record<string, unknown>;
  timestamp: string;
}

export default function Home() {
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [activeCase, setActiveCase] = useState<Case | null>(null);
  const [traces, setTraces] = useState<TraceEntry[]>([]);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [rightTab, setRightTab] = useState<"sar" | "trace">("trace");
  const [error, setError] = useState<string | null>(null);

  const handleInvestigate = useCallback(async (alert: Alert) => {
    setSelectedAlert(alert);
    setIsInvestigating(true);
    setActiveCase(null);
    setTraces([]);
    setError(null);

    try {
      const res = await fetch("/api/invoke", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transaction_id: alert.transaction_id,
          originator: alert.originator,
          beneficiary: alert.beneficiary,
          amount: alert.amount,
          currency: alert.currency,
          channel: alert.channel,
          country_pair: alert.country_pair,
          memo: alert.memo,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || errData.error || "Investigation failed");
      }
      const caseData: Case = await res.json();
      setActiveCase(caseData);
      setRightTab("sar");

      // Fetch traces
      const traceRes = await fetch(`/api/invoke?case_id=${caseData.case_id}&traces=true`);
      if (traceRes.ok) {
        const traceData = await traceRes.json();
        setTraces(traceData.traces || []);
      }
    } catch (err) {
      console.error("Investigation error:", err);
      setError(err instanceof Error ? err.message : "Investigation failed");
    } finally {
      setIsInvestigating(false);
    }
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Left: Alert Queue */}
      <div className="w-80 border-r border-[var(--card-border)] flex flex-col">
        <AlertQueue
          onSelectAlert={handleInvestigate}
          selectedAlertId={selectedAlert?.alert_id}
        />
      </div>

      {/* Center: Investigation Workspace */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <InvestigationWorkspace
          alert={selectedAlert}
          activeCase={activeCase}
          isInvestigating={isInvestigating}
          error={error}
        />
      </div>

      {/* Right: SAR Draft + Reasoning Trace */}
      <div className="w-[480px] border-l border-[var(--card-border)] flex flex-col">
        <RightPanel
          activeCase={activeCase}
          traces={traces}
          activeTab={rightTab}
          onTabChange={setRightTab}
        />
      </div>
    </div>
  );
}
