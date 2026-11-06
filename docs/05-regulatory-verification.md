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
- **Status:** Verified (primary)
- **Sources:** [SBP: Islamic Finance Policy Department](https://www.sbp.org.pk/departments/ifpd.htm), [SBP: IFPD circulars 2026 index](https://archive.sbp.org.pk/ifpd/2026/2026.htm)
- **Checked:** 2026-11-06
- **Related:** BUG-036

### REG-002. CAR minimum 11.5%
- **Value in code:** `CAR_MINIMUM = Decimal("11.5")`
- **Original note:** says it matches SBP's Basel III requirement, corroborated by Dubai Islamic Bank Pakistan FY2023 disclosures.
- **Status:** Claimed. To be re-verified, including the separate CET1 and Tier 1 minimums and whether 11.5% includes the capital conservation buffer.
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
- **Status:** Unverified. They differ by Prudential Regulations category (corporate, SME, agriculture, consumer, microfinance), and IFRS 9 now applies. They must be set per category from the current regulations.
- **Related:** GAP-014

### REG-007. IBD Circular No. 03 of 2012 (pool management instructions)
- **Used in code:** as the reference for all pool ratios.
- **Status:** Claimed. It is widely cited as the base instructions for profit and loss distribution and pool management. The current amended version and its relationship to the IFPD circulars still need to be confirmed.

### REG-008. Other circular numbers the original note called fabricated
- "IFPD Circular 08/2024": not checked yet.
- "IBD Circular 02/2019": not checked yet.
- "BSD-1 Circular 01/2025": not found yet, but still used in `DFS_VERSION` (BUG-037).
- **Status:** Unverified. Because REG-001 and REG-004 showed the original note was wrong twice, these will each be checked rather than assumed fake.

### REG-009. SBP circular monitor URLs
- `SBP_BPRD_URL = https://www.sbp.org.pk/bprd/` and `SBP_IFPD_URL = https://www.sbp.org.pk/ifpd/`
- **Status:** The IFPD path is consistent with real SBP pages (REG-001). The BPRD path is to be checked when the monitor is built (GAP-008).
