import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileSignature, Lock, MessageSquareText, OctagonX, Send, ShieldCheck, Undo2, UserRound } from "lucide-react";
import { useState } from "react";
import { api, type Review, type WorkflowStatus } from "../lib/api";
import { shortHash } from "../lib/format";
import { ROLE_LABEL } from "./PersonSwitcher";

const STEPS: { key: WorkflowStatus; label: string }[] = [
  { key: "DRAFT", label: "Preparer explains breaches" },
  { key: "SUBMITTED", label: "With the approver" },
  { key: "APPROVED", label: "Approved and locked" },
];

export function WorkflowBadge({ status, locked }: { status?: WorkflowStatus; locked?: boolean }) {
  if (!status) return null;
  const map: Record<WorkflowStatus, [string, string]> = {
    DRAFT: ["Draft", "bg-surface text-muted ring-line"],
    SUBMITTED: ["Awaiting approval", "bg-info-soft text-info ring-info/30"],
    APPROVED: ["Approved", "bg-pass-soft text-pass ring-pass/30"],
    REJECTED: ["Returned to preparer", "bg-warn-soft text-warn ring-warn/30"],
  };
  const [label, cls] = map[status];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${cls}`}>
      {locked && <Lock size={12} aria-hidden />} {label}
    </span>
  );
}

export function ReviewView({ id }: { id: string }) {
  const client = useQueryClient();
  const q = useQuery({ queryKey: ["submission", id, "review"], queryFn: () => api.review(id) });
  const refresh = () => {
    client.invalidateQueries({ queryKey: ["submission", id] });
    client.invalidateQueries({ queryKey: ["audit"] });
  };
  const [error, setError] = useState<string | null>(null);
  const onError = (e: Error) => setError(e.message);
  const note = useMutation({ mutationFn: (v: { item_id: string | null; body: string; kind: "explanation" | "comment" }) => api.addNote(id, v), onSuccess: () => { setError(null); refresh(); }, onError });
  const submit = useMutation({ mutationFn: (c?: string) => api.submitForApproval(id, c), onSuccess: () => { setError(null); refresh(); }, onError });
  const approve = useMutation({ mutationFn: (c?: string) => api.approve(id, c), onSuccess: () => { setError(null); refresh(); }, onError });
  const reject = useMutation({ mutationFn: (c: string) => api.reject(id, c), onSuccess: () => { setError(null); refresh(); }, onError });
  if (!q.data) return <p className="text-sm text-muted">Loading the review…</p>;
  const r = q.data;
  const explained = r.breaches.filter((b) => b.explanation).length;

  return (
    <div className="space-y-6">
      <Header r={r} />
      {error && <p role="alert" className="rounded-lg border border-fail/30 bg-fail-soft px-4 py-3 text-sm text-fail"><strong>Not allowed:</strong> {error}</p>}

      {r.locked && (
        <div className="flex items-start gap-3 rounded-xl border border-pass/30 bg-pass-soft p-4 text-sm text-pass">
          <Lock size={18} className="mt-0.5 shrink-0" aria-hidden />
          <p>
            Approved by <strong>{r.decided_by?.name}</strong> on {new Date(r.decided_at!).toLocaleString("en-GB")}. The results are locked:
            the database refuses any change to them. Results fingerprint <span className="font-mono">{shortHash(r.results_digest, 16)}</span>.
          </p>
        </div>
      )}

      <section className="rounded-xl border border-line bg-panel">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-3">
          <h3 className="font-semibold">Breaches and the preparer's explanations</h3>
          <span className="num text-sm text-muted">{explained} of {r.breaches.length} explained</span>
        </div>
        {r.breaches.length === 0 && <p className="px-5 py-4 text-sm text-muted">No breaches. The preparer can submit straight away.</p>}
        <ul className="divide-y divide-line">
          {r.breaches.map((b) => (
            <BreachRow key={b.id} b={b} canWrite={r.allowed.note && (r.you.role === "PREPARER" || r.you.role === "ADMIN")} blocked={r.blocked_reason.note}
              onSave={(text) => note.mutate({ item_id: b.id, body: text, kind: "explanation" })} saving={note.isPending} />
          ))}
        </ul>
      </section>

      <Decision r={r} onSubmit={(c) => submit.mutate(c)} onApprove={(c) => approve.mutate(c)} onReject={(c) => reject.mutate(c)}
        busy={submit.isPending || approve.isPending || reject.isPending} />

      <History r={r} />
    </div>
  );
}

function Header({ r }: { r: Review }) {
  const order: WorkflowStatus[] = ["DRAFT", "SUBMITTED", "APPROVED"];
  const current = r.workflow_status === "REJECTED" ? 0 : order.indexOf(r.workflow_status);
  return (
    <div className="rounded-xl border border-line bg-panel p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Four eyes approval</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            One person prepares and explains, a different person approves. The database enforces it: nobody can approve
            their own submission, every breach needs an explanation, and an approval is bound to the exact results it saw.
          </p>
        </div>
        <WorkflowBadge status={r.workflow_status} locked={r.locked} />
      </div>
      <ol className="mt-5 grid gap-2 sm:grid-cols-3" aria-label="Approval steps">
        {STEPS.map((s, i) => (
          <li key={s.key} className={`rounded-lg border px-3 py-2 text-sm ${i < current || r.locked ? "border-pass/30 bg-pass-soft text-pass" : i === current ? "border-brand bg-brand-soft text-ink" : "border-line text-faint"}`}>
            <span className="num mr-2 font-semibold">{i + 1}</span>{s.label}
          </li>
        ))}
      </ol>
      {r.workflow_status === "REJECTED" && <p className="mt-3 text-sm text-warn">Returned by the approver. The preparer can update the explanations and submit again.</p>}
      <p className="mt-4 flex items-center gap-2 text-sm text-muted">
        <UserRound size={15} aria-hidden /> You are acting as <strong className="text-ink">{r.you.name}</strong> ({ROLE_LABEL[r.you.role]}).
        <span className="hidden text-faint md:inline">Switch person from the top right corner.</span>
      </p>
    </div>
  );
}

function BreachRow({ b, canWrite, blocked, onSave, saving }: { b: Review["breaches"][number]; canWrite: boolean; blocked: string | null; onSave: (t: string) => void; saving: boolean }) {
  const [text, setText] = useState("");
  const [editing, setEditing] = useState(false);
  return (
    <li className="px-5 py-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 font-medium"><OctagonX size={15} className="text-fail" aria-label="Breach" /> {b.label}</p>
          <p className="text-xs text-faint">{b.category} · <span className="font-mono">{b.id}</span></p>
        </div>
        {b.explanation ? <span className="inline-flex items-center gap-1 text-xs text-pass"><CheckCircle2 size={13} /> Explained</span> : <span className="text-xs text-fail">Needs an explanation</span>}
      </div>
      {b.explanation && !editing && (
        <blockquote className="mt-2 border-l-2 border-line pl-3 text-sm text-muted">
          {b.explanation.body}
          <span className="mt-1 block text-xs text-faint">{b.explanation.author.name}, {new Date(b.explanation.at).toLocaleString("en-GB")}</span>
        </blockquote>
      )}
      {canWrite && (!b.explanation || editing) && (
        <div className="mt-3 flex flex-col gap-2 sm:flex-row">
          <label className="sr-only" htmlFor={`exp-${b.id}`}>Explanation for {b.label}</label>
          <textarea id={`exp-${b.id}`} value={text} onChange={(e) => setText(e.target.value)} rows={2}
            placeholder="Why did this happen, and what is being done about it?"
            className="min-h-16 flex-1 rounded-md border border-line bg-surface px-3 py-2 text-sm" />
          <button disabled={text.trim().length < 3 || saving} onClick={() => { onSave(text); setText(""); setEditing(false); }}
            className="self-start rounded-lg bg-brand px-3 py-2 text-sm font-medium text-panel disabled:opacity-40">Save explanation</button>
        </div>
      )}
      {canWrite && b.explanation && !editing && (
        <button onClick={() => setEditing(true)} className="mt-2 text-xs text-brand hover:underline">Add a newer explanation</button>
      )}
      {!canWrite && !b.explanation && blocked && <p className="mt-2 text-xs text-faint">{blocked}</p>}
    </li>
  );
}

function Decision({ r, onSubmit, onApprove, onReject, busy }: { r: Review; onSubmit: (c?: string) => void; onApprove: (c?: string) => void; onReject: (c: string) => void; busy: boolean }) {
  const [comment, setComment] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  if (r.locked) return null;
  const isPreparerStage = r.workflow_status === "DRAFT" || r.workflow_status === "REJECTED";
  return (
    <section className="rounded-xl border border-line bg-panel p-5">
      {isPreparerStage ? (
        <>
          <h3 className="flex items-center gap-2 font-semibold"><Send size={16} className="text-brand" /> Submit for approval</h3>
          <p className="mt-1 text-sm text-muted">The approver will see the results, the AI breakdown and your explanations.</p>
          <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={2} placeholder="Optional note for the approver"
            className="mt-3 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm" aria-label="Note for the approver" />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button disabled={!r.allowed.submit || busy} onClick={() => onSubmit(comment || undefined)}
              className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-panel disabled:opacity-40">
              <Send size={15} /> Submit for approval
            </button>
            {r.blocked_reason.submit && <span className="text-sm text-muted">{r.blocked_reason.submit}</span>}
          </div>
        </>
      ) : (
        <>
          <h3 className="flex items-center gap-2 font-semibold"><FileSignature size={16} className="text-brand" /> Approver's decision</h3>
          <p className="mt-1 text-sm text-muted">
            Submitted by <strong>{r.submitted_by?.name}</strong>{r.submitted_at ? ` on ${new Date(r.submitted_at).toLocaleString("en-GB")}` : ""}.
            Your approval will be bound to results fingerprint <span className="font-mono">{shortHash(r.submitted_digest, 16)}</span>
            {r.submitted_digest !== r.results_digest && <strong className="text-fail"> (the results have changed since submission)</strong>}.
          </p>
          <textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={2} placeholder="Comment (required to return it to the preparer)"
            className="mt-3 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm" aria-label="Approver comment" />
          <label className="mt-3 flex items-start gap-2 text-sm">
            <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} className="mt-1" />
            I have reviewed the results, the checks and every explanation.
          </label>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button disabled={!r.allowed.approve || !confirmed || busy} onClick={() => onApprove(comment || undefined)}
              className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-panel disabled:opacity-40">
              <ShieldCheck size={15} /> Approve and lock
            </button>
            <button disabled={!r.allowed.reject || comment.trim().length < 3 || busy} onClick={() => onReject(comment)}
              className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm font-medium hover:bg-warn-soft disabled:opacity-40">
              <Undo2 size={15} /> Return to preparer
            </button>
            {r.blocked_reason.approve && <span className="text-sm text-muted">{r.blocked_reason.approve}</span>}
          </div>
        </>
      )}
    </section>
  );
}

function History({ r }: { r: Review }) {
  const items = [
    ...r.history.map((h) => ({ at: h.at, who: h.actor, text: h.action === "SUBMIT" ? "Submitted for approval" : h.action === "APPROVE" ? "Approved and locked" : "Returned to preparer", comment: h.comment, digest: h.results_digest })),
    ...r.notes.filter((n) => n.kind === "comment").map((n) => ({ at: n.at, who: n.author, text: "Comment", comment: n.body, digest: null as string | null })),
  ].sort((a, b) => a.at.localeCompare(b.at));
  if (!items.length) return null;
  return (
    <section className="rounded-xl border border-line bg-panel">
      <h3 className="flex items-center gap-2 border-b border-line px-5 py-3 font-semibold"><MessageSquareText size={16} /> Decision history</h3>
      <ol className="divide-y divide-line">
        {items.map((h, i) => (
          <li key={i} className="grid gap-1 px-5 py-3 text-sm md:grid-cols-[170px_1fr_200px]">
            <span className="num text-xs text-faint">{new Date(h.at).toLocaleString("en-GB")}</span>
            <span>
              <strong>{h.text}</strong> <span className="text-muted">by {h.who.name} ({ROLE_LABEL[h.who.role]})</span>
              {h.comment && <span className="mt-0.5 block text-muted">“{h.comment}”</span>}
            </span>
            {h.digest && <span className="font-mono text-xs text-faint" title={h.digest}>results {shortHash(h.digest, 12)}</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}
