# 06. System Design

**Status:** Draft for owner review, 2026-11-06
**Scope:** the full production design of the system, replacing the prototype's partial design.
**Related:**
- [07-guidelines-and-data.md](07-guidelines-and-data.md): official rules and the data plan
- [08-roadmap.md](08-roadmap.md): build order
- [02-bug-register.md](02-bug-register.md): bugs and gaps this design must close

Decisions are numbered `DEC-###`. Each one records the choice, the alternatives and the reason, so the teaching folder can explain why the system looks the way it does.

---

## 1. Product in one paragraph

**Name (working):** SBP Islamic RegTech.

A web application that lets an Islamic bank in Pakistan upload its data and get correct, explainable regulatory figures. The data is the trial balance, the financing portfolio, the deposit pools and the pool income. The figures are capital adequacy, non performing financing and provisioning, expected credit loss, pool profit distribution and the 75% depositor rule, plus Shariah and cross return checks. Every figure can be traced back, in one click, to the exact file, rows, mapping rule, regulatory rule and circular it came from. A preparer submits, a reviewer approves (four eyes). The system produces the report pack and an AI written summary that is checked against the numbers.

It is built as a portfolio product: real architecture, real regulatory logic and a public demo running on synthetic data for a fictional bank, "Example Islamic Bank Ltd (EXIB)".

## 2. Requirements

### 2.1 Functional

| # | Requirement |
|---|---|
| F1 | Upload four dataset types per reporting period: GL trial balance, financing portfolio (contract level), deposit balances (account level, daily or monthly average), pool data (pool assets, income, profit sharing ratios, weightages) |
| F2 | Accept T24, Flexcube and generic layouts in CSV, XLSX and Parquet, with large files uploaded straight to storage |
| F3 | Validate structure and accounting integrity: the trial balance must balance, no duplicate accounts, required fields present, and dates inside the period |
| F4 | Map bank GL codes to SBP reporting codes using versioned mapping sets. AI suggests mappings for new accounts, and a human approves them |
| F5 | Compute regulatory metrics from a versioned rulebook with effective dates, so any past period can be recomputed exactly |
| F6 | Run validation checks: breach, cross return, Shariah, IFRS 9 staging, completeness |
| F7 | Maker checker workflow: draft, submitted, approved or rejected, locked. Every step is audited |
| F8 | Generate a PDF report pack, an Excel workbook and the SBP return file(s) |
| F9 | AI features: executive commentary, mapping suggestions, circular analysis, analyst Q&A. Swappable between cloud (OpenRouter) and local (Ollama) |
| F10 | Tamper evident audit log of every action, viewable and exportable |
| F11 | Multi tenant: many banks on one deployment, each strictly isolated |
| F12 | Public demo mode: read only access to the fictional bank, with no sign up |

### 2.2 Non functional

| # | Requirement | Target |
|---|---|---|
| N1 | Scale | One period of a large bank: 8 million deposit accounts, 600 thousand financing contracts, about 240 million daily deposit balance rows, 30 million schedule rows, about 2,500 GL leaf accounts across 1,150 branches (sizing in [07 section 2.3](07-guidelines-and-data.md)) |
| N2 | Processing time | Full large bank period in under 15 minutes on 8 vCPU and 32 GB RAM. Demo bank in under 30 seconds |
| N3 | API speed | p95 under 300 ms for dashboard reads |
| N4 | Exactness | All money in exact decimal arithmetic. Recomputing the same inputs, mapping version and rule version gives byte identical results |
| N5 | Traceability | Every reported number links to its inputs, rule and source file hash |
| N6 | Security | OWASP ASVS level 2 as the target. Strict tenant isolation. No customer identifiers stored in clear |
| N7 | Availability (demo) | Best effort. (Production design: 99.9% with a standby database) |
| N8 | Cost (demo) | Run on free or near free tiers |
| N9 | Portability | Runs fully on premises (production) or on cloud (demo) with configuration changes only |

## 3. Architecture overview

```
                        +---------------------------------------------+
   Browser              |  Web app (React + TypeScript)               |
   (bank staff,         |  Public site and case study (Astro)         |
    demo visitors)      +----------------------+----------------------+
                                               | HTTPS (JSON, SSE)
                                               v
                        +---------------------------------------------+
                        |  API service (FastAPI, async)                |
                        |  auth, tenancy, workflow, read models,      |
                        |  presigned upload URLs, progress stream      |
                        +-----+----------------+-----------------+----+
                              |                |                 |
                 enqueue jobs |                | SQL             | presign
                              v                v                 v
   +--------------------------+--+   +------------------+   +------------------------+
   | Job queue (in PostgreSQL)   |   | PostgreSQL       |   | Object storage (S3 API) |
   | durable, transactional      |   | metadata, results|   | raw files (immutable),  |
   +--------------+--------------+   | rulebook, audit  |   | Parquet data lake,      |
                  |                  | row level        |   | reports                 |
                  v                  | security         |   +-----------+------------+
   +-----------------------------+   +--------+---------+               ^
   | Worker(s) (Python)          |------------+                         |
   | DuckDB engine per job:      |------------------------------------- +
   | ingest, normalise, compute, |   reads raw, writes Parquet, reports
   | validate, report            |
   +--------------+--------------+
                  |
                  v
   +-----------------------------+
   | AI gateway                  |---> OpenRouter (demo and testing)
   | (OpenAI compatible client)  |---> Ollama on premises (production)
   +-----------------------------+
```

