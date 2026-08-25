const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type AnalyzeResponse = { run_id: string; status: string };

export type AgentStepEvent = {
  run_id: string;
  step: string;
  status: "started" | "completed" | "failed";
  message?: string;
};

export type EvidenceItem = {
  doc_id: string;
  source: string;
  source_type: string;
  document_date?: string | null;
  snippet: string;
  bm25_score?: number | null;
  vector_score?: number | null;
  fused_score?: number | null;
  citation_id: string;
};

export type ReportOutput = {
  title: string;
  outlook: string;
  executive_summary: string;
  bullish_signals: string[];
  bearish_signals: string[];
  opportunity_score: number;
  risk_score: number;
  confidence: string;
  top_evidence: EvidenceItem[];
  recommended_actions: string[];
  sources: string[];
  verification_passed: boolean;
  market_chart: Array<{ date: string; close: number }>;
};

export type ReportResponse = {
  id: string;
  run_id: string;
  status: string;
  report: ReportOutput;
  opportunity_score?: number;
  risk_score?: number;
  confidence?: string;
};

export async function startAnalysis(ticker: string, question: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker, question }),
  });
  if (!res.ok) throw new Error("Failed to start analysis");
  return res.json();
}

export async function getReport(runId: string): Promise<ReportResponse> {
  const res = await fetch(`${API_URL}/reports/${runId}`);
  if (!res.ok) throw new Error("Report not ready");
  return res.json();
}

export async function submitDecision(runId: string, action: "approve" | "reject" | "rerun", notes?: string) {
  const res = await fetch(`${API_URL}/reports/${runId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, notes }),
  });
  if (!res.ok) throw new Error("Failed to submit decision");
  return res.json();
}

export function streamRun(runId: string, onEvent: (event: AgentStepEvent) => void): EventSource {
  const source = new EventSource(`${API_URL}/runs/${runId}/stream`);
  source.addEventListener("agent_step", (message) => {
    const data = JSON.parse((message as MessageEvent).data) as AgentStepEvent;
    onEvent(data);
  });
  return source;
}

export function getApiUrl() {
  return API_URL;
}
