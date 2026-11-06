# LI-07. 240 million rows in 4 seconds, no cluster

**Week 2, Friday** | Milestone: M2 | Image: none (text post), or a terminal screenshot of the benchmark

---

For the 75% savings profit rule, a bank needs the average balance of every savings account for the month. For a large bank that can mean 8 million accounts, a balance a day, 30 days: 240 million rows.

I measured what Daleel's design does with that, on a small 4 CPU cloud machine:

🔹 Writing 240 million daily balances to Parquet (compressed, columnar): 41 seconds, 1.1 GB
🔹 Averaging every account, then totalling by profit tier: 3.9 seconds
🔹 That is about 61 million rows per second, in exact decimal arithmetic, not floating point

No Spark. No cluster. No data warehouse. Just DuckDB, an embedded analytical engine, reading Parquet files.

Why this matters for regulatory software:
🔹 The same code runs on a laptop, a bank's own server or a free cloud container. That suits SBP's expectation that material bank workloads stay onshore.
🔹 PostgreSQL keeps what people read and write (results, approvals, the audit log). The heavy columns stay in files.
🔹 There is no cluster to secure, patch or pay for.

The benchmark script is in the repository (backend/benchmarks/daily_balances.py), so anyone can rerun it.

#DuckDB #DataEngineering #Performance #Parquet #RegTech