### DEC-001. A modular monolith with separate workers, not microservices

- **Choice:** One Python codebase, deployed as two process types: the `api` and the `worker`. Inside, it is split into strict domain modules (section 5).
- **Alternatives:** microservices; a single process.
- **Why:** The heavy work (crunching hundreds of millions of rows) must not block the API. That requires separate workers, not separate codebases. Microservices would add network calls, distributed transactions and deployment cost with no benefit at this team size. Module boundaries are enforced in code (import rules checked in CI), so any module can be split out later if it ever needs to scale on its own.

### DEC-002. Two storage engines: PostgreSQL for state, Parquet plus DuckDB for bulk data

- **Choice:**
  - Bulk rows (deposit daily balances, financing contracts, transactions) are stored as **Parquet** files in object storage and processed with **DuckDB** inside the workers.
  - **PostgreSQL** holds everything transactional and everything the UI reads: tenants, users, submissions, mapping sets, the rulebook, aggregated balances, metric results with lineage, validation results, approvals, the audit log and the job queue.
- **Alternatives:** everything in PostgreSQL; Spark; a cloud warehouse (BigQuery, Snowflake).
- **Why:**
  - About 240 million daily balance rows per period (large bank profile) would bloat PostgreSQL, slow its backups and fight the API for resources.
  - Parquet is columnar and compressed, often 5 to 10 times smaller than CSV, and is an open standard.
  - DuckDB is an embedded analytical engine. It processes Parquet with all CPU cores, streams data larger than memory, and has exact `DECIMAL(38, s)` arithmetic.
  - It needs no cluster, so the same code runs on a laptop, a bank server or a cloud container.
  - Spark would be over sized and costly. Cloud warehouses break on premises deployment (N9) and SBP's data localisation expectations.
- **Pattern name:** "lakehouse lite" with a medallion layout (CON-090):
  - `raw/`: the original upload, never changed
  - `bronze/`: parsed to typed Parquet, as received
  - `silver/`: cleaned, validated and pseudonymised
  - `gold/`: aggregated to regulatory reporting codes

### DEC-003. A job queue inside PostgreSQL

- **Choice:** A PostgreSQL backed job queue (the Procrastinate library, which uses `SELECT ... FOR UPDATE SKIP LOCKED`), with jobs chained into a pipeline.
- **Alternatives:** Celery with Redis or RabbitMQ; Temporal; cloud queues.
- **Why:** A job is enqueued in the same database transaction that creates the submission, so a submission can never exist without its job, or a job without its submission (the transactional outbox idea, CON-091). It adds no new infrastructure to run, back up or secure, and the throughput is far more than a reporting workload needs. Temporal is excellent for long workflows but would add a cluster to the demo. If one is ever needed, the pipeline steps are written as idempotent functions, so moving them is mechanical.

### DEC-004. Direct to storage uploads with integrity checks from end to end

- **Choice:**
  1. The browser asks the API for a presigned multipart upload URL and sends the file straight to object storage in parallel chunks, which can be resumed.
  2. The browser computes the file's SHA-256 while reading it (Web Crypto, streamed).
  3. The worker recomputes the hash from storage. If the two hashes differ, the submission is rejected.
  4. The raw bucket has versioning and object lock (write once), so an uploaded file can never be changed.
- **Why:** Gigabyte files never pass through the API, which stays fast and cheap. The double hash proves the file the system processed is the file the user sent. That is the chain of custody (CON-012).

## 4. Processing pipeline

Each step is an idempotent job. Running it again with the same input gives the same output, so a failed step can simply be retried. Every step writes its status, timings and counts to the database, and publishes progress to the UI over Server Sent Events (DEC-011).

