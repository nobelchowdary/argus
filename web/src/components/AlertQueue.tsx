"use client";

import { useEffect, useState } from "react";
import type { Alert } from "@/app/page";

interface AlertQueueProps {
  onSelectAlert: (alert: Alert) => void;
  selectedAlertId?: string;
}

// Hardcoded demo alerts for when backend is unavailable
const FALLBACK_ALERTS: Alert[] = [
  {
    alert_id: "GC-001",
    transaction_id: "TXN-2026-04-15-98500",
    originator: "Acme Logistics LLC (Delaware, US)",
    beneficiary: "Verde Holdings Ltd (BVI)",
    amount: 98500.0,
    currency: "USD",
    channel: "wire",
    country_pair: "US-VG",
    memo: "Consulting services Q1 2026",
    timestamp: "2026-04-15T14:23:00Z",
    risk_score: 0.87,
    status: "pending",
  },
  {
    alert_id: "GC-004",
    transaction_id: "TXN-2026-04-20-250000",
    originator: "Northern Industrial Corp (Ontario, CA)",
    beneficiary: "Shenzhen MegaTech Electronics Co Ltd (CN)",
    amount: 250000.0,
    currency: "USD",
    channel: "wire",
    country_pair: "CA-CN",
    memo: "PO-2026-1847 - Electronic components batch shipment",
    timestamp: "2026-04-20T09:45:00Z",
    risk_score: 0.62,
    status: "pending",
  },
  {
    alert_id: "ALERT-003",
    transaction_id: "TXN-2026-04-22-45000",
    originator: "Bright Star Trading FZE (Dubai, AE)",
    beneficiary: "Pacific Rim Exports Inc (Panama, PA)",
    amount: 45000.0,
    currency: "USD",
    channel: "wire",
    country_pair: "AE-PA",
    memo: "Trade finance - textiles",
    timestamp: "2026-04-22T11:30:00Z",
    risk_score: 0.74,
    status: "pending",
  },
  {
    alert_id: "ALERT-004",
    transaction_id: "TXN-2026-04-25-12500",
    originator: "Johannesburg Capital Partners (ZA)",
    beneficiary: "Malta Investment Services Ltd (MT)",
    amount: 12500.0,
    currency: "EUR",
    channel: "wire",
    country_pair: "ZA-MT",
    memo: "Investment advisory fees",
    timestamp: "2026-04-25T16:15:00Z",
    risk_score: 0.55,
    status: "pending",
  },
];

function getRiskColor(score: number): string {
  if (score >= 0.8) return "text-red-400";
  if (score >= 0.6) return "text-amber-400";
  return "text-green-400";
}

function getRiskBg(score: number): string {
  if (score >= 0.8) return "bg-red-500/10 border-red-500/30";
  if (score >= 0.6) return "bg-amber-500/10 border-amber-500/30";
  return "bg-green-500/10 border-green-500/30";
}

export function AlertQueue({ onSelectAlert, selectedAlertId }: AlertQueueProps) {
  const [alerts, setAlerts] = useState<Alert[]>(FALLBACK_ALERTS);

  useEffect(() => {
    fetch("/api/invoke")
      .then((res) => res.json())
      .then((data) => {
        if (data.alerts && data.alerts.length > 0) {
          setAlerts(data.alerts);
        }
      })
      .catch(() => {
        // Use fallback alerts
      });
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-[var(--card-border)]">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-[var(--muted)]">
          Alert Queue
        </h2>
        <p className="text-xs text-[var(--muted)] mt-1">
          {alerts.length} pending alerts
        </p>
      </div>

      {/* Alert List */}
      <div className="flex-1 overflow-y-auto">
        {alerts.map((alert) => (
          <button
            key={alert.alert_id}
            onClick={() => onSelectAlert(alert)}
            className={`w-full text-left p-4 border-b border-[var(--card-border)] hover:bg-white/5 transition-colors ${
              selectedAlertId === alert.alert_id ? "bg-white/10" : ""
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-mono text-[var(--muted)]">
                {alert.alert_id}
              </span>
              <span
                className={`text-xs font-bold ${getRiskColor(alert.risk_score)}`}
              >
                {(alert.risk_score * 100).toFixed(0)}%
              </span>
            </div>
            <div className="text-sm font-medium truncate">
              {alert.originator.split("(")[0].trim()}
            </div>
            <div className="text-xs text-[var(--muted)] mt-0.5">
              → {alert.beneficiary.split("(")[0].trim()}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span
                className={`text-xs px-2 py-0.5 rounded border ${getRiskBg(
                  alert.risk_score
                )}`}
              >
                ${alert.amount.toLocaleString()}
              </span>
              <span className="text-xs text-[var(--muted)]">
                {alert.country_pair}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
