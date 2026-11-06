# Project Documentation

This folder is the written record of the SBP Islamic Banking RegTech system. It is kept up to date as the system is built, so that at the end it can be turned into a complete teaching folder (`docs/learn/`).

## Files

| # | File | What it contains |
|---|---|---|
| 1 | [01-prototype-snapshot.md](01-prototype-snapshot.md) | What the system is, who it is for, how it is designed, and exactly what exists today |
| 2 | [02-bug-register.md](02-bug-register.md) | Every known bug and missing piece, with location, severity, evidence and how it was found |
| 3 | [03-fix-log.md](03-fix-log.md) | The fix for each bug: what prompted it, the approach, and how it will be (or was) verified |
| 4 | [04-concepts-register.md](04-concepts-register.md) | Every topic, concept, tool and design idea the system uses, in plain language |
| 5 | [05-regulatory-verification.md](05-regulatory-verification.md) | Every regulatory number and reference, with its source and verification status |
| 6 | [06-system-design.md](06-system-design.md) | The production system design, with numbered decisions (`DEC-###`) |
| 7 | [07-guidelines-and-data.md](07-guidelines-and-data.md) | The official SBP rules the system implements, the synthetic data plan, and the AI model choices |
| 8 | [08-roadmap.md](08-roadmap.md) | Milestones, what each delivers and which bugs and gaps it closes |
| | [evidence/](evidence/) | Scripts and captured output that prove the bugs exist (and later, that the fixes work) |

## ID scheme

Every item has a permanent ID so the documents can point at each other.

| Prefix | Meaning | Lives in |
|---|---|---|
| `BUG-###` | A defect in code that exists | 02-bug-register.md |
| `GAP-###` | A piece of the system that is planned but not built (empty file) | 02-bug-register.md |
| `FIX-###` | The fix for the bug or gap with the same number (`FIX-012` fixes `BUG-012`, `FIX-G03` fixes `GAP-003`) | 03-fix-log.md |
| `CON-###` | A concept, topic or tool | 04-concepts-register.md |
| `REG-###` | A regulatory fact or reference | 05-regulatory-verification.md |
| `DEC-###` | A design decision, with alternatives and reasons | 06-system-design.md |
| `LI-##`, `Blog-##` | Social media drafts | [../social-media/](../social-media/) |

IDs are never renumbered or reused. When an item is closed it stays in its file with its final status, so the history is never lost.

## Severity scale used for bugs

| Severity | Meaning |
|---|---|
| Critical | The system cannot run, or it produces a wrong regulatory figure without warning anyone |
| High | A common input crashes or is processed wrongly, or there is a real security or compliance risk |
| Medium | Wrong in some cases, misleading output, or a weakness that will cause problems later |
| Low | Cosmetic, naming, documentation or tidiness problem |

## Status values

`Open` (found, not fixed), `Planned` (fix designed), `Fixed` (code changed), `Verified` (fix proven by running code), `Won't fix` (with a reason).