```
UPLOADED
   |  1. verify      hash check, virus/type check, register dataset version
   v
   |  2. profile     detect CBS layout from headers, infer schema, row count, encoding
   v
   |  3. parse       raw -> bronze Parquet with an explicit schema per layout
   v                (DuckDB read_csv / read_xlsx with exact DECIMAL types)
   |  4. clean       bronze -> silver: sign rules, date rules, pseudonymise identifiers,
   v                reject rows with reasons (kept in a rejects file, never dropped)
   |  5. integrity   trial balance balances, contract totals reconcile to GL control
   v                accounts, deposit totals reconcile to GL
   |  6. map         join to the mapping set version -> gold balances per reporting code,
   v                unmapped report, mapping coverage percent
   |  7. compute     metric graph (DEC-006) using the rulebook as of the period end
   v
   |  8. validate    validation rules -> PASS / WARNING / FAIL with evidence
   v
   |  9. narrate     AI commentary from aggregated results only, number grounding check
   v
READY FOR REVIEW -> SUBMITTED -> APPROVED (locked, report pack generated) or REJECTED
```

**Reconciliation is central (step 5).** The financing portfolio total must equal the financing control accounts in the trial balance, and the deposit totals must equal the deposit accounts. Differences above a tolerance are a FAIL. This is how real regulatory reporting catches missing branches or extraction errors, and it is what makes the numbers trustworthy (CON-027).

## 5. Domain modules (backend)

```
backend/src/regtech/
  core/          settings, logging, errors, decimal context, ids, time
  tenancy/       institutions, row level security session setup
  identity/      users, roles, login, tokens, MFA, sessions
  audit/         append only, hash chained audit events
  storage/       object storage client, presigned URLs, lake paths
  datasets/      dataset types, canonical schemas, layouts (T24, Flexcube, generic)
  ingestion/     verify, profile, parse, clean, integrity (DuckDB)
  mapping/       mapping sets, versions, rules, apply, unmapped, AI suggestions
  rulebook/      regulatory rules with effective dates and sources (REG ids)
  metrics/       metric graph engine plus metric definitions:
                   capital (CAR), asset_quality (classification, NPF, provisions),
                   ecl (IFRS 9 stages, PD x LGD x EAD), pools (WAGY, 75% rule,
                   PER, IRR, distribution), liquidity (later)
  validation/    validation rule engine and rule definitions
  workflow/      submission state machine, maker checker approvals
  reporting/     PDF (Typst), Excel (XlsxWriter), SBP return files
  ai/            gateway, prompts, schemas, grounding checks, evaluations
  jobs/          queue tasks that call the modules above
  api/           FastAPI routers, request and response schemas, SSE
```

Rule: a module may import only `core` and the modules listed for it in an import contract, which CI checks with `import-linter`. This keeps the monolith modular (DEC-001).

### DEC-005. A rulebook held as versioned data, with effective dates

- **Choice:** Every regulatory number (minimum CAR, days past due bands, provision rates, risk weights, the 75% factor, and so on) is a rule record:

  ```yaml
  id: capital.car.minimum_total
  value: "11.50"
  unit: percent
  effective_from: 2019-12-31
  effective_to: null
  source: REG-002          # links to docs/05-regulatory-verification.md
  verification: verified_primary
  ```

  Rules live in `rulebook/*.yaml` in git (reviewed like code) and are loaded into PostgreSQL as an immutable version. A calculation asks for a rule *as of the period end date*.
- **Why:**
  - Regulations change. Recalculating March 2024 must use the rules in force in March 2024.
  - Each number carries its source and verification status, so an unverified rule can be shown with a warning on screen and in reports.
  - New circulars become reviewable data changes, not code changes.
  - Pattern names: "regulation as code" and "bitemporal data" (CON-092).

### DEC-006. Metrics as a dependency graph with lineage

- **Choice:** Each metric is a small pure function that declares its inputs:

  ```python
  @metric("asset_quality.npf_ratio", unit="percent",
          inputs=["asset_quality.npf_total", "asset_quality.gross_financing"],
          rules=["asset_quality.npf_alert_threshold"])
  def npf_ratio(npf_total: Money, gross_financing: Money, rules: Rules) -> Ratio: ...
  ```

  The engine builds the graph, runs it in dependency order, and stores every result with its lineage:
  - the input values and their own lineage
  - the rule versions used
  - the mapping version used
  - the dataset hashes
  - the code version (git commit)
- **Why:** This is what makes "click any number to see where it came from" possible (CON-081). It also gives automatic recomputation of only the affected metrics when an input changes, and makes each metric unit testable on its own.

### DEC-007. Exact money arithmetic everywhere

- **Choice:**
  - Python `Decimal` with an explicit context: 38 digits of precision, ROUND_HALF_EVEN.
  - DuckDB `DECIMAL(38, 4)` for amounts.
  - PostgreSQL `NUMERIC(38, 4)` for amounts.
  - Amounts travel as strings in JSON.
  - Rounding happens only at presentation, using a documented rule.
- **Why:** Fixes the class of bugs in BUG-019 and enforces N4. Banker's rounding (half to even) avoids the upward bias of always rounding halves up.

### DEC-008. One sign convention, settled at the silver layer (closes FIX-015)

