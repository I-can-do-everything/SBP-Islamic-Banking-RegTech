# 08. Roadmap

**Status:** Draft for owner review, 2026-11-06
**Builds:** the design in [06-system-design.md](06-system-design.md)
**Closes:** the bugs and gaps in [02-bug-register.md](02-bug-register.md), through the fixes in [03-fix-log.md](03-fix-log.md)

The project is built in milestones. Each milestone ends with something that works, is tested and is documented. Each one also produces at least one social media post (see [social-media/](../social-media/)).

| Milestone | Goal | Delivers | Closes | Posts |
|---|---|---|---|---|
| M0. Foundations | A clean, safe, reproducible base | Monorepo layout (DEC-016), uv and pnpm workspaces, locked dependencies, full `.gitignore`, pre-commit (ruff, pyright, eslint), GitHub Actions CI skeleton, docker compose with PostgreSQL and MinIO, settings that refuse weak secrets in production | BUG-040, BUG-047, BUG-038, BUG-001 (the new code replaces the broken imports), GAP-011 (partly), GAP-012 (skeleton) | LI-01 to LI-04, Blog-01 |
| M1. Data | Realistic synthetic data at two scales | `datagen` package: seeded, deterministic generator for EXIB (demo) and a large bank scale test, calibrated to public figures (see 07). Canonical dataset schemas. T24, Flexcube and generic export layouts, including dirty data on purpose (bad cells, DR/CR suffixes, dd/mm/yyyy dates, BOM, unmapped accounts) | Gives the test data for FIX-002 to FIX-016 | LI-05 |
| M2. Ingestion engine | Files in, trusted Parquet out | Presigned uploads, verify, profile, parse, clean, integrity steps on DuckDB. Rejects with reasons. Trial balance and reconciliation checks. Benchmarks at both scales | BUG-002 to BUG-016, DEC-002, DEC-004, DEC-007, DEC-008 | LI-06, LI-07 |
| M3. Mapping | Bank GL to SBP reporting codes | Versioned mapping sets, anchored matching with an overlap check, exact apportionment, unmapped report, demo mapping for EXIB | BUG-017 to BUG-023, GAP-004, GAP-013 (mapping part) | LI-08 |
| M4. Rulebook and metrics | Correct regulatory numbers | Rulebook with effective dates and sources. Metric graph engine with lineage. Metrics: classification and provisioning, NPF, ECL stages, CAR (structured), pools (WAGY and the 75% rule, PER, IRR, distribution) | BUG-024 to BUG-037, GAP-014, DEC-005, DEC-006, DEC-009 | LI-09, LI-10, Blog-02 |
| M5. Validation and workflow | Checks and four eyes approval | Validation engine and rule set, submission state machine, maker checker | GAP-005, GAP-003 | LI-11 |
| M6. Platform | API, security, audit, database | PostgreSQL schema and migrations with row level security and partitions, auth (Argon2id, rotating tokens, MFA), hash chained audit log, REST API with OpenAPI and SSE | BUG-039, BUG-041 to BUG-046, GAP-001, GAP-002, GAP-009 | LI-12 |
| M7. Web app | The product UI | Design tokens, React app with all key screens, lineage panel, generated API client, accessibility checks | GAP-010 | LI-13, LI-14 (with screenshots) |
| M8. Reports | Report pack | Typst PDF, Excel workbook, SBP return export (marked uncertified until the file spec is confirmed) | GAP-006 | LI-15 |
| M9. AI | Useful, safe AI | AI gateway (OpenRouter and Ollama), commentary with grounding check, mapping suggestions, circular watcher, analyst Q and A, evaluations | GAP-007, GAP-008 | LI-16, Blog-03 |
| M10. Launch | Public demo | Cloud deployment, observability, load test results, public site and case study, demo walkthrough video script | GAP-011 (rest) | LI-17, Blog-04 |
| M11. Learn | Teaching folder | `docs/learn/` built from the registers, as CLAUDE.md requires | | |

## How each milestone is run

1. Write or update the design notes for the milestone in the docs.
2. Write tests first for the bugs being closed (each bug becomes a regression test).
3. Build.
4. Run all checks. Record evidence in the fix log.
5. Update the concepts register and the regulatory log.
6. Draft the social posts for the milestone, with screenshots of synthetic data only.
7. Commit, push, and check in with the owner.

## Network access

- Done 2026-11-06: a personal environment "SBP-Islamic-Banking-RegTech" allows `www.sbp.org.pk`, `archive.sbp.org.pk` and `openrouter.ai`. OpenRouter is reachable.
- SBP's site blocks automated clients with Cloudflare. Primary circulars come from owner downloads in `docs/sources/sbp/`.
- Before M9, an OpenRouter API key is added as an environment secret (never in code or chat).
