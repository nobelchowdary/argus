"use client";

import type { Case, TraceEntry } from "@/app/page";

interface RightPanelProps {
  activeCase: Case | null;
  traces: TraceEntry[];
  activeTab: "sar" | "trace";
  onTabChange: (tab: "sar" | "trace") => void;
}

function ReasoningTrace({ traces }: { traces: TraceEntry[] }) {
  if (traces.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-[var(--muted)]">
          Run an investigation to see the reasoning trace.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      {traces.map((trace, i) => (
        <div
          key={i}
          className="border border-[var(--card-border)] rounded-lg p-3"
        >
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                trace.phase === "investigator_draft"
                  ? "bg-blue-500/20 text-blue-300"
                  : trace.phase === "skeptic_verdict"
                  ? "bg-purple-500/20 text-purple-300"
                  : trace.phase === "investigator_revision"
                  ? "bg-cyan-500/20 text-cyan-300"
                  : "bg-green-500/20 text-green-300"
              }`}
            >
              {trace.phase.replace(/_/g, " ")}
            </span>
            <span className="text-[10px] text-[var(--muted)]">
              iter {trace.iteration}
            </span>
            <span className="text-[10px] text-[var(--muted)] ml-auto">
              {new Date(trace.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <pre className="text-[11px] text-[var(--muted)] whitespace-pre-wrap overflow-hidden max-h-40 leading-relaxed">
            {JSON.stringify(trace.content, null, 2).slice(0, 500)}
            {JSON.stringify(trace.content, null, 2).length > 500 && "..."}
          </pre>
        </div>
      ))}
    </div>
  );
}

function SarDraftPane({ sarDraft }: { sarDraft: string }) {
  if (!sarDraft) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-sm text-[var(--muted)]">
          SAR draft will appear after investigation completes.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <div className="prose prose-sm prose-invert max-w-none">
        {sarDraft.split("\n").map((line, i) => {
          if (line.startsWith("# "))
            return (
              <h1 key={i} className="text-lg font-bold mt-4 mb-2">
                {line.slice(2)}
              </h1>
            );
          if (line.startsWith("## "))
            return (
              <h2 key={i} className="text-sm font-semibold mt-4 mb-2 text-[var(--accent)]">
                {line.slice(3)}
              </h2>
            );
          if (line.startsWith("### "))
            return (
              <h3 key={i} className="text-sm font-medium mt-3 mb-1">
                {line.slice(4)}
              </h3>
            );
          if (line.startsWith("- "))
            return (
              <li key={i} className="text-xs text-[var(--muted)] ml-4 list-disc">
                {line.slice(2)}
              </li>
            );
          if (line.startsWith("> "))
            return (
              <blockquote
                key={i}
                className="text-xs border-l-2 border-amber-500 pl-3 text-amber-300/80 my-2"
              >
                {line.slice(2)}
              </blockquote>
            );
          if (line.startsWith("---"))
            return <hr key={i} className="border-[var(--card-border)] my-4" />;
          if (line.trim() === "") return <br key={i} />;
          return (
            <p key={i} className="text-xs text-[var(--muted)] leading-relaxed">
              {line}
            </p>
          );
        })}
      </div>
    </div>
  );
}

export function RightPanel({
  activeCase,
  traces,
  activeTab,
  onTabChange,
}: RightPanelProps) {
  return (
    <div className="flex flex-col h-full">
      {/* Tab switcher */}
      <div className="flex border-b border-[var(--card-border)]">
        <button
          onClick={() => onTabChange("trace")}
          className={`flex-1 py-3 text-xs font-medium uppercase tracking-wider transition-colors ${
            activeTab === "trace"
              ? "text-[var(--accent)] border-b-2 border-[var(--accent)]"
              : "text-[var(--muted)] hover:text-white"
          }`}
        >
          Reasoning Trace
        </button>
        <button
          onClick={() => onTabChange("sar")}
          className={`flex-1 py-3 text-xs font-medium uppercase tracking-wider transition-colors ${
            activeTab === "sar"
              ? "text-[var(--accent)] border-b-2 border-[var(--accent)]"
              : "text-[var(--muted)] hover:text-white"
          }`}
        >
          SAR Draft
        </button>
      </div>

      {/* Content */}
      {activeTab === "trace" ? (
        <ReasoningTrace traces={traces} />
      ) : (
        <SarDraftPane sarDraft={activeCase?.sar_draft || ""} />
      )}
    </div>
  );
}