- **Choice:**
  - Raw and bronze data keep the bank's own signs.
  - At silver, every amount is stored as signed *debit positive*, which is the ledger convention.
  - Each reporting code carries its normal balance (debit or credit).
  - The gold layer adds a `presented_amount`, which is positive on the account's normal side.
  - Metrics read only presented amounts.
  - An account sitting on its abnormal side (for example an overdrawn deposit) triggers a validation WARNING with the account listed.
- **Status:** Adopted, following standard accounting practice. The owner can override this decision.

### DEC-009. Gross financing defined explicitly (closes FIX-033)

- **Choice:** Gross financing = performing plus non performing financing, before provisions. It is derived from the contract level portfolio (classification by days past due) and reconciled to the GL.
- **Note:** This removes the need to guess from account code naming. Classification comes from the contract data, as the Prudential Regulations require.
- **Status:** Adopted. The owner can override this decision.

## 6. Data model (PostgreSQL)

Main tables (the full DDL comes with the migrations, which use Alembic):

| Table | Purpose | Notes |
|---|---|---|
| `institution` | tenants (banks) | |
| `app_user`, `role_assignment` | users and roles per institution | roles: PREPARER, REVIEWER, APPROVER, ADMIN, AUDITOR (read only), DEMO_VIEWER |
| `reporting_period` | period per institution (month or quarter end) | |
| `submission` | one run of the pipeline for a period, versioned (v1, v2 ...) | state machine column, optimistic locking |
| `dataset_version` | each uploaded file: type, layout, sha256, storage keys per layer, row counts, schema version | immutable once verified |
| `ingest_reject` | summary of rejected rows with reasons, plus a link to the rejects Parquet | |
| `mapping_set`, `mapping_version`, `mapping_rule` | versioned GL to reporting code mapping | rule match by exact code or anchored pattern (FIX-018), priority, and an overlap check |
| `reporting_code` | SBP reporting codes, description, normal balance, hierarchy | seeded from the official structure where public |
| `gold_balance` | aggregated balances per submission and reporting code | **partitioned by period** (range) |
| `rule`, `rule_version` | the rulebook (DEC-005) | |
| `metric_result` | value, unit, status, lineage (JSONB), rule versions | partitioned by period |
| `validation_result` | check id, status, evidence (JSONB) | |
| `approval` | maker checker actions with comments | approvers cannot approve their own submission |
| `report_artifact` | generated files, hash, storage key, expiry | |
| `ai_interaction` | provider, model, prompt version, input hash, output, tokens, cost, grounding result | input payloads are aggregated data only |
| `audit_event` | append only, hash chained (DEC-010) | **partitioned by month** |
| `job` tables | queue (Procrastinate) | |

### Multi tenancy (DEC-012)

Every tenant owned row has `institution_id`. PostgreSQL **row level security** policies allow access only to rows whose `institution_id` equals the session's `app.institution_id`, which the API sets at the start of each request from the verified token. Even a bug in the API's own query filters cannot leak another bank's data. Workers run as a separate database role, scoped per job.

### Partitioning and indexing

- Large tables are range partitioned by period, so old periods can be archived or moved to cheaper storage, and queries for one period touch one partition.
- Composite B-tree indexes on `(institution_id, submission_id, ...)` serve the main lookups.
- BRIN indexes on time columns of the audit log, which is cheap for append only data.
- `pg_stat_statements` is enabled to watch slow queries.

## 7. Security design

| Area | Design |
|---|---|
| Passwords | Argon2id (memory hard, current best practice), length 12 to 128 (fixes BUG-043) |
| Tokens | Short lived access token (15 min, held in memory). Rotating refresh token in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie. Refresh token reuse detection revokes the whole session family |
| Signing | Asymmetric (EdDSA) JWT signing keys, rotated, with a key id in the header. The app refuses to start with a default or weak key in production (fixes BUG-038) |
| MFA | TOTP required for APPROVER and ADMIN |
| Authorisation | Role based checks in the API, plus row level security in the database (defence in depth, CON-083). Maker checker rule enforced in both the API and a database constraint |
| Identifiers | Customer identifiers (CNIC, account numbers) are pseudonymised at the silver layer with keyed HMAC-SHA256. The key is kept outside the database. Reports never show customer identifiers |
| Data in transit and at rest | TLS everywhere. Storage encryption. Database encryption at rest from the provider (demo) or the disk (on premises) |
| Web | Strict Content Security Policy, CSRF protection for cookie endpoints, secure headers, file type checks by content (magic bytes), size limits, zip bomb guard for XLSX |
| Rate limits | Per user and per IP limits on login, upload and download. Kept in PostgreSQL for the demo, with Valkey as the upgrade path |
| Audit | Every login, upload, mapping change, rule change, approval, download and AI call is an audit event |
| Secrets | Environment or secret manager only. Never in git (closes BUG-047 together with the `.gitignore` fix) |
| Supply chain | Locked dependencies (uv and pnpm lock files), Dependabot, `pip-audit`, `pnpm audit`, container image scanning |

