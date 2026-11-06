import {
  ArrowRight, BookOpenCheck, Check, FileSpreadsheet, Fingerprint, Landmark, Layers, Lock, ScanSearch, Sparkles, Table2, Users, X,
} from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";
import { Mark } from "../components/Layout";
import { StatusBadge } from "../components/Status";

// Every number on this page comes from a measured run or a documented source
// (docs/06-system-design.md benchmark, docs/03-fix-log.md, docs/05-regulatory-verification.md).
const proof = [
  { value: "86,707", unit: "cells", text: "cleaned and counted from one messy T24 and Flexcube export, in about 6 seconds" },
  { value: "240 m", unit: "rows", text: "of daily deposit balances averaged and totalled in 3.9 seconds on 4 CPUs" },
  { value: "0", unit: "numbers", text: "written by the AI. It writes placeholders; the calculation engine fills them" },
  { value: "17 of 26", unit: "rules", text: "verified in primary SBP documents, each labelled with its source and status" },
];

const problems = [
  {
    icon: FileSpreadsheet,
    title: "Spreadsheets sit in the critical path",
    text: "Trial balances and portfolios leave T24 or Flexcube as exports and are reworked by hand. Monthly RCOA returns go to SBP within five working days (BSD-1 Circular No. 01 of 2025), so there is little time to check the work.",
  },
  {
    icon: Landmark,
    title: "Islamic rules sit on top of Basel",
    text: "Since January 2025, profit on rupee savings must be at least 75% of the pools' weighted average gross yield (IFPD Circular No. 09 of 2024). Add the Mudarib share cap, PER and IRR limits, and IFRS 9 day bands that differ by portfolio. Generic tools treat these as custom work.",
  },
  {
    icon: Fingerprint,
    title: "Trust is the real bottleneck",
    text: "Auditors and inspectors ask where each number came from. AI could help, but models invent numbers, and SBP's cloud framework keeps material bank data onshore. So most teams keep doing it by hand.",
  },
];

const pillars = [
  { icon: ScanSearch, title: "Messy in, clean out", text: "Reads raw T24, Flexcube and spreadsheet exports, shows every fix it makes, rejects what it cannot read (never a silent zero), and hands back the ideal ingestion template." },
  { icon: Layers, title: "Evidence behind every figure", text: "Click any number: formula, inputs, the rule version in force on the reporting date, the SBP paragraph, and the fingerprint of the file it came from." },
  { icon: BookOpenCheck, title: "Built for Islamic banks in Pakistan", text: "A dated rulebook with the 75% savings rule, pool limits, Annexure C stage bands and Basel III minimums, each marked primary, secondary or assumption. Assumptions never raise a breach." },
  { icon: Sparkles, title: "AI that cannot write numbers", text: "The model never sees a figure. It cites SBP excerpts shown word for word, every sentence is checked, and a deterministic summary takes over if it fails. Runs on free cloud models or fully on premises." },
  { icon: Users, title: "Four eyes, enforced by the database", text: "Every breach must be explained before submission. Nobody approves their own work. An approval is bound to the exact results, which are then locked." },
  { icon: Lock, title: "Isolation and audit", text: "Row level security keeps each workspace apart even if the app has a bug, and a hash chained audit log shows any tampering." },
];

const landscape = [
  {
    title: "International regulatory reporting suites",
    examples: "Regnology (which now also owns OneSumX, Moody's regulatory reporting and Vermeg's AGILE), AxiomSL under Nasdaq",
    strong: "Hundreds of returns across many regulators, mature data models, certification and vendor support.",
    daleel: "Here, SBP and Islamic pool rules are the core rather than an add on, every figure shows its lineage on screen, and it runs on premises or on free infrastructure.",
  },
  {
    title: "Islamic profit and pool systems",
    examples: "Azentio iMAL Profit Calculation, Finastra Fusion Islamic Profit Distribution, Intellect, ITS ETHIX; Codebase Technologies upgraded pool management at NBP",
    strong: "Running profit calculation and distribution across pools, day to day.",
    daleel: "Daleel checks the outcome against SBP's rules (75% of WAGY, the Mudarib cap, PER and IRR limits, weightage notice) and ties it to capital and asset quality in one approved submission.",
  },
  {
    title: "In house spreadsheets and bespoke builds",
    examples: "Common at Pakistani banks; local vendors have also built SBP report automation for individual banks",
    strong: "Fit the bank's own chart of accounts and cost little to start.",
    daleel: "Daleel keeps that flexibility (configurable mapping, any export layout) and adds reconciliation, a dated rulebook, four eyes approval and a tamper evident trail.",
  },
];

