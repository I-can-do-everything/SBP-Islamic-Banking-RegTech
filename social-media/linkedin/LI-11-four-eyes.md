# LI-11. Validation before anyone signs

**Week 4, Monday** | Milestone: M5 | Image: `assets/screens/05-results.png`

---

A ratio can be calculated perfectly from data that is wrong. So Daleel checks the data before it trusts the ratios.

On the stressed demo bank it ran eleven checks alongside thirty metrics:

🔹 Does the trial balance balance? Yes.
🔹 Does the financing portfolio agree to the ledger, mode by mode? Yes.
🔹 Do deposit accounts agree to the ledger? No. They are out by PKR 3,386.67, and Daleel points to the one row it rejected because a cell said #REF!.
🔹 Is any charity booked as income? Yes, PKR 12 million. SBP's IFRS 9 instructions say it must not be.
🔹 Does any Qard (current) account show profit? No, as Shariah requires.
🔹 Is every Mudarabah deposit assigned to a pool? Yes.

Each check shows its status as an icon and a word, never by colour alone, because the people reading these screens should not have to guess.

Next step on the roadmap: four eyes approval, where the person who prepares a submission can never be the one who approves it, enforced by the database and not just the screen.

#Compliance #Accounting #DataQuality #RegTech #IslamicFinance
