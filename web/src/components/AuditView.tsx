import { useMutation, useQuery } from "@tanstack/react-query";
import { Link2, ShieldCheck, ShieldX } from "lucide-react";
import { api } from "../lib/api";
import { shortHash } from "../lib/format";

export function AuditView() {
  const events = useQuery({ queryKey: ["audit"], queryFn: api.audit, refetchInterval: 5000 });
  const verify = useMutation({ mutationFn: api.verifyAudit });
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-line bg-panel p-5">
        <div>
          <h2 className="text-lg font-semibold">Tamper evident audit trail</h2>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Each event stores a SHA-256 hash of the previous event and itself. The database refuses edits and deletions,
            and changing any past event would break every hash after it.
          </p>
        </div>
        <button onClick={() => verify.mutate()} className="inline-flex items-center gap-2 rounded-lg bg-brand-fill px-4 py-2 text-sm font-medium text-on-brand hover:opacity-90">
          <ShieldCheck size={16} /> Verify the chain
        </button>
      </div>
      {verify.data && (
        <div role="status" className={`flex items-center gap-2 rounded-lg p-3 text-sm ${verify.data.valid ? "bg-pass-soft text-pass" : "bg-fail-soft text-fail"}`}>
          {verify.data.valid ? <ShieldCheck size={16} /> : <ShieldX size={16} />}
          {verify.data.valid
            ? `Chain intact: ${verify.data.events} events recomputed, head ${shortHash(verify.data.head, 16)}`
            : `Chain broken at event ${verify.data.broken_at}`}
        </div>
      )}
      <ol className="overflow-hidden rounded-xl border border-line bg-panel">
        {(events.data ?? []).map((e, i) => (
          <li key={e.id} className="grid gap-1 border-b border-line px-5 py-3 text-sm last:border-0 md:grid-cols-[170px_1fr_260px]">
            <span className="num text-xs text-faint">{new Date(e.occurred_at).toLocaleString("en-GB")}</span>
            <span>
              <span className="font-medium">{e.action}</span> <span className="text-muted">by {e.actor}</span>
              {e.resource && <span className="block font-mono text-xs text-faint">{e.resource}</span>}
            </span>
            <span className="flex items-center gap-1.5 font-mono text-xs text-muted" title={e.hash}>
              {i > 0 && <Link2 size={12} className="text-faint" aria-label="linked to previous" />}
              {shortHash(e.prev_hash, 8) || "genesis"} → {shortHash(e.hash, 12)}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
