# LI-16. An AI that is not allowed to write numbers

**Week 5, Wednesday** | Milestone: M9 | Image: `assets/screens/08-breakdown-ai.png`

---

I wanted an AI summary in Daleel. I did not want an AI that could tell a compliance officer the wrong capital ratio.

So the model never sees a number.

It receives facts like "F21: Capital adequacy ratio, status WARNING", and writes "The capital adequacy ratio is {F21}." The app replaces {F21} with a phrase from the calculation engine: "11.19%, above the 10.00% minimum but 0.31 percentage points short of the 11.50% level that includes the capital conservation buffer".

Then every reply is checked before anyone sees it:
🔹 any digit outside a placeholder: rejected
🔹 a placeholder the point does not cite: rejected
🔹 an SBP excerpt that is not related to the cited facts: rejected
🔹 "meets the requirement" describing a breach: rejected
🔹 a breach left out: added back and labelled "added by Daleel"

One check came from a real failure. A free model renamed the IRR (investment risk reserve) as "return of equity contribution". No wrong numbers, but wrong words. Now each point must name its facts in their own words, or it is rejected.

If the model fails twice, a deterministic summary is shown instead, and the screen says so.

All of this runs on free models through OpenRouter. In a real bank it would switch to a local model, because customer data should stay inside the bank.

#AI #LLM #Hallucination #RegTech #ResponsibleAI
