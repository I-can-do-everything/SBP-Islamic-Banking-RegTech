# 03. Fix Log

Each `FIX-###` fixes the `BUG-###` with the same number in [02-bug-register.md](02-bug-register.md). `FIX-G##` closes `GAP-0##`.

**Current state (2026-11-06):** every fix below is **Planned**. No code has been changed yet. This task only documented the prototype. When a fix is applied, its entry gets the commit, the date, the change made and the verification evidence, and its status moves to Fixed and then Verified.

## Entry format

Each entry records:

- **Prompted by:** what made the fix necessary (the bug, its evidence, and why it matters)
- **Approach:** what will change and why this way
- **Verification:** how we will prove the fix works (usually an automated test in `backend/tests/`)
- **Status / commit:** filled in when the fix is applied

---

## Proposed order of work

Fixes are grouped so that each group can be tested before the next one starts. The order follows the data flow: a later layer cannot be tested while the layer before it is broken.

| Phase | Fixes | Why this order |
|---|---|---|
| P0. Safety first | FIX-047, FIX-040 | Stop bank data and secrets from ever being committed, and freeze library versions before writing tests |
| P1. Make the code load | FIX-001, FIX-017, FIX-021 | Nothing else can be tested until every module loads |
| P2. Agree the accounting rules | FIX-015, FIX-033 | The sign convention and the meaning of "gross financing" decide how every later fix is written. These need the owner's sign off. |
| P3. Ingestion | FIX-002 to FIX-014, FIX-016 | Get correct, complete records out of real files |
| P4. Normalisation | FIX-018 to FIX-020, FIX-022, FIX-023 | Map every account correctly and report anything unmapped |
| P5. Calculations and regulatory logic | FIX-024 to FIX-037 | Correct ratios, correct references |
| P6. Schemas, models, security settings | FIX-038, FIX-039, FIX-041 to FIX-046 | Before the API and database are built on top of them |
| P7. Build the gaps | FIX-G01 to FIX-G14 | Database, API, pipeline, validation, reports, AI, frontend, deployment |

Tests (GAP-012) are written alongside each phase, not at the end.

---

## P0. Safety first

### FIX-047. Complete the `.gitignore`
- **Prompted by:** BUG-047. The upload folders will hold confidential bank trial balances. During the audit, cache folders appeared as new files in git straight away.
- **Approach:** Add `backend/uploads/raw/*`, `backend/uploads/reports/*` (keeping their `.gitkeep`), `__pycache__/`, `*.pyc`, `.pytest_cache/`, `node_modules/`, `frontend/dist/`, `.astro/`, `.DS_Store`, `*.log`.
- **Verification:** Create dummy files in each location and confirm `git status` does not list them.
- **Status:** Planned

### FIX-040. Pin dependency versions
- **Prompted by:** BUG-040. The same input must always give the same output, which means fixed library versions.
- **Approach:** Keep `requirements.txt` as the readable list of direct dependencies. Add a locked file with exact versions (for example made with `pip-compile` or `uv`), and install from the locked file in Docker and CI.
- **Verification:** A clean install from the lock file runs the full test suite.
- **Status:** Planned

## P1. Make the code load

### FIX-001. Move `from __future__ import annotations` to the top
- **Prompted by:** BUG-001. Four files fail to load (shown by the compile check), which blocks normalisation, calculations, models and schemas.
- **Approach:** In each of the four files, place the import straight after the module docstring, before any other import.
- **Verification:** `python -m py_compile` passes on every file. A test imports every module in the `app` package.
- **Status:** Planned

### FIX-017. `get_balance` default of `Decimal("0")`
- **Prompted by:** BUG-017. A missing account returned the `Decimal` class and crashed every sum.
- **Approach:** Default to `Decimal("0")`. Also add an option to record which requested accounts were missing, so the calculation can say "Salam: no balance reported" in its audit trail instead of silently using zero.
- **Verification:** A test where accounts are missing returns 0 and lists the missing codes. A CAR test with no Salam or Istisna succeeds.
- **Status:** Planned

