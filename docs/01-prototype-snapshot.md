# 01. Prototype Snapshot

**Snapshot date:** 2026-11-06
**Commit examined:** `e96988c` (feat(calculations): Add Pool Management Calculations)
**Branch:** `claude/keen-newton-6bi1jn`

This document describes what the system is meant to be and exactly what exists in the repository at the snapshot date. Bugs are listed separately in [02-bug-register.md](02-bug-register.md). Concepts named here are explained in [04-concepts-register.md](04-concepts-register.md) (look for the `CON-###` tags).

---

## 1. What the system is

A **regulatory reporting system for Islamic banks in Pakistan**.

Every bank regulated by the State Bank of Pakistan (SBP, CON-030) must send it figures that show the bank is safe and Shariah compliant. Examples are how much capital the bank holds against its risks (CAR, CON-040) and how much of its financing has gone bad (NPF ratio, CON-038). Islamic banks have extra rules about how profit is shared with depositors (pool management, CON-043).

In most banks this work is semi manual. Someone exports a trial balance (CON-020) from the core banking system (CON-022), reworks it in spreadsheets to match SBP's Reporting Chart of Accounts (RCOA, CON-024), calculates the ratios, checks them, and prepares the submission. That is slow, error prone and hard to audit.

This system automates that chain and keeps a full audit trail from the uploaded file to the final number.

## 2. Who it is for

| User | What they need from the system |
|---|---|
| Uploader (bank finance or regulatory reporting officer) | Upload the monthly or quarterly trial balance, see processing progress, fix mapping problems |
| Reviewer (compliance officer, head of regulatory reporting) | See ratios, breaches and warnings, read the commentary, approve before submission |
| Admin | Manage users, institutions and mapping rules |
| Auditor (internal, external, or SBP inspection) | Trace any reported number back to the exact file and accounts it came from |

The roles `UPLOADER`, `REVIEWER` and `ADMIN` appear in `backend/app/schemas/submission.py` (line 233).

## 3. Intended design: a layered pipeline

The code describes a pipeline of layers. Each layer takes the output of the one before it.

```
 Bank's core banking system (T24, Flexcube, other)
              |
              |  trial balance export (CSV or XLSX)
              v
 +---------------------------+
 | Layer 1: Ingestion        |  detect file format, read balances exactly,
 | layers/ingestion/         |  fingerprint the file (SHA-256)
 +---------------------------+
              |  list of {account_code, description, balance}
              v
 +---------------------------+
 | Layer 2: Normalisation    |  map bank account codes to SBP RCOA codes
 | layers/normalisation/     |  (direct, aggregation, apportionment), sum per RCOA code
 +---------------------------+
              |  {RCOA code: balance}
              v
 +---------------------------+
 | Layer 3: Calculations     |  NPF ratio, CAR, pool management ratios,
 | layers/calculations/      |  breach flags, formula and inputs kept for audit
 +---------------------------+
              |
              v
 +---------------------------+
 | Layer 4: Validation       |  cross return checks, DFS format, Shariah,      (not built)
 |                           |  breach, IFRS 9 staging
 +---------------------------+
              |
              v
 +---------------------------+
 | Layer 5: Reporting        |  PDF report, DFS submission file,                (not built)
 |                           |  AI commentary from a local LLM
 +---------------------------+
```

Around the pipeline:

- **API** (FastAPI, CON-060): upload, list submissions, view results, download reports, audit log. (Not built.)
- **Database** (Supabase PostgreSQL, CON-063): submissions, normalised balances, ratios, validation results, users, audit log. (Not built.)
- **Security**: JWT login (CON-066), bcrypt password hashing (CON-067), roles, rate limits, time limited download links. (Settings exist, code does not.)
- **Frontend** (Astro, CON-070): login, dashboard, upload, submissions list and detail, audit log pages. (File names exist, all empty.)
- **AI commentary** (Ollama, CON-075): a local model writes a plain language summary of the results. Temperature 0 so the output is repeatable, plus "hallucination flags" that catch claims not supported by the numbers. Local only, so bank data never leaves the bank. (Settings and response schema exist, code does not.)
- **SBP circular monitor**: checks SBP web pages every 6 hours for new rules. (Settings exist, code does not.)
- **Deployment**: Docker (CON-072), Caddy web server (CON-073). (Files exist, all empty.)

## 4. Tech stack (as declared)

| Area | Choice | Where declared |
|---|---|---|
| Backend language | Python (tested here on 3.13) | `backend/` |
| Web framework | FastAPI + Uvicorn | `backend/requirements.txt` |
| Data validation | Pydantic v2, pydantic-settings | `requirements.txt`, `app/schemas/`, `app/core/config.py` |
| Database | Supabase PostgreSQL, through REST (httpx) or direct (SQLAlchemy + asyncpg) | `requirements.txt`, `config.py` |
| File reading | `csv` (standard library), openpyxl for Excel, chardet (declared, not used yet) | `layers/ingestion/` |
| PDF reports | reportlab | `requirements.txt` |
| Security | python-jose (JWT), bcrypt | `requirements.txt` |
| Local AI | Ollama, model `llama3.1:8b` | `config.py` |
| Testing | pytest, pytest-asyncio | `requirements.txt` |
| Frontend | Astro, TypeScript | `frontend/` (empty files) |
| Web server / proxy | Caddy | `frontend/Caddyfile.frontend` (empty) |
| Containers | Docker, docker compose | empty files |

Note: `python-jose` gets little maintenance today. When security is built we should consider `PyJWT` instead. This is a recommendation, not a bug, and will be decided when the security layer is designed.

