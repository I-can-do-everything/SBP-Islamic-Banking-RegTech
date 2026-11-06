# Social Media

Drafts for LinkedIn posts and blog articles that document the build of this project in public. Every post is tied to a milestone in [docs/08-roadmap.md](../docs/08-roadmap.md).

## Rules for every post

1. **Synthetic data only.** Screenshots show the fictional "Example Islamic Bank Ltd (EXIB)" or diagrams. Never real bank names in a data context, never customer data, never keys, tokens, URLs of private services, emails or internal hostnames.
2. **Honest claims.** Say "portfolio project", "prototype" or "demo" where true. Never claim SBP approval or certification. Regulatory facts must match [docs/05-regulatory-verification.md](../docs/05-regulatory-verification.md).
3. **No em dashes or en dashes** (project writing rule).
4. **One idea per post.** A hook in the first two lines (LinkedIn cuts the rest behind "see more"), a concrete example or number, a lesson, and a light call to action.
5. **3 to 5 hashtags**, at the end.
6. Screenshots are made with Playwright at 2x scale from the demo (or rendered diagrams) and saved in `assets/`. Each asset has a note in `assets/README.md` saying what it shows and confirming it holds no sensitive information.

## Posting schedule

Target: 3 to 4 posts per week. The project is being built now, so the drafts can all be written now and published on this schedule. Suggested days: Monday, Wednesday, Friday (plus Saturday in four post weeks). Best time for a Pakistan and Gulf audience: about 9:00 to 10:00 PKT.

| Week | Day | ID | Topic | Milestone | Status |
|---|---|---|---|---|---|
| 1 | Mon | LI-01 | Announcement: what I am building and why | Planning | Drafted |
| 1 | Wed | LI-02 | I audited my own prototype and found 47 bugs | Audit | Drafted |
| 1 | Fri | LI-03 | Fact checking regulatory citations | Audit | Drafted |
| 1 | Sat | LI-04 | System design for bank scale data | Design | Drafted |
| 1 | | Blog-01 | Part 1: audit, verify, then design | Planning | Drafted |
| 2 | Mon | LI-05 | Synthetic data that behaves like a real bank | M1 | Planned |
| 2 | Wed | LI-06 | Exact money: why float is banned | M2 | Planned |
| 2 | Fri | LI-07 | 150 million rows on a laptop with DuckDB | M2 | Planned |
| 3 | Mon | LI-08 | Mapping a bank's ledger to SBP codes | M3 | Planned |
| 3 | Wed | LI-09 | Regulation as code: rules with effective dates | M4 | Planned |
| 3 | Fri | LI-10 | The 75% rule explained with a worked example | M4 | Planned |
| 3 | | Blog-02 | Part 2: the calculation engine and lineage | M4 | Planned |
| 4 | Mon | LI-11 | Four eyes approval in software | M5 | Planned |
| 4 | Wed | LI-12 | A tamper evident audit log in PostgreSQL | M6 | Planned |
| 4 | Fri | LI-13 | Designing for compliance officers | M7 | Planned |
| 4 | Sat | LI-14 | Click any number to see where it came from | M7 | Planned |
| 5 | Mon | LI-15 | Generating the report pack | M8 | Planned |
| 5 | Wed | LI-16 | AI that is not allowed to make up numbers | M9 | Planned |
| 5 | | Blog-03 | Part 3: safe AI in regulated software | M9 | Planned |
| 5 | Fri | LI-17 | Launch: try the demo | M10 | Planned |
| 5 | | Blog-04 | Part 4: lessons from building RegTech end to end | M10 | Planned |

## Folders

- `linkedin/`: one file per post, `LI-##-short-name.md`
- `blog/`: one file per article
- `assets/`: images used by posts, with `assets/README.md` describing each
