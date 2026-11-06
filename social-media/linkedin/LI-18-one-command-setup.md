# LI-18. From git clone to a live demo with one wizard

**Week 5, Thursday** | Milestone: M10 | Image: a terminal screenshot of `npm run setup` (keys hidden)

---

The worst part of trying someone's portfolio project is usually the setup page: a list of twelve environment variables and a "good luck".

So Daleel has a wizard:

npm run setup

It walks you through:
1️⃣ Where it runs: your computer, the free cloud, or both
2️⃣ The AI key. It tells you where to click on OpenRouter, hides the key as you paste it, and checks it. A wrong key is rejected on the spot.
3️⃣ The database. It prints the exact SQL to run in Supabase, with a password it generated for you. Then it rewrites the connection string to use an app role that cannot bypass row level security.
4️⃣ Security. It generates the signing secret, so you never invent one.
5️⃣ Features. Visitor uploads on or off, the size limit, and whether a demo visitor can switch people to try four eyes approval.
6️⃣ Hosting. Give it a Hugging Face token and it creates the Space and adds every secret and variable itself. Without one, it prints a list ready to paste.

Then npm run deploy packages the last commit and publishes it.

Everything stays on your machine, in files that git ignores and only you can read. The token is never printed, not even in error messages.

All of it is free: Supabase, Hugging Face Spaces and OpenRouter's free models.

#DeveloperExperience #DevOps #OpenSource #RegTech #Automation
