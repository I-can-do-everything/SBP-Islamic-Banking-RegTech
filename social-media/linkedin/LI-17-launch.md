# LI-17. Daleel: try it

**Week 5, Friday** | Milestone: M10 | Publish only after the demo is deployed (docs/09-deployment.md) | Images: `assets/screens/01-landing.png`, `03-transformation.png`, `06-evidence-drawer.png`, `08-breakdown-ai.png`

---

Daleel is live. It is an Islamic bank regulatory compliance tool, built in public over the last few weeks.

Upload a bank's messy export, or pick a sample, and in seconds you see:
🔹 every sheet recognised and every cell cleaned, before and after
🔹 capital adequacy, IFRS 9 staging and provisioning, the 75% savings rule, pool limits and Shariah checks
🔹 every figure traced to its rows, rule and SBP circular
🔹 an AI breakdown that cannot invent a number, citing SBP text word for word
🔹 a tamper evident audit trail you can verify yourself

It runs entirely on free infrastructure: Supabase PostgreSQL with row level security, a Hugging Face Space, and OpenRouter free models. The code is on GitHub.

[demo link] · [GitHub link]

It is a portfolio project on synthetic data for a fictional bank, and not certified by SBP. But every rule is labelled with its source, and the hard parts are real: reconciliation, sign conventions, the day bands, the pool yield.

If you work in regulatory reporting, Islamic finance, data engineering or AI safety, I would love to know what you would test first.

#RegTech #IslamicBanking #FinTech #AI #Portfolio
