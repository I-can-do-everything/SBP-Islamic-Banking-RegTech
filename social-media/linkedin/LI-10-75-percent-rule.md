# LI-10. The 75% rule, worked through

**Week 3, Friday** | Milestone: M4 | Image: `assets/screens/06-evidence-drawer.png`

---

Since 1 January 2025, Islamic banks in Pakistan must pay profit on rupee savings deposits at a rate of at least 75% of the weighted average gross yield (WAGY) of their pools (IFPD Circular No. 09 of 2024).

Here is how Daleel checks it on the stressed demo bank:

1️⃣ Gross yield of each pool = monthly gross income / monthly average pool assets
2️⃣ Leave out the pools for the Shariah compliant standing ceiling facility and OMOs, as the circular says
3️⃣ Weight by assets, which is the same as total eligible income / total eligible assets, annualised: 12.73%
4️⃣ Minimum savings rate = 75% of that: 9.55%
5️⃣ Savings accounts of financial institutions, public sector enterprises and public limited companies are excluded
6️⃣ Rate actually paid per tier: S1 9.10%, S2 9.80%, S3 10.10%

Result: tier S1 is 0.45 percentage points short, across 10,994 eligible accounts. Breach.

Two details that are easy to get wrong:
🔹 Include the SCF and OMO pools and the WAGY falls, the threshold falls, and the breach disappears
🔹 The rule is about a profit rate against a yield, not a share of income. My original prototype tested the share.

Click the number in the demo and you see every step above, the rows behind it and the circular text.

#IslamicBanking #IslamicFinance #Compliance #RegTech #Pakistan
