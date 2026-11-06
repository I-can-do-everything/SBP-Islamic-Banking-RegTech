# LI-15. Giving the bank its data back, cleaner

**Week 5, Monday** | Milestone: M8 | Image: `assets/screens/04-transformation-financing.png`

---

Most tools take messy data in and give only results back. Daleel also gives the data back, in the shape it should have been in.

After every upload you can download the "ideal ingestion document", the Daleel Standard Template:
🔹 one sheet per dataset, with standard column names and types
🔹 plain numbers (no separators, no DR or CR), ISO dates, rates as fractions
🔹 a dictionary sheet explaining every field
🔹 a fixes sheet listing every change Daleel made, with counts and raw examples
🔹 a rejected sheet with every row it would not guess at, and why
🔹 the fingerprint of the original file

The point is not to make the bank depend on Daleel to clean its exports. It is to show the bank exactly what clean looks like, so next month's extract can arrive that way.

The financing sheet in the demo, for example, goes from "Diminishing Musharaka", "DM" and "DIMINISHING MUSHARAKAH" to one value. It goes from "1.2500%" and "0.0125" to one format, and from 17/09/2036 to 2036-09-17.

#DataQuality #DataEngineering #Banking #RegTech #Automation
