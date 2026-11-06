# 02. Bug Register

**Baseline:** commit `e96988c`, examined on 2026-11-06.
**Fixes:** each `BUG-###` is fixed by the `FIX-###` with the same number in [03-fix-log.md](03-fix-log.md). Each `GAP-###` is closed by `FIX-G##`.
**Concepts:** `CON-###` tags point to [04-concepts-register.md](04-concepts-register.md). `REG-###` tags point to [05-regulatory-verification.md](05-regulatory-verification.md).

---

## Status update (2026-11-06)

All of BUG-001 to BUG-047 are now closed, either fixed with a regression test or made unnecessary by the rebuild. The gaps are closed except GAP-006 (PDF report pack, partly done) and GAP-008 (circular watcher). See the implementation record in [03-fix-log.md](03-fix-log.md#implementation-record-2026-11-06). Seven new issues found during the build (BUG-048 to BUG-054) are recorded there too, with how each was found. Later rounds added BUG-055 to BUG-058 (four eyes approval and setup wizard) and BUG-059 to BUG-064 (brand, landing page, worker lanes and a CI failure), all fixed and recorded in the same place.

## How these bugs were found

Four methods were used, in this order. Each bug says which method found it.

| Method | What was done |
|---|---|
| **M1. Reading** | Every file with code was read line by line, by someone acting as a software engineer, an accountant and a compliance officer at the same time. |
| **M2. Compile check** | `python3 -m py_compile` on every non-empty Python file. This finds code that Python refuses to load. |
| **M3. Runtime probe** | A scratch copy of the backend was made. Only BUG-001 was patched in the copy, so the rest of the code could load. Then each function was called with small, realistic inputs (a T24 style CSV, an Excel file, sample balances) and the result was recorded. The script and its output are in [evidence/](evidence/). |
| **M4. Regulatory check** | Regulatory claims in the code were checked against public sources (SBP website and press reports). Results are in [05-regulatory-verification.md](05-regulatory-verification.md). |

**A correction made during the audit.** Reading alone suggested that `file_reader.py` line 73 (`.strip*()`) would stop the file from loading. The compile check showed it is valid Python: it means "the method multiplied by an empty tuple", and fails only when that line runs (BUG-002). Reading also suggested that `compute_hash` had no body. The probe showed it works and returns the correct SHA-256. It was **not** recorded as a bug. These show why reading must be backed by running code.

---

## Summary table

| ID | Severity | Area | Title | Status |
|---|---|---|---|---|
| BUG-001 | Critical | Startup | `from __future__` import in the wrong place, 4 files will not load | Open |
| BUG-002 | High | Ingestion | Balances ending in " DR" crash the parser | Open |
| BUG-003 | Medium | Ingestion | Scientific notation is misread (`1.5E+3` becomes `1.53`) | Open |
| BUG-004 | High | Ingestion | Unreadable balances silently become zero | Open |
| BUG-005 | Critical | Ingestion | Encoding name typo `utr-8-sig` crashes every CSV read | Open |
| BUG-006 | Critical | Ingestion | CSV column lookup throws away every value it finds | Open |
| BUG-007 | High | Ingestion | CSV rows would be added several times (wrong indentation) | Open |
| BUG-008 | High | Ingestion | Debit and credit keys do not match, so T24 and Flexcube balances are never calculated | Open |
| BUG-009 | High | Ingestion | `str[value]` crashes on dates written as dd/mm/yyyy | Open |
| BUG-010 | Critical | Ingestion | `read_file` calls `_read_csv` without the format argument | Open |
| BUG-011 | High | Ingestion | Excel reader puts the account name into the account code | Open |
| BUG-012 | Critical | Ingestion | Excel check looks for the wrong file name, every XLSX is rejected | Open |
| BUG-013 | Medium | Ingestion | Excel files are always labelled `GENERIC_CSV` | Open |
| BUG-014 | Low | Ingestion | Error message has an unclosed quote | Open |
| BUG-015 | Critical | Accounting | Debit minus credit makes capital, deposits and income negative, ratios assume positive | Open |
| BUG-016 | Low | Ingestion | Any binary file with a comma passes as a CSV | Open |
| BUG-017 | Critical | Normalisation | `get_balance` default is the `Decimal` class, not zero | Open |
| BUG-018 | High | Normalisation | Mapping patterns match prefixes, so NPF accounts can map as performing financing | Open |
| BUG-019 | Medium | Normalisation | Apportionment uses float and does not check percentages total 100 | Open |
| BUG-020 | High | Normalisation | Unknown bank silently gets the sample mapping | Open |
| BUG-021 | Critical | Normalisation | `sample_mapping.json` is empty, loading any mapping crashes | Open |
| BUG-022 | Medium | Normalisation | Unmapped accounts disappear from ratios without a warning | Open |
| BUG-023 | Low | Normalisation | Docstrings name modules and classes that do not exist | Open |
| BUG-024 | Critical | Calculations | NPF function returns an incomplete result and crashes | Open |
| BUG-025 | Medium | Calculations | `to_dict` key typo `retio_name` | Open |
| BUG-026 | Low | Calculations | Missing limits become the text "None" | Open |
| BUG-027 | Critical | Calculations | Depositor share is hard coded at 55%, so it always breaches | Open |
| BUG-028 | High | Regulatory | Depositor check tests a profit share, SBP rule is about a profit rate vs pool gross yield | Open |
| BUG-029 | Medium | Calculations | IRR ratio assumes depositors get 50%, contradicts other assumptions | Open |
| BUG-030 | Medium | Regulatory | PER and IRR ratios divide a balance by period income, against unverified caps | Open |
| BUG-031 | Medium | Calculations | Profit rate always annualised as if the period is one month | Open |
| BUG-032 | High | Regulatory | CAR is heavily simplified and would materially misstate capital adequacy | Open |
| BUG-033 | Medium | Accounting | NPF denominator assumes performing codes already include NPF | Open |
| BUG-034 | Medium | Regulatory | 7% NPF "maximum" is shown as an SBP limit but is not verified | Open |
| BUG-035 | Low | Calculations | Docstring promises provisioning, ECL and a CalculationService that do not exist | Open |
| BUG-036 | High | Regulatory | Config note wrongly calls IFPD and IFPD Circular 09/2024 fabricated | Open |
| BUG-037 | Medium | Regulatory | `DFS_VERSION` uses a citation the same file says does not exist | Open |
| BUG-038 | Medium | Security | Default secret key only gives a warning | Open |
| BUG-039 | Medium | Security | Seeded default passwords are known to anyone who reads the code | Open |
| BUG-040 | Medium | Reproducibility | Dependency versions not pinned | Open |
| BUG-041 | Medium | Models | `RawSubmission.to_dict` crashes when a field is not set | Open |
| BUG-042 | Medium | Schemas | `File_size_bytes` has a capital F | Open |
| BUG-043 | Medium | Security | Passwords limited to 15 characters | Open |
| BUG-044 | Low | Schemas | `occured_at` spelling | Open |
| BUG-045 | Low | Schemas | Health check says `local_sqlite`, stack is PostgreSQL | Open |
| BUG-046 | Low | Schemas | Email and role are unchecked free text | Open |
| BUG-047 | High | Security | `.gitignore` does not exclude uploaded bank files, caches or node_modules | Open |

Gaps (planned but not built): GAP-001 to GAP-014, listed at the end.

**Counts:** Critical 10, High 12, Medium 17, Low 8. Total 47 bugs, 14 gaps.

---

## Detailed entries

### Startup

#### BUG-001. `from __future__ import annotations` is not the first statement

- **Severity:** Critical
- **Location:**
  - `backend/app/layers/calculations/ratios.py` line 31
  - `backend/app/layers/normalisation/mapper.py` line 23
  - `backend/app/models/submission.py` line 9
  - `backend/app/schemas/submission.py` line 18
- **What is wrong:** Python requires a `from __future__` import to be the first statement in a file (only the docstring and comments may come before it). In these four files it comes after other imports.
- **Impact:** Python refuses to load the four files. Everything that imports them fails as well: the normalisation package (it imports `mapper.py`), all calculations, all models and all API schemas. In effect, nothing beyond ingestion can run.
- **Evidence (M2):** `py_compile` output for each file: `SyntaxError: from __future__ imports must occur at the beginning of the file`.
- **Concepts:** CON-003 (Python modules and imports), CON-004 (postponed annotations).
- **Fix:** FIX-001

### Ingestion layer

#### BUG-002. Balances ending in " DR" crash the parser

- **Severity:** High
- **Location:** `file_reader.py` line 73: `str_value = str_value[:-3].strip*()`
- **What is wrong:** A typo. `strip*()` means "the method `strip` multiplied by an empty tuple" instead of calling `strip()`.
- **Impact:** Any balance written like `1234.00 DR` raises `TypeError`, and the whole file fails. Many trial balance exports use DR and CR suffixes.
- **Evidence (M3):** `_parse_balance("100.00 DR")` gives `TypeError: can't multiply sequence by non-int of type 'builtin_function_or_method'`.
- **How found:** M1 suspected it. M2 showed it loads, so it is a runtime bug. M3 confirmed.
- **Concepts:** CON-002 (parsing money text).
- **Fix:** FIX-002

#### BUG-003. Scientific notation is misread

- **Severity:** Medium
- **Location:** `file_reader.py` lines 79 to 87 (the character filter loop)
- **What is wrong:** The loop keeps only digits, one dot and a leading minus. In `1.5E+3` it drops `E` and `+` and keeps `1.53`.
- **Impact:** Excel and some exports write large or small numbers as `1.5E+3`. The value 1,500 would be read as 1.53, with no error.
- **Evidence (M3):** `_parse_balance("1.5E+3")` returns `1.53`.
- **Concepts:** CON-001 (Decimal), CON-002.
- **Fix:** FIX-003

#### BUG-004. Unreadable balances silently become zero

- **Severity:** High
- **Location:** `file_reader.py` lines 90 to 91 (no digits gives 0), and lines 185 to 189, 249 to 253 (`_parse_balance(value) or Decimal('0')` turns a failed parse, `None`, into 0)
- **What is wrong:** If a balance cannot be read, the code quietly uses zero instead of reporting it.
- **Impact:** In regulatory reporting a corrupted cell must stop the process or at least raise a warning. A silent zero could, for example, remove a whole NPF balance and understate the NPF ratio.
- **Evidence (M3):** `_parse_balance("abc")` returns `0`.
- **Concepts:** CON-015 (fail loudly, data quality), CON-031 (audit trail).
- **Fix:** FIX-004

#### BUG-005. Encoding name typo crashes every CSV read

- **Severity:** Critical
- **Location:** `file_reader.py` line 122: `'utr-8-sig'`
- **What is wrong:** It should be `'utf-8-sig'`. Python raises `LookupError` for an unknown encoding name, and the loop only catches `UnicodeDecodeError`, so it does not move on to the next encoding.
- **Impact:** Every CSV file fails before a single row is read.
- **Evidence (M3):** `_read_csv(<T24 csv>, T24)` gives `LookupError: unknown encoding: utr-8-sig`.
- **Concepts:** CON-010 (text encodings and the BOM).
- **Fix:** FIX-005

#### BUG-006. CSV column lookup throws away every value it finds

- **Severity:** Critical
- **Location:** `file_reader.py` lines 169 to 198
- **What is wrong:** The block that stores a value (`if field == 'account_code': ...`) is indented inside the loop over alternative column names, after the `break`. When a matching column is found, the loop breaks *before* storing it. Values are stored only when nothing was found, so every field is stored as empty or zero.
- **Impact:** Every row has an empty account code, every row is skipped, and the reader returns an empty list. CSV ingestion cannot produce any data.
- **Evidence (M3):** With BUG-005 patched in the scratch copy, `_read_csv` on a valid T24 file returns `[]`, and on a valid generic CSV also returns `[]`.
- **Concepts:** CON-003 (Python indentation is logic).
- **Fix:** FIX-006

#### BUG-007. CSV rows would be added several times

- **Severity:** High
- **Location:** `file_reader.py` lines 200 to 208
- **What is wrong:** The net balance calculation and `records.append(record)` are indented inside the `for field` loop instead of after it. Once BUG-006 is fixed, each row would be appended once per field (four or five times).
- **Impact:** Balances would be counted several times, multiplying every total.
- **Evidence (M1):** Read from the indentation. It cannot be shown at runtime until BUG-006 is fixed, because BUG-006 stops any row being appended. The fix test (FIX-007) will prove it.
- **Concepts:** CON-003.
- **Fix:** FIX-007

#### BUG-008. Debit and credit keys do not match

- **Severity:** High
- **Location:** `file_reader.py` lines 185 and 187 store `record['debit']` and `record['credot']` (typo). Line 201 checks for `'debit_balance'` and `'credit_balance'`.
- **What is wrong:** The names written and the names read are different, so the net balance is never calculated for T24 or Flexcube files. Those records have no `balance` at all.
- **Impact:** The two main banking system formats would produce records with no balance. The Excel reader uses `debit_balance` correctly, so the two readers also disagree.
- **Evidence (M1):** Read from the code. Confirmed at runtime as part of FIX-008.
- **Concepts:** CON-020 (trial balance), CON-021 (debit and credit).
- **Fix:** FIX-008

#### BUG-009. `str[value]` crashes on dd/mm/yyyy dates

- **Severity:** High
- **Location:** `file_reader.py` line 196
- **What is wrong:** `str[value]` (square brackets) should be `str(value)`. It raises `TypeError`, and only `ValueError` is caught.
- **Impact:** Any file whose date is not in `yyyy-mm-dd` form crashes. Pakistani bank exports often use `dd/mm/yyyy`.
- **Evidence (M1):** Read from the code. Python has no `str[...]` form that returns a string. Will be shown by the FIX-009 test.
- **Concepts:** CON-011 (date parsing).
- **Fix:** FIX-009

#### BUG-010. `read_file` calls `_read_csv` without the format

- **Severity:** Critical
- **Location:** `file_reader.py` line 295: `records = _read_csv(file_bytes)`
- **What is wrong:** `_read_csv` needs two arguments, the bytes and the detected format. Only one is passed. The format is detected on line 288 and then not used.
- **Impact:** The main entry point fails for every CSV.
- **Evidence (M3):** `read_file(<T24 csv>, "tb.csv")` gives `TypeError: _read_csv() missing 1 required positional argument: 'format'`.
- **Fix:** FIX-010

#### BUG-011. Excel reader puts the account name into the account code

- **Severity:** High
- **Location:** `file_reader.py` line 244
- **What is wrong:** A column counts as the account code if its header *contains* `ACCOUNT` or `CODE`. `ACCOUNT_NAME` and `ACCOUNT_DESC` contain `ACCOUNT`, so the description overwrites the code. Also `'AC_no'` is lowercase but compared with an uppercased header, so it can never match. A header like `BRANCH_CODE` would also be taken as the account code.
- **Impact:** Account codes become names such as "Murabaha", which then match no mapping rule.
- **Evidence (M3):** An Excel file with headers `ACCOUNT_NO, ACCOUNT_NAME, DR_AMT, CR_AMT` was read as `{'account_code': 'Murabaha', ...}`.
- **Concepts:** CON-013 (exact header matching).
- **Fix:** FIX-011

#### BUG-012. Every Excel file is rejected

- **Severity:** Critical
- **Location:** `format_detector.py` line 53: `'[Content_Types.xml]'`
- **What is wrong:** The file inside every XLSX archive is named `[Content_Types].xml` (the bracket closes before `.xml`). The comment on line 52 has it right, the code has it wrong.
- **Impact:** All XLSX uploads fail with "File claims to be XLSX but is not a valid Excel file".
- **Evidence (M3):** A real XLSX made with openpyxl was rejected with exactly that message.
- **Concepts:** CON-014 (XLSX is a ZIP of XML files, magic bytes).
- **Fix:** FIX-012

#### BUG-013. Excel files are always labelled `GENERIC_CSV`

- **Severity:** Medium
- **Location:** `format_detector.py` line 126
- **What is wrong:** For XLSX the detector does not look at headers at all and returns `GENERIC_CSV`.
- **Impact:** The stored `cbs_format` is wrong for every Excel upload, which weakens the audit record. T24 or Flexcube exports saved as Excel would not get their specific handling.
- **Evidence (M1).**
- **Fix:** FIX-013

#### BUG-014. Unclosed quote in an error message

- **Severity:** Low
- **Location:** `file_reader.py` line 298: `'{filename}` has no closing quote.
- **Fix:** FIX-014

#### BUG-015. Sign convention: ratios get negative capital, deposits and income

- **Severity:** Critical
- **Location:** `file_reader.py` lines 65 to 70 (CR means negative), line 204 and line 258 (balance = debit minus credit). `ratios.py` throughout (expects positive amounts).
- **What is wrong:** In double entry accounting, assets have debit balances and liabilities, equity and income have credit balances (CON-021). Debit minus credit is a valid convention, but it makes capital, deposits, reserves and income *negative*. The calculation code adds capital as if it were positive, and checks `if gross_pool_income > 0`. Nothing between the two layers converts signs. The two layers were written with different conventions.
- **Impact:** Every capital, deposit and income based ratio is wrong. CAR comes out negative. Pool ratios fall into their "denominator is zero or less" branch and report 0.
- **Evidence (M3):** The same balances gave CAR = `11.50000000` with positive capital and `-11.50000000` with capital entered as credit (negative), which is exactly what the reader would produce.
- **How found:** M1, from the accountant role, reading the reader and the ratios side by side. Confirmed by M3.
- **Concepts:** CON-020, CON-021 (normal balances), CON-026 (sign normalisation).
- **Fix:** FIX-015

#### BUG-016. Weak CSV validation

- **Severity:** Low
- **Location:** `format_detector.py` lines 72 to 93
- **What is wrong:** `latin-1` can decode any bytes, so any file whose first line has a comma is accepted as a CSV, including binary files renamed to `.csv`. Line 17 imports `struct`, which is never used.
- **Impact:** Junk files get further into the pipeline than they should and fail later with confusing errors.
- **Fix:** FIX-016

### Normalisation layer

#### BUG-017. `get_balance` returns the `Decimal` class instead of zero

- **Severity:** Critical
- **Location:** `service.py` line 52: `default = Decimal`
- **What is wrong:** It should be `Decimal("0")`. It currently returns the class itself, not a number.
- **Impact:** Any calculation that asks for an account the bank does not have crashes. This is very common: few banks have Salam or Istisna balances, and the NPF and CAR code asks for both.
- **Evidence (M3):** `get_balance({}, "X")` returns `<class 'decimal.Decimal'>`. Summing two missing accounts gives `TypeError: unsupported operand type(s) for +: 'int' and 'type'`. CAR with Salam and Istisna missing crashes in the same way.
- **Fix:** FIX-017

#### BUG-018. Mapping patterns match prefixes only

- **Severity:** High
- **Location:** `mapper.py` line 61: `self._compiled_pattern.match(cbs_code)`
- **What is wrong:** `re.match` only anchors at the start of the text. A rule with pattern `3590-MUR` also matches `3590-MUR-NPF-001`.
- **Impact:** Depending on rule order, non performing Murabaha could be mapped into performing Murabaha. That would understate NPF and overstate performing financing. The accountant role treats this as a classification risk.
- **Evidence (M3):** `MappingRule("3590-MUR", ...).matches("3590-MUR-NPF-001")` returns `True`.
- **Concepts:** CON-016 (regular expressions, anchoring), CON-025.
- **Fix:** FIX-018

#### BUG-019. Apportionment loses money and uses float

- **Severity:** Medium
- **Location:** `mapper.py` line 81: `Decimal(str(percentage / 100))`
- **What is wrong:** `percentage / 100` is computed in float before becoming `Decimal`, which breaks the project's own "never float" rule. Nothing checks that the percentages add up to 100, and nothing puts the rounding remainder anywhere.
- **Impact:** Money is created or lost when an account is split. The trial balance would no longer balance.
- **Evidence (M3):** Splitting 100.00 as 33.33 / 33.33 / 33.33 gives 99.99. 0.01 disappears.
- **Concepts:** CON-001, CON-025.
- **Fix:** FIX-019

#### BUG-020. Unknown bank silently gets the sample mapping

- **Severity:** High
- **Location:** `mapper.py` lines 157 to 161
- **What is wrong:** If no mapping file exists for a bank, the loader falls back to `sample_mapping.json` without telling anyone.
- **Impact:** Bank A's data could be mapped using a different bank's or an example chart of accounts, and the report would look normal. For a regulatory filing this must be a hard error.
- **Evidence (M1).**
- **Concepts:** CON-015.
- **Fix:** FIX-020

#### BUG-021. `sample_mapping.json` is empty

- **Severity:** Critical
- **Location:** `backend/config/sample_mapping.json` (0 bytes)
- **Impact:** Combined with BUG-020, every call to `RCOAMapper.load()` ends up here and crashes.
- **Evidence (M3):** `RCOAMapper.load("MEEZ")` gives `JSONDecodeError: Expecting value: line 1 column 1`.
- **Fix:** FIX-021

#### BUG-022. Unmapped accounts disappear without a warning

- **Severity:** Medium
- **Location:** `mapper.py` lines 248 to 257, `aggregate_by_rcoa`
- **What is wrong:** Unmapped accounts are grouped under the code `UNMAPPED`. No ratio reads that code, and no warning is raised.
- **Impact:** A new product account opened by the bank would quietly drop out of every ratio. Good practice is to report unmapped balances and stop if they are material.
- **Concepts:** CON-015, CON-027 (completeness and reconciliation).
- **Fix:** FIX-022

#### BUG-023. Docstrings name things that do not exist

- **Severity:** Low
- **Location:** `normalisation/__init__.py` lines 6 to 18 (`app.layers.normalization`, `NormalizationService`), `mapper.py` line 14 and 119 (`config/mappings/`, while the code looks in `config/`), `service.py` docstring (`NormalizationService`), `mapper.py` line 137 (`MAPPING_CONFIG_DIR`, not a setting)
- **Impact:** Misleads anyone following the docs.
- **Fix:** FIX-023

### Calculations layer

#### BUG-024. NPF function returns an incomplete result

- **Severity:** Critical
- **Location:** `ratios.py` lines 147 to 149
- **What is wrong:** It computes the ratio, the breach flag and the formula, then builds `CalculationResult(ratio_name="NPF_RATIO")` with only the name. The other required fields are missing.
- **Evidence (M3):** `TypeError: CalculationResult.__init__() missing 4 required positional arguments: 'ratio_value', 'numerator', 'denominator', and 'formula_applied'`.
- **Fix:** FIX-024

#### BUG-025. `to_dict` writes `retio_name`

- **Severity:** Medium
- **Location:** `ratios.py` line 68
- **Impact:** The API schema `RatioResponse` expects `ratio_name`, so serialising a result would fail validation.
- **Evidence (M3):** The CAR `to_dict()` output shows `'retio_name': 'CAR'`.
- **Fix:** FIX-025

#### BUG-026. Missing limits become the text "None"

- **Severity:** Low
- **Location:** `ratios.py` lines 74 to 75
- **Evidence (M3):** CAR output shows `'regulatory_maximum': 'None'`. Reports would print the word None.
- **Fix:** FIX-026

#### BUG-027. Depositor share is hard coded at 55%

- **Severity:** Critical
- **Location:** `ratios.py` line 328
- **What is wrong:** `actual_depositor_share = net_distributable_income * 0.55`, then the ratio divides that by `net_distributable_income`. The answer is always exactly 55%, whatever the bank's data. With a 75% minimum this is always reported as a breach.
- **Impact:** A false regulatory breach on every submission.
- **Evidence (M3):** `DEPOSITOR_SHARE_RATIO = 55.00000000, breach = True` on sample data.
- **Fix:** FIX-027 (together with FIX-028)

#### BUG-028. The depositor check tests the wrong thing

- **Severity:** High
- **Location:** `ratios.py` lines 324 to 342, `config.py` line 311
- **What is wrong:** The SBP rule (IFPD Circular No. 09 of 2024, REG-004) requires Islamic banks to pay profit on PKR savings deposits at a *rate* of at least 75% of the weighted average gross yield of all their pools. The pool gross yield is monthly gross earnings divided by monthly average pool assets. Deposits of financial institutions, public sector enterprises and public limited companies are excluded, and so are the pools for SBP's Shariah compliant standing facilities and open market operations. The code instead compares a *share of income*, so even with real data it would answer a different question.
- **Impact:** The check cannot confirm or detect a breach of the actual rule.
- **How found:** M4. Searching for the source of the 75% figure led to the circular itself.
- **Concepts:** CON-043 (pool management), CON-045 (weighted average gross yield).
- **Fix:** FIX-028

#### BUG-029. IRR ratio assumes depositors get 50%

- **Severity:** Medium
- **Location:** `ratios.py` line 309
- **What is wrong:** The IRR denominator uses 50% of gross income as the "depositor share". Line 328 assumes 55%, and the config minimum is 75%. Three different assumptions for the same quantity.
- **Fix:** FIX-029

#### BUG-030. PER and IRR ratios mix a balance with period income

- **Severity:** Medium
- **Location:** `ratios.py` lines 298 to 320, `config.py` lines 309 to 310
- **What is wrong:** PER and IRR are reserves (balances built up over time). Gross pool income is a flow for one period. Dividing one by the other gives a number that changes with the period length. The 20% and 10% caps are marked in `config.py` itself as indicative, not SBP limits (REG-005), yet they drive `breach_flag`.
- **Impact:** Reports could show "breaches" of limits SBP does not set.
- **Concepts:** CON-044 (PER and IRR), CON-028 (stock vs flow).
- **Fix:** FIX-030

#### BUG-031. Profit rate always annualised as one month

- **Severity:** Medium
- **Location:** `ratios.py` line 349
- **What is wrong:** Multiplies by 12 whatever the actual reporting period is. The submission has `reporting_period_start` and `reporting_period_end`, which are not used. The formula text says "Average Deposits", but the code uses closing balances.
- **Impact:** A quarterly submission would overstate the rate about three times.
- **Fix:** FIX-031

#### BUG-032. CAR is heavily simplified

- **Severity:** High
- **Location:** `ratios.py` lines 153 to 250
- **What is wrong:** Disclosed in comments as a prototype simplification, but material:
  - risk weighted assets include only financing at 100%. There is no market risk or operational risk RWA, and no risk weights by counterparty
  - cash and government Sukuk are read (lines 216 to 217) but not used
  - no regulatory deductions (goodwill, intangibles, deferred tax)
  - general provisions counted in Tier 2 with no cap
  - there are no separate minimums for CET1 and Tier 1, only total CAR
  - the `formula` variable on line 238 is built and never used
- **Impact:** The reported CAR would not match the bank's real Basel III return.
- **Concepts:** CON-040 (CAR), CON-041 (Basel III capital tiers), CON-042 (risk weighted assets).
- **Fix:** FIX-032

#### BUG-033. NPF denominator assumption is not enforced

- **Severity:** Medium
- **Location:** `ratios.py` lines 109 to 117
- **What is wrong:** The comment says the `3590` financing codes are "performing + non-performing". NPF sits in separate `3595` codes. If the mapping puts NPF only in `3595` (which the code naming suggests), then total gross financing must be `3590 + 3595`. Otherwise the denominator is too small and the NPF ratio is overstated. Nothing in the code or mapping enforces either choice.
- **Concepts:** CON-038 (NPF), CON-024.
- **Fix:** FIX-033

#### BUG-034. 7% NPF "maximum" is not verified as an SBP limit

- **Severity:** Medium
- **Location:** `config.py` line 287, `ratios.py` docstring lines 98 to 104
- **What is wrong:** It is described as a maximum "per SBP CAELS guidelines" and drives a breach flag. It has not been verified as a binding SBP limit (REG-003). CAELS (CON-034) is SBP's rating framework, not a list of hard limits.
- **Fix:** FIX-034

#### BUG-035. Promised calculations do not exist

- **Severity:** Low
- **Location:** `ratios.py` docstring lines 4 to 25 (provisions, ECL, `CalculationService`). `DPD_THRESHOLDS` and `PROVISION_RATES` are imported but unused.
- **Fix:** FIX-035 (and GAP-014)

### Configuration and regulatory references

#### BUG-036. The verification note is wrong about IFPD

- **Severity:** High (compliance documentation)
- **Location:** `config.py` lines 237 to 241 and 264 to 272
- **What is wrong:** The note says "IFPD does not appear to be a real SBP department code" and lists "IFPD Circular 09/2024" as likely fabricated. Both statements are false:
  - The Islamic Finance Policy Department (IFPD) is a real SBP department in the Islamic Finance Group, set up in December 2022 (REG-001).
  - IFPD Circular No. 09 of 2024 is real, and it is the source of the 75% rule (REG-004). It was later amended by IFPD Circular Letter No. 01 of 2025.

  The same note gives the 75% rule's source as IBD Circular No. 03 of 2012 instead. The settings even contain the correct `SBP_IFPD_URL`.

  **Update 2026-11-06 (second research pass):** "IFPD Circular 08/2024" (the Revised Shariah Governance Framework) and "BSD-1 Circular 01/2025" (DFS revisions through DAP4) also appear to be real (REG-008). That makes four of the five "fabricated" references wrong. "IBD Circular 02/2019" is still unchecked.
- **Impact:** Correct references were deleted and replaced with vaguer ones. Anyone relying on the note would distrust a real circular.
- **How found:** M4.
- **Fix:** FIX-036

#### BUG-037. `DFS_VERSION` uses a citation the file says does not exist

- **Severity:** Medium
- **Location:** `config.py` line 340: `DFS_VERSION = "BSD1-01-2025"`
- **What is wrong:** The verification note says "BSD-1 Circular 01/2025" could not be found, but the constant still uses it. It will be written into every DFS file.
- **Update 2026-11-06:** The circular appears to be real (BSD-1 C01/2025, revisions to Data File Structures for RCOA returns through DAP4, REG-008 and REG-015). So the note is wrong, not the reference. The remaining problem: a circular number is not a file format version, and the real DFS layouts are not public. They are given to banks through DAP4. The fix becomes a pluggable export adapter, marked "format not certified" (see [07 section 1.5](07-guidelines-and-data.md)).
- **Fix:** FIX-037

#### BUG-038. Default secret key only gives a warning

- **Severity:** Medium
- **Location:** `config.py` line 157 and the `validate_secret_key` validator
- **What is wrong:** If production forgets to set `SECRET_KEY`, the app starts anyway with a key everyone can read in this repository. Anyone could then sign valid login tokens.
- **Concepts:** CON-066 (JWT signing).
- **Fix:** FIX-038

#### BUG-039. Known default passwords

- **Severity:** Medium
- **Location:** `config.py` lines 173 to 177 (`ChangeMe123!` for admin and demo users)
- **Fix:** FIX-039

#### BUG-040. Dependency versions not pinned

- **Severity:** Medium
- **Location:** `backend/requirements.txt` (only `>=` minimums)
- **Impact:** Two installs on different days can get different library versions. For a regulatory system the same input must always give the same output, so the exact versions must be recorded.
- **Concepts:** CON-017 (reproducible builds).
- **Fix:** FIX-040

### Models and schemas

#### BUG-041. `RawSubmission.to_dict` crashes on partial objects

- **Severity:** Medium
- **Location:** `models/submission.py` lines 40 to 58
- **What is wrong:** Fields are only type annotations at class level, with no values. If a field was not passed in, reading it raises `AttributeError`. The `hasattr` guard protects `id` only.
- **Evidence (M3):** `RawSubmission(id="1").to_dict()` gives `AttributeError: 'RawSubmission' object has no attribute 'institution_code'`.
- **Fix:** FIX-041

#### BUG-042. `File_size_bytes` has a capital F

- **Severity:** Medium
- **Location:** `schemas/submission.py` line 53
- **Impact:** The database and model use `file_size_bytes`, so building `SubmissionDetail` from a database row would fail as a required field missing.
- **Fix:** FIX-042

#### BUG-043. Passwords limited to 15 characters

- **Severity:** Medium
- **Location:** `schemas/submission.py` line 231
- **What is wrong:** Long passphrases are the strongest kind of password, and current guidance (NIST SP 800-63B) says to allow at least 64 characters. bcrypt reads up to 72 bytes.
- **Evidence (M3):** A 26 character passphrase is rejected.
- **Concepts:** CON-067 (bcrypt).
- **Fix:** FIX-043

#### BUG-044. `occured_at` spelling

- **Severity:** Low
- **Location:** `schemas/submission.py` line 124. Should be `occurred_at`. Must be fixed before the database table is created, or it gets baked into the database.
- **Fix:** FIX-044

#### BUG-045. Health check default says `local_sqlite`

- **Severity:** Low
- **Location:** `schemas/submission.py` line 266. The stack is Supabase PostgreSQL. Leftover from an earlier design.
- **Fix:** FIX-045

#### BUG-046. Email and role are unchecked text

- **Severity:** Low
- **Location:** `schemas/submission.py` lines 230, 233
- **What is wrong:** Email is a plain string, so `abc` is accepted. Role accepts any text, so `SUPERADMIN` or a typo would be stored.
- **Fix:** FIX-046

### Repository

#### BUG-047. `.gitignore` is incomplete

- **Severity:** High (data protection)
- **Location:** `.gitignore`
- **What is wrong:** It does not ignore `backend/uploads/raw/*` or `backend/uploads/reports/*`, which will hold real bank trial balances and reports. It also does not ignore `__pycache__/`, `node_modules/`, `.DS_Store`, `.pytest_cache/`, or Astro build output.
- **Impact:** One careless `git add .` could publish confidential bank financial data. During this audit, running the compile check created `__pycache__` folders that git immediately listed as new files (they were deleted).
- **Concepts:** CON-018 (data confidentiality).
- **Fix:** FIX-047

---

## Gaps (planned but not built)

These are empty files or features described in docstrings with no code. They are not defects in existing code, but the system cannot work without them.

| ID | Gap | Files |
|---|---|---|
| GAP-001 | Application entry point and API routes | `app/main.py`, `app/api/*.py` |
| GAP-002 | Database connection, auth dependencies, security helpers, audit logging | `app/core/database.py`, `deps.py`, `security.py`, `audit.py` |
| GAP-003 | Pipeline runner that joins the layers and records status changes | `app/services/pipeline_runner.py` |
| GAP-004 | Normalisation service (load mapping, map, aggregate, store) | `layers/normalisation/service.py` |
| GAP-005 | Validation layer (cross return, DFS format, Shariah, breach, IFRS 9) | not created |
| GAP-006 | Reporting layer (PDF, DFS file) | not created |
| GAP-007 | AI commentary with local Ollama and hallucination checks | not created |
| GAP-008 | SBP circular monitor | not created |
| GAP-009 | Database schema and migrations | `supabase/migrations/*.sql` |
| GAP-010 | Frontend | everything in `frontend/` |
| GAP-011 | Containers and deployment | `docker-compose.yml`, Dockerfiles, Caddyfile, `.dockerignore` |
| GAP-012 | Tests | `backend/tests/*.py` |
| GAP-013 | README and real mapping configuration | `README.md`, `backend/config/` |
| GAP-014 | Provisioning and ECL calculations | promised in `ratios.py` docstring |
