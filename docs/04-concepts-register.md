# 04. Concepts Register

A running list of every topic, concept, tool and design idea the system uses. Each entry has a short plain language explanation and shows where it is used. At the end of the project, each entry will be expanded into a full lesson in `docs/learn/`.

**Status:** `In code` means used in the code that exists now. `Planned` means it is part of the design but not built yet.

ID ranges: 001 to 019 software engineering, 020 to 029 accounting, 030 to 049 regulation and Islamic finance, 060 to 079 tech stack, 080 onward design philosophy. Gaps in the numbers are left on purpose for future entries.

---

## Software engineering (CON-001 to CON-019)

| ID | Concept | Plain explanation | Where used | Status |
|---|---|---|---|---|
| CON-001 | `Decimal` instead of `float` for money | Computers store `float` in binary, so 0.1 + 0.2 is not exactly 0.3. `Decimal` stores numbers in base 10, exactly as written, which is what money needs. | `file_reader._parse_balance`, all of `ratios.py` | In code |
| CON-002 | Parsing money written as text | Exports write amounts as `1,234.50`, `(500)`, `500 CR`, `-500`, `1.5E+3`. Each form must be turned into the same exact number. | `file_reader._parse_balance` | In code |
| CON-003 | Python modules, packages and indentation | A folder with `__init__.py` is a package. Importing it runs that file. In Python, indentation decides which loop a line belongs to, so a wrong indent changes the logic. | Every package. BUG-006, BUG-007 | In code |
| CON-004 | Postponed annotations (`from __future__ import annotations`) | Lets type hints refer to classes not yet defined. It must be the first statement in a file. | 4 files (BUG-001) | In code |
| CON-005 | Settings from environment variables | Secrets and server settings are read from the environment or a `.env` file, not written into code, so one codebase runs safely in development and production. | `config.py` `Settings` | In code |
| CON-006 | Caching with `lru_cache` | Remembers a function's result so the settings are only read once. | `get_settings()` | In code |
| CON-007 | Dataclasses as standard records | A compact way to define a record with named fields. Every calculation returns the same shape, which keeps the audit trail consistent. | `CalculationResult` | In code |
| CON-008 | Enums and state machines | A fixed list of allowed values (RECEIVED, PROCESSING, COMPLETE, FAILED). A submission moves between these states, and each move is logged. | `config.py` enums | In code |
| CON-009 | Pydantic models (validation) | Classes that check incoming and outgoing data has the right fields and types, and produce API documentation automatically. | `schemas/submission.py`, `Settings` | In code |
| CON-010 | Text encodings and the BOM | Files are bytes, and the encoding (UTF-8, Windows-1252) says how bytes become letters. Excel often adds a Byte Order Mark at the start of UTF-8 files, handled by `utf-8-sig`. | `format_detector`, `file_reader` | In code |
| CON-011 | Date parsing | Turning `30/06/2025` or `2025-06-30` into a real date. The format must be known, because 01/02 means January 2 in some countries and February 1 in others. | `file_reader._read_csv` | In code |
| CON-012 | Cryptographic hashing (SHA-256) for chain of custody | A hash is a fingerprint of a file. Any change, even one character, gives a completely different hash. Storing it proves which exact file produced a report. | `format_detector.compute_hash` | In code |
| CON-013 | Header detection and column mapping | Different systems name the same column differently (`GL_ACCOUNT_CODE`, `ACCOUNT_NO`). The reader recognises the system from its headers and maps each column to a standard name. | `format_detector.EXPECTED_HEADERS`, `file_reader` | In code |
| CON-014 | File signatures (magic bytes) and XLSX structure | Files are checked by their content, not just their name. An XLSX file is a ZIP archive (starts with `PK`) holding XML files, including `[Content_Types].xml`. | `format_detector._detect_xlsx` | In code |
| CON-015 | Fail loudly, never silently | In regulatory work a wrong number that looks right is the worst outcome. Bad or missing data must cause an error or a visible warning, not a default value. | Design rule behind BUG-004, 020, 022 | Planned (rule) |
| CON-016 | Regular expressions and anchoring | Patterns that match text. `match` checks only the start, while `fullmatch` requires the whole text to fit the pattern. | `mapper.MappingRule` | In code |
| CON-017 | Reproducible builds and pinned dependencies | Recording exact library versions so the system behaves the same every time it is installed. | `requirements.txt` | Planned |
| CON-018 | Data confidentiality in source control | Real customer or bank data, secrets and generated files must never enter git. `.gitignore` enforces this. | `.gitignore` | In code (incomplete) |
| CON-019 | Layered pipeline architecture | The work is split into layers (ingest, normalise, calculate, validate, report). Each has one job and a clear input and output, so each can be tested and replaced on its own. | `app/layers/` | In code |

