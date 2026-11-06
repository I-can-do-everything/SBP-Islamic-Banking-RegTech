# LI-09. Regulation as data, with dates

**Week 3, Wednesday** | Milestone: M4 | Image: `assets/screens/11-rulebook.png`

---

Regulations change. A compliance tool that hard codes them gives the right answer only until the next circular.

In Daleel every regulatory number lives in a rulebook, as data:

capital.ccb: the capital conservation buffer
🔹 2.5%, in force until March 2020 (BPRD Circular No. 06 of 2013)
🔹 1.5%, in force from 26 March 2020 (COVID relief letter)

A calculation for September 2026 uses 1.5%. Recalculate December 2019 and it uses 2.5%, automatically.

Each rule also carries where it comes from and how sure we are:
🔹 primary: I read it in the SBP document itself
🔹 secondary: news, bank disclosures or a quoted page
🔹 demo assumption: my own placeholder, which can never raise a breach on its own

Today, 17 of the 26 rules have a version verified against primary SBP PDFs. They include the IFRS 9 stage bands, the CET1 and Tier 1 minimums, the Tier 2 provision cap, and the Mudarib share, PER and IRR limits. The 75% savings rule I verified by reading the official Urdu text of the circular.

The rulebook is public in the demo, so anyone can see exactly which number came from where.

#RegTech #Compliance #StateBankOfPakistan #SoftwareDesign #IslamicFinance
