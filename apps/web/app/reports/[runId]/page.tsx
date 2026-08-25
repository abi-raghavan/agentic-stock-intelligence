"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getReport, ReportResponse, submitDecision } from "@/lib/api";

export default function ReportPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [decisionMessage, setDecisionMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const data = await getReport(runId);
        if (active) {
          setReport(data);
          setLoading(false);
        }
      } catch {
        if (active) setTimeout(poll, 1500);
      }
    };
    poll();
    return () => {
      active = false;
    };
  }, [runId]);

  async function handleDecision(action: "approve" | "reject" | "rerun") {
    try {
      const result = await submitDecision(runId, action);
      setDecisionMessage(`Report marked as ${result.status}.`);
      setReport((prev) => (prev ? { ...prev, status: result.status } : prev));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed");
    }
  }

  if (loading) {
    return <div className="card">Generating report...</div>;
  }

  if (!report) {
    return <div className="card text-[var(--danger)]">{error || "Report unavailable"}</div>;
  }

  const data = report.report;

  return (
    <div className="space-y-6">
      <section className="card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-widest text-[var(--muted)]">Intelligence Report</p>
            <h1 className="mt-2 text-3xl font-semibold">{data.title}</h1>
            <p className="mt-2 text-[var(--muted)]">Outlook: {data.outlook}</p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <Metric label="Opportunity" value={`${data.opportunity_score}/10`} tone="success" />
            <Metric label="Risk" value={`${data.risk_score}/10`} tone="danger" />
            <Metric label="Confidence" value={data.confidence} tone="accent" />
          </div>
        </div>
        <p className="mt-6 leading-7 text-[var(--muted)]">{data.executive_summary}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button className="btn-primary" onClick={() => handleDecision("approve")}>
            Approve
          </button>
          <button className="btn-secondary" onClick={() => handleDecision("reject")}>
            Reject
          </button>
          <button className="btn-secondary" onClick={() => handleDecision("rerun")}>
            Re-run analysis
          </button>
          <span className="self-center text-sm text-[var(--muted)]">Status: {report.status}</span>
        </div>
        {decisionMessage && <p className="mt-3 text-sm text-[var(--success)]">{decisionMessage}</p>}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="text-lg font-medium">Bullish signals</h2>
          <ul className="mt-4 space-y-2 text-sm">
            {data.bullish_signals.map((item) => (
              <li key={item} className="rounded-lg bg-[var(--success)]/10 p-3">
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h2 className="text-lg font-medium">Bearish signals</h2>
          <ul className="mt-4 space-y-2 text-sm">
            {data.bearish_signals.map((item) => (
              <li key={item} className="rounded-lg bg-[var(--danger)]/10 p-3">
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="card">
        <h2 className="text-lg font-medium">Price trend</h2>
        <div className="mt-4 h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.market_chart}>
              <XAxis dataKey="date" hide />
              <YAxis domain={["auto", "auto"]} stroke="#8ea0bf" />
              <Tooltip />
              <Line type="monotone" dataKey="close" stroke="#4f8cff" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="card">
        <h2 className="text-lg font-medium">Top evidence</h2>
        <div className="mt-4 space-y-4">
          {data.top_evidence.map((item) => (
            <details key={item.doc_id} className="rounded-lg border border-white/10 bg-white/5 p-4">
              <summary className="cursor-pointer font-medium">
                [{item.citation_id}] {item.source} · fused {item.fused_score?.toFixed(4) ?? "n/a"}
              </summary>
              <p className="mt-3 text-sm text-[var(--muted)]">{item.snippet}</p>
              <div className="mt-3 flex flex-wrap gap-3 text-xs text-[var(--muted)]">
                <span>BM25: {item.bm25_score?.toFixed(3) ?? "n/a"}</span>
                <span>Vector: {item.vector_score?.toFixed(3) ?? "n/a"}</span>
                <span>Type: {item.source_type}</span>
                <span>Date: {item.document_date || "unknown"}</span>
              </div>
            </details>
          ))}
        </div>
      </section>

      <section className="card">
        <h2 className="text-lg font-medium">Recommended actions</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-[var(--muted)]">
          {data.recommended_actions.map((action) => (
            <li key={action}>{action}</li>
          ))}
        </ul>
        <h3 className="mt-6 text-sm font-medium uppercase tracking-widest text-[var(--muted)]">Sources</h3>
        <ul className="mt-3 space-y-2 text-sm">
          {data.sources.map((source) => (
            <li key={source}>{source}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone: "success" | "danger" | "accent" }) {
  const toneClass =
    tone === "success" ? "text-[var(--success)]" : tone === "danger" ? "text-[var(--danger)]" : "text-[var(--accent)]";
  return (
    <div className="rounded-lg bg-white/5 p-3">
      <div className="text-xs uppercase tracking-widest text-[var(--muted)]">{label}</div>
      <div className={`mt-1 text-lg font-semibold capitalize ${toneClass}`}>{value}</div>
    </div>
  );
}