## Accounting (CON-020 to CON-029)

| ID | Concept | Plain explanation | Where used | Status |
|---|---|---|---|---|
| CON-020 | General ledger and trial balance | The general ledger holds every account. A trial balance lists each account's closing balance at a date. Total debits must equal total credits. | The input file | In code |
| CON-021 | Debit, credit and normal balances | Double entry bookkeeping. Assets and expenses normally have debit balances. Liabilities, equity (capital) and income normally have credit balances. | `_parse_balance` CR/DR handling, BUG-015 | In code |
| CON-022 | Core banking systems (CBS) | The bank's main software for accounts and transactions. Temenos T24 and Oracle Flexcube are widely used in Pakistan. Each exports data in its own layout. | `CBSFormat` enum | In code |
| CON-023 | Account codes and chart of accounts | Every ledger account has a code. A chart of accounts is the full structured list of codes. Each bank has its own. | Mapping rules | In code |
| CON-024 | SBP Reporting Chart of Accounts (RCOA) | The standard chart of accounts SBP uses for reporting. Each bank's codes must be translated into RCOA codes. The codes in this prototype (such as `3590-MUR`) are placeholders, to be checked against the official RCOA. | `config.RCOA_RANGES`, `ratios.py` | In code |
| CON-025 | Account mapping (direct, aggregation, apportionment) | Direct: one bank account to one RCOA code. Aggregation: many to one, summed. Apportionment: one account split across several RCOA codes by percentage. | `mapper.py` | In code |
| CON-026 | Sign normalisation | Converting signed ledger balances into the positive "presented" amounts that formulas expect, using each account's normal balance. | FIX-015 | Planned |
| CON-027 | Completeness and reconciliation | Proving nothing was lost: the mapped totals must reconcile back to the trial balance totals, and unmapped balances must be reported. | FIX-022 | Planned |
| CON-028 | Stocks and flows | A stock is a balance at a moment (deposits, reserves). A flow happens over a period (income, profit). Ratios that mix them depend on the period length. | BUG-030 | In code |
| CON-029 | Reporting periods and annualisation | Converting a rate for a period into a yearly rate, using the actual number of days. | BUG-031 | In code |

## Regulation and Islamic finance (CON-030 to CON-049)

