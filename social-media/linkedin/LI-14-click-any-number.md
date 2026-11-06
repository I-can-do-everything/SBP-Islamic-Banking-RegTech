# LI-14. Click any number

**Week 4, Saturday** | Milestone: M7 | Image: `assets/screens/06-evidence-drawer.png`

---

"Where did this number come from?" is the most expensive question in regulatory reporting. Answering it often means hours in spreadsheets.

In Daleel it is one click. Every metric stores its lineage when it is calculated:

🔹 the formula, written in plain words
🔹 every input value, which are themselves metrics with their own lineage
🔹 each rule used, with the version in force on the reporting date, the SBP document, the paragraph, and whether it was verified from the primary source
🔹 the evidence table: the tiers, pools, stages or exposure classes behind the figure
🔹 the fingerprint of the file the data came from

Under the hood, each metric is a small function that declares what it depends on. The engine sorts them so everything runs in the right order, and records the trail as it goes.

The result: an auditor and a junior analyst can both see why the CAR is 11.19%, without asking anyone.

#DataLineage #RegTech #Audit #SoftwareArchitecture #Transparency
