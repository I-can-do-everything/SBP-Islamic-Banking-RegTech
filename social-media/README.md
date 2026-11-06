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
| 2 | Mon | LI-05 | Synthetic data that behaves like a real bank | M1 | Drafted |
| 2 | Wed | LI-06 | The 332 rupees my own test data lost | M2 | Drafted |
| 2 | Fri | LI-07 | 240 million rows in 4 seconds | M2 | Drafted |
| 3 | Mon | LI-08 | Mapping a bank's ledger without silent guesses | M3 | Drafted |
| 3 | Wed | LI-09 | Regulation as data, with dates | M4 | Drafted |
| 3 | Fri | LI-10 | The 75% rule, worked through | M4 | Drafted |
| 3 | | Blog-02 | Part 2: from a messy export to numbers with evidence | M4 | Drafted |
| 4 | Mon | LI-11 | Four eyes, enforced by the database | M5 | Drafted |
| 4 | Wed | LI-12 | An audit log you cannot quietly edit | M6 | Drafted |
| 4 | Fri | LI-13 | Designing for the person who signs the return | M7 | Drafted |
| 4 | Sat | LI-14 | Click any number | M7 | Drafted |
| 5 | Mon | LI-15 | Giving the bank its data back, cleaner | M8 | Drafted |
| 5 | Wed | LI-16 | An AI that is not allowed to write numbers | M9 | Drafted |
| 5 | Thu | LI-18 | From git clone to a live demo with one wizard | M10 | Drafted |
| 5 | | Blog-03 | Part 3: an AI that is not allowed to write numbers | M9 | Drafted |
| 5 | Fri | LI-17 | Launch (publish after deployment) | M10 | Drafted |
| 6 | Mon | LI-19 | A compliance tool in signal red | M7 | Drafted |
| 6 | Wed | LI-20 | One slow AI call froze every other user | M10 | Drafted |
| 5 | | Blog-04 | Part 4: lessons from building RegTech end to end | M10 | Planned |

## Folders

- `linkedin/`: one file per post, `LI-##-short-name.md`
- `blog/`: one file per article
- `assets/`: images used by posts, with `assets/README.md` describing each
