import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { VerificationBadge } from "../components/Status";
import { api } from "../lib/api";

export function Rulebook() {
  const [asOf, setAsOf] = useState("2026-09-30");
  const q = useQuery({ queryKey: ["rulebook", asOf], queryFn: () => api.rulebook(asOf) });
  const groups = new Map<string, NonNullable<typeof q.data>>();
  for (const r of q.data ?? []) {
    const key = r.rule_id.split(".")[0];
    groups.set(key, [...(groups.get(key) ?? []), r]);
  }
  const titles: Record<string, string> = { capital: "Capital adequacy", asset_quality: "Asset quality and IFRS 9", pools: "Pool management and profit distribution", shariah: "Shariah", integrity: "Data integrity" };

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">Rulebook</h1>
      <p className="mt-2 max-w-3xl text-muted">
        Every regulatory number Daleel uses, with the date it applies from and the document it comes from. A calculation
        uses the version in force on its reporting date. <strong className="font-medium text-ink">Primary</strong> means read in the SBP document
        itself; <strong className="font-medium text-ink">secondary</strong> means an SBP page snippet, news report or bank disclosure;
        a <strong className="font-medium text-ink">demo assumption</strong> can never produce a breach on its own.
      </p>
      <label className="mt-6 inline-flex items-center gap-3 text-sm text-muted">
        Rules in force on
        <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} className="rounded-md border border-line bg-panel px-3 py-1.5 text-ink" />
      </label>
      {[...groups.entries()].map(([key, rules]) => (
        <section key={key} className="mt-8">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-faint">{titles[key] ?? key}</h2>
          <ul className="mt-3 divide-y divide-line rounded-xl border border-line bg-panel">
            {rules.map((r) => (
              <li key={r.rule_id} className="px-5 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <p className="font-medium">{r.title}</p>
                  <VerificationBadge value={r.source.verification} />
                </div>
                <p className="num mt-1 text-sm text-ink">
                  {r.value !== null ? `${r.value}${r.unit === "percent" ? "%" : r.unit === "flag" ? (r.value === "1" ? " (yes)" : " (no)") : ` ${r.unit}`}` : r.list ? r.list.join(", ") : r.table ? `Table of ${Object.keys(r.table).length} entries` : ""}
                  <span className="text-muted"> · in force from {r.effective_from}</span>
                </p>
                <p className="mt-1 text-xs text-faint">{r.source.doc}{r.source.section ? `, ${r.source.section}` : ""} · <span className="font-mono">{r.rule_id}</span>{r.source.ref ? ` · ${r.source.ref}` : ""}</p>
                {r.table && typeof Object.values(r.table)[0] === "string" && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {Object.entries(r.table).map(([k, v]) => <span key={k} className="num rounded bg-surface px-2 py-0.5 font-mono text-xs ring-1 ring-line">{k}: {String(v)}</span>)}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