### FIX-021. Provide a real sample mapping file
- **Prompted by:** BUG-021. The empty JSON file crashes every mapping load.
- **Approach:** Write a documented sample mapping that covers every RCOA code used by the calculations (financing, NPF, capital, deposits, pool income, PER, IRR). Name it clearly as an example (see FIX-020: it must never be used for a real bank by accident).
- **Verification:** A test loads it and maps one account of each kind.
- **Status:** Planned

## P2. Agree the accounting rules (needs owner sign off)

### FIX-015. One sign convention, applied in one place
- **Prompted by:** BUG-015. The reader produces debit minus credit (credit balances negative), but the calculations expect positive capital, deposits and income. In testing, CAR changed from 11.5% to -11.5% just because of the sign.
- **Approach (proposed):**
  1. Ingestion keeps the raw signed amount (debit positive, credit negative). This is the bank's own data, unchanged.
  2. Each RCOA code in the mapping carries its **normal balance** (debit for assets and expenses, credit for liabilities, equity and income).
  3. Normalisation stores both the raw signed balance and a **presented balance**, which is positive when the account sits on its normal side.
  4. Calculations read only presented balances.
  5. A balance on the wrong side (for example a deposit account in debit) raises a validation warning instead of being silently flipped.
  6. Ingestion also checks that total debits equal total credits. A trial balance that does not balance is rejected.
- **Verification:** Tests with a small balanced trial balance in credit negative form give the same ratios as hand calculated figures. A test with an unbalanced file is rejected.
- **Status:** Planned (awaiting owner sign off)

### FIX-033. Define gross financing explicitly
- **Prompted by:** BUG-033. Depending on the mapping, the NPF denominator may leave out the NPF balances themselves.
- **Approach (proposed):** Gross financing = performing financing (`3590-*`) + non performing financing (`3595-*`). Write this rule into the mapping documentation, and add a validation check that no account maps to both.
- **Verification:** A test with performing 950 and NPF 50 gives an NPF ratio of exactly 5%.
- **Status:** Planned (awaiting owner sign off)

## P3. Ingestion

### FIX-002. Fix the DR suffix typo
- **Prompted by:** BUG-002, `TypeError` on `"100.00 DR"`.
- **Approach:** `.strip*()` becomes `.strip()`.
- **Verification:** A test that `"100.00 DR"` gives `100.00` and `"100.00 CR"` gives `-100.00`.
- **Status:** Planned

### FIX-003. Read scientific notation correctly
- **Prompted by:** BUG-003, `1.5E+3` read as `1.53`.
- **Approach:** After removing commas, brackets and DR/CR, try `Decimal(text)` directly first (it understands `1.5E+3`). Use the character filter only for known formats. Reject anything left over (see FIX-004).
- **Verification:** Tests for `1.5E+3`, `-2.5e-2`, `1,234.50`, `(500)`.
- **Status:** Planned

### FIX-004. Never turn unreadable data into zero
- **Prompted by:** BUG-004. `"abc"` became 0 with no warning, which would let corrupted data reach a regulatory filing.
- **Approach:** `_parse_balance` raises a clear error (or returns a parse issue) naming the row, column and raw text. The reader collects these issues. If any exist, the submission stops with a list of problem cells. Truly blank cells and `-` are still read as zero, because accounting exports use them for zero.
- **Verification:** A test that a file with one bad cell is rejected with a message pointing to that cell.
- **Status:** Planned

### FIX-005. Fix the encoding name
- **Prompted by:** BUG-005, `LookupError` on every CSV.
- **Approach:** `'utr-8-sig'` becomes `'utf-8-sig'`. Share one encoding list and one decode helper between `format_detector.py` and `file_reader.py`, so they cannot drift apart again. Record which encoding was used.
- **Verification:** Tests with UTF-8, UTF-8 with BOM, and Windows-1252 files.
- **Status:** Planned

