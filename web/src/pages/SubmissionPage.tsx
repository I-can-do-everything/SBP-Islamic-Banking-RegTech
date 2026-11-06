import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle, Loader2, OctagonX } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router";
import { AuditView } from "../components/AuditView";
import { BreakdownView } from "../components/BreakdownView";
import { ResultsView } from "../components/ResultsView";
import { Transformation } from "../components/Transformation";
import { api } from "../lib/api";
import { dateLabel, shortHash } from "../lib/format";

interface ProgressEvent { id: number; stage: string; status: string; message: string; data: Record<string, unknown> }

const STAGES = [
  { key: "upload", label: "Received" },
  { key: "ingest", label: "Transformed" },
  { key: "calculate", label: "Calculated" },
  { key: "narrate", label: "Explained" },
];

const TABS = [
  { key: "transform", label: "Transformation" },
  { key: "results", label: "Results" },
  { key: "breakdown", label: "AI breakdown" },
  { key: "audit", label: "Audit trail" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function useProgress(id: string) {
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const client = useQueryClient();
  useEffect(() => {
    let source: EventSource | null = null;
    let closed = false;
    setEvents([]);
    api.eventsUrl(id).then((url) => {
      if (closed) return;
      source = new EventSource(url);
      source.addEventListener("progress", (e) => {
        const ev = JSON.parse((e as MessageEvent).data) as ProgressEvent;
        setEvents((prev) => (prev.some((p) => p.id === ev.id) ? prev : [...prev, ev]));
        if (ev.status === "done" || ev.status === "error") {
          client.invalidateQueries({ queryKey: ["submission", id] });
        }
      });
      source.addEventListener("end", () => source?.close());
    });
    return () => {
      closed = true;
      source?.close();
    };
  }, [id, client]);
  return events;
}

export function SubmissionPage() {
  const { id = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const events = useProgress(id);
  const submission = useQuery({ queryKey: ["submission", id, "meta"], queryFn: () => api.submission(id), refetchInterval: (q) => (q.state.data?.status === "READY" || q.state.data?.status === "FAILED" ? false : 2000) });
  const s = submission.data;
  const ingested = s && ["INGESTED", "PROCESSING", "READY"].includes(s.status);
  const ready = s?.status === "READY";
  const defaultTab: TabKey = ready ? "results" : "transform";
  const tab = (params.get("tab") as TabKey) || defaultTab;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-faint">Submission</p>
          <h1 className="text-2xl font-semibold tracking-tight">{s?.institution ?? "Loading…"}</h1>
          <p className="mt-1 text-sm text-muted">
            {s?.period_end ? `Period ended ${dateLabel(s.period_end)}` : "Reading the reporting date…"}
            {s?.filename && <> · <span className="font-mono text-xs">{s.filename}</span></>}
            {s?.sha256 && <> · <span className="font-mono text-xs" title={s.sha256}>sha256 {shortHash(s.sha256, 12)}</span></>}
          </p>
        </div>
        <Stepper events={events} failed={s?.status === "FAILED"} />
      </div>

      {s?.status === "FAILED" && (
        <div role="alert" className="mt-6 rounded-lg border border-fail/30 bg-fail-soft p-4 text-sm text-fail">
          <strong>Processing stopped at the {s.error?.stage} step.</strong> {s.error?.message}
        </div>
      )}

      <Timeline events={events} />

      <div className="mt-8 border-b border-line" role="tablist" aria-label="Submission sections">
        <div className="flex gap-1 overflow-x-auto">
          {TABS.map((t) => {
            const disabled = (t.key === "transform" && !ingested) || (t.key !== "transform" && t.key !== "audit" && !ready);
            const active = tab === t.key;
            return (
              <button
                key={t.key}
                role="tab"
                aria-selected={active}
                disabled={disabled}
                onClick={() => setParams({ tab: t.key }, { replace: true })}
                className={`whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition ${active ? "border-brand text-ink" : "border-transparent text-muted hover:text-ink"} disabled:cursor-not-allowed disabled:opacity-40`}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-6">
        {tab === "transform" && ingested && <Transformation id={id} />}
        {tab === "results" && ready && <ResultsView id={id} />}
        {tab === "breakdown" && ready && <BreakdownView id={id} />}
        {tab === "audit" && <AuditView />}
        {!ingested && s?.status !== "FAILED" && (
          <div className="flex items-center gap-3 rounded-lg border border-line bg-panel p-6 text-sm text-muted">
            <Loader2 size={18} className="animate-spin text-brand" /> Reading the file. The transformation will appear here in a few seconds.
          </div>
        )}
      </div>
    </div>
  );
}

function Stepper({ events, failed }: { events: ProgressEvent[]; failed: boolean }) {
  return (
    <ol className="flex items-center gap-2" aria-label="Pipeline progress">
      {STAGES.map((stage, i) => {
        const evs = events.filter((e) => e.stage === stage.key);
        const done = evs.some((e) => e.status === "done");
        const error = evs.some((e) => e.status === "error");
        const running = !done && !error && evs.some((e) => e.status === "running");
        return (
          <li key={stage.key} className="flex items-center gap-2">
            {i > 0 && <span className={`h-px w-6 ${done ? "bg-brand" : "bg-line"}`} aria-hidden />}
            <span className={`flex items-center gap-1.5 text-xs font-medium ${done ? "text-brand" : error ? "text-fail" : running ? "text-ink" : "text-faint"}`}>
              {done ? <CheckCircle2 size={16} /> : error || (failed && running) ? <OctagonX size={16} /> : running ? <Loader2 size={16} className="animate-spin" /> : <Circle size={16} />}
              {stage.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function Timeline({ events }: { events: ProgressEvent[] }) {
  if (!events.length) return null;
  const last = events[events.length - 1];
  return (
    <details className="mt-6 rounded-lg border border-line bg-panel">
      <summary className="cursor-pointer px-4 py-3 text-sm">
        <span className="text-faint">Latest: </span>
        <span className="text-ink">{last.message}</span>
      </summary>
      <ol className="space-y-1.5 border-t border-line px-4 py-3 text-sm">
        {events.map((e) => (
          <li key={e.id} className="flex gap-3">
            <span className="w-20 shrink-0 text-xs uppercase tracking-wide text-faint">{e.stage}</span>
            <span className={e.status === "error" ? "text-fail" : "text-muted"}>{e.message}</span>
          </li>
        ))}
      </ol>
    </details>
  );
}