### DEC-010. Tamper evident audit log

- **Choice:** Each audit event stores `hash = SHA-256(previous_hash + canonical JSON of the event)`. The database role used by the app can only `INSERT` into the table (no `UPDATE` or `DELETE`, enforced by grants and a trigger). A daily job writes the latest hash (the "anchor") to the immutable raw bucket. A verification endpoint recomputes the chain.
- **Why:** If anyone edits or deletes a past event, every later hash stops matching, and the break shows exactly where. Auditors and regulators expect this kind of integrity (CON-093).

## 8. API design

- REST under `/api/v1`, described by OpenAPI 3.1, which FastAPI generates.
- The TypeScript client for the frontend is **generated** from the OpenAPI document, so a backend change that breaks the frontend fails the build (end to end type safety).
- `Idempotency-Key` header on POST requests that start work, so a double click or retry never runs a pipeline twice.
- Cursor pagination for lists. ETags for cacheable reads.
- Errors follow RFC 9457 (problem details) JSON.
- **DEC-011:** Progress uses Server Sent Events, fed by PostgreSQL `LISTEN/NOTIFY`. This is simpler than WebSockets for one way updates, works through proxies, and reconnects automatically.

Main resources:

```
POST /auth/login  /auth/refresh  /auth/logout  /auth/mfa/verify
GET  /institutions/me
POST /periods/{id}/submissions                 create submission (draft)
POST /submissions/{id}/datasets                request presigned upload
POST /submissions/{id}/datasets/{d}/complete   confirm upload, start pipeline
GET  /submissions/{id}                          status, counts
GET  /submissions/{id}/events                   SSE progress stream
GET  /submissions/{id}/metrics                  results
GET  /metrics/{id}/lineage                      lineage tree for one number
GET  /submissions/{id}/validations
GET  /submissions/{id}/unmapped
POST /submissions/{id}/submit | /approve | /reject
GET  /submissions/{id}/reports/{kind}           expiring download link
GET/POST /mapping-sets ...  /mapping-suggestions (AI)
GET  /rulebook?as_of=YYYY-MM-DD
GET  /audit-events?cursor=...  GET /audit-events/verify
POST /ai/ask                                    analyst Q and A (tool calling)
GET  /health  /ready
```

## 9. AI design

### DEC-013. One gateway, two providers

- **Choice:** One `AIGateway` built on the OpenAI compatible chat API, which both OpenRouter and Ollama support. Configuration selects the provider:
  - `AI_PROVIDER=openrouter` for testing and the demo
  - `AI_PROVIDER=ollama` for production on premises
- Model names per task live in configuration (see [07-guidelines-and-data.md](07-guidelines-and-data.md) section 4 for the current recommendations).

### Rules every AI feature follows

1. **Data minimisation.** The gateway accepts only typed payloads (Pydantic models) built from aggregated results. A payload type that could carry customer level rows does not exist, so it cannot be sent by mistake.
2. **Structured output.** Responses must match a JSON schema. Invalid output is retried once, then the feature falls back to a template.
3. **Number grounding.** Every number in AI text is extracted and matched against the metric results it was given (within rounding). Unmatched numbers are flagged as hallucinations, and the text is shown with the flags or blocked (CON-077).
4. **Determinism.** Temperature 0 and a fixed seed where supported. Prompts are versioned files in git.
5. **Human in the loop.** AI never changes data. Mapping suggestions and rulebook changes from circulars are *proposals* that a human accepts.
6. **Full audit.** Model, prompt version, input hash, output, token usage and cost are stored for each call.
7. **Evaluations.** A small golden set per task (inputs with expected properties) runs in CI against the configured model, so a model change is measured, not guessed (CON-094).
8. **Privacy settings on OpenRouter.** Request only zero data retention providers that do not train on data (`zdr: true`, `data_collection: "deny"`). Even so, only synthetic data is ever sent to a cloud model. Under SBP's cloud framework (REG-017), sending real customer level data offshore would need SBP approval, which is why production uses Ollama on premises.

### AI features

| Feature | How it works |
|---|---|
| Executive commentary | Metric results, trends and breaches go in. Out comes JSON with headline, key points (each citing metric ids) and risks. Then the grounding check runs |
| Mapping suggestions | Embedding similarity between the GL description and reporting code descriptions shortlists candidates. A small model reranks them and explains its choice. The user accepts or edits, and accepted mappings become a new mapping version |
| Circular watcher | A scheduled job fetches the SBP IFPD and BPRD circular index pages, finds new items and extracts their text. The model summarises and extracts proposed rule changes as JSON matched to rulebook ids. A compliance user reviews and accepts, which creates a new rulebook version |
| Analyst Q and A | Tool calling agent with read only tools (`get_metric`, `compare_periods`, `get_lineage`, `list_breaches`). It cannot see raw data. Answers cite metric ids |