### FIX-006 and FIX-007. Rewrite the CSV column lookup
- **Prompted by:** BUG-006 (every found value thrown away, reader returns nothing) and BUG-007 (each row would be appended several times).
- **Approach:** Rewrite the loop as two clear steps. First, once per file, work out which real column holds each standard field by matching headers exactly (ignoring case and spaces). Second, for each row, read those columns, build one record, and append it once. This is simpler and also faster.
- **Verification:** A 3 row T24 CSV gives exactly 3 records with the right codes and balances. A generic CSV gives the same.
- **Status:** Planned

### FIX-008. One set of field names for both readers
- **Prompted by:** BUG-008. CSV stores `debit` and `credot`, then checks for `debit_balance` and `credit_balance`.
- **Approach:** Define the standard record fields once (a small dataclass or TypedDict: `account_code`, `description`, `debit`, `credit`, `balance`, `date`, `source_row`) and use it in both the CSV and Excel readers.
- **Verification:** T24 and Flexcube tests check that `balance = debit - credit` on every record.
- **Status:** Planned

### FIX-009. Fix the date fallback
- **Prompted by:** BUG-009. `str[value]` crashes on dd/mm/yyyy.
- **Approach:** One date helper that tries a list of known formats (`%Y-%m-%d`, `%d/%m/%Y`, `%d-%b-%Y`, `%Y%m%d`) and also accepts Excel date cells. Check the file's date against the submission's reporting period.
- **Verification:** Tests for each format, and for a date outside the reporting period.
- **Status:** Planned

### FIX-010. Pass the detected format to the CSV reader
- **Prompted by:** BUG-010.
- **Approach:** `_read_csv(file_bytes, detected_format)`.
- **Verification:** `read_file` on a T24 CSV returns records and the `T24` format.
- **Status:** Planned

### FIX-011 and FIX-013. Use the same header rules for Excel
- **Prompted by:** BUG-011 (name overwrote code) and BUG-013 (Excel always labelled generic).
- **Approach:** Read the Excel header row, run it through the same format detection as CSV (so T24 or Flexcube saved as Excel is recognised), then use the same exact column mapping as FIX-006.
- **Verification:** The test Excel file from the audit (`ACCOUNT_NO, ACCOUNT_NAME, DR_AMT, CR_AMT`) gives `account_code = 3590-MUR-001` and format `FLEXCUBE`.
- **Status:** Planned

### FIX-012. Correct the XLSX signature check
- **Prompted by:** BUG-012. Every XLSX was rejected.
- **Approach:** Look for `[Content_Types].xml`. Also check for `xl/workbook.xml`, so other ZIP based files (like .docx) renamed to .xlsx are rejected.
- **Verification:** A real XLSX passes. A renamed DOCX and a random ZIP are rejected.
- **Status:** Planned

### FIX-014. Close the quote in the error message
- **Prompted by:** BUG-014.
- **Status:** Planned

### FIX-016. Stronger CSV validation
- **Prompted by:** BUG-016.
- **Approach:** Reject files that contain NUL bytes or that fail to parse with a consistent column count in the first rows. Remove the unused `struct` import.
- **Verification:** A binary file renamed to .csv is rejected with a clear message.
- **Status:** Planned

## P4. Normalisation

### FIX-018. Match the whole account code
- **Prompted by:** BUG-018. `3590-MUR` matched `3590-MUR-NPF-001`.
- **Approach:** Use `fullmatch` so a pattern must describe the whole code. Add a mapping check that warns when one account matches more than one rule, because then rule order silently decides the answer.
- **Verification:** The audit case returns `False`. A test where two rules overlap produces a warning.
- **Status:** Planned

### FIX-019. Exact apportionment
- **Prompted by:** BUG-019. Splitting 100.00 into thirds lost 0.01.
- **Approach:** Store percentages as text in the JSON and read them as `Decimal`. Check that they add up to exactly 100 when the mapping loads. Round each share to 2 decimal places, and give any remainder to the largest share so the total always equals the original.
- **Verification:** 100.00 split into thirds totals exactly 100.00. A mapping with 99% total fails to load.
- **Status:** Planned

