import { Link } from "react-router";

const pipeline = [
  ["Receive", "The file is fingerprinted with SHA-256 and stored unchanged. That fingerprint follows every number to the report."],
  ["Read and recognise", "Daleel finds the real header row (skipping titles, page break headers and TOTAL rows), works out which dataset each sheet is, and which system produced it (T24, Flexcube or generic)."],
  ["Transform", "Every value is cleaned in DuckDB SQL: thousands separators, DR and CR suffixes, brackets, scientific notation, day first dates, percentages, product spellings. Each fix is counted. Unreadable cells reject their row with a reason; they are never turned into zero. The result is the Daleel Standard Template."],
  ["Reconcile", "The trial balance must balance. The financing portfolio must agree to the financing accounts in the ledger, and the deposit accounts to the deposit accounts."],
  ["Map", "Each GL account is mapped to a reporting code with a full pattern match. Balances are signed debit positive and presented on each code's normal side. Unmapped accounts are reported, not dropped."],
  ["Calculate", "Contracts are classified by days past due using SBP's IFRS 9 Annexure C bands; ECL and Prudential Regulations provisions follow, with the higher of the two for Stage 3. Capital ratios, the leverage ratio and the pool rules (including the 75% savings profit rule) are computed from a dated rulebook. Every result stores its formula, inputs, rules and evidence."],
  ["Explain", "An AI model writes the breakdown, but it never sees a number. It writes placeholders the engine fills, cites SBP excerpts by id, and every sentence is checked for digits, citations, status wording and coverage of every breach. If anything fails twice, a deterministic summary is shown instead."],
];

const stack = [
  ["Backend", "Python, FastAPI, DuckDB (columnar, exact decimals), PostgreSQL with row level security and a hash chained audit log, a job queue inside PostgreSQL"],
  ["AI", "OpenRouter free models for the demo, Ollama for on premises use; retrieval with PostgreSQL full text search over primary SBP documents"],
  ["Frontend", "React, TypeScript, TanStack Query, Tailwind CSS, Server Sent Events for live progress"],
  ["Data", "A seeded generator for the fictional Example Islamic Bank, calibrated to SBP's Islamic Banking Bulletin"],
];

export function HowItWorks() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">How Daleel works</h1>
      <p className="mt-3 text-lg leading-relaxed text-muted">
        Regulatory figures carry personal accountability, so Daleel is built around one idea: every number must be able
        to show its evidence. Here is the path a file takes.
      </p>
      <ol className="mt-8 space-y-5">
        {pipeline.map(([title, text], i) => (
          <li key={title} className="grid grid-cols-[36px_1fr] gap-4">
            <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-soft text-sm font-semibold text-brand">{i + 1}</span>
            <div>
              <h2 className="font-semibold">{title}</h2>
              <p className="mt-1 leading-relaxed text-muted">{text}</p>
            </div>
          </li>
        ))}
      </ol>
      <h2 className="mt-12 text-xl font-semibold">Built with</h2>
      <dl className="mt-4 divide-y divide-line rounded-xl border border-line bg-panel">
        {stack.map(([k, v]) => (
          <div key={k} className="grid gap-1 px-5 py-3 md:grid-cols-[140px_1fr]">
            <dt className="font-medium">{k}</dt>
            <dd className="text-sm text-muted">{v}</dd>
          </div>
        ))}
      </dl>
      <h2 className="mt-12 text-xl font-semibold">Limits, stated plainly</h2>
      <ul className="mt-3 list-disc space-y-2 pl-5 leading-relaxed text-muted">
        <li>SBP's Reporting Chart of Accounts and DAP4 file layouts are given only to banks, so Daleel uses its own illustrative reporting codes and does not produce a certified SBP return.</li>
        <li>Some rule values come from secondary sources or are demo assumptions. The <Link to="/rulebook" className="text-brand hover:underline">rulebook</Link> labels each one.</li>
        <li>The capital calculation uses a simplified standardised approach; market and operational risk come from the bank's own figures.</li>
        <li>In a real bank, customer level data should stay on premises and the AI should run locally, in line with SBP's cloud outsourcing framework.</li>
      </ul>
      <Link to="/demo" className="mt-10 inline-flex rounded-lg bg-brand-fill px-5 py-2.5 text-sm font-medium text-on-brand hover:opacity-90">Try the demo</Link>
    </div>
  );
}
