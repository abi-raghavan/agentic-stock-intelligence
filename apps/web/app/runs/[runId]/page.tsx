"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AgentStepEvent, getReport, streamRun } from "@/lib/api";

const STEPS = ["planning", "research", "retrieval", "risk", "verification", "report"];

export default function LiveRunPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const [events, setEvents] = useState<AgentStepEvent[]>([]);
  const [done, setDone] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const source = streamRun(runId, (event) => {
      setEvents((prev) => [...prev, event]);
      if (event.step === "done") setDone(true);
      if (event.step === "error") setFailed(true);
    });
    return () => source.close();
  }, [runId]);

  useEffect(() => {
    if (!done || failed) return;
    getReport(runId).catch(() => undefined);
  }, [done, failed, runId]);

  const stepStatus = useMemo(() => {
    const map: Record<string, "pending" | "running" | "done" | "failed"> = {};
    for (const step of STEPS) map[step] = "pending";
    for (const event of events) {
      if (!STEPS.includes(event.step)) continue;
      if (event.status === "started") map[event.step] = "running";
      if (event.status === "completed") map[event.step] = "done";
      if (event.status === "failed") map[event.step] = "failed";
    }
    return map;
  }, [events]);

  return (
    <div className="space-y-6">
      <div className="card">
        <p className="text-sm uppercase tracking-widest text-[var(--muted)]">Live Agent Execution</p>
        <h1 className="mt-2 text-2xl font-semibold">Run {runId.slice(0, 8)}...</h1>
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {STEPS.map((step) => (
            <div key={step} className="rounded-lg border border-white/10 bg-white/5 p-4">
              <div className="flex items-center justify-between">
                <span className="capitalize">{step}</span>
                <span
                  className={`badge ${
                    stepStatus[step] === "done"
                      ? "bg-[var(--success)]/20 text-[var(--success)]"
                      : stepStatus[step] === "running"
                        ? "bg-[var(--accent)]/20 text-[var(--accent)]"
                        : stepStatus[step] === "failed"
                          ? "bg-[var(--danger)]/20 text-[var(--danger)]"
                          : "bg-white/10 text-[var(--muted)]"
                  }`}
                >
                  {stepStatus[step]}
                </span>
              </div>
            </div>
          ))}
        </div>
        {done && !failed && (
          <div className="mt-6">
            <Link href={`/reports/${runId}`} className="btn-primary">
              View Intelligence Report
            </Link>
          </div>
        )}
        {failed && <p className="mt-4 text-sm text-[var(--danger)]">Run failed. Check API logs for details.</p>}
      </div>

      <div className="card">
        <h2 className="text-lg font-medium">Execution timeline</h2>
        <div className="mt-4 space-y-3">
          {events.map((event, idx) => (
            <div key={`${event.step}-${idx}`} className="rounded-lg bg-white/5 p-3 text-sm">
              <div className="font-medium capitalize">
                {event.step} · {event.status}
              </div>
              {event.message && <div className="mt-1 text-[var(--muted)]">{event.message}</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
