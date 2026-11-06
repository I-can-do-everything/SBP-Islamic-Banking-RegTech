# 07. Official Guidelines, Data Plan and AI Models

**Status:** Research snapshot, 2026-11-06
**Used by:** [06-system-design.md](06-system-design.md) and the rulebook (DEC-005)
**Verification of individual facts:** [05-regulatory-verification.md](05-regulatory-verification.md) (REG ids)

## How this research was done, and its limits

Three research passes were run in parallel: SBP guidelines, datasets and calibration figures, and AI models.

**Important limit:** this cloud workspace's network could not open `sbp.org.pk`, bank websites or `openrouter.ai` directly. The proxy refused the connections. Every fact below therefore comes from web search results: quoted snippets of official SBP pages, news reports (Dawn, Business Recorder) and banks' own published disclosures. None is yet marked "Verified (primary)". Before any rule value goes into the rulebook as verified, the primary page must be read.

**Update, same day:** the workspace network now allows `www.sbp.org.pk`, `archive.sbp.org.pk` and `openrouter.ai` (environment "SBP-Islamic-Banking-RegTech"). OpenRouter is reachable. SBP's site still answers 403 from its own Cloudflare bot protection, which blocks automated clients. We will not try to get around a website's bot protection. Instead, the owner downloads the circulars in a normal browser and saves them to `docs/sources/sbp/`, and they are read from there. The priority list is at the end of [05-regulatory-verification.md](05-regulatory-verification.md).

Status words used here are the same as in file 05:

| Status | Meaning |
|---|---|
| Secondary (SBP snippet) | Text quoted from an sbp.org.pk page in search results, but the full page has not been read |
| Secondary | News reports or bank disclosures |
| Unverified | Background knowledge, to be checked |

---

## 1. Regulatory map

What the system implements, and where each rule comes from.

### 1.1 Capital adequacy (Basel III)

