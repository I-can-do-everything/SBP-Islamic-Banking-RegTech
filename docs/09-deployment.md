# 09. Deployment (free tier)

**Requirement from the owner:** use free tools only, choosing the best ones.
**Decision:** DEC-017 (below). Everything runs as one container plus one managed PostgreSQL database.

## DEC-017. Free hosting stack

| Need | Choice | Free tier (as researched, check before relying on it) | Why this one |
|---|---|---|---|
| Database | **Supabase** (PostgreSQL) | 500 MB database, pauses after a week without activity | Real PostgreSQL with row level security, which Daleel depends on (DEC-012); also offers storage and auth if needed later |
| App (API, worker, web) | **Hugging Face Spaces**, Docker SDK | CPU basic: 2 vCPU, 16 GB RAM; sleeps after 48 hours idle; disk is not persistent | The most memory of any free container host, which suits DuckDB; one public URL for the whole demo |
| AI | **OpenRouter** free models | Rate limited (about 20 requests a minute, 50 to 1,000 a day) | One OpenAI compatible API across many models, with fallback |
| CI | GitHub Actions | Free for public repositories | Tests on every push |

Alternatives considered:
- Neon (PostgreSQL, also free, also has RLS): a good alternative to Supabase.
- Render and Koyeb (512 MB RAM): too little memory for DuckDB.
- Fly.io and Cloud Run: need a card or billing account.
- Cloudflare Pages for the web app: free and fast, but serving the app from the same container keeps one URL and avoids cross origin settings. The web build is static, so it can move to Pages at any time.

Consequences of the free tier, and why they are acceptable for a demo:
- **Uploads are lost when the Space restarts**, because the disk is not persistent. Demo workspaces expire after 12 hours anyway, and the samples are regenerated at start up.
- **The first visit after idle is slow** while the Space and the database wake up.
- **Free AI models can be slow or rate limited.** Daleel shows its deterministic summary at once and swaps in the AI version when it arrives.

## Steps

### 1. Database (Supabase)

1. Create a project at supabase.com and pick a region close to your users.
2. In the SQL editor, create the app role. It cannot bypass row level security:
   ```sql
   CREATE ROLE daleel_app LOGIN PASSWORD 'choose-a-long-random-password' NOSUPERUSER NOBYPASSRLS NOCREATEROLE;
   GRANT CREATE, USAGE ON SCHEMA public TO daleel_app;
   ```
3. Copy the Session pooler connection string, and replace the user and password with `daleel_app` and its password. Daleel creates its tables on first start (migrations), owned by `daleel_app`, so forced row level security applies to them.

### 2. App (Hugging Face Space)

1. Create a Space with the **Docker** SDK, then push this repository to it (or connect it to GitHub).
2. In Settings, add these as **Secrets**:
   - `DATABASE_URL`: the Supabase string from step 1
   - `JWT_SECRET`: a long random value (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
   - `OPENROUTER_API_KEY`: from openrouter.ai/keys
3. Add this as a **Variable**:
   - `CORS_ORIGINS`: the Space URL, for example `https://<user>-daleel.hf.space`
4. The Dockerfile listens on port 7860, the Spaces default. On start the app:
   - applies migrations
   - indexes the SBP sources
   - generates the two sample workbooks
   - starts the embedded worker
5. In production mode the app refuses to start with a weak `JWT_SECRET`.

### 3. Check

- `GET /health` returns `{"status": "ok", ...}`.
- Open the Space URL, run the stressed sample, and check:
  - the Transformation tab
  - the Results tab
  - the AI breakdown (it may take a few minutes on free models)
  - Audit trail, then Verify the chain

## Production reference (a real bank)

This is not part of the free demo. It is how the same code would run inside a bank, in line with SBP's cloud outsourcing framework (REG-017):
- on premises, or with an onshore provider approved by SBP
- PostgreSQL with a streaming replica
- S3 compatible object storage with object lock for raw files
- `AI_PROVIDER=ollama` with a local model, so no data leaves the bank
- single sign on through the bank's identity provider
- separate worker processes (`daleel worker`)
