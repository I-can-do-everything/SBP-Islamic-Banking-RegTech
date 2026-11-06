# LI-01. Announcement

**Week 1, Monday** | Milestone: Planning | Image: `assets/architecture-overview.png`

---

Every month, Islamic banks in Pakistan turn millions of ledger rows into a handful of numbers that the State Bank of Pakistan reads very closely.

Capital adequacy. Non performing financing. How profit is shared with depositors.

In many banks a big part of that journey still runs through spreadsheets: exported, reworked, checked by hand, and then defended in front of auditors.

So I am building a regulatory reporting engine for Islamic banks, in public, as a portfolio project.

What it will do:
🔹 Take the trial balance, the financing portfolio and the deposit pools straight from the core banking system export
🔹 Map the bank's own accounts to SBP's reporting codes
🔹 Calculate the ratios from a rulebook where every threshold is tied to the circular it came from
🔹 Let you click any number and see exactly which file, rows and rule produced it
🔹 Run four eyes approval before anything is final
🔹 Write an AI summary that is not allowed to invent a single number

The demo runs on a fictional bank with synthetic data, built to the same structures a real bank uses.

Over the next few weeks I will share what I learn: the system design, the accounting traps, the regulation, and the bugs.

First lesson next post: I audited the prototype I started with and found 47 bugs.

#RegTech #IslamicBanking #FinTech #SystemDesign #Pakistan
