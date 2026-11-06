import { useQuery } from "@tanstack/react-query";
import { BadgeCheck, BookOpen, ExternalLink, Loader2, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { api, type BreakdownPoint, type Excerpt, type Segment } from "../lib/api";
import { StatusIcon, VerificationBadge } from "./Status";

const KIND: Record<BreakdownPoint["kind"], { label: string; cls: string }> = {
  breach: { label: "Breach", cls: "border-l-fail" },
  concern: { label: "Attention", cls: "border-l-warn" },
  action: { label: "Next step", cls: "border-l-info" },
  strength: { label: "Strength", cls: "border-l-pass" },
};

export function BreakdownView({ id }: { id: string }) {
  const q = useQuery({
    queryKey: ["submission", id, "breakdown"],
    queryFn: () => api.breakdown(id),
    refetchInterval: (query) => (query.state.data?.grounding?.status === "pending" || query.state.data?.status === "pending" ? 4000 : false),
  });
  const [excerpt, setExcerpt] = useState<Excerpt | null>(null);
  const b = q.data;
  if (!b || b.status === "pending") return <p className="flex items-center gap-2 text-sm text-muted"><Loader2 size={16} className="animate-spin" /> Preparing the breakdown…</p>;
  const pendingAi = b.grounding?.status === "pending";
  const excerpts = new Map((b.excerpts ?? []).map((e) => [e.id, e]));

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {b.source === "ai" ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-soft px-2.5 py-1 font-medium text-brand"><Sparkles size={13} /> AI written · {b.model}</span>
          ) : (
            <span className="rounded-full bg-surface px-2.5 py-1 font-medium text-muted ring-1 ring-line">Deterministic summary</span>
          )}
          {pendingAi && <span className="inline-flex items-center gap-1.5 text-muted"><Loader2 size={13} className="animate-spin" /> The AI version is being written and checked; it will replace this summary.</span>}
        </div>
        <h2 className="mt-3 text-xl font-semibold leading-snug">{b.headline}</h2>
        <ul className="mt-5 space-y-3">
          {(b.points ?? []).map((p, i) => (
            <li key={i} className={`rounded-lg border border-line border-l-4 bg-panel p-4 ${KIND[p.kind].cls}`}>
              <div className="mb-1.5 flex items-center justify-between gap-2 text-xs">
                <span className="font-semibold uppercase tracking-wide text-faint">{KIND[p.kind].label}</span>
                {p.added_by === "daleel" && b.source === "ai" && <span className="text-faint">Added by Daleel: the AI did not cover this breach</span>}
              </div>
              <p className="leading-relaxed">{p.segments.map((s, j) => <Seg key={j} s={s} />)}</p>
              {p.source_ids.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {p.source_ids.map((sid) => {
                    const e = excerpts.get(sid);
                    return e ? (
                      <button key={sid} onClick={() => setExcerpt(e)} className="inline-flex items-center gap-1.5 rounded border border-line px-2 py-0.5 text-xs text-muted hover:border-brand hover:text-brand">
                        <BookOpen size={12} /> {shortDoc(e.doc_title)}{e.section ? ` §${e.section}` : ""}
                      </button>
                    ) : null;
                  })}
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>

      <aside className="space-y-4">
        <div className="rounded-xl border border-line bg-panel p-4">
          <h3 className="flex items-center gap-2 font-semibold"><BadgeCheck size={18} className="text-pass" /> Grounding report</h3>
          <dl className="mt-3 space-y-2 text-sm">
            <Row k="Status" v={b.grounding?.status === "passed" ? "Every check passed" : b.grounding?.status === "pending" ? "AI pending" : "Deterministic fallback"} />
            <Row k="Figures filled by the engine" v={String(b.grounding?.placeholders_filled ?? 0)} />
            <Row k="Breaches covered" v={`${(b.grounding?.fails_total ?? 0)} of ${b.grounding?.fails_total ?? 0}`} />
            <Row k="Breaches added by Daleel" v={String(b.grounding?.fails_added_by_daleel ?? 0)} />
            {b.source === "ai" && <Row k="Figures attached by Daleel" v={String(b.grounding?.figures_attached_by_daleel ?? 0)} />}
            {b.source === "ai" && <Row k="Attempts" v={String(b.grounding?.attempts ?? 1)} />}
          </dl>
          <ul className="mt-3 space-y-1 border-t border-line pt-3 text-xs text-muted">
            <li>The model never sees a number. Highlighted figures come from the calculation engine.</li>
            <li>Citations open the SBP text word for word.</li>
            <li>Wording is checked against each item's status.</li>
          </ul>
          {b.grounding?.ai_error && <p className="mt-3 text-xs text-warn">AI unavailable: {b.grounding.ai_error.slice(0, 140)}</p>}
        </div>
        <div className="rounded-xl border border-line bg-panel p-4 text-sm">
          <h3 className="font-semibold">SBP sources retrieved</h3>
          <ul className="mt-2 space-y-1.5">
            {(b.excerpts ?? []).map((e) => (
              <li key={e.id}>
                <button onClick={() => setExcerpt(e)} className="text-left text-muted hover:text-brand">{shortDoc(e.doc_title)}{e.section ? ` §${e.section}` : ""}{e.page ? `, p. ${e.page}` : ""}</button>
              </li>
            ))}
          </ul>
        </div>
      </aside>

      {excerpt && <ExcerptPanel e={excerpt} onClose={() => setExcerpt(null)} />}
    </div>
  );
}

function Seg({ s }: { s: Segment }) {
  if (s.type === "text") return <>{s.value}</>;
  const tone = s.status === "FAIL" ? "bg-fail-soft text-fail" : s.status === "WARNING" ? "bg-warn-soft text-warn" : s.status === "PASS" ? "bg-pass-soft text-pass" : "bg-info-soft text-info";
  return (
    <mark className={`num rounded px-1 py-0.5 font-medium ${tone}`} title="Value from the calculation engine">
      {s.status && <span className="mr-1 inline-block align-[-2px]"><StatusIcon status={s.status} size={13} /></span>}
      {s.value}
    </mark>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-muted">{k}</dt>
      <dd className="num font-medium">{v}</dd>
    </div>
  );
}

function shortDoc(title: string) {
  return title.split(":")[0].replace(/, Annex$/, "");
}

function ExcerptPanel({ e, onClose }: { e: Excerpt; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center p-4 sm:items-center" role="dialog" aria-modal="true" aria-label="SBP source excerpt">
      <button className="absolute inset-0 bg-ink/30" onClick={onClose} aria-label="Close" />
      <div className="relative max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-line bg-panel p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wider text-faint">SBP source, quoted word for word</p>
            <h3 className="mt-1 font-semibold">{e.doc_title}</h3>
            <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
              {e.section && <span>Section {e.section}</span>}{e.page && <span>Page {e.page}</span>}<VerificationBadge value={e.verification} />
            </p>
          </div>
          <button onClick={onClose} className="rounded-md p-1.5 text-muted hover:bg-brand-soft" aria-label="Close"><X size={18} /></button>
        </div>
        <blockquote className="mt-4 whitespace-pre-wrap border-l-2 border-accent pl-4 text-sm leading-relaxed">{e.text}</blockquote>
        {e.url && (
          <a href={e.url} target="_blank" rel="noreferrer" className="mt-4 inline-flex items-center gap-1.5 text-sm text-brand hover:underline">
            Open the document on sbp.org.pk <ExternalLink size={14} />
          </a>
        )}
      </div>
    </div>
  );
}
