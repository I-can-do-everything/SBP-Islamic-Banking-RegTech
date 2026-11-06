# LI-06. The 332 rupees my own test data lost

**Week 2, Wednesday** | Milestone: M2 | Image: `assets/screens/03-transformation.png`

---

My synthetic bank's trial balance did not balance. It was out by PKR 332.12.

I had built the ledger myself, in exact decimal arithmetic, balanced by construction. So where did 332 rupees go?

Into scientific notation.

To make the export realistic, I had written one large balance, the GoP Ijarah Sukuk holding, the way Excel sometimes shows big numbers: in scientific notation, with seven significant digits. For a balance in the tens of billions, the rest of the number was simply gone.

Daleel's first check on any upload is "do total debits equal total credits?". It failed loudly, before a single ratio was calculated.

That is exactly why the check exists. In real reporting this happens when someone opens a CSV in Excel, saves it, and sends it on. The file looks fine and the totals are wrong.

What I took from it:
🔹 Every money value stays as exact text until it is parsed into a decimal. Never a float.
🔹 Integrity checks run before calculations, not after.
🔹 A check that catches your own mistakes is worth more than one that only catches other people's.

The ingestion screen now shows every fix it makes, cell by cell. In the demo file that is 86,707 cells cleaned, plus one row it refused to guess at.

#DataQuality #Accounting #SoftwareEngineering #RegTech #Excel
