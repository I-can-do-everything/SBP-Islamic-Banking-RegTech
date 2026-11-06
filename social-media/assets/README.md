# Assets

Images used by the social media drafts. Every image is rendered from source in `src/` (HTML and CSS) with Playwright at 2x scale, so it can be regenerated and edited.

To re-render (from this folder):

```bash
NODE_PATH=$(npm root -g) node src/render.js architecture-overview audit-by-numbers
```

| File | Used by | Shows | Sensitive information check |
|---|---|---|---|
| `architecture-overview.png` | LI-01, LI-04, Blog-01 | System architecture: web app, API, PostgreSQL, workers with DuckDB, object storage, rulebook, AI gateway | Diagram only. No data, hostnames, keys or real bank names. Carries the "Portfolio project. Synthetic data. Not an SBP certified system." footer |
| `audit-by-numbers.png` | LI-02, Blog-01 | Bug counts by severity from the prototype audit, and the sign convention example (11.5% vs -11.5%) | Counts and an illustrative calculation only. No data from any bank |

Screenshots of the running app will be added from milestone M7 onward, captured from the demo bank (EXIB, synthetic data) by the Playwright end to end tests.

## App screenshots (`screens/`)

Captured at 2x by a Playwright script driving the real app (local run, 2026-11-06), using the stressed sample of the fictional Example Islamic Bank. Every value shown is synthetic. No real bank, customer, key, token or private URL appears in any image; the only hashes shown are fingerprints of the synthetic file.

| File | Shows | Used by |
|---|---|---|
| `01-landing.png` | Landing page with a traced figure | LI-17, README |
| `02-demo.png` | Sample selection and upload | LI-05 |
| `03-transformation.png` | Trial balance transformation: fixes, mapping, before and after | LI-06, Blog-02 |
| `04-transformation-financing.png` | Financing sheet: spellings translated, dates and rates converted | LI-15 |
| `05-results.png` | Results: capital, asset quality, profit distribution, checks | LI-08, LI-11, LI-13, Blog-02 |
| `06-evidence-drawer.png` | Evidence panel for the 75% rule | LI-10, LI-14, README |
| `07-breakdown-initial.png` | Deterministic summary shown while the AI writes | Blog-03 |
| `08-breakdown-ai.png` | Grounded AI breakdown and grounding report | LI-16, Blog-03 |
| `09-citation.png` | SBP excerpt quoted word for word | Blog-03 |
| `10-audit.png` | Audit chain verified | LI-12 |
| `11-rulebook.png` | Rulebook with source status | LI-09 |
| `12-review-draft.png` | Review tab before explanations: eight breaches need explaining | LI-11 |
| `13-review-submitted-preparer.png` | Submitted; the preparer cannot approve their own work | LI-11 |
| `14-review-approver.png` | The Head of Compliance reviewing explanations before approving | LI-11 |
| `15-review-approved.png` | Approved and locked, bound to the results fingerprint | LI-11 |
| `16-audit-after-approval.png` | Audit chain verified after the approval | LI-12 |