| ID | Concept | Plain explanation | Where used | Status |
|---|---|---|---|---|
| CON-030 | State Bank of Pakistan (SBP) and its departments | Pakistan's central bank and banking regulator. Rules are issued as circulars by departments such as BPRD (banking policy), IFPD (Islamic finance policy) and others. | Throughout | In code |
| CON-031 | Audit trail | A record showing who did what, when, and with which data, so any reported number can be traced back to its source. | `CalculationResult`, planned audit log | In code / Planned |
| CON-032 | Islamic banking principles | No interest (riba). Returns come from trade, leasing or partnership, and profit and loss is shared. A Shariah board approves products. | Domain basis | In code |
| CON-033 | Islamic financing products | Murabaha (cost plus sale), Ijarah (leasing), Diminishing Musharakah (partnership where the customer gradually buys out the bank), Salam (advance payment for goods delivered later), Istisna (financing goods to be manufactured). | `ratios.py` account codes | In code |
| CON-034 | CAELS rating | SBP's supervisory rating framework (Capital, Asset quality, Earnings, Liquidity, Sensitivity). It is an assessment framework, not a list of hard limits. | Cited in `ratios.py` | In code |
| CON-035 | RCOA, DFS and DAP4 | Banks report to SBP through the Data Acquisition Portal (DAP4). Returns follow the Reporting Chart of Accounts (RCOA), and each return has a Data File Structure (DFS) that fixes its file layout. The layouts are given to banks, not published. | `config.DFS_*`, REG-015 | Planned |
| CON-036 | Shariah compliance checks | Checks that products and pools follow Shariah rules and SBP's Shariah governance framework. | `ValidationCheckType.SHARIAH` | Planned |
| CON-037 | Asset classification, days past due and provisioning | Financing is classified by how many days payments are overdue (OAEM, Substandard, Doubtful, Loss), and a provision (expected loss set aside) is required for each class. | `config.DPD_THRESHOLDS`, `PROVISION_RATES` | In code (unused) |
| CON-038 | Non performing financing (NPF) ratio | Bad financing divided by total financing. The Islamic banking version of the non performing loan ratio. | `calculate_npf_ratio` | In code |
| CON-039 | IFRS 9 expected credit loss (ECL) | An accounting standard: banks set aside provisions for expected future losses, in three stages based on how much credit risk has increased. | `ValidationCheckType.IFRS9` | Planned |
| CON-040 | Capital adequacy ratio (CAR) | Capital divided by risk weighted assets. It shows whether the bank has enough of its own money to absorb losses. | `calculate_car` | In code |
| CON-041 | Basel III capital tiers | International standard. CET1 (common equity, the strongest), Additional Tier 1, and Tier 2 (subordinated debt or Sukuk, some provisions), each with its own minimum. | `calculate_car` | In code (simplified) |
| CON-042 | Risk weighted assets (RWA) | Each asset is multiplied by a risk weight (0% for government securities, 100% for an unrated corporate, and so on), plus charges for market and operational risk. | `calculate_car` | In code (simplified) |
| CON-043 | Pool management and profit distribution | Depositors' funds go into pools. Pool income is shared between depositors and the bank (the Mudarib) under SBP rules. | `calculate_pool_ratios` | In code |
| CON-044 | PER and IRR reserves | Profit Equalisation Reserve (smooths profit paid to depositors across periods) and Investment Risk Reserve (absorbs future losses), both set aside from pool profit. | `calculate_pool_ratios` | In code |
| CON-045 | Weighted average gross yield (WAGY) and the 75% rule | Since 1 January 2025, Islamic banks must pay profit on eligible PKR savings deposits at a rate of at least 75% of the weighted average gross yield of their pools (IFPD Circular No. 09 of 2024). | BUG-028, REG-004 | Planned |
| CON-046 | Mudarabah and Wakala deposits | Mudarabah: the depositor provides money and the bank manages it, sharing profit. Wakala: the bank acts as agent for a fee. | `2150-MUD`, `2150-WAK` | In code |
| CON-047 | Declared profit rate | The annualised profit rate a bank announces for depositors in a period. | `calculate_pool_ratios` | In code |
| CON-048 | Mudarib share, weightages and Hiba | The bank's share of pool profit as manager (Mudarib, capped at 50%). Weightages give different deposit types different shares of profit, and are announced before each month. Hiba is a gift the bank may give from its own share. | REG-012 | Planned |
| CON-049 | Outsourcing and cloud rules for banks | SBP requires banks to keep material workloads with onshore cloud providers unless it approves otherwise. This shapes where the system and its AI may run. | REG-017, DEC-013 | Planned |

## Tech stack (CON-060 to CON-079)

