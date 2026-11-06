import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Download, FileSpreadsheet, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { api, type IngestedDataset } from "../lib/api";
import { DATASET_LABEL, FIX_LABEL, STRUCTURAL_LABEL } from "../lib/format";

export function Transformation({ id }: { id: string }) {
  const q = useQuery({ queryKey: ["submission", id, "ingestion"], queryFn: () => api.ingestion(id) });
  const [active, setActive] = useState<string | null>(null);
  if (q.isLoading || !q.data) return <p className="text-sm text-muted">Loading the transformation…</p>;
  const data = q.data;
  const order = ["TRIAL_BALANCE", "FINANCING", "DEPOSITS", "POOLS", "CAPITAL"];
  data.datasets.sort((a, b) => order.indexOf(a.kind) - order.indexOf(b.kind));
  const current = data.datasets.find((d) => d.kind === active) ?? data.datasets[0];
  const plural = (n: number, word: string) => `${n.toLocaleString()} ${word}${n === 1 ? "" : "s"}`;
  const totalFixes = data.datasets.reduce((n, d) => n + d.fixes.reduce((m, f) => m + f.cells, 0), 0);
  const totalRejected = data.datasets.reduce((n, d) => n + d.rejected_count, 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-line bg-panel p-5">
        <div>
          <h2 className="text-lg font-semibold">From raw export to the Daleel Standard Template</h2>
          <p className="mt-1 text-sm text-muted">
            {data.datasets.length} datasets recognised · <span className="num">{plural(totalFixes, "cell")}</span> cleaned ·{" "}
            <span className="num">{plural(totalRejected, "row")}</span> rejected with a reason · template {data.template_version}
          </p>
        </div>
        <button
          onClick={async () => { window.location.href = await api.templateUrl(id); }}
          className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-panel hover:opacity-90"
        >
          <Download size={16} /> Download the ideal ingestion document
        </button>
      </div>

      {(data.missing_datasets.length > 0 || data.skipped_sheets.length > 0) && (
        <div className={`rounded-lg border p-4 text-sm ${data.missing_datasets.length ? "border-warn/30 bg-warn-soft text-warn" : "border-line bg-panel text-muted"}`}>
          {data.missing_datasets.length > 0 && <p>Not supplied: {data.missing_datasets.map((k) => DATASET_LABEL[k] ?? k).join(", ")}. Metrics that need them are shown as not available.</p>}
          {data.skipped_sheets.map((s) => <p key={s.sheet}>Sheet “{s.sheet}” skipped: {s.reason}.</p>)}
        </div>
      )}

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Datasets">
        {data.datasets.map((d) => (
          <button
            key={d.kind}
            role="tab"
            aria-selected={current?.kind === d.kind}
            onClick={() => setActive(d.kind)}
            className={`rounded-lg border px-3 py-2 text-left text-sm ${current?.kind === d.kind ? "border-brand bg-brand-soft" : "border-line bg-panel hover:bg-brand-soft/50"}`}
          >
            <span className="block font-medium">{DATASET_LABEL[d.kind] ?? d.kind}</span>
            <span className="num block text-xs text-muted">{d.row_count.toLocaleString()} rows{d.rejected_count ? ` · ${d.rejected_count} rejected` : ""}</span>
          </button>
        ))}
      </div>

      {current && <DatasetDetail d={current} />}
    </div>
  );
}

