# LI-03. Fact checking regulatory citations

**Week 1, Friday** | Milestone: Audit | Image: none (text post)

---

My prototype had a note that said a regulator's department "does not appear to be real".

It is real.

The code for my Islamic banking RegTech project included a careful looking verification note. It listed which regulatory references were confirmed and which looked invented. It flagged five references as likely invented, including SBP's Islamic Finance Policy Department itself.

When I checked, four of the five appear to be real. One of them (IFPD Circular No. 09 of 2024) is the very rule the code was trying to implement:

➡️ Since January 2025, Islamic banks must pay profit on rupee savings deposits at a rate of at least 75% of the weighted average gross yield of their pools.

Worse, because the source was set aside, the code tested the wrong thing. It checked a share of income, while the rule compares a profit rate with a pool yield.

What I changed:

🔹 Every regulatory number now lives in one log with its source, the date it was checked, and a status: verified, claimed or unverified
🔹 Unverified values can still be shown, but never trigger a breach on their own
🔹 Code comments point to the log instead of repeating their own version of the truth

The lesson is not "verify your sources". Everyone says that.

The lesson is that verification notes need verification too. A confident "this is fake" can cost you as much as a confident "this is true".

Not legal or compliance advice. This is a portfolio project, and every rule still needs sign off from a qualified compliance function before real use.

#Compliance #RegTech #IslamicFinance #StateBankOfPakistan #DataQuality