## 5. What exists today, file by file

### 5.1 Files with code

| File | Lines | What it does | State |
|---|---|---|---|
| `backend/app/core/config.py` | 345 | Status enums (submission, CBS format, validation type and status), application settings, regulatory constants with a verification note, RCOA code list, DFS constants | Loads. Contains regulatory note errors (BUG-036, BUG-037) |
| `backend/app/layers/ingestion/format_detector.py` | 184 | Works out whether a file is XLSX or CSV and which banking system made it, checks size, computes SHA-256 hash | Loads. XLSX always rejected (BUG-012) |
| `backend/app/layers/ingestion/file_reader.py` | 302 | Parses balances to `Decimal`, reads CSV and XLSX into a standard record format | Loads. CSV path cannot return any data (BUG-005, 006, 010) |
| `backend/app/layers/ingestion/__init__.py` | 32 | Re-exports the ingestion functions | Fine |
| `backend/app/layers/normalisation/mapper.py` | 320 | Mapping rules (direct, aggregation, apportionment), loads per bank mapping JSON, maps accounts, sums by RCOA code | Does not load (BUG-001) |
| `backend/app/layers/normalisation/service.py` | 52 | Only `get_balance()` so far. The normalisation service it describes is not written | `get_balance` broken (BUG-017) |
| `backend/app/layers/normalisation/__init__.py` | 30 | Re-exports | Docstring describes things that do not exist (BUG-023) |
| `backend/app/layers/calculations/ratios.py` | 365 | `CalculationResult` record, NPF ratio, CAR, pool management ratios | Does not load (BUG-001). NPF crashes (BUG-024). Several regulatory logic issues |
| `backend/app/models/submission.py` | 59 | `RawSubmission` plain class with `to_dict` | Does not load (BUG-001) |
| `backend/app/models/__init__.py` | 10 | Re-exports | Fine |
| `backend/app/schemas/submission.py` | 280 | Pydantic request and response shapes for every planned endpoint | Does not load (BUG-001). Field issues (BUG-042 to 046) |
| `backend/requirements.txt` | 31 | Python dependencies | Versions not pinned (BUG-040) |
| `.gitignore` | 8 | Ignores virtual envs and `.env` | Incomplete (BUG-047) |

### 5.2 Empty files (0 bytes)

These exist only as names. Each one is a planned piece of work, listed as a `GAP` in the bug register.

- Backend entry and API: `app/main.py`, `app/api/routes.py`, `auth.py`, `submissions.py`, `reports.py`, `audit.py`
- Backend core: `app/core/database.py`, `deps.py`, `security.py`, `audit.py`
- Pipeline: `app/services/pipeline_runner.py`
- Mapping data: `backend/config/sample_mapping.json`
- Tests: `backend/tests/test_auth.py`, `test_pipeline.py`, `test_integration.py`, `manual_auth_integration.py`
- Database: `supabase/migrations/initial_schema.sql`, `audit_log.sql`
- Frontend: every file in `frontend/` including `package.json`, `astro.config.js`, all pages, layout, styles, libs
- Deployment: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/Dockerfile.dev`, `frontend/Caddyfile.frontend`, both `.dockerignore`
- `README.md`

### 5.3 Summary in numbers

- About 1,980 lines of Python with code in them, across 11 files.
- 4 of the 11 files cannot even be loaded by Python (BUG-001).
- Nothing can be started: there is no `main.py`, no API, no database code, no frontend.
- 47 bugs and 14 gaps recorded in the bug register at this snapshot.

## 6. Good design decisions already present

These are worth keeping, and will be explained in the teaching folder.

1. **Money as `Decimal`, never `float`** (CON-001). The balance parser reads text straight into `Decimal`, which avoids rounding errors in money.
2. **File fingerprinting** (CON-012). A SHA-256 hash of the uploaded file ties every later number back to the exact input. `compute_hash` was tested and works.
3. **A standard result record for every calculation** (`CalculationResult`, CON-007). Each ratio carries its formula, input accounts, limits, breach flag and regulatory reference, which is what an auditor or SBP inspector needs.
4. **Configurable mapping per bank** (CON-025). Mapping rules live in JSON, not in code, so a new bank does not need a code change.
5. **Explicit status states** (CON-008) for submissions and validations, which supports an audit trail of every state change.
6. **Local AI only** (CON-075), so confidential bank data is not sent to an outside AI service. Temperature 0 makes results repeatable.
7. **Honest disclaimers.** `REGULATORY_DISCLAIMER` in `config.py` states that figures are not certified. The verification note tries to separate verified from unverified values, although parts of that note are themselves wrong (see BUG-036 and [05-regulatory-verification.md](05-regulatory-verification.md)).
8. **Settings from environment** (CON-005), with a warning when the default secret key is used.

## 7. Main risks at this stage

1. **Accounting sign convention** (BUG-015). The reader computes debit minus credit, which makes capital, deposits and income negative. The ratio code assumes they are positive. A correct looking CAR of 11.5% became -11.5% in testing. Every later layer depends on this being settled first.
2. **Pool management logic does not match the actual SBP rule** (BUG-027, BUG-028). The depositor share check always reports a breach, and it tests a profit share when the SBP rule (IFPD Circular No. 09 of 2024) is about a profit rate compared with the pool's gross yield.
3. **Silent data loss** (BUG-004, BUG-020, BUG-022). Unreadable balances become zero, an unknown bank silently gets the sample mapping, and unmapped accounts quietly fall out of the ratios. In regulatory reporting a silent error is worse than a crash.
4. **No tests.** Every bug in the register was found by reading and probing. None would have survived a basic test suite.