### FIX-020. No silent fallback mapping
- **Prompted by:** BUG-020. An unknown bank silently got the sample mapping.
- **Approach:** Load only the bank's own mapping file. If it does not exist, stop with a clear error. The sample is used only when a developer asks for it explicitly. Record the mapping version and file hash on every submission.
- **Verification:** Loading an unknown institution raises an error. The mapping version appears in the submission record.
- **Status:** Planned

### FIX-022. Report unmapped balances
- **Prompted by:** BUG-022. Unmapped accounts dropped out of ratios silently.
- **Approach:** Normalisation returns a list of unmapped accounts and their total. Add a validation check: any unmapped balance is a WARNING, and above a set materiality level it is a FAIL. Show the list on screen so the mapping can be fixed.
- **Verification:** A test with one unmapped account produces the warning and lists it.
- **Status:** Planned

### FIX-023. Correct the docstrings
- **Prompted by:** BUG-023.
- **Approach:** Update names and paths to match the real code once the normalisation service exists (GAP-004).
- **Status:** Planned

## P5. Calculations and regulatory logic

### FIX-024. Complete the NPF result
- **Prompted by:** BUG-024.
- **Approach:** Return the full `CalculationResult` (value rounded consistently, numerator, denominator, full formula listing every code, input accounts, limit, breach flag, reference). Apply the gross financing definition from FIX-033.
- **Verification:** NPF 50 on gross 1,000 gives 5.00000000 with every field filled in.
- **Status:** Planned

### FIX-025 and FIX-026. Correct the result dictionary
- **Prompted by:** BUG-025 (`retio_name`) and BUG-026 (`"None"` as text).
- **Approach:** Key `ratio_name`. Missing limits become JSON `null`. Add a test that every `to_dict()` output validates against the `RatioResponse` schema, so the two can never drift apart again.
- **Status:** Planned

### FIX-027 and FIX-028. Rebuild the depositor profit check from the actual rule
- **Prompted by:** BUG-027 (always 55%, always breach) and BUG-028 (the code tests a profit share, the rule is about a profit rate). Source: IFPD Circular No. 09 of 2024, REG-004.
- **Approach (to be confirmed against the circular text before coding):**
  - Pool gross yield for the month = pool gross earnings / average pool assets for the month.
  - Weighted average gross yield (WAGY) across all pools, excluding the pools for SBP's Shariah compliant standing facilities and open market operations.
  - Required minimum rate = 75% of WAGY.
  - Actual rate = the profit rate the bank paid on eligible PKR savings deposits (excluding financial institutions, public sector enterprises and public limited companies).
  - Breach if actual rate < required minimum.
  - This needs new inputs that a trial balance does not contain (average pool assets, the pool split, profit paid by deposit category). They will come as an extra upload or form, which will be designed with the owner.
- **Verification:** Worked example tests, for example a WAGY of 15.2% needs at least 11.4% paid (this matches a published analyst example, REG-004).
- **Status:** Planned (needs the circular text and an input design decision)

### FIX-029. One assumption for depositor share
- **Prompted by:** BUG-029.
- **Approach:** Remove the hard coded 50%. The IRR base becomes the actual depositors' share of distributable profit, taken from the bank's profit sharing ratios (supplied as input, like FIX-028).
- **Status:** Planned

### FIX-030. Redefine PER and IRR checks
- **Prompted by:** BUG-030.
- **Approach:** Show PER and IRR balances and their movements during the period. Check them against the bank's own approved PER and IRR policy, which is entered as configuration per bank, and against the SBP framework limits once they are verified (REG-005). Until a limit is verified, show the value without a breach flag, labelled "indicative".
- **Status:** Planned

### FIX-031. Annualise using the real period
- **Prompted by:** BUG-031.
- **Approach:** Annualisation factor = 365 / number of days in the reporting period, taken from the submission. Use average deposits where available, and state clearly in the formula text when closing balances are used.
- **Verification:** The same data as a 30 day and a 91 day period gives correctly scaled rates.
- **Status:** Planned