function DatasetDetail({ d }: { d: IngestedDataset }) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Info label="Source sheet" value={d.source_name} />
        <Info label="Layout recognised" value={d.layout} hint={d.detail?.slice(0, 2).join(", ")} />
        <Info label="Fingerprint of clean data" value={`${d.canonical_sha256.slice(0, 16)}…`} mono />
      </div>

      <section className="rounded-xl border border-line bg-panel">
        <h3 className="border-b border-line px-5 py-3 font-semibold">What Daleel changed</h3>
        <ul className="divide-y divide-line text-sm">
          {Object.entries(d.structural).map(([k, n]) => (
            <li key={k} className="flex items-center justify-between gap-4 px-5 py-2.5">
              <span>{STRUCTURAL_LABEL[k] ?? k}</span>
              <span className="num text-muted">{n} row{n === 1 ? "" : "s"}</span>
            </li>
          ))}
          {d.fixes.map((f) => (
            <li key={`${f.field}-${f.fix}`} className="grid gap-1 px-5 py-2.5 md:grid-cols-[1fr_auto]">
              <span>
                {FIX_LABEL[f.fix] ?? f.fix} <span className="font-mono text-xs text-faint">in {f.field}</span>
                {f.examples.length > 0 && (
                  <span className="mt-0.5 block font-mono text-xs text-muted">e.g. {f.examples.filter(Boolean).slice(0, 2).map((e) => `“${e}”`).join(", ")}</span>
                )}
              </span>
              <span className="num text-muted">{f.cells.toLocaleString()} cell{f.cells === 1 ? "" : "s"}</span>
            </li>
          ))}
          {d.translations.map((t) => (
            <li key={`${t.field}-${t.from}`} className="flex items-center justify-between gap-4 px-5 py-2.5">
              <span>
                <span className="font-mono text-xs">“{t.from}”</span> <ArrowRight size={12} className="inline text-faint" /> <span className="font-mono text-xs text-brand">{t.to}</span>
                <span className="ml-2 text-xs text-faint">{t.field}</span>
              </span>
              <span className="num text-muted">{t.rows.toLocaleString()} row{t.rows === 1 ? "" : "s"}</span>
            </li>
          ))}
          {!d.fixes.length && !d.translations.length && !Object.keys(d.structural).length && <li className="px-5 py-3 text-muted">This sheet was already clean.</li>}
        </ul>
      </section>

      {d.rejects_sample && d.rejects_sample.length > 0 && (
        <section className="rounded-xl border border-fail/30 bg-fail-soft/40">
          <h3 className="flex items-center gap-2 px-5 py-3 font-semibold text-fail"><TriangleAlert size={16} /> Rows that could not be used</h3>
          <ul className="space-y-1 px-5 pb-4 text-sm">
            {d.rejects_sample.map((r) => (
              <li key={r.source_row}><span className="num font-mono text-xs text-faint">row {r.source_row}</span> · {r.reason}. It was left out, not counted as zero.</li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-xl border border-line bg-panel">
        <h3 className="border-b border-line px-5 py-3 font-semibold">Column mapping</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-faint">
              <tr><th className="px-5 py-2 font-medium">Column in the export</th><th className="px-5 py-2 font-medium">Standard field</th><th className="px-5 py-2 font-medium">How it was matched</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {d.header_map.map((m) => (
                <tr key={m.field}>
                  <td className="px-5 py-2 font-mono text-xs">{m.source}</td>
                  <td className="px-5 py-2 font-mono text-xs text-brand">{m.field}</td>
                  <td className="px-5 py-2 text-xs text-muted">{m.method === "exact" ? "Known column name" : m.method === "fuzzy" ? `Close spelling (${m.score}%)` : "AI proposal, verified by type"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <Preview title="Before: raw export" icon columns={d.before.columns} rows={d.before.rows} rowNumbers={d.before.source_rows} />
        <Preview title="After: standard template" columns={d.after.columns} rows={d.after.rows} />
      </div>
    </div>
  );
}

function Info({ label, value, hint, mono }: { label: string; value: string; hint?: string; mono?: boolean }) {
  return (
    <div className="rounded-xl border border-line bg-panel p-4">
      <p className="text-xs uppercase tracking-wide text-faint">{label}</p>
      <p className={`mt-1 font-medium ${mono ? "font-mono text-sm" : ""}`}>{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}

function Preview({ title, columns, rows, rowNumbers, icon }: { title: string; columns: string[]; rows: (string | null)[][]; rowNumbers?: number[]; icon?: boolean }) {
  return (
    <section className="min-w-0 rounded-xl border border-line bg-panel">
      <h3 className="flex items-center gap-2 border-b border-line px-4 py-3 text-sm font-semibold">
        {icon && <FileSpreadsheet size={15} className="text-faint" />} {title}
      </h3>
      <div className="max-h-80 overflow-auto">
        <table className="w-full whitespace-nowrap text-xs">
          <thead className="sticky top-0 bg-panel text-left text-faint">
            <tr>
              {rowNumbers && <th className="px-3 py-2 font-medium">row</th>}
              {columns.map((c) => <th key={c} className="px-3 py-2 font-mono font-medium">{c}</th>)}
            </tr>
          </thead>
          <tbody className="divide-y divide-line font-mono">
            {rows.map((r, i) => (
              <tr key={i}>
                {rowNumbers && <td className="px-3 py-1.5 text-faint">{rowNumbers[i]}</td>}
                {r.map((v, j) => <td key={j} className="num px-3 py-1.5">{v ?? <span className="text-faint">null</span>}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
