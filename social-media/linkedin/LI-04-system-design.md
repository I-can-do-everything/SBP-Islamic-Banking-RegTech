# LI-04. System design for bank scale data

**Week 1, Saturday** | Milestone: Design | Image: `assets/architecture-overview.png`

---

A trial balance has a few thousand rows. So why design a regulatory system for hundreds of millions?

Because the trial balance is the easy part.

To check the profit rule for depositors, you need deposit balances for every account, often for every day. A large bank can have millions of accounts. Five million accounts times 30 days is 150 million rows, every month.

Here is the design I chose for my Islamic banking RegTech project, and why:

🧱 PostgreSQL for state
Users, submissions, approvals, results, the rulebook and the audit log. Row level security keeps each bank's data isolated, even if the application code has a bug.

📦 Parquet plus DuckDB for bulk data
Raw files land in object storage and never change. Workers turn them into compressed, columnar Parquet and crunch them with DuckDB. That gives exact decimal maths, every CPU core, no cluster, and the same code on a laptop or a bank server.

📬 A job queue inside PostgreSQL
Creating a submission and queuing its processing happen in one transaction. There is no extra system to run, and work never gets lost between two databases.

⬆️ Uploads straight to storage
Large files go from the browser directly to storage, hashed on both ends. If the hashes differ, the file is rejected. That is the chain of custody.

🧭 A modular monolith, not microservices
One codebase, two process types (API and workers), with strict module boundaries checked in CI. It is simple to run today, and any module can be split out later.

The goal is not to use fashionable tools. The goal is that every number survives an audit, and that the system stays fast when the data gets big.

#SystemDesign #DataEngineering #DuckDB #PostgreSQL #RegTech
