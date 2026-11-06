# LI-12. An audit log you cannot quietly edit

**Week 4, Wednesday** | Milestone: M6 | Image: `assets/screens/10-audit.png`

---

Most audit logs are just tables. Anyone with enough access can change a row, and nobody would know.

Daleel's audit log is a hash chain inside PostgreSQL:
🔹 Each event stores a SHA-256 fingerprint of itself plus the previous event's fingerprint
🔹 A database trigger computes it, so the application cannot get it wrong
🔹 Another trigger refuses every UPDATE and DELETE
🔹 Change any past event and every fingerprint after it stops matching

There is a "Verify the chain" button in the demo. It recomputes every hash in your workspace and tells you where the chain breaks, if it does.

The same database also enforces isolation. Every demo visitor gets their own workspace, and row level security in PostgreSQL only returns rows for that workspace. The policy is forced, so it applies even to the table owner. My tests try to read and write across workspaces, and the database refuses.

The point is that safety belongs in the layer that cannot be bypassed by a bug.

#PostgreSQL #Security #Audit #RegTech #SoftwareEngineering
