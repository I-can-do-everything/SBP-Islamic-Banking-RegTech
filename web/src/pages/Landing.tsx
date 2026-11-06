import { ArrowRight, BookOpenCheck, FileSpreadsheet, Fingerprint, Lock, ScanSearch, ShieldCheck, Sparkles } from "lucide-react";
import { Link } from "react-router";
import { StatusBadge } from "../components/Status";

const steps = [
  { icon: FileSpreadsheet, title: "Upload the bank's export", text: "A trial balance, financing portfolio, deposits and pool data, straight from a T24, Flexcube or spreadsheet export. Messy is fine." },
  { icon: ScanSearch, title: "See it transformed", text: "Daleel recognises each sheet, maps every column, fixes formats and shows the before and after, cell counts included. Download the result as the Daleel Standard Template." },
  { icon: ShieldCheck, title: "Get verified results", text: "Capital adequacy, IFRS 9 staging and provisioning, the 75% savings profit rule, pool limits and Shariah checks, each traced to its rule and SBP circular." },
];

const guarantees = [
  { icon: Fingerprint, title: "Chain of custody", text: "Every upload is fingerprinted (SHA-256) and stored unchanged. Every result names the file it came from." },
  { icon: BookOpenCheck, title: "Rules with sources", text: "Each threshold lives in a versioned rulebook with its effective date and the SBP document it comes from, marked primary, secondary or assumption." },
  { icon: Sparkles, title: "AI that cannot invent numbers", text: "The model never sees a figure. It writes placeholders the engine fills, cites SBP excerpts by id, and every sentence is checked before you see it." },
  { icon: Lock, title: "Isolation and audit", text: "Database row level security keeps each workspace separate, and a hash chained audit log shows any tampering." },
];

export function Landing() {
  return (
    <div>
      <section className="relative overflow-hidden border-b border-line bg-panel">
        <div className="girih pointer-events-none absolute inset-0 opacity-[0.07]" aria-hidden />
        <div className="relative mx-auto grid max-w-7xl gap-10 px-4 py-16 md:grid-cols-[1.15fr_1fr] md:py-24">
          <div>
            <p className="text-sm font-medium uppercase tracking-wider text-accent">Islamic bank regulatory compliance</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink md:text-5xl">
              Every figure carries its evidence.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
              <strong className="font-semibold text-ink">Daleel</strong> (<span lang="ar">دليل</span>, Arabic for evidence)
              turns a raw core banking export into State Bank of Pakistan regulatory results. Click any number to see the
              rows, the rule and the circular behind it.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/demo" className="inline-flex items-center gap-2 rounded-lg bg-brand px-5 py-2.5 text-sm font-medium text-panel hover:opacity-90">
                Try the demo <ArrowRight size={16} />
              </Link>
              <Link to="/how-it-works" className="inline-flex items-center gap-2 rounded-lg border border-line px-5 py-2.5 text-sm font-medium text-ink hover:bg-brand-soft">
                How it works
              </Link>
            </div>
            <p className="mt-4 text-xs text-faint">No sign up. Runs on synthetic data for a fictional bank.</p>
          </div>
          <ExampleCard />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-14">
        <h2 className="text-2xl font-semibold tracking-tight">Three steps, nothing hidden</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {steps.map((s, i) => (
            <div key={s.title} className="rounded-xl border border-line bg-panel p-5">
              <div className="flex items-center gap-3">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-soft text-sm font-semibold text-brand">{i + 1}</span>
                <s.icon size={18} className="text-accent" aria-hidden />
              </div>
              <h3 className="mt-4 font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-line bg-panel">
        <div className="mx-auto max-w-7xl px-4 py-14">
          <h2 className="text-2xl font-semibold tracking-tight">Built to survive an audit</h2>
          <div className="mt-6 grid gap-x-8 gap-y-6 md:grid-cols-2">
            {guarantees.map((g) => (
              <div key={g.title} className="flex gap-4">
                <g.icon size={22} className="mt-0.5 shrink-0 text-brand" aria-hidden />
                <div>
                  <h3 className="font-semibold">{g.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{g.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function ExampleCard() {
  const chain = [
    ["Source file", "EXIB_regulatory_extract_2026-09.xlsx", "sha256 fe2e7df0…"],
    ["Rows used", "10,994 eligible savings accounts", "Deposits sheet, tier S1"],
    ["Rule", "75% of the weighted average gross yield", "pools.savings_min_share_of_wagy"],
    ["Source", "IFPD Circular No. 09 of 2024, para 1", "Primary source"],
  ];
  return (
    <div className="rounded-2xl border border-line bg-surface p-5 shadow-sm" aria-label="Example of a traced figure">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-faint">Profit distribution</p>
          <p className="mt-1 font-medium">Lowest savings tier profit rate</p>
        </div>
        <StatusBadge status="FAIL" />
      </div>
      <p className="num mt-3 text-4xl font-semibold tracking-tight">9.10%</p>
      <p className="mt-1 text-sm text-muted">0.45 percentage points below the 9.55% minimum</p>
      <ol className="mt-5 space-y-2 border-t border-line pt-4">
        {chain.map(([k, v, s]) => (
          <li key={k} className="grid grid-cols-[92px_1fr] gap-3 text-sm">
            <span className="text-faint">{k}</span>
            <span>
              <span className="text-ink">{v}</span>
              <span className="block font-mono text-xs text-faint">{s}</span>
            </span>
          </li>
        ))}
      </ol>
      <p className="mt-4 text-xs text-faint">Illustrative example from the stressed demo scenario.</p>
    </div>
  );
}
