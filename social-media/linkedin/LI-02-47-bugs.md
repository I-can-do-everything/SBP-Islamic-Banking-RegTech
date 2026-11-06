# LI-02. I audited my own prototype and found 47 bugs

**Week 1, Wednesday** | Milestone: Audit | Image: `assets/audit-by-numbers.png`

---

I audited the prototype of my RegTech project before writing a single new feature.

47 bugs. 10 of them critical.

The one that taught me the most was not a crash. It was a sign.

In accounting, assets sit on the debit side, while capital, deposits and income sit on the credit side. The file reader stored balances as debit minus credit, which made capital negative. The ratio code assumed capital was positive.

Result: a healthy capital adequacy ratio of 11.5% came out as minus 11.5%.

No error. No warning. Just a wrong number that looked like a number.

Three lessons I am taking into the rebuild:

1️⃣ Run the code, do not just read it.
Reading told me one function was broken. Running it showed it worked. Reading told me another line would stop the file loading. Running it showed it only failed on balances ending in "DR". Two of my own assumptions were wrong.

2️⃣ In regulatory software, silent errors are worse than crashes.
Unreadable cells became zero. Unmapped accounts quietly fell out of the ratios. A crash gets fixed the same day. A silent zero can end up in a filing.

3️⃣ Settle the accounting rules before writing code.
One sign convention, decided once, applied in one place. Every later layer depends on it.

Every bug is now in a register with the file, the line, the evidence and the planned fix, and each one will become a regression test.

#SoftwareEngineering #RegTech #Accounting #Testing #IslamicBanking