| Rule | Value | Source | Status |
|---|---|---|---|
| Framework | Instructions for Basel III Implementation in Pakistan | BPRD Circular No. 06 of 2013 ([link](https://www.sbp.org.pk/bprd/2013/C6.htm)) | Secondary (SBP snippet) |
| CET1 minimum | 6.0% | same, and bank disclosures for Dec 2025 | Secondary |
| Tier 1 minimum | 7.5% | same | Secondary |
| Total CAR minimum, before buffer | 10.0% | same | Secondary |
| Capital conservation buffer | 1.5% (cut from 2.5% in March 2020, not restored as far as found) | BPRD CL No. 12 of 2020 ([link](https://www.sbp.org.pk/bprd/2020/CL12.htm)) | Secondary (SBP snippet) |
| Total CAR including buffer | **11.5%** | sum of the above, and bank disclosures | Secondary |
| Leverage ratio | 3% (Tier 1 / exposure) | BPRD C06/2013 | Secondary |
| D-SIB surcharges | Bank specific (none of the current D-SIBs is an Islamic bank). Configurable per institution | SBP press releases 29 Aug 2025 and 21 Aug 2026 | Secondary |
| Credit risk weights (standardised) | Revised approach (Basel III Phase II). PKR claims on GoP and SBP get 0% | BPRD Circular No. 03 of 2025 ([link](https://www.sbp.org.pk/bprd/2025/C3.htm)) | Secondary (SBP snippet). The full risk weight annex must be read |
| IFRS 9 transitional add back to CET1 | Over 5 years, for new Stage 1 and 2 ECL only, from 90% down to 10% | BPRD C03/2022 Annex B ([link](https://www.sbp.org.pk/bprd/2022/C3-Annex-B.pdf)) | Secondary |
| Minimum paid up capital | Rs 20 billion by 31 Dec 2030 (was Rs 10 billion) | BPRD Circular No. 02 of 2026 (27 Oct 2026) | Secondary (news) |

**Islamic contracts:** no SBP Islamic specific risk weight annex was found. SBP appears to apply the standardised approach by economic substance:
- Murabaha, Salam and Istisna receivables use the counterparty's risk weight.
- Ijarah and Diminishing Musharakah use the counterparty, retail or housing weights.
- Equity type Musharakah and Mudarabah investments are treated as equity or investment exposures.
- GoP Ijarah Sukuk in PKR get 0%.

This is unverified, so the rulebook will hold risk weights as data that can be changed and will label them.

### 1.2 Asset classification, provisioning and IFRS 9

| Rule | Value | Source | Status |
|---|---|---|---|
| Corporate and commercial classification by days past due (DPD) | OAEM 60 (0%), Substandard 90 (25%), Doubtful 180 (50%), Loss 365 (100%). Provision on outstanding less allowed collateral (forced sale value) | Prudential Regulations R-8, BSD C07/2005 ([link](https://www.sbp.org.pk/bsd/2005/C7.htm)) | Secondary for 90, 180, 365 and 25%. OAEM and 50%, 100% Unverified |
| SME, consumer, agriculture, housing | Similar pattern with category differences. Credit cards and trade bills: Loss at 180 days | PR annexures | Unverified (each category's annex must be read) |
| IFRS 9 instructions | SBP IFRS 9 Application Instructions | BPRD Circular No. 03 of 2022 ([link](https://www.sbp.org.pk/bprd/2022/C3.htm)) | Secondary (SBP snippet) |
| IFRS 9 effective date | 1 January 2024 | BPRD CL No. 07 of 2023 | Secondary |
| Stage backstops (corporate, consumer) | Stage 1: 0 to 59 DPD. Stage 2: 60 to 89 DPD. Stage 3: 90+ DPD | C03/2022 Annexure C (as updated) | Secondary (garbled snippet) |
| Stage backstops (housing, infrastructure) | Stage 2: 90 to 179. Stage 3: 180+ | same | Secondary |
| Stage backstops (agriculture) | Stage 2: 90 to 364. Stage 3: 365+ | same | Secondary |
| Stage 3 floor | Provision = higher of IFRS 9 ECL and the Prudential Regulations requirement | same | Secondary |
| Charity on Islamic products | Must not be recognised as income | BPRD CL No. 01 of 2025 | Secondary (SBP snippet) |
| Extra Stage 1 and 2 provisions above ECL | May be kept until 31 Dec 2026 | BPRD CL 01/2025 | Secondary |

**NPF "maximum 7%" (prototype):** no SBP source found. It stays an internal alert threshold, not a regulatory limit (REG-003, FIX-034).

### 1.3 Pool management and profit distribution

| Rule | Value | Source | Status |
|---|---|---|---|
| Base instructions | Profit and Loss Distribution and Pool Management for IBIs. Board and Shariah Board approved pool framework, copy to SBP within 3 months | IBD Circular No. 03 of 2012 ([link](https://www.sbp.org.pk/ibd/2012/C3.htm)) | Secondary (SBP snippet) |
| Mudarib share cap | Not more than 50% of distributable profit | same | Secondary |
| PER | Set aside from gross pool income before the bank and depositor split, within the bank's own approved policy | same | Secondary |
| IRR | Set aside from the depositors' share. Cap reported as up to 1% of depositors' profit (old annex) | same | Unverified |
| Weightages | Declared in advance for each month, published, not changed within the month | same | Partly unverified (exact notice period) |
| Special Hiba | Not allowed from January 2015 | IBD CL No. 01 of 2013 | Secondary |
| **Minimum profit on PKR savings** | **At least 75% of the weighted average gross yield (WAGY) of all pools, from 1 Jan 2025.** Excludes deposits of financial institutions, public sector enterprises and public limited companies | IFPD Circular No. 09 of 2024 ([link](https://www.sbp.org.pk/ifpd/2024/C9.htm)) | Secondary (SBP snippet and news) |
| WAGY formula | Each pool: monthly gross earnings / monthly average pool assets. Weighted across pools. Pools for Shariah compliant standing ceiling facility and OMOs excluded. "(excluding fixed assets)" was deleted, so all pool assets count | C9/2024 and IFPD CL No. 01 of 2025 | Secondary (SBP snippet) |
| Hiba from Mudarib share | Allowed as "a part of" the share to meet the minimum. A bank with a PER may cut its Mudarib share only if the PER is insufficient | C9/2024 | Secondary |
| Provision reversals | Credited to the same pool that bore the charge | IFPD CL 01/2025 | Secondary |
| Pool audit | External audit covers pool management and its IT systems. External Shariah audit report to SBP within 45 days | IBD CL No. 01 of 2017 | Secondary |

### 1.4 Shariah governance

| Rule | Source | Status |
|---|---|---|
| Revised Shariah Governance Framework, effective 1 Jan 2025, replaces IBD C01/2018 | IFPD Circular No. 08 of 2024 ([link](https://www.sbp.org.pk/ifpd/2024/C8.htm)) | Secondary (SBP snippet and news) |
| AAOIFI standards adopted with SBP changes: SS 31 (gharar), SS 47 (profit calculation), SS 20 (commodities), Tawarruq | IFPD C01, C02, C03 of 2025 and C03 of 2026 | Secondary |
| Placement of Islamic funds with a conventional parent is restricted | IFPD Circular No. 01 of 2026 | Secondary |

**Shariah checks the system will automate** (design choices based on the rules above):
- charity income excluded from income and pool income
- Mudarib share at most 50%
- the monthly 75% WAGY test
- provision reversals to the right pool
- no special Hiba
- weightages declared before the month and unchanged
- every deposit and asset tagged to exactly one pool
- PER and IRR within the bank's policy
- no mixing with conventional funds

### 1.5 Reporting to SBP

| Fact | Value | Source | Status |
|---|---|---|---|
| Portal | Data Acquisition Portal, version 4 (DAP4) | BSD-1 C01/2025 | Secondary |
| File formats | DFS (Data File Structures) for RCOA (Reporting Chart of Accounts) returns. So "DFS" in the prototype is the correct term | same | Secondary |
| Revision | New DFS for all RCOA returns for IFRS 9 and new financial statement formats; old DFS discontinued | BSD-1 Circular No. 01 of 2025 ([link](https://www.sbp.org.pk/bsd-1/2025/C1.htm)), 24 Jan 2025 | Secondary (SBP listing and news) |
| Deadlines | Daily and weekly returns: 2 working days. Monthly: 5. Quarterly: 12 | same | Secondary |
| Is RCOA public? | No. Code lists and DFS templates are given to reporting entities through DAP4 | | Unverified |

**What this means for the build:** we cannot copy the real RCOA codes or DFS layouts. The system uses an **illustrative reporting code structure** that follows the same principles: hierarchical codes, normal balances, and returns as schedule by line by column. It is clearly labelled as illustrative. The export format is a pluggable adapter, so a bank with DAP4 access could add the real DFS layout as configuration. This is the honest version of FIX-037.

### 1.6 Technology, outsourcing, cloud and AI

| Rule | Value | Source | Status |
|---|---|---|---|
| Technology governance | Enterprise Technology Governance and Risk Management Framework | BPRD Circular No. 05 of 2017 | Secondary |
| Outsourcing | Outsourcing outside Pakistan needs prior SBP approval | BPRD Circular No. 06 of 2019 | Secondary |
| Cloud | Banks: material workloads only on onshore cloud providers unless SBP approves offshore case by case. Board approval, data segregation | BPRD Circular No. 01 of 2023 ([link](https://www.sbp.org.pk/bprd/2023/C1.htm)) | Secondary (SBP snippet) |
| AI | SBP Responsible AI guidelines were in draft (2025). No final guideline found by Nov 2026 | news | Secondary |
| Data protection law | No general personal data protection act in force as of Nov 2026. Banking secrecy (Banking Companies Ordinance 1962 s.33A) applies | legal guides, news | Secondary |

**What this means for the build:**
- A regulatory reporting system holding customer level financing and deposit data is very likely a *material workload*. So in production it runs on premises or with an onshore provider, and AI runs locally (Ollama). This confirms DEC-013 and the production design in 06 section 12.
- The cloud demo is acceptable only because it holds synthetic data for a fictional bank.
- Even with synthetic data, the AI gateway sends only aggregated figures and uses OpenRouter's zero data retention routing, so the demo builds the right habits.

### 1.7 Liquidity (later milestone)

| Rule | Value | Source | Status |
|---|---|---|---|
| LCR and NSFR | Minimum 100% each, applies to Islamic banks | BPRD Circular No. 08 of 2016 | Circular Secondary, values Unverified |

---

## 2. Data plan

### 2.1 Public datasets reviewed

**Finding:** no public dataset has a real Pakistani bank's trial balance or chart of accounts, and SBP's RCOA codes are not public. So we **generate our own synthetic data**. Public datasets are used only as structural references, and their raw rows are never committed (several licences forbid redistribution).

| Dataset | What we borrow | Licence note |
|---|---|---|
| FFIEC Call Reports (US) | Regulatory return shape: schedule, line item code, value, plus validation rules | Public |
| EBA transparency and stress test files | IFRS 9 stage and non performing exposure breakdowns | Public with attribution |
| IFSB Prudential and Structural Islamic Financial Indicators | Indicator definitions (CAR, NPF, financing by mode) for Islamic banks, including Pakistan | Public |
| Oracle Flexcube GL documentation | GL hierarchy: node and leaf accounts, codes of up to 9 characters, only leaf accounts take postings | Docs, structure only |
| Temenos T24 reporting notes (unofficial) | Product category ranges and consolidation keys | Unofficial, inspiration only |
| Berka (PKDD 1999 Czech bank) | Core banking relational model: client, account, transaction, loan | No explicit licence, structure only |
| Home Credit (Kaggle 2018) | Application, contract, monthly balance and instalment tables | Competition rules, structure only |
| Freddie Mac and Fannie Mae loan level data | Origination plus monthly performance split, used for home finance (Diminishing Musharakah) | No redistribution, structure only |
| IBM AMLworld (NeurIPS 2023) | Transaction layout (from and to bank and account, amount, payment type) | CDLA Sharing 1.0 |
| AgamiAI Indian Bank Statements (Hugging Face, 2025) | South Asian transaction narration style | Apache 2.0 |

### 2.2 Calibration figures (to make EXIB look like a real Pakistani Islamic bank)

| Figure | Value | Date | Source | Status |
|---|---|---|---|---|
| Islamic banking assets | PKR 16.3 trillion, 23.7% market share | Jun 2026 | SBP Islamic Banking Bulletin Jun 2026 | Secondary (SBP PDF snippet) |
| Islamic banking deposits | PKR 12.7 trillion | Jun 2026 | same | Secondary (SBP PDF snippet) |
| Islamic banking net financing | PKR 6.0 trillion. Financing to deposits about 49 to 51% | Jun 2026, Mar 2026 | same | Secondary (SBP PDF snippet) |
| Branches | 7,757 | Jun 2026 | same | Secondary (SBP PDF snippet) |
| Financing mix | Diminishing Musharakah 34.0%, Musharakah including Running Musharakah 25.7%, Istisna 10.1%, Murabaha 9.2%, others about 21% (Ijarah, Salam, Tijarah and others) | Mar 2026 | IBB Mar 2026 | Secondary (SBP PDF snippet) |
| Deposit mix | Current (Qard, no profit) about 41%, savings (Mudarabah) about 36%, term about 22% | Dec 2025 | IBB Dec 2025 via news | Secondary |
| NPF ratio (gross) | 2.4% | Mar 2026 | IBB Mar 2026 | Secondary (SBP PDF snippet) |
| Provision coverage | about 125% (industry), 146% (largest Islamic bank) | 2025 to 2026 | IBB, bank annual report | Secondary |
| CAR (Islamic banks) | 17.6% | Mar 2026 | IBB Mar 2026 | Secondary (SBP PDF snippet) |
| Savings profit rate example | 6.3% to 7.0% a year (one large bank, individual savings, 2026) | 2026 | bank's published rate sheet | Secondary |
| Mudarib share on general PKR pools | Typically 50% | 2026 | several banks' declared rate sheets | Secondary |
| SBP policy rate | 12.00% from 27 Oct 2026 | Oct 2026 | SBP Monetary Policy Committee (news) | Secondary |
| Account size skew | About 70% of accounts under Rs 50,000. About 3% over Rs 1 million | 2025 | news citing SBP deposit statistics | Secondary |

The demo dataset will state "calibrated to SBP Islamic Banking Bulletin, March and June 2026" in its metadata.

### 2.3 Synthetic data generator (`datagen`)

**Design:**
- Pure Python using NumPy and Polars. It writes Parquet and CSV directly.
- **Seeded and deterministic:** the same seed always gives byte identical files, so tests and screenshots are reproducible.
- **Generated from the bottom up:** customers, then accounts and contracts, then daily balances and instalments, then GL postings, then the trial balance. Because the trial balance is built from the detail, the reconciliation checks have something real to reconcile.
- Islamic contract fields on the financing tape:
  - mode, asset or commodity
  - cost and profit (Murabaha)
  - rental schedule (Ijarah, Diminishing Musharakah)
  - bank's share units (Diminishing Musharakah)
  - profit sharing ratio (Musharakah)
  - prudential category, DPD, IFRS 9 stage, collateral forced sale value
  - pool assignment
- Pools: monthly pool assets, gross income, Mudarib share, weightages and declared rates. These are calibrated so EXIB passes the 75% test in most months, with one planted near miss.
- Exports in three layouts (T24 style, Flexcube style and generic) as CSV, XLSX and Parquet.
- **Dirty data mode:** plants the exact problems found in the prototype audit:
  - DR and CR suffixes, brackets for negatives, scientific notation
  - Windows-1252 encoding and a byte order mark
  - dd/mm/yyyy dates
  - an unreadable cell, an unmapped new product account
  - a one paisa trial balance difference, a branch missing from the portfolio
  - an account on its abnormal side

  Every planted problem must be caught by the pipeline. This turns the bug register into a living test.
- Fictional names only. Customer identifiers are random and clearly fake (they do not follow the real CNIC check pattern).

**Sizes** (design assumptions scaled from the ratios above, not sourced figures):

| Dataset | Demo bank (EXIB) | Large bank scale test |
|---|---|---|
| Branches | 25 | 1,150 |
| Customers | 20,000 | 5,000,000 |
| Deposit accounts | 30,000 | 8,000,000 |
| Financing contracts | 3,000 | 600,000 |
| Repayment and rental schedule rows | about 150,000 | about 30 million |
| Daily deposit balance rows per month | 900,000 | **240 million** |
| Daily financing balance rows per month | 90,000 | 18 million |
| GL leaf accounts | about 400 | about 2,500 |
| Trial balance rows (branch by account, non zero only) | about 6,000 | about 1 million |
| Pools | 4 | 10 |

The large profile sets the scale target N1 in 06. A one month large bank run is about 240 million rows of daily balances, which is the main reason for the Parquet plus DuckDB design (DEC-002).

---

## 3. Reporting codes used by the demo

Because the official RCOA is not public, the demo uses an illustrative code tree designed to mirror its principles. The tree has these branches:

- assets (cash and balances with SBP, due from financial institutions, investments including GoP Ijarah Sukuk, Islamic financing by mode with performing and non performing sub codes, fixed assets, other assets)
- liabilities (deposits by type and contract, due to financial institutions, subordinated Sukuk, other liabilities, PER, IRR)
- equity (paid up capital, statutory reserve, other reserves, unappropriated profit)
- income and expense by mode and pool
- memorandum codes for the capital and pool calculations

Each code carries its normal balance and its parent. The full list ships in `mappings/reporting_codes.yaml` with a header saying it is illustrative.

---

## 4. AI models (testing through OpenRouter)

**Research limit:** `openrouter.ai` could not be opened from this workspace, so model names and prices come from search snippets of OpenRouter pages and price trackers. They are stored as configuration, not code, and will be confirmed with the live `/api/v1/models` endpoint when M9 starts.

### 4.1 OpenRouter settings we will use

- Endpoint: `https://openrouter.ai/api/v1`, OpenAI compatible, with a bearer token kept in the environment.
- Request `provider: { zdr: true, data_collection: "deny", require_parameters: true }`. This routes only to zero data retention endpoints that support the features we ask for.
- `response_format` with a strict JSON schema for structured output.
- A `models: [...]` list for automatic fallback.
- Usage and cost are recorded from each response.
- Free (`:free`) models are limited (20 requests per minute, 50 to 1,000 per day) and usually log prompts. Use them only for quick development, never with the zero retention setting.

### 4.2 Initial model choices (to confirm at M9)

| Task | Primary (demo) | Low cost or fallback | Local production (Ollama) |
|---|---|---|---|
| Executive commentary (strict JSON, numbers only) | `anthropic/claude-sonnet-4.6` | `openai/gpt-5-mini`, `google/gemini-3.1-flash-lite` | `qwen3.6:27b` or `gemma4:26b` (24 GB GPU) |
| Mapping suggestions | embeddings `qwen/qwen3-embedding-0.6b` + reranker `openai/gpt-5-nano` | `deepseek/deepseek-v4-flash` | `qwen3-embedding` + `qwen3.5:9b` (same embedding family, so vectors stay compatible) |
| Circular analysis (long documents) | `google/gemini-3.6-flash` | `deepseek/deepseek-v4-pro`, `qwen/qwen3.6-plus` | `qwen3.6:27b` with a large context, plus chunking |
| Analyst Q and A (tool calling) | `anthropic/claude-sonnet-4.6` | `openai/gpt-5-mini` | `qwen3.6:27b` or `gpt-oss:20b` |

Notes:
- Using the same open weight families (Qwen, DeepSeek, gpt-oss) in the demo where possible makes the switch to local more predictable.
- All prices and names are "unconfirmed" until checked live. The evaluation suite (06 section 9) decides the final choice by measured grounding and accuracy, not by reputation.

### 4.3 Differences the gateway hides

| Difference | Handling |
|---|---|
| Model names | Per task name map in configuration |
| Structured output | Strict schema where supported, then Pydantic validation, one retry with the error message, then a template fallback |
| Context length | Ollama's context is set per model (`num_ctx`). Long circulars are chunked and summarised in two stages on both providers |
| Tool calling reliability | Few, flat tools, a cap on agent steps, and validation of tool arguments |
| Cost reporting | Recorded on OpenRouter. Tokens and latency only on Ollama |
| Fallbacks | OpenRouter `models` list, and our own retry for Ollama |

---

## 5. Sources

**SBP pages and circulars** (as cited in search results; full pages to be read once network access is allowed):

- [BPRD C06/2013](https://www.sbp.org.pk/bprd/2013/C6.htm)
- [BPRD CL12/2020](https://www.sbp.org.pk/bprd/2020/CL12.htm)
- [BPRD C03/2025](https://www.sbp.org.pk/bprd/2025/C3.htm)
- [BPRD C03/2022](https://www.sbp.org.pk/bprd/2022/C3.htm)
- [C03/2022 Annex B](https://www.sbp.org.pk/bprd/2022/C3-Annex-B.pdf)
- [BPRD CL07/2023](https://www.sbp.org.pk/bprd/2023/CL7.htm)
- [BPRD CL20/2025](https://www.sbp.org.pk/bprd/2025/CL20.htm)
- [BSD C07/2005](https://www.sbp.org.pk/bsd/2005/C7.htm)
- [IBD C03/2012](https://www.sbp.org.pk/ibd/2012/C3.htm)
- [IBD CL01/2013](https://www.sbp.org.pk/ibd/2013/CL1.htm)
- [IFPD C09/2024](https://www.sbp.org.pk/ifpd/2024/C9.htm)
- [IFPD CL01/2025](https://www.sbp.org.pk/circulars/ifpd-circular-letter-no-01-of-2025)
- [IFPD C08/2024](https://www.sbp.org.pk/ifpd/2024/C8.htm)
- [BSD-1 C01/2025](https://www.sbp.org.pk/bsd-1/2025/C1.htm)
- [BPRD C05/2017](https://www.sbp.org.pk/bprd/2017/C5.htm)
- [BPRD C06/2019](https://www.sbp.org.pk/bprd/2019/C6.htm)
- [BPRD C01/2023](https://www.sbp.org.pk/bprd/2023/C1.htm)
- [BPRD C08/2016](https://www.sbp.org.pk/bprd/2016/C8.htm)

**SBP publications:**

- [Islamic Banking Bulletin June 2026](https://www.sbp.org.pk/assets/document/publications/Islamic_Banking_Bulletin_-_30_June_2026.pdf)
- [Islamic Banking Bulletin March 2026](https://www.sbp.org.pk/assets/document/publications/Islamic_Banking_Bulletin-31March2026.pdf)
- [Islamic Banking Bulletin December 2025](https://www.sbp.org.pk/assets/document/publications/Islamic_Banking_Bulletin_December_2025.pdf)
- [Banking Sector Review H1 CY26](https://www.sbp.org.pk/assets/document/publications/H1CY26.pdf)
- [Financial Stability Review 2025](https://www.sbp.org.pk/assets/document/publications/Financial-Stability-Review-2025.pdf)

**News:**

- [Business Recorder on the revised DFS](https://www.brecorder.com/news/40344539/banks-dfis-sbp-revises-dfss-of-all-rcoa-returns)
- [Business Recorder on the 75% rule](https://www.brecorder.com/news/40334633)
- [Dawn](https://www.dawn.com/news/1875065)

**Datasets:**

- [FFIEC CDR](https://cdr.ffiec.gov/public/)
- [EBA transparency exercise](https://www.eba.europa.eu/risk-and-data-analysis/risk-analysis/eu-wide-transparency-exercise)
- [IFSB data](https://www.ifsb.org/data-metadata/)
- [Oracle Flexcube GL](https://docs.oracle.com/cd/E64763_01/html/GL/GL01_C.htm)
- [IBM AML data](https://github.com/IBM/AML-Data)
- [Freddie Mac loan level](https://freddiemac.com/research/datasets/sf-loanlevel-dataset)
- [AgamiAI statements](https://huggingface.co/datasets/AgamiAI/Indian-Bank-Statements)

**AI:**

- [OpenRouter quick start](https://openrouter.ai/docs/quick-start)
- [Provider routing](https://openrouter.ai/docs/features/provider-routing)
- [Zero data retention](https://openrouter.ai/docs/features/zdr)
- [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs.md)
- [Limits](https://openrouter.ai/docs/api/reference/limits)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
