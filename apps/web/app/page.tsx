"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startAnalysis } from "@/lib/api";

export default function AnalyzePage() {
  const router = useRouter();
  const [ticker, setTicker] = useState("NVDA");
  const [question, setQuestion] = useState("Should I be worried about NVIDIA over the next 30 days?");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await startAnalysis(ticker, question);
      router.push(`/runs/${result.run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start analysis");
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
      <section className="card">
        <p className="text-sm uppercase tracking-widest text-[var(--muted)]">Analyze Stock</p>
        <h1 className="mt-2 text-3xl font-semibold">Evidence-backed intelligence reports</h1>
        <p className="mt-3 max-w-2xl text-[var(--muted)]">
          Enter a ticker and question. The multi-agent system will plan research, retrieve evidence, assess risk,
          verify claims, and generate a source-backed report.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label className="mb-2 block text-sm">Ticker</label>
            <input className="input" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
          </div>
          <div>
            <label className="mb-2 block text-sm">Question</label>
            <textarea
              className="input min-h-28"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
          <button className="btn-primary" disabled={loading}>
            {loading ? "Starting analysis..." : "Analyze"}
          </button>
        </form>
      </section>

      <aside className="card">
        <h2 className="text-lg font-medium">Demo query</h2>
        <p className="mt-3 text-sm text-[var(--muted)]">
          Try NVIDIA with a risk-focused question to watch planner, research, hybrid RAG retrieval, risk synthesis,
          verification, and final report generation.
        </p>
        <ul className="mt-6 space-y-3 text-sm">
          <li className="rounded-lg bg-white/5 p-3">Live news via Yahoo Finance + Google News RSS</li>
          <li className="rounded-lg bg-white/5 p-3">Live market data and fundamentals via yfinance</li>
          <li className="rounded-lg bg-white/5 p-3">Hybrid BM25 + vector retrieval with RRF fusion</li>
          <li className="rounded-lg bg-white/5 p-3">Citation-tracked claims and verification loop</li>
          <li className="rounded-lg bg-white/5 p-3">Human-in-the-loop approve / reject / re-run</li>
        </ul>
      </aside>
    </div>
  );
}
