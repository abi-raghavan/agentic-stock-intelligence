"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startAnalysis } from "@/lib/api";

export default function AnalyzePage() {
  const router = useRouter();
  const [ticker, setTicker] = useState("Tata Motors");
  const [question, setQuestion] = useState("Should I be worried about Tata Motors over the next 30 days?");
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
          Enter an Indian or US ticker, or company name. Live data from Yahoo Finance and Google News.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label className="mb-2 block text-sm">Stock / Ticker</label>
            <input
              className="input"
              placeholder="Tata Motors, TATAMOTORS.NS, NVDA, Reliance"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
            />
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
        <h2 className="text-lg font-medium">Examples</h2>
        <ul className="mt-4 space-y-2 text-sm text-[var(--muted)]">
          <li>Tata Motors · Reliance · TCS · INFY</li>
          <li>TATAMOTORS.NS · RELIANCE.NS (NSE)</li>
          <li>NVDA · AAPL (US)</li>
        </ul>
      </aside>
    </div>
  );
}
