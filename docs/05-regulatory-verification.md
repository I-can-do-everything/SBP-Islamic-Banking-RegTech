# 05. Regulatory Verification Log

Every regulatory number and reference used by the system, with its source and how sure we are of it. This file is the single source of truth: code comments should point here, not repeat their own versions.

**Important:** this is research from public sources. It is not a review by a licensed compliance officer, lawyer or Shariah adviser. Before any real filing, every item must be confirmed against the current SBP circulars and the bank's own compliance function.

## Status values

| Status | Meaning |
|---|---|
| Verified (primary) | Confirmed on the SBP website or in the circular itself |
| Verified (secondary) | Confirmed by reliable secondary sources (major newspapers, bank disclosures), primary text not yet read in full |
| Claimed | Stated as verified in the original code, not re-checked in this project yet |
| Unverified | Plausible, no source found yet |
| Wrong | Shown to be incorrect |

---

## Log

### REG-001. IFPD is a real SBP department
- **Claim in code:** `config.py` lines 268 to 270 say "IFPD does not appear to be a real SBP department code".
- **Finding:** The claim is **wrong**. The Islamic Finance Policy Department (IFPD) is an SBP department within the Islamic Finance Group, which was set up in December 2022. It issues circulars and acts as secretariat to SBP's Shariah Advisory Committee. It has issued circulars from 2024 to 2026.
- **Status:** Secondary (SBP snippet). The SBP department page and the IFPD circular index pages appeared in search results with matching titles and content, but were not opened directly (the workspace network blocks sbp.org.pk). Strong evidence, to be upgraded to primary once the page is read.
- **Sources:** [SBP: Islamic Finance Policy Department](https://www.sbp.org.pk/departments/ifpd.htm), [SBP: IFPD circulars 2026 index](https://archive.sbp.org.pk/ifpd/2026/2026.htm)
- **Checked:** 2026-11-06
- **Related:** BUG-036

### REG-002. CAR minimum 11.5%
- **Value in code:** `CAR_MINIMUM = Decimal("11.5")`
- **Original note:** says it matches SBP's Basel III requirement, corroborated by Dubai Islamic Bank Pakistan FY2023 disclosures.
- **Update 2026-11-06:** Research found the breakdown: CET1 6.0%, Tier 1 7.5%, total 10.0%, plus a capital conservation buffer of 1.5% (cut from 2.5% by BPRD CL 12 of 2020 and not restored as far as found), giving 11.5% in total. Framework: BPRD Circular No. 06 of 2013. Bank disclosures for December 2025 show the same figures.
- **Status:** Secondary (SBP snippet and bank disclosures). The primary pages still need to be read. See [07 section 1.1](07-guidelines-and-data.md).
- **Related:** BUG-032

### REG-003. NPF "maximum" 7%
- **Value in code:** `NPF_MAXIMUM = Decimal("7.0")`, described as "per SBP CAELS guidelines".
- **Status:** Unverified. No source yet shows this as a binding SBP limit. CAELS is a rating framework.
- **Related:** BUG-034

### REG-004. Depositor profit at least 75% of pool gross yield
- **Value in code:** `DEPOSITOR_SHARE_MIN = Decimal("75.0")`, cited as IBD Circular No. 03 of 2012 as amended.
- **Finding:**
  - The primary source is **IFPD Circular No. 09 of 2024** (26 November 2024), effective 1 January 2025.
  - Islamic banks must pay profit on PKR savings deposits at a rate of at least 75% of the weighted average gross yield of all their pools.
  - Excluded deposits: those of financial institutions, public sector enterprises and public limited companies.
  - Excluded pools: those for SBP's Shariah compliant standing ceiling facilities and open market operations.
  - Pool gross yield = monthly gross earnings divided by monthly average pool assets. The original text said "excluding fixed assets". IFPD Circular Letter No. 01 of 2025 (21 January 2025) deleted that phrase.
  - The rule replaced the earlier minimum profit rate requirement (50 basis points below the SBP policy rate).
  - Published analyst example: a 15.2% gross yield requires at least 11.4% to be paid.
- **Status:** Verified (secondary), with the primary circular located. The full circular text still needs to be read before FIX-028 is coded.
- **Sources:** [SBP: IFPD Circular No. 09 of 2024](https://www.sbp.org.pk/circulars/ifpd-circular-no-09-of-2024), [SBP archive: IFPD 2024 C9](https://www.sbp.org.pk/ifpd/2024/C9.htm), [Business Recorder](https://www.brecorder.com/news/40334633), [Dawn](https://www.dawn.com/news/1875065), [ProPakistani](https://propakistani.pk/2024/11/26/islamic-banks-to-pay-75-of-gross-yield-as-profit-on-savings-sbp/amp/), [regalert summary of IFPD CL 01 of 2025](https://regalert.today/document/69b82cf1-fbf0-4e51-9e65-fca470095909/text)
- **Checked:** 2026-11-06
- **Related:** BUG-027, BUG-028, BUG-036

### REG-005. PER cap 20% and IRR cap 10%
- **Value in code:** `PER_CAP_PERCENT = 20.0`, `IRR_CAP_PERCENT = 10.0`
- **Original note:** says these are indicative. SBP's framework caps the Mudarib's fee on PER and IRR funds and caps IRR contributions, but it does not set one ratio for all banks. Banks set their own policies.
- **Status:** Unverified as SBP limits (the original note agrees). They must not drive breach flags (FIX-030).
- **Related:** BUG-030

### REG-006. Days past due thresholds and provision rates
- **Value in code:** `DPD_THRESHOLDS` (OAEM 1, Substandard 91, Doubtful 181, Loss 366 days) and `PROVISION_RATES` (0, 0, 25%, 50%, 100%).
- **Update 2026-11-06:** For corporate and commercial financing, research found Substandard at 90 days (25%), Doubtful at 180 (50%) and Loss at 365 (100%), with OAEM at 60 days, not 1 day as in the code. IFRS 9 stage backstops sit on top of these (REG-011).
- **Status:** 90, 180 and 365 days and 25%: Secondary. OAEM 60 and 50%, 100%: Unverified. Other categories: Unverified. The code value OAEM = 1 day is likely wrong.
- **Related:** GAP-014

### REG-007. IBD Circular No. 03 of 2012 (pool management instructions)
- **Used in code:** as the reference for all pool ratios.
- **Status:** Claimed. It is widely cited as the base instructions for profit and loss distribution and pool management. The current amended version and its relationship to the IFPD circulars still need to be confirmed.

### REG-008. Other circular numbers the original note called fabricated
- "IFPD Circular 08/2024": **appears real.** It is the Revised Shariah Governance Framework (22 Nov 2024, effective 1 Jan 2025). Secondary (SBP snippet and news).
- "BSD-1 Circular 01/2025": **appears real.** It covers revisions to the Data File Structures (DFS) under RCOA through DAP4 (24 Jan 2025). Secondary (SBP listing and Business Recorder). So `DFS_VERSION` cited a real circular, but a circular number is not a file format version (BUG-037 updated).
- "IBD Circular 02/2019": still not checked.
- **Status:** The original note was wrong about four of its five "fabricated" references (REG-001, REG-004 and the two above). It cannot be relied on, and FIX-036 replaces it.

### REG-009. SBP circular monitor URLs
- `SBP_BPRD_URL = https://www.sbp.org.pk/bprd/` and `SBP_IFPD_URL = https://www.sbp.org.pk/ifpd/`
- **Status:** The IFPD path is consistent with real SBP pages (REG-001). The BPRD path is to be checked when the monitor is built (GAP-008).

---

## Entries added from the 2026-11-06 research

All of these are **Secondary**: taken from SBP page snippets in search results, news or bank disclosures. They become Verified (primary) only when the SBP page itself has been read. Full details and links are in [07-guidelines-and-data.md](07-guidelines-and-data.md).

| ID | Fact | Source | Status |
|---|---|---|---|
| REG-010 | Leverage ratio minimum 3% (Tier 1 / exposure) | BPRD C06/2013 | Secondary |
| REG-011 | IFRS 9 effective 1 Jan 2024. Stage backstops: corporate and consumer Stage 2 at 60 DPD and Stage 3 at 90; housing 90 and 180; agriculture 90 and 365. The Stage 3 provision is the higher of ECL and the Prudential Regulations amount | BPRD C03/2022, CL07/2023, CL20/2025 | Secondary (garbled snippet for the table) |
| REG-012 | Mudarib share at most 50% of distributable profit. No special Hiba since Jan 2015 | IBD C03/2012, IBD CL01/2013 | Secondary |
| REG-013 | Provision reversals go to the pool that bore the charge. The WAGY denominator includes fixed assets | IFPD CL01/2025 | Secondary (SBP snippet) |
| REG-014 | Charity income on Islamic products is not income | BPRD CL01/2025 | Secondary (SBP snippet) |
| REG-015 | Reporting: RCOA returns in DFS format through DAP4. Deadlines: daily and weekly 2 working days, monthly 5, quarterly 12. The RCOA code list is not public | BSD-1 C01/2025 | Secondary |
| REG-016 | Revised standardised credit risk weights (Basel III Phase II). PKR claims on GoP and SBP get 0% | BPRD C03/2025 | Secondary (SBP snippet). The annex is not read |
| REG-017 | Cloud: banks' material workloads stay with onshore providers unless SBP approves | BPRD C01/2023 | Secondary (SBP snippet) |
| REG-018 | Minimum paid up capital Rs 20 billion by 31 Dec 2030 | BPRD C02/2026 | Secondary (news) |
| REG-019 | IFRS 9 transitional CET1 add back over 5 years (90% falling to 10%) for new Stage 1 and 2 ECL | BPRD C03/2022 Annex B | Secondary |
| REG-020 | Revised Shariah Governance Framework effective 1 Jan 2025 | IFPD C08/2024 | Secondary (SBP snippet and news) |
| REG-021 | LCR and NSFR minimum 100% each | BPRD C08/2016 | Values Unverified |
| REG-022 | No general personal data protection act in force as of Nov 2026. Banking secrecy under the Banking Companies Ordinance 1962 s.33A applies | legal guides, news | Secondary |

### Priority primary checks

SBP's website blocks automated access (Cloudflare), so these are read from copies the owner downloads into `docs/sources/sbp/` (file name = circular id, for example `IFPD-C09-2024.pdf`).

1. IFPD C09/2024 and IFPD CL01/2025: the full WAGY method and exclusions (REG-004, REG-013)
2. BPRD C03/2022 Annexure C: the stage backstop table (REG-011)
3. BPRD C03/2025 annex: credit risk weights (REG-016)
4. The Prudential Regulations annexures: provision percentages per category (REG-006)

---

## Primary verification pass (2026-11-06, build day)

The SBP website blocks automated access to its HTML pages, but its PDF files under `/assets/documents/circulars/` could be downloaded directly. They are kept in [sources/sbp/](sources/sbp/), with their extracted text, and are the corpus for Daleel's retrieval. Two were scanned images in Urdu, so they were read visually; an unofficial English translation of IFPD C09/2024 is kept next to the original.

| ID | Fact | Read in | New status |
|---|---|---|---|
| REG-004 | 75% of WAGY on PKR savings (excluding FI, PSE, PLC deposits); yield = monthly gross income / monthly average pool assets; SCF and OMO pools excluded; clauses 4.2.3 deleted, 5.2.1 and 5.2.2 amended; effective 1 Jan 2025 | `IFPD-C09-2024-U.pdf` (official Urdu text, dated 26 Nov 2024) | **Verified (primary)** |
| REG-002 | CET1 6.0%, Tier 1 7.5%, total 10.0%; buffer 2.5% fully phased in by 2019 | `BPRD-C06-2013-Basel-III-Instructions.pdf`, para 2.2 and transition table | **Verified (primary)**. The cut of the buffer to 1.5% (BPRD CL 12 of 2020) remains Secondary |
| REG-010 | Tier 1 leverage ratio 3% | same, Introduction (iii) | **Verified (primary)** |
| REG-011 | Stage bands by portfolio (corporate, consumer, housing, SME, agriculture, infrastructure, microfinance); Stage 3 provision is the higher of ECL and the PR requirement | `BPRD-C03-2022-Annex-C.pdf` | **Verified (primary)** |
| REG-019 | Transitional add back of new Stage 1 and 2 provisions to CET1: 90, 70, 50, 30, 10% | `BPRD-C03-2022-Annex-B.pdf` | **Verified (primary)** |
| REG-012 | Mudarib share at most 50% of distributable profit (4.1.2); weightages announced at least 3 working days ahead and not changed (4.2.2); special Hiba phased out to 0% by 2015 (5.3) | `IBD-C03-2012-Annex-Pool-Management.pdf` | **Verified (primary)** |
| REG-023 (new) | PER: monthly contribution at most 2% of pool net income; accumulated PER at most 30% of equity or Islamic Banking Fund; 50% liability and 50% reserve; Mudarib share for managing PER at most 10% (5.1). IRR: contribution up to 1% of depositors' profit after Mudarib share until the bank has its own model; Mudarib share for managing IRR at most 10% (6.1 to 6.3) | same | **Verified (primary)** |
| REG-024 (new) | Stage 1 and 2 provisions count in Tier 2 up to 1.25% of credit RWA | `BPRD-C03-2022-IFRS9-Instructions.pdf`, para 3.21 | **Verified (primary)** |
| REG-025 (new) | Without its own LGD model, a bank may use the Foundation IRB LGDs of BSD Circular No. 08 of 2006 | same, para 3.16 | Reference **primary**; the 45% value itself is Secondary (BSD C08/2006 not read) |
| REG-026 (new) | Demo assumptions: default PDs, the NPF alert level, unmapped materiality, reconciliation tolerance, illustrative risk weights | Daleel rulebook | Assumption: shown, never a breach on its own |
| REG-020 | Shariah Governance Framework 2024 | `IFPD-C08-2024-Annex-SGF.pdf` | Document held (primary); not yet used for automated checks |
| (note) | BPRD CL 20 of 2025 updates Annexure C day counts for microfinance banks only | `BPRD-CL20-2025-U.pdf` (Urdu, read visually) | **Verified (primary)**; not relevant to the demo bank |

Still open: the full IFPD CL 01/2025 text (fixed assets now included in pool assets, Secondary), the Prudential Regulations annexures (25%, 50%, 100% provision rates), and the BPRD C03/2025 risk weight annex.