### FIX-032. A properly structured CAR
- **Prompted by:** BUG-032.
- **Approach:** Split CAR into its parts:
  - CET1, Additional Tier 1 and Tier 2 capital, with regulatory deductions
  - credit RWA by asset class with configurable risk weights (0% for cash and GoP Ijarah Sukuk, and so on)
  - market and operational risk RWA as inputs
  - separate CET1, Tier 1 and total CAR minimums (values verified first, REG-002)
  - the general provision cap in Tier 2

  Until the full model exists, label the output clearly as "simplified, credit risk only".
- **Status:** Planned

### FIX-034. Label the NPF threshold honestly
- **Prompted by:** BUG-034.
- **Approach:** Rename it as an internal alert threshold (configurable per bank). Do not call it an SBP limit unless a source is found (REG-003). Breaches against it become WARNING, not FAIL.
- **Status:** Planned

### FIX-035. Provisioning and ECL
- **Prompted by:** BUG-035. Closed together with GAP-014.
- **Status:** Planned

### FIX-036. Correct the regulatory verification note
- **Prompted by:** BUG-036. IFPD and IFPD Circular No. 09 of 2024 were wrongly called fabricated.
- **Approach:** Rewrite the note in `config.py` to point to [05-regulatory-verification.md](05-regulatory-verification.md) as the single source of truth, and restore the correct reference for the 75% rule.
- **Status:** Planned

### FIX-037. Verify or remove `DFS_VERSION`
- **Prompted by:** BUG-037.
- **Approach:** Find the current DFS file specification. Until then, set the value to an explicit placeholder that the reporting layer refuses to submit with.
- **Status:** Planned

## P6. Schemas, models, security settings

### FIX-038. Refuse to start in production with the default secret
- **Prompted by:** BUG-038.
- **Approach:** If `ENVIRONMENT` is `production` and the key is the default or shorter than 32 bytes, stop at startup with a clear message.
- **Verification:** A test of settings with each combination.
- **Status:** Planned

### FIX-039. No known default passwords
- **Prompted by:** BUG-039.
- **Approach:** Seed accounts only in development. In production, the first admin is created from environment variables or a one time setup command, and must change the password at first login.
- **Status:** Planned

### FIX-041. Replace the hand written model class
- **Prompted by:** BUG-041.
- **Approach:** Decide the data layer first (GAP-002 and GAP-009). Then use either a Pydantic model or a dataclass with proper defaults, so `to_dict` cannot fail on missing attributes.
- **Status:** Planned

### FIX-042, FIX-043, FIX-044, FIX-045, FIX-046. Schema corrections
- **Prompted by:** BUG-042 to BUG-046.
- **Approach:**
  - FIX-042: rename to `file_size_bytes`
  - FIX-043: password length 12 to 128 characters
  - FIX-044: rename to `occurred_at`
  - FIX-045: `database_mode` default `"postgres"`
  - FIX-046: `EmailStr` for email (needs the `email-validator` package), and a `UserRole` enum for role
- **Verification:** Schema unit tests for each field.
- **Status:** Planned

## P7. Gaps

| Fix | Closes | Summary of the plan (detailed designs will be written into this log when each starts) |
|---|---|---|
| FIX-G01 | GAP-001 | FastAPI app, routers for auth, submissions, reports, audit, plus a health check |
| FIX-G02 | GAP-002 | Database access, JWT auth, role checks, audit log writer |
| FIX-G03 | GAP-003 | Pipeline runner with status changes RECEIVED, PROCESSING, COMPLETE, FAILED, each one audited |
| FIX-G04 | GAP-004 | Normalisation service |
| FIX-G05 | GAP-005 | Validation layer |
| FIX-G06 | GAP-006 | PDF and DFS report generation |
| FIX-G07 | GAP-007 | Local AI commentary that may only quote numbers the system calculated |
| FIX-G08 | GAP-008 | SBP circular monitor |
| FIX-G09 | GAP-009 | Database schema and migrations |
| FIX-G10 | GAP-010 | Frontend, designed for compliance staff |
| FIX-G11 | GAP-011 | Docker and deployment |
| FIX-G12 | GAP-012 | Test suite, built phase by phase |
| FIX-G13 | GAP-013 | README and mapping configuration |
| FIX-G14 | GAP-014 | Provisioning (from classification and days past due) and IFRS 9 ECL |

