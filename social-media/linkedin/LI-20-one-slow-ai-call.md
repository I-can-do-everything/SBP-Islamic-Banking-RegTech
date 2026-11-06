# LI-20. One slow AI call froze every other user

**Week 6, Wednesday** | Milestone: M10 | Image: none, or a simple two lane diagram

---

My own screenshot script found a bug that would have hit every visitor to the live demo.

Daleel processes uploads with a job queue stored in PostgreSQL. A worker picks up the next job: read the file, calculate, then ask an AI model to write the breakdown.

The AI step uses free models. Sometimes they take minutes.

And there was one worker. So while it waited for one visitor's AI write up, the next visitor's upload sat in the queue, untouched. One slow model call froze the whole demo.

The fix is two lanes:
⚡ One worker takes everything except the AI step. Reading and calculating stay fast.
🐢 One worker takes only the AI step. It can be as slow as it needs to be.

Both claim jobs with SELECT ... FOR UPDATE SKIP LOCKED, so two workers never take the same job.

While I was there, I found a second problem: if the free host restarts mid job, that job stayed "running" forever. Now a job running for more than 15 minutes is treated as abandoned and retried, or marked failed after its last attempt.

Two new tests cover both. The lesson: put slow, unreliable work in its own lane, and never trust that a worker will live long enough to finish.

#SoftwareEngineering #PostgreSQL #SystemDesign #BackendDevelopment #AI
