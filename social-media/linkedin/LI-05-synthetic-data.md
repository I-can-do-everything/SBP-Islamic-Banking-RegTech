# LI-05. Synthetic data that behaves like a real bank

**Week 2, Monday** | Milestone: M1 | Image: `assets/screens/02-demo.png`

---

You cannot demo a banking tool with real bank data. You also cannot demo it with toy data, because toy data never breaks anything.

So for Daleel, my Islamic banking compliance tool, I built a generator for a fictional bank, Example Islamic Bank Ltd, and made it misbehave on purpose.

It builds the bank from the bottom up:
🔹 3,000 financing contracts, with the mode mix calibrated to SBP's Islamic Banking Bulletin (Diminishing Musharakah 34%, Musharakah about 26%, Istisna 10%, Murabaha 9%)
🔹 30,000 deposit accounts, most with small balances, as in real Pakistani banking
🔹 four investment pools, including the standing ceiling facility and OMO pools that the 75% rule tells you to leave out
🔹 a general ledger built from that detail, so the trial balance reconciles to the rupee

Then it exports everything the way core banking systems actually do. There are title rows above the header, a page break that repeats the header, a TOTAL row, "1,250.00 DR", "(500)", a number in scientific notation, dd/mm/yyyy dates and "Diminishing Musharaka" spelled three ways.

The same seed always produces the same bank, so every test and every screenshot can be reproduced.

There are two versions. A healthy bank, and a stressed one with eight planted breaches that the system must catch.

It caught all eight. And one I had not planted. More on that tomorrow.

#SyntheticData #DataEngineering #IslamicBanking #RegTech #Testing
