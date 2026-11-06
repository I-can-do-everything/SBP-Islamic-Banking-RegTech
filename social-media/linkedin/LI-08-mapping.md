# LI-08. Mapping a bank's ledger without silent guesses

**Week 3, Monday** | Milestone: M3 | Image: `assets/screens/05-results.png`

---

Every bank numbers its general ledger differently. Regulators want one structure. Mapping one onto the other is where small mistakes hide.

My original prototype matched account codes by prefix. A rule for "3590-MUR" also matched "3590-MUR-NPF-001". In plain words, non performing Murabaha could quietly be counted as performing.

How Daleel maps now:
🔹 A rule must match the whole account code, never just the start
🔹 If one account fits two rules, that is reported, not silently decided by rule order
🔹 When one account is split across two reporting lines, the shares are exact decimals that must total 100%, and the rounding remainder goes to the largest share. A property test tries hundreds of random amounts to prove the split always adds back to the original.
🔹 One sign convention, applied in one place: debit positive in the ledger, shown positive on each line's normal side. An account on its wrong side is flagged, never flipped quietly.
🔹 An account with no mapping is listed with its balance, as a warning, or as a failure above a materiality level

The demo file contains a new product account nobody mapped yet. Daleel finds it, shows PKR 250 million unmapped, and keeps it out of the ratios until someone decides where it belongs.

#Accounting #RegTech #DataEngineering #IslamicFinance #Testing
