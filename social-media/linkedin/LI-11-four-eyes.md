# LI-11. Four eyes, enforced by the database

**Week 4, Monday** | Milestone: M5 | Images: `assets/screens/14-review-approver.png`, `assets/screens/15-review-approved.png`

---

"Nobody approves their own work" is one of the oldest controls in banking. In most software it is one if statement away from being bypassed.

In Daleel, the four eyes rule lives in PostgreSQL itself. Before the database accepts a decision, a trigger checks:

🔹 Only a preparer can submit, and only after writing an explanation for every breach. The stressed demo bank has 8, and the database counts them.
🔹 Only an approver can decide, and never someone who uploaded or submitted that submission.
🔹 Returning it to the preparer needs a written reason.
🔹 The approval stores a SHA-256 fingerprint of the exact results. If anything changed after submission, the approval is refused.
🔹 Once approved, the results are locked. The database refuses any change to the figures, the data behind them, or the upload.
🔹 Every submission, decision and explanation is append only, and lands in the hash chained audit log.

The screen explains in advance why a button is disabled ("Four eyes rule: you prepared or submitted this, so someone else must decide"). But the screen is a courtesy. The database is the control.

In the demo, one visitor can switch between the Reporting Officer and the Head of Compliance to try it. In a real bank each person signs in separately and that switch is off.

#InternalControls #Compliance #PostgreSQL #RegTech #Audit
