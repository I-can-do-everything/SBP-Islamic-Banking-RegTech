import { useQuery } from "@tanstack/react-query";
import { ChevronRight, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Check, type Metric, type Status } from "../lib/api";
import { cell, metricValue, type AmountMode } from "../lib/format";
import { StatusBadge, StatusIcon, VerificationBadge } from "./Status";

const ORDER = ["Capital", "Asset quality", "Profit distribution", "Balance sheet"];

export function ResultsView({ id }: { id: string }) {
  const q = useQuery({ queryKey: ["submission", id, "results"], queryFn: () => api.results(id) });
  const [selected, setSelected] = useState<Metric | null>(null);
  const [mode, setMode] = useState<AmountMode>("compact");
  if (q.isLoading || !q.data) return <p className="text-sm text-muted">Loading results…</p>;
  const { metrics, checks } = q.data;
  const all = [...metrics.map((m) => m.status), ...checks.map((c) => c.status)];
  const count = (s: Status) => all.filter((x) => x === s).length;
  const groups = ORDER.map((cat) => ({ cat, items: metrics.filter((m) => m.category === cat) })).filter((g) => g.items.length);
  const checkGroups = Array.from(new Set(checks.map((c) => c.category)));

  return (
    <div className="space-y-8">
      <div className="grid gap-3 sm:grid-cols-3">
        <Summary status="FAIL" n={count("FAIL")} label="Breaches" />
        <Summary status="WARNING" n={count("WARNING")} label="Need attention" />
        <Summary status="PASS" n={count("PASS")} label="Within requirements" />
      </div>

      <div className="flex items-center justify-end gap-2 text-xs text-muted">
        Amounts
        <div className="inline-flex rounded-md border border-line p-0.5">
          {(["compact", "full"] as const).map((m) => (
            <button key={m} onClick={() => setMode(m)} className={`rounded px-2 py-1 ${mode === m ? "bg-brand-soft text-brand" : ""}`}>
              {m === "compact" ? "Millions / billions" : "Full figures"}
            </button>
          ))}
        </div>
      </div>

      {groups.map((g) => (
        <section key={g.cat}>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-faint">{g.cat}</h2>
          <ul className="mt-3 divide-y divide-line overflow-hidden rounded-xl border border-line bg-panel">
            {g.items.map((m) => (
              <li key={m.id}>
                <button
                  onClick={() => setSelected(m)}
                  className="grid w-full grid-cols-[1fr_auto] items-center gap-3 px-5 py-3 text-left hover:bg-surface md:grid-cols-[minmax(0,1fr)_200px_120px_20px]"
                  aria-label={`${m.label}: open evidence`}
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{m.label}</span>
                    {m.threshold && (
                      <span className="block text-xs text-muted">
                        {m.threshold.type === "min" ? "Minimum" : "Maximum"} {metricValue(m.threshold.value, m.unit)}
                        {m.threshold.with_buffer ? ` · ${metricValue(m.threshold.with_buffer, m.unit)} with the conservation buffer` : ""}
                        {m.threshold.kind ? ` (${m.threshold.kind})` : ""}
                      </span>
                    )}
                  </span>
                  <span className="num text-right text-lg font-semibold md:text-right">{metricValue(m.value, m.unit, mode)}</span>
                  <span className="hidden md:block"><StatusBadge status={m.status} /></span>
                  <ChevronRight size={16} className="hidden text-faint md:block" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        </section>
      ))}

      <section>
        <h2 className="text-sm font-semibold uppercase tracking-wider text-faint">Integrity, reconciliation and Shariah checks</h2>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {checkGroups.flatMap((cat) => checks.filter((c) => c.category === cat)).map((c) => <CheckCard key={c.id} c={c} />)}
        </div>
      </section>

      {selected && <LineageDrawer metric={selected} mode={mode} onClose={() => setSelected(null)} />}
    </div>
  );
}

function Summary({ status, n, label }: { status: Status; n: number; label: string }) {
  return (
    <div className="flex items-center gap-4 rounded-xl border border-line bg-panel p-4">
      <StatusIcon status={status} size={26} />
      <div>
        <p className="num text-2xl font-semibold">{n}</p>
        <p className="text-sm text-muted">{label}</p>
      </div>
    </div>
  );
}

function CheckCard({ c }: { c: Check }) {
  return (
    <div className="rounded-xl border border-line bg-panel p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-faint">{c.category}</p>
          <p className="font-medium">{c.label}</p>
        </div>
        <StatusBadge status={c.status} />
      </div>
      <p className="mt-2 text-sm leading-relaxed text-muted">{c.message}</p>
      {c.rules?.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-faint">
          {c.rules.map((r) => (
            <span key={r.rule_id} className="inline-flex items-center gap-1.5">
              {r.source?.verification !== "assumption" && r.source?.doc} <VerificationBadge value={r.source?.verification} />
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function LineageDrawer({ metric: m, mode, onClose }: { metric: Metric; mode: AmountMode; onClose: () => void }) {
  useEffect(() => {
    const key = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal="true" aria-label={`Evidence for ${m.label}`}>
      <button className="absolute inset-0 bg-ink/30" onClick={onClose} aria-label="Close evidence panel" />
      <aside className="relative h-full w-full max-w-2xl overflow-y-auto border-l border-line bg-panel p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-faint">{m.category} · evidence</p>
            <h2 className="mt-1 text-xl font-semibold">{m.label}</h2>
          </div>
          <button onClick={onClose} className="rounded-md p-1.5 text-muted hover:bg-brand-soft" aria-label="Close"><X size={18} /></button>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <span className="num text-3xl font-semibold">{metricValue(m.value, m.unit, mode)}</span>
          <StatusBadge status={m.status} />
        </div>

        <Block title="How it is calculated">
          <p className="rounded-md bg-surface px-3 py-2 font-mono text-sm">{m.formula}</p>
          {m.explanation && <p className="mt-2 text-sm leading-relaxed text-muted">{m.explanation}</p>}
        </Block>

        {m.inputs?.length > 0 && (
          <Block title="Inputs">
            <ul className="divide-y divide-line rounded-md border border-line text-sm">
              {m.inputs.map((i) => (
                <li key={i.label} className="flex items-center justify-between gap-4 px-3 py-2">
                  <span>{i.label}</span>
                  <span className="num font-medium">{metricValue(i.value, i.unit, mode)}</span>
                </li>
              ))}
            </ul>
          </Block>
        )}

        {m.rules?.length > 0 && (
          <Block title="Rules applied (as in force on the period end)">
            <ul className="space-y-3">
              {m.rules.map((r) => (
                <li key={r.rule_id} className="rounded-md border border-line p-3 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-medium">{r.title}</span>
                    <VerificationBadge value={r.source?.verification} />
                  </div>
                  {r.value && <p className="num mt-1 text-muted">Value: {r.value}{r.unit === "percent" ? "%" : ` ${r.unit}`} · in force from {r.effective_from}</p>}
                  <p className="mt-1 text-xs text-faint">{r.source?.doc}{r.source?.section ? `, ${r.source.section}` : ""} · <span className="font-mono">{r.rule_id}</span></p>
                </li>
              ))}
            </ul>
          </Block>
        )}

        {m.table && m.table.rows.length > 0 && (
          <Block title="Evidence">
            <div className="max-h-96 overflow-auto rounded-md border border-line">
              <table className="w-full whitespace-nowrap text-xs">
                <thead className="sticky top-0 bg-panel text-left text-faint">
                  <tr>{m.table.columns.map((c) => <th key={c} className="px-3 py-2 font-medium">{c}</th>)}</tr>
                </thead>
                <tbody className="num divide-y divide-line">
                  {m.table.rows.map((r, i) => (
                    <tr key={i}>{r.map((v, j) => <td key={j} className={`px-3 py-1.5 ${j > 0 ? "text-right" : ""}`}>{cell(v, m.table!.columns[j])}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Block>
        )}

        {m.notes?.length > 0 && (
          <Block title="Notes">
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted">{m.notes.map((n) => <li key={n}>{n}</li>)}</ul>
          </Block>
        )}
      </aside>
    </div>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-faint">{title}</h3>
      {children}
    </section>
  );
}