| ID | Concept | Plain explanation | Where used | Status |
|---|---|---|---|---|
| CON-060 | FastAPI | A Python web framework for building APIs. It uses type hints and Pydantic to validate requests and create documentation. | `requirements.txt` | Planned |
| CON-061 | Uvicorn and ASGI | The server program that runs a FastAPI app and handles many requests at once. | `requirements.txt` | Planned |
| CON-062 | REST API design | Organising the backend as resources (submissions, reports) that are accessed over HTTP with standard methods. | `schemas/` shapes | Planned |
| CON-063 | Supabase and PostgreSQL | PostgreSQL is a robust open source database. Supabase hosts it and adds a REST interface and other services. | `config.py` | Planned |
| CON-064 | SQLAlchemy and asyncpg | Python libraries to talk to PostgreSQL directly, without blocking other requests. | `requirements.txt` | Planned |
| CON-065 | httpx | An HTTP client for Python, used to call Supabase's REST interface and the local Ollama server. | `requirements.txt` | Planned |
| CON-066 | JWT authentication | After login, the server gives a signed token. The user sends it with each request, and the server checks the signature with its secret key. | `config.py` token settings | Planned |
| CON-067 | bcrypt password hashing | Passwords are stored as slow, salted hashes, so a stolen database does not reveal them. | `requirements.txt` | Planned |
| CON-068 | Rate limiting | Limits how many uploads, downloads or login attempts are allowed per time window, to stop abuse and password guessing. | `config.py` | Planned |
| CON-069 | Expiring download links | Report downloads use short lived tokens, so a leaked link stops working after a few minutes. | `config.py` | Planned |
| CON-070 | Astro | A frontend framework that builds fast, mostly static pages and adds interactivity only where it is needed. | `frontend/` | Planned |
| CON-071 | TypeScript | JavaScript with types, which catches mistakes before the code runs. | `frontend/src/lib/*.ts` | Planned |
| CON-072 | Docker and docker compose | Packages each part of the system with everything it needs, so it runs the same on every machine. | Dockerfiles | Planned |
| CON-073 | Caddy | A web server that serves the frontend, forwards API calls and handles HTTPS certificates automatically. | `Caddyfile.frontend` | Planned |
| CON-074 | reportlab | A Python library that generates PDF reports. | `requirements.txt` | Planned |
| CON-075 | Ollama and local LLMs | Runs an AI language model (here `llama3.1:8b`) on the bank's own server, so confidential data never leaves it. | `config.py` | Planned |
| CON-076 | Temperature 0 and deterministic AI output | Temperature controls randomness. At 0 the model gives the most likely answer, which makes output repeatable for audit. | `OLLAMA_TEMPERATURE` | Planned |
| CON-077 | Hallucination checks | Automatically comparing every number and claim in the AI text against the calculated results, and flagging anything unsupported. | `CommentaryResponse.hallucination_flags` | Planned |
| CON-078 | Data sovereignty | Keeping data within the bank, and within Pakistan, as banking secrecy and data rules expect. | Local AI design | Planned |
| CON-079 | pytest | The Python testing framework used to prove each part works. | `requirements.txt` | Planned |

## Design philosophy (CON-080 onward)

| ID | Concept | Plain explanation | Status |
|---|---|---|---|
| CON-080 | Context relevant design | Every design choice follows from what the app does and who uses it. Here the users are finance and compliance staff, so the design values accuracy, traceability, dense but calm information, and clear warning states over decoration. | Planned (frontend) |
| CON-081 | Audit first design | Every number must be explainable: show its formula, inputs, source file hash and regulatory reference, one click away. | In code (`CalculationResult`) |
| CON-082 | Configuration over code | Bank specific and regulation specific values live in configuration that can be reviewed and versioned, not inside code. | In code (mapping JSON, constants) |
| CON-083 | Defence in depth | Several independent security layers (validation, authentication, roles, rate limits, audit log, expiring links), so one failure does not expose data. | Planned |
| CON-084 | Maker checker (four eyes) | One person prepares, a different person approves. The rule is enforced by the software, so nobody can approve their own work. | Planned |

## Architecture patterns (CON-090 onward)

| ID | Concept | Plain explanation | Where used | Status |
|---|---|---|---|---|
| CON-090 | Medallion data layout and lakehouse lite | Data moves through layers: raw (as received, never changed), bronze (typed), silver (cleaned), gold (aggregated). Files are kept in open formats (Parquet) in object storage, and a query engine (DuckDB) reads them directly. | DEC-002 | Planned |
| CON-091 | Transactional outbox | Saving a record and queuing its follow up work in the same database transaction, so one cannot happen without the other. | DEC-003 | Planned |
| CON-092 | Regulation as code and bitemporal data | Regulatory values are versioned data with "valid from" and "valid to" dates, so a past period is always calculated with the rules of its time. | DEC-005 | Planned |
| CON-093 | Hash chained audit log | Each log entry includes a fingerprint of the previous one. Any edit or deletion breaks the chain at that point. | DEC-010 | Planned |
| CON-094 | LLM evaluations | A fixed set of test inputs with expected properties, used to measure an AI model's accuracy before and after a change. | 06 section 9 | Planned |
| CON-095 | Row level security | Database rules that restrict which rows a session can see (here: only its own bank's rows). | DEC-012 | Planned |
| CON-096 | Synthetic data generation | Building realistic but fake data from rules and statistics, seeded so it is identical every run. | 07 section 2.3 | Planned |
| CON-097 | Columnar storage (Parquet) and vectorised engines (DuckDB) | Storing data column by column compresses it well and lets the engine read only the needed columns and process them in batches across all CPU cores. | DEC-002 | Planned |
| CON-098 | Idempotency | Doing the same request twice has the same effect as doing it once, so retries are safe. | 06 section 8 | Planned |
| CON-099 | Server Sent Events | A simple one way stream from server to browser for live progress updates. | DEC-011 | Planned |