## 10. Frontend and design

### DEC-014. React app for the product, Astro for the public site

- **Choice:**
  - **Product app:** React 19, TypeScript, Vite, TanStack Router (type safe routes), TanStack Query (server state and caching), TanStack Table with TanStack Virtual (virtualised grids that show 100 thousand rows smoothly), Tailwind CSS v4 with design tokens, accessible headless components (Radix based), and Apache ECharts for charts.
  - **Public site:** Astro, for the landing page, case study and docs. It is static, fast and good for SEO. This keeps the original Astro choice where it fits best.
- **Why:** The product is an authenticated, highly interactive data application. That is where a client side React app with strong data tooling is the better fit. Astro is best for content pages. Both share one design token file.

### Design philosophy: context relevant design (CON-080)

**Who uses it:** regulatory reporting officers, compliance heads, finance controllers and auditors. They work under deadlines, are personally accountable for every number, and spend long sessions reading tables. Errors carry penalties.

**What the design must therefore do:**

| Principle | What it means on screen |
|---|---|
| Trust through traceability | Every figure is a link. Clicking it opens a side panel with formula, inputs, rule and circular, mapping version and file hash. Nothing is a dead end |
| Calm density | Lots of data per screen, but quiet: a neutral palette, generous line height, clear grouping, and no decorative animation. Motion is used only to show cause and effect |
| Numbers first | Tabular (fixed width) digits, right aligned, consistent decimals, units always shown, negative numbers in brackets as accountants write them, PKR with a choice of millions or full figures |
| Status never by colour alone | PASS, WARNING and FAIL each have an icon, a word and a colour, and the colours are checked for colour blindness and contrast (WCAG 2.2 AA) |
| Accountability visible | Who prepared, who reviewed, when, and which version are always shown in the header of a submission. Locked periods look locked |
| Progressive disclosure | Overview first (status of all ratios), then category, then metric, then lineage, then rows |
| Keyboard first | Power users can move through tables and approve with the keyboard. A command palette (Ctrl+K) is available |
| Bilingual ready | English first. Layout and fonts prepared for Urdu (right to left) later |