const sources = [
  ["Regnology completes Wolters Kluwer FRR (OneSumX) acquisition", "https://www.pulse.bot/ma/news/regnology-extends-balance-sheet-centric-reporting-model-with-wolters-kluwer-frr-acquisition-167b4c9e-c252-4fe4-a61b-ef280084e463"],
  ["Regnology acquires Moody's regulatory reporting and ALM", "https://www.privsource.com/acquisitions/deal/regnology-acquires-moody-s-regulatory-reporting-alm-solutions-y3SBdj"],
  ["Azentio iMAL Islamic profit calculation", "https://www.azentio.com/banking/imal-islamic-banking/imal-islamic-profit-calculation"],
  ["Finastra Fusion Islamic Profit Distribution", "https://www.finastra.com/sites/default/files/documents/2018/03/brochure_fusion-islamic-profit-distribution-factsheet.pdf"],
  ["NBP modernises pool management with Codebase Technologies", "https://salaamgateway.com/story/national-bank-of-pakistan-modernizes-pool-management-with-codebase-technologies"],
];

export function Landing() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-line bg-panel">
        <div className="girih pointer-events-none absolute inset-0 opacity-[0.05]" aria-hidden />
        <div className="absolute inset-x-0 top-0 h-1 bg-signal" aria-hidden />
        <div className="relative mx-auto grid max-w-7xl gap-12 px-4 py-16 md:grid-cols-[1.1fr_1fr] md:py-24">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs font-medium text-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-signal" aria-hidden /> Portfolio showcase · open source · synthetic data
            </p>
            <h1 className="mt-5 text-4xl font-semibold leading-[1.08] tracking-tight text-ink md:text-6xl">
              Every figure carries its <span className="relative whitespace-nowrap text-brand">evidence<span className="absolute -bottom-1 left-0 h-1 w-full rounded bg-signal" aria-hidden /></span>.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
              <strong className="font-semibold text-ink">Daleel</strong> (<span lang="ar">دليل</span>, Arabic for evidence) is a working
              regulatory compliance tool for Islamic banks in Pakistan. It reads a bank's raw export, calculates State Bank of
              Pakistan figures, proves where every number came from, and gets two different people to sign it off.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to="/demo" className="inline-flex items-center gap-2 rounded-lg bg-brand-fill px-5 py-3 text-sm font-semibold text-on-brand shadow-sm hover:opacity-90">
                Run the live demo <ArrowRight size={16} />
              </Link>
              <a href="#compare" className="inline-flex items-center gap-2 rounded-lg border border-line px-5 py-3 text-sm font-medium text-ink hover:bg-surface">
                What makes it different
              </a>
            </div>
            <p className="mt-4 text-xs text-faint">No sign up. About two minutes. The bank, its customers and its data are fictional.</p>
          </div>
          <EvidenceCard />
        </div>
      </section>

      {/* Proof strip */}
      <section aria-label="Measured results" className="border-b border-line bg-surface">
        <div className="mx-auto grid max-w-7xl grid-cols-2 gap-px bg-line md:grid-cols-4">
          {proof.map((p) => (
            <div key={p.unit} className="bg-surface px-5 py-7">
              <p className="num text-3xl font-semibold tracking-tight text-ink md:text-4xl">
                {p.value} <span className="text-base font-medium text-brand">{p.unit}</span>
              </p>
              <p className="mt-2 text-sm leading-snug text-muted">{p.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* What this is */}
      <Section id="what" eyebrow="What this is" title="A complete showcase, honest about its limits">
        <div className="grid gap-8 md:grid-cols-[1.2fr_1fr]">
          <div className="space-y-4 text-lg leading-relaxed text-muted">
            <p>
              Daleel is a portfolio project, not a vendor product. It is built end to end: ingestion, a calculation engine,
              grounded AI, four eyes approval and an audit trail, with a public demo on a fictional bank,
              <span className="text-ink"> Example Islamic Bank Ltd</span>.
            </p>
            <p>
              The point is to show how regulatory software for Islamic banks could be built when every number has to stand up
              in front of an auditor, a Shariah board and the regulator.
            </p>
          </div>
          <div className="rounded-2xl border border-line bg-panel p-6">
            <Checklist ok items={["Real SBP rules, 17 read in the primary documents", "A real calculation engine, tested on 240 million rows", "Real controls: four eyes, locking, audit chain", "Open source, runs free or on premises"]} />
            <div className="my-4 border-t border-line" />
            <Checklist items={["Not certified by SBP, and not a submitted return (DAP4 file layouts are given only to banks)", "No real bank or customer data, ever"]} />
          </div>
        </div>
      </Section>

      {/* Problem */}
      <Section id="problem" eyebrow="The problem" title="Month end at an Islamic bank is hard to prove" tone="panel">
        <div className="grid gap-5 md:grid-cols-3">
          {problems.map((p, i) => (
            <article key={p.title} className="relative rounded-2xl border border-line bg-surface p-6">
              <span className="num absolute right-5 top-4 text-5xl font-semibold text-line" aria-hidden>{i + 1}</span>
              <p.icon size={22} className="text-brand" aria-hidden />
              <h3 className="mt-4 text-lg font-semibold">{p.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{p.text}</p>
            </article>
          ))}
        </div>
      </Section>

      {/* Answer */}
      <Section id="answer" eyebrow="How Daleel answers" title="Built around one idea: show the evidence">
        <div className="grid gap-x-10 gap-y-8 md:grid-cols-2 lg:grid-cols-3">
          {pillars.map((p) => (
            <div key={p.title} className="border-t-2 border-signal pt-5">
              <p.icon size={20} className="text-brand" aria-hidden />
              <h3 className="mt-3 font-semibold">{p.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{p.text}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Compare */}
      <Section id="compare" eyebrow="How it compares" title="Not a replacement for an enterprise suite. A different way to build one." tone="panel">
        <p className="max-w-3xl text-muted">
          Banks in Pakistan typically combine three kinds of tools. Each is strong at something real. Here is where Daleel takes
          a different path, as of November 2026.
        </p>
        <div className="mt-8 grid gap-5 lg:grid-cols-3">
          {landscape.map((l) => (
            <article key={l.title} className="flex flex-col rounded-2xl border border-line bg-surface">
              <div className="p-6">
                <h3 className="text-lg font-semibold">{l.title}</h3>
                <p className="mt-1 text-xs leading-relaxed text-faint">{l.examples}</p>
                <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-faint">Where they are strong</p>
                <p className="mt-1 text-sm leading-relaxed text-muted">{l.strong}</p>
              </div>
              <div className="mt-auto rounded-b-2xl border-t border-line bg-brand-soft p-6">
                <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-brand"><Mark className="h-3.5 w-3.5" /> Where Daleel differs</p>
                <p className="mt-1 text-sm leading-relaxed text-ink">{l.daleel}</p>
              </div>
            </article>
          ))}
        </div>
        <div className="mt-10 grid gap-6 rounded-2xl border border-line bg-surface p-6 md:grid-cols-[1fr_1.4fr]">
          <div>
            <h3 className="text-lg font-semibold">The combination that stands out</h3>
            <p className="mt-2 text-sm text-muted">Each idea exists somewhere. Having all of them in one open, inspectable tool is the point.</p>
          </div>
          <ul className="grid gap-2 text-sm sm:grid-cols-2">
            {["Islamic and SBP rules as first class, dated data", "Lineage for every single figure", "AI that is structurally unable to state a number", "Controls enforced in the database, not the screen", "Messy exports in, ideal template out", "Free to run, or fully on premises"].map((t) => (
              <li key={t} className="flex items-start gap-2"><Check size={16} className="mt-0.5 shrink-0 text-brand" aria-hidden />{t}</li>
            ))}
          </ul>
        </div>
        <details className="mt-6 text-xs text-faint">
          <summary className="cursor-pointer">Sources for the market notes</summary>
          <ul className="mt-2 space-y-1">
            {sources.map(([t, u]) => <li key={u}><a href={u} target="_blank" rel="noreferrer" className="underline-offset-2 hover:text-brand hover:underline">{t}</a></li>)}
          </ul>
          <p className="mt-2">Product facts come from vendor and press publications. Daleel has not been benchmarked against these products.</p>
        </details>
      </Section>

      {/* Try it */}
      <Section id="try" eyebrow="Try it" title="See it in two minutes">
        <ol className="grid gap-4 md:grid-cols-4">
          {[
            ["Run the stressed sample", "A messy export with eight planted breaches."],
            ["Watch it transform", "Every fix counted, before and after, ideal template to download."],
            ["Open a breach", "The 75% rule, its tiers, rows, rule and SBP paragraph."],
            ["Approve it, twice", "Explain as the Reporting Officer, decide as the Head of Compliance."],
          ].map(([t, d], i) => (
            <li key={t} className="rounded-2xl border border-line bg-panel p-5">
              <span className="num flex h-8 w-8 items-center justify-center rounded-full bg-brand-soft text-sm font-semibold text-brand">{i + 1}</span>
              <h3 className="mt-3 font-semibold">{t}</h3>
              <p className="mt-1 text-sm text-muted">{d}</p>
            </li>
          ))}
        </ol>
      </Section>

      {/* Closing band */}
      <section className="relative bg-brand-fill">
        <div className="absolute inset-x-0 top-0 h-1 bg-signal" aria-hidden />
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-4 py-14 md:flex-row md:items-center">
          <div>
            <h2 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">See the evidence for yourself.</h2>
            <p className="mt-2 text-lg text-white/90">Free, open source, and nothing to install.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to="/demo" className="inline-flex items-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-semibold text-[#c81414] hover:bg-white/90">
              Run the live demo <ArrowRight size={16} />
            </Link>
            <Link to="/how-it-works" className="inline-flex items-center gap-2 rounded-lg px-5 py-3 text-sm font-semibold text-white ring-1 ring-white/70 hover:bg-white/10">
              <Table2 size={16} /> How it works
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function Section({ id, eyebrow, title, tone, children }: { id: string; eyebrow: string; title: string; tone?: "panel"; children: ReactNode }) {
  return (
    <section id={id} className={`scroll-mt-16 border-b border-line ${tone === "panel" ? "bg-panel" : ""}`}>
      <div className="mx-auto max-w-7xl px-4 py-16 md:py-20">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand">{eyebrow}</p>
        <h2 className="mt-2 max-w-3xl text-3xl font-semibold tracking-tight md:text-4xl">{title}</h2>
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
}

function Checklist({ items, ok = false }: { items: string[]; ok?: boolean }) {
  return (
    <ul className="space-y-2.5 text-sm">
      {items.map((t) => (
        <li key={t} className="flex items-start gap-2.5">
          {ok ? <Check size={16} className="mt-0.5 shrink-0 text-pass" aria-label="Yes" /> : <X size={16} className="mt-0.5 shrink-0 text-faint" aria-label="No" />}
          <span className={ok ? "text-ink" : "text-muted"}>{t}</span>
        </li>
      ))}
    </ul>
  );
}

function EvidenceCard() {
  const chain = [
    ["File", "EXIB_regulatory_extract_2026-09.xlsx", "sha256 fe2e7df0…"],
    ["Rows", "10,994 eligible savings accounts", "Deposits sheet, tier S1"],
    ["Rule", "At least 75% of the weighted average gross yield", "pools.savings_min_share_of_wagy"],
    ["Source", "IFPD Circular No. 09 of 2024, para 1", "Primary source"],
  ];
  return (
    <div className="relative self-center" aria-label="Example of a traced figure">
      <div className="absolute -inset-3 -z-0 rounded-[1.6rem] bg-signal/10 blur-2xl" aria-hidden />
      <div className="relative rounded-2xl border border-line bg-surface p-6 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-faint">Profit distribution</p>
            <p className="mt-1 font-medium">Lowest savings tier profit rate</p>
          </div>
          <StatusBadge status="FAIL" />
        </div>
        <p className="num mt-3 text-5xl font-semibold tracking-tight">9.10%</p>
        <p className="mt-1 text-sm text-muted">0.45 percentage points below the 9.55% minimum</p>
        <ol className="mt-6 space-y-3 border-l-2 border-signal pl-4">
          {chain.map(([k, v, s]) => (
            <li key={k} className="grid grid-cols-[64px_1fr] gap-3 text-sm">
              <span className="text-xs font-semibold uppercase tracking-wider text-brand">{k}</span>
              <span>
                <span className="text-ink">{v}</span>
                <span className="block font-mono text-xs text-faint">{s}</span>
              </span>
            </li>
          ))}
        </ol>
        <p className="mt-5 text-xs text-faint">From the stressed demo scenario. Click any number in the demo to see this.</p>
      </div>
    </div>
  );
}