---

## Implementation record (2026-11-06)

The prototype in `backend/app` was replaced by the `daleel` package (`backend/src/daleel`). Every fix below was either carried into the new code or made unnecessary by the redesign. "Verified" means an automated test in `backend/tests` proves it; the test names are listed. Run them with `cd backend && uv run pytest`.

| Fix | Status | Where it lives now | Evidence |
|---|---|---|---|
| FIX-001 | Closed by redesign | All new modules put `from __future__ import annotations` first | `ruff` and import of every module in the test run |
| FIX-002 | Verified | `ingestion/clean.py` macro `d_money` | `test_money_parsing[100.00 DR]` |
| FIX-003 | Verified | DuckDB decimal cast understands exponents | `test_money_parsing[1.5E+3]`. While building the sample data, a 7 digit scientific notation cell lost 332.12, and the trial balance check (`integrity.tb_balanced`) caught it. That is the real world version of this bug, and the reason the generator now writes full precision. |
| FIX-004 | Verified | Unreadable cells give a row level reject with a reason | `test_bug004_unreadable_is_not_zero`, `test_unreadable_row_rejected_with_reason` |
| FIX-005 | Verified | `ingestion/reader.py` `ENCODINGS` | `test_bug005_to_010_messy_t24_csv` (Windows-1252 file) |
| FIX-006, FIX-007 | Verified | Column lookup rewritten as SQL over a mapped header | same test: 5 rows in, 5 rows out |
| FIX-008 | Verified | One schema (`datasets/schemas.py`) for every reader | same test, balances net correctly |
| FIX-009 | Verified | `d_date` macro, day first formats | `test_rates_and_dates` |
| FIX-010 | Closed by redesign | One entry point `ingest_file` | end to end tests |
| FIX-011, FIX-012 | Verified | Exact header matching; XLSX checked for `[Content_Types].xml` and `xl/workbook.xml` | `test_bug011_bug012_xlsx_name_does_not_overwrite_code` |
| FIX-013 | Verified | Layout detection runs for every sheet type | ingestion result shows T24 and FLEXCUBE layouts |
| FIX-014 | Closed by redesign | Errors use structured messages | |
| FIX-015 | Verified | DEC-008: signed debit positive, presented on the normal side (`mapping/mapper.py`) | `test_baseline_golden` (CAR positive, balances on normal side) |
| FIX-016 | Verified | NUL bytes and broken ZIPs rejected | `test_renamed_binary_is_rejected` |
| FIX-017 | Closed by redesign | Missing accounts sum to zero in SQL and are visible in lineage | golden tests |
| FIX-018 | Verified | `re.fullmatch`, overlap report | `test_bug018_full_match_only` |
| FIX-019 | Verified | Exact shares, remainder to the largest share | `test_bug019_apportionment_conserves_total` (Hypothesis property) |
| FIX-020 | Verified | Only the configured mapping is loaded, never a silent sample | mapping version recorded on each submission |
| FIX-021 | Closed by redesign | `mappings/default.yaml` is real and validated on load | |
| FIX-022 | Verified | Unmapped accounts reported; WARNING, or FAIL above materiality | `test_baseline_golden` (planted unmapped account is a WARNING) |
| FIX-023 | Closed by redesign | Docstrings rewritten | |
| FIX-024 to FIX-026 | Closed by redesign | `metrics/engine.py` `MetricResult` is always complete; JSON from typed rows | `test_every_metric_has_lineage` |
| FIX-027, FIX-028 | Verified | `pool.wagy`, `pool.savings_min_rate`, `pool.savings_lowest_rate` follow IFPD C09/2024, read in its official Urdu text | `test_stressed_detects_every_planted_breach`, `test_wagy_excludes_scf_and_omo` |
| FIX-029 | Closed by redesign | Mudarib share comes from each pool's data | |
| FIX-030 | Verified | PER and IRR checks use the primary limits from IBD C03/2012 Annex (2% monthly PER, 30% of equity, 1% IRR) | stressed golden test |
| FIX-031 | Verified | Annualised with the real period length (365 / days) | lineage formula |
| FIX-032 | Verified (simplified) | CET1, Tier 1, Tier 2 with the 1.25% cap, CCB, leverage, transitional add back | golden CAR range; CAR inside the buffer is a WARNING in the stressed run |
| FIX-033 | Verified | DEC-009: gross financing from contracts, reconciled to the GL by mode | `recon.financing` PASS in both scenarios |
| FIX-034 | Verified | NPF alert is a labelled assumption that can only WARN | engine rule in `metrics/engine.py` |
| FIX-035 | Verified | Provisioning and ECL implemented (GAP-014) | `test_classification_follows_annexure_c` |
| FIX-036 | Done | Verification lives in docs/05 and the rulebook; the wrong note is gone with the prototype | |
| FIX-037 | Done | No DFS version claim; reporting codes labelled illustrative | |
| FIX-038 | Verified | `Settings` refuses a weak `JWT_SECRET` in production | |
| FIX-039 | Closed by redesign | No seeded passwords; the demo uses anonymous workspaces | |
| FIX-040 | Done | `backend/uv.lock`, `web/pnpm-lock.yaml`; Docker installs with `--frozen` | |
| FIX-041 to FIX-046 | Closed by redesign | Replaced by the new schema and API | |
| FIX-047 | Done | Complete `.gitignore`; runtime data in `backend/var/` | `git check-ignore` on `backend/.env` |
| FIX-G01 to FIX-G05 | Done | API, security, pipeline, normalisation, validation | |
| FIX-G06 | Partly done | Ideal template workbook; the PDF report pack is still to do | |
| FIX-G07 | Done | Grounded AI breakdown | `test_validator_rejects_digits_and_bad_citations`, `test_template_covers_every_failure` |
| FIX-G08 | Open | SBP circular watcher | |
| FIX-G09 to FIX-G13 | Done | Migrations, web app, Docker, tests, README | |
| FIX-G14 | Done | Provisioning and ECL | |