**Visual identity (draft, superseded by [DEC-025](#dec-025-signal-red-brand-and-a-landing-page-inside-the-app)):**
- Base colours: a deep, desaturated green (a nod to Islamic finance without cliché) with slate neutrals. A muted gold accent is used only for the approval state.
- Light and dark themes.
- Typography: Inter for the interface and IBM Plex Mono for codes and hashes. Noto Nastaliq Urdu is reserved for future Urdu text.
- A subtle geometric (girih inspired) line pattern appears only on the public site and empty states, never behind data.

**Key screens:**
1. Period dashboard
2. Upload and live pipeline progress
3. Reconciliation
4. Unmapped accounts and AI suggestions
5. Metric explorer with lineage panel
6. Validation results
7. Review and approve
8. Report pack
9. Rulebook timeline
10. Audit log with chain verification
11. Circular watcher inbox

## 11. Reporting

- **PDF report pack** made with **Typst** (DEC-015). Typst is a modern typesetting engine, much faster than browser based PDF, with precise layout for tables, and its templates are plain text kept in git. The pack contains:
  - cover with institution, period, version and approval status
  - summary dashboard
  - each ratio with formula and inputs
  - breaches and validation results
  - AI commentary marked as AI generated, with its grounding result
  - appendix with dataset hashes, mapping and rule versions, the audit chain anchor and the disclaimer
- **Excel workbook** made with XlsxWriter in constant memory mode, with one sheet per return.
- **SBP return files** in the format SBP specifies (see 07 section 2.4). Until the official file specification is confirmed, the export is clearly marked "format not certified" (closes FIX-037).

## 12. Deployment

| Environment | Setup |
|---|---|
| Local | `docker compose up`: PostgreSQL 17, MinIO (S3 compatible), api, worker, web, and optional Ollama (compose profile `local-ai`). Seed command loads the demo bank |
| Demo (cloud) | Web and public site on Cloudflare Pages. API and worker as containers on Fly.io (or Render). Managed PostgreSQL (Neon or Supabase). Cloudflare R2 object storage. All on free or low cost tiers |
| Production (bank, reference design) | On premises Kubernetes or VMs (or an onshore cloud provider approved under SBP's cloud framework, BPRD C01/2023, REG-017), PostgreSQL with streaming replica and point in time recovery, S3 compatible storage with object lock (MinIO or a bank appliance), Ollama on a GPU server, and an identity provider through OIDC. No customer data leaves the bank |

### DEC-016. Infrastructure as code and CI

- GitHub Actions on every push:
  - lint (ruff, eslint)
  - type check (pyright strict, tsc)
  - unit and property tests
  - integration tests with real PostgreSQL and MinIO containers (Testcontainers)
  - import contracts
  - AI evaluations (on demand, because they cost tokens)
  - Playwright end to end tests
  - container build and scan
- Deploys from `main` to the demo after the checks pass.
- Docker images are multi stage, run as non root, and use slim base images.

## 13. Observability

- Structured JSON logs (structlog) with request id, tenant and job id. Never log amounts tied to identifiers.
- OpenTelemetry traces across api, queue and worker, so one upload can be followed through every step.
- Metrics: job duration per step, rows per second, queue depth, API latency, AI tokens and cost.
- Error tracking with Sentry (free tier) in the demo.

## 14. Testing strategy

| Level | Tool | What it proves |
|---|---|---|
| Unit | pytest | Each function, including every bug from 02 as a regression test |
| Property based | Hypothesis | Rules that must hold for any input. Examples: apportionment always conserves the total; parsing then formatting gives the original amount; a balanced trial balance stays balanced after mapping |
| Golden calculations | pytest with hand worked cases | Every metric matches a worked example prepared by the accountant role and written into the docs |
| Integration | Testcontainers | The real pipeline on PostgreSQL and MinIO |
| Contract | generated OpenAPI client | Frontend and backend agree |
| End to end | Playwright | Main user journeys. Also produces the screenshots for social media (synthetic data only) |
| Load | Locust (API), pipeline benchmark script | N1 to N3 targets on the large synthetic bank |
| AI evals | small golden sets | Commentary grounding rate, mapping top 3 accuracy, extraction accuracy |

## 15. Repository layout (target)

```
/backend            Python package regtech (uv project), Alembic migrations, tests
/web                React product app
/site               Astro public site and case study
/rulebook           versioned YAML rules (DEC-005)
/mappings           mapping sets per institution (demo bank included)
/datagen            synthetic data generator (see 07)
/infra              docker compose, Dockerfiles, Fly and Cloudflare configs
/docs               documentation (this folder), later docs/learn/
/social-media       LinkedIn posts, blog articles, screenshots
```

The prototype's `backend/app` code is replaced module by module. Each prototype bug is closed either by a fix carried into the new module, or by the module being redesigned. The fix log records which.

## 16. Open questions for the owner

1. Is the working name fine, and is the fictional bank name "Example Islamic Bank Ltd (EXIB)" acceptable?
2. Demo hosting: Fly.io plus Neon plus Cloudflare (proposed), or another preference?
3. Should the public demo let visitors upload their own small file, or stay read only? Read only is safer and is proposed.

---

## Decisions taken during the build (2026-11-06)

### DEC-018. Name: Daleel
"Daleel" (دليل) is Arabic for evidence or proof. In Islamic scholarship a ruling must come with its *daleel*. That matches the product's one idea: every figure carries its evidence. Tagline: "an Islamic bank regulatory compliance tool". The demo bank stays "Example Islamic Bank Ltd (EXIB)", so it cannot be mistaken for a real bank.

### DEC-019. Grounded narrative protocol (hallucination designed out)
- **Choice:** The model receives facts *without values* and writes placeholders that the app fills with phrases rendered by the engine. Replies are validated for:
  - digits outside placeholders
  - placeholder ownership
  - citation existence and relevance
  - status wording
  - label fidelity
  - breach coverage

  The model gets one retry; after that a deterministic template is used.
- **Alternatives:**
  - letting the model see numbers and then checking them: it can still mis-copy or round
  - fine tuning: costly, and still probabilistic
  - no AI at all: loses the plain language value
- **Why:** A model that never receives a digit cannot output a wrong one, so the numeric hallucination risk is removed rather than reduced. The remaining risks are wording risks, and the validator covers them.

### DEC-020. Lexical retrieval, structured first
- **Choice:** PostgreSQL full text search over primary SBP documents, preferring the exact clause a rule cites (`retrieve_for_rules`).
- **Alternatives:** an embeddings model plus pgvector.
- **Why:**
  - Regulatory text is precise. Lexical search finds "Mudarib share" or "weightages" exactly.
  - It is free and deterministic, and runs inside the same database.
  - The rule to clause link is known in advance, so semantic search adds little.
  - Embeddings remain an easy upgrade.

### DEC-021. One container for the demo
- **Choice:** The API serves the built web app and runs the worker in a thread (`EMBEDDED_WORKER`), with one image and one URL. See [09-deployment.md](09-deployment.md) (DEC-017) for the free hosting stack.
- **Why:** Free hosts give one container. Splitting the services later only needs `daleel worker` and a static host for `web/dist`.

### DEC-022. Instant deterministic summary, AI when ready
- **Choice:** The calculate step stores a template summary at once. The narrate step replaces it with the AI version when the model answers.
- **Why:** Free models can take minutes. The user should never wait for the AI to see verified results.

### Benchmark: the N1 and N2 scale targets (measured 2026-11-06)

`backend/benchmarks/daily_balances.py` on the build machine: 4 vCPU, 15 GB RAM, DuckDB 2.0.

| Profile | Rows | Write Parquet | Average per account, then per tier |
|---|---|---|---|
| 2 million accounts x 30 days | 60 million | 10.3 s (280 MB) | 0.9 s (66 million rows/s) |
| 8 million accounts x 30 days (large bank, N1) | 240 million | 41.0 s (1.1 GB) | 3.9 s (61 million rows/s) |

The heaviest step of the large bank profile takes seconds, far inside the 15 minute target (N2), using exact `DECIMAL(38,4)`. This supports DEC-002.

### DEC-023. Four eyes approval enforced by the database
- **Choice:** Submission, approval and rejection are rows in an append only `approval` table. A trigger checks every rule before a row is accepted:
  - roles
  - every breach explained before submission
  - nobody decides on a submission they uploaded or submitted
  - a rejection needs a reason
  - an approval must match the SHA-256 fingerprint of the results taken at submission

  Approval locks the submission, and triggers then refuse any change to its results, data or upload.
- **Alternatives:** checking the rules in the API only; a workflow engine.
- **Why:**
  - Maker checker is a control auditors test. A control that lives only in application code can be bypassed by a bug or a direct database change; a trigger cannot.
  - Binding the approval to a fingerprint means the approver provably approved exactly what was submitted.
- **Demo:** Each workspace has three people (preparer, approver, and an administrator who can do either, but never both on one submission). A visitor can switch between them (`DEMO_PERSONAS`). In production each person signs in separately and the switch is off.

### DEC-024. Setup wizard
See [09-deployment.md](09-deployment.md#dec-024-a-setup-wizard-instead-of-a-deployment-manual).

### DEC-025. Signal red brand and a landing page inside the app
- **Choice:** The owner set the brand colour to #ff2c2c. The interface is built on warm paper and near black ink, with that red as the one strong colour. The red is split into roles, because a single red cannot do every job and stay readable:

  | Token | Light | Dark | Job | Contrast (WCAG 2.2) |
  |---|---|---|---|---|
  | `signal` | #ff2c2c | #ff2c2c | The exact brand red, for large marks only: the star mark, the hero underline, top bars, the favicon | 3.7:1 on white, enough for large shapes (3:1), not for small text |
  | `brand` | #d41c1c | #ff5a52 | Red text and links | 5.3:1 on white, 4.7:1 on its soft tint; 5.9:1 on the dark panel |
  | `brand-fill` + `on-brand` | #d41c1c with white | same | Buttons and the landing page's closing band | 5.3:1 |
  | `fail` | #9f1239 | #fb7185 | Breaches, a crimson rose kept visibly different from the brand red | 8.0:1 and 6.8:1 |
  | `faint` | #776b67 | #958884 | The quietest text (labels, captions) | at least 4.5:1 on every background it sits on |

  Passing steps and approvals stay green, so a red brand never makes success look like failure.
- **Alternatives:**
  - #ff2c2c everywhere. Rejected: white text on it is 3.7:1 and red text on white is the same, both below the 4.5:1 floor for body text.
  - A separate Astro site for the landing page (the plan in DEC-014). Rejected for now: one deployable on a free host is simpler, and the landing page reuses the app's tokens, fonts and components, so the two can never drift apart.
- **Why:**
  - **Context relevant design (CON-080):** compliance staff read red as risk. The brand red is therefore used for identity and calls to action, never for data, while breaches use their own rose red with an icon and the word "Breach" (status is never shown by colour alone).
  - **The landing page has one job:** say plainly what the showcase is, what problem it solves and how it differs from national and international products, with sources. It leads with a real traced figure from the demo (the "evidence card"), because the claim "every figure carries its evidence" is more convincing shown than told.
- **Competitor comparison:** written from public product pages, linked on the page, with a note that it compares approaches, not feature lists, and that the products named are mature commercial systems.

### DEC-026. Separate worker lanes for slow AI jobs
- **Choice:** Each process runs two queue workers. One takes every job except the AI write-up (ingest, calculate); the other takes only the AI write-up. Both claim jobs with `FOR UPDATE SKIP LOCKED`, so they never take the same job. A job still marked running after 15 minutes is treated as abandoned and goes back in the queue, or fails if it has used its attempts.
- **Alternatives:** one worker (what we had: see BUG-059); a thread per job (no limit on load); a separate queue service.
- **Why:** A free AI model can take minutes. With one worker, one visitor's AI wait stopped every other visitor's upload from being processed. Lanes keep the fast, deterministic work fast. The stale job rule covers a free host restarting mid job (BUG-060).

