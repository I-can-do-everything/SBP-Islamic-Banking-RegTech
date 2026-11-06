"""Benchmark: the 75% rule input at scale, with DuckDB on Parquet.

Generates N accounts x D days of synthetic daily savings balances (exact DECIMAL),
writes them to Parquet, then computes what the 75% rule needs: each account's
average balance for the month, then totals per tier. Prints timings.

Usage: uv run python benchmarks/daily_balances.py [accounts] [days]
"""

from __future__ import annotations

import os
import sys
import tempfile
import time

import duckdb

accounts = int(sys.argv[1]) if len(sys.argv) > 1 else 2_000_000
days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
rows = accounts * days
con = duckdb.connect()
print(f"DuckDB {duckdb.__version__}, {os.cpu_count()} CPUs, {accounts:,} accounts x {days} days = {rows:,} rows")
with tempfile.TemporaryDirectory() as tmp:
    path = f"{tmp}/daily.parquet"
    t = time.perf_counter()
    con.execute(f"""
        COPY (
          SELECT a AS account_id, d AS day,
                 CASE WHEN a % 100 < 85 THEN 'S1' WHEN a % 100 < 97 THEN 'S2' ELSE 'S3' END AS tier,
                 CAST((hash(a) % 5000000) / 100.0 + d AS DECIMAL(38,4)) AS balance
          FROM range({accounts}) r(a), range({days}) s(d)
        ) TO '{path}' (FORMAT parquet, COMPRESSION zstd)""")
    write = time.perf_counter() - t
    size_mb = os.path.getsize(path) / 1e6
    t = time.perf_counter()
    result = con.execute(f"""
        WITH per_account AS (
          SELECT account_id, any_value(tier) AS tier, avg(balance) AS average_balance
          FROM read_parquet('{path}') GROUP BY account_id)
        SELECT tier, count(*) AS accounts, sum(average_balance) AS total
        FROM per_account GROUP BY tier ORDER BY tier""").fetchall()
    query = time.perf_counter() - t
print(f"write Parquet: {write:.1f} s ({size_mb:,.0f} MB)")
print(f"average per account, then per tier: {query:.1f} s ({rows / query / 1e6:.1f} million rows per second)")
for tier, n, total in result:
    print(f"  {tier}: {n:,} accounts, total average balance {total:,.2f}")