### New issues found and fixed while building (BUG-048 onward)

| ID | What happened | How it was found | Fix |
|---|---|---|---|
| BUG-048 | A dash ("-") in money columns outside the trial balance was read as missing, which wrongly rejected half the deposit rows | First ingestion run showed 15,090 rejected rows, all "missing PROFIT_ACCRUED" on current accounts | A dash or NIL is zero everywhere; only an empty cell can be missing |
| BUG-049 | The INFO sheet with institution and period was not read | Meta came back empty | Key and value scan over every sheet |
| BUG-050 | Generated bank had negative equity (liabilities larger than assets) | Accountant review of the first results: CET1 negative | GoP Ijarah Sukuk became the exact balancing asset |
| BUG-051 | 7 digit scientific notation in the sample export lost 332.12 | `integrity.tb_balanced` failed | Full precision in the generator (and a lesson for the posts) |
| BUG-052 | OpenRouter rejects fallback lists longer than three models (HTTP 400) | AI breakdown fell back to the template; the error body said so | Models are sent in groups of three |
| BUG-053 | A weak free model wrote breach points with no figures and renamed IRR as "return of equity contribution" | Reading the screenshot of the AI breakdown | Two new validator rules: each cited fact must appear as its placeholder, and must be named with its own words |
| BUG-054 | DuckDB `GROUP BY ALL` refused a CASE mixing a grouped column and an aggregate | Binder error on first run | Explicit GROUP BY columns |
