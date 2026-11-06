# 09. Deployment (free tier)

**Requirement from the owner:** free tools only, the best ones, and a setup as easy as `npm run setup`.
**Decisions:** DEC-017 (hosting stack) and DEC-024 (setup wizard), below.

## The short version

```bash
npm run setup
```

Follow the wizard. It explains each account to create, takes your keys (hidden while you type), checks them, asks which features to turn on, and writes your settings. Then:

```bash
npm run deploy
```

That publishes the app to your Hugging Face Space. When it has built (5 to 10 minutes):

```bash
npm run setup:check
```

You need Node 18 or newer and git. Nothing else needs installing for the wizard.

## What the wizard does, step by step

| Step | What you do | What the wizard does |
|---|---|---|
| Where will it run? | Choose: your computer, the free cloud demo, or both | Skips the questions you do not need |
| 1. AI | Create a free OpenRouter account and an API key, then paste it | Checks the key against OpenRouter (rejects a wrong key and asks again) and sets the free model list. Ollama or no AI are also options |
| 2. Database | Local: keep the default. Cloud: create a Supabase project, run the SQL the wizard prints (it creates the `daleel_app` role with a password generated for you), then paste the Session pooler address | Rewrites the address to use the `daleel_app` role (which cannot bypass row level security) with `sslmode=require`. Can test the connection |
| 3. Security | Nothing | Generates a long random `JWT_SECRET` |
| 4. Features | Answer yes or no | Visitor uploads on or off, upload size, demo person switching (four eyes), session length |
| 5. Hugging Face | Create a free account and a Write token, or create the Space yourself | With a token, it creates the Space and adds every secret and variable for you. Without one, it prints them ready to paste |
| 6. Save | Nothing | Writes `backend/.env` (local) and `.env.deploy` (cloud). Both are ignored by git and readable only by you |

Run it again at any time; your previous answers are the defaults.

## The settings it writes

| Setting | Where | Meaning |
|---|---|---|
| `DATABASE_URL` | secret | PostgreSQL address, as the `daleel_app` role |
| `JWT_SECRET` | secret | Signs demo session tokens. Long and random; the app refuses to start in production with a weak one |
| `OPENROUTER_API_KEY` | secret | AI key (when the AI is OpenRouter) |
| `ENVIRONMENT` | variable | `production` in the cloud |
| `AI_PROVIDER`, `AI_MODELS` | variable | `openrouter`, `ollama` or `off`; models are tried in order, three per request |
| `ALLOW_UPLOADS`, `MAX_UPLOAD_MB` | variable | Whether visitors may upload their own files, and the size limit |
| `DEMO_PERSONAS` | variable | Lets one visitor switch between preparer and approver to try four eyes approval. Turn off when real people sign in separately |
| `SESSION_HOURS` | variable | How long a demo session lasts |
| `CORS_ORIGINS`, `PUBLIC_URL` | variable | The Space's own address |
| `HF_SPACE`, `HF_TOKEN` | `.env.deploy` only | Used by `npm run deploy`; never sent to the Space |

## DEC-017. Free hosting stack

| Need | Choice | Free tier (check before relying on it) | Why |
|---|---|---|---|
| Database | **Supabase** PostgreSQL | 500 MB; pauses after a week without activity | Real PostgreSQL with row level security, which Daleel depends on. Its Session pooler works over IPv4, which Hugging Face needs |
| App (API, worker, web) | **Hugging Face Spaces**, Docker | 2 vCPU, 16 GB RAM; sleeps after 48 hours idle; disk is not persistent | The most memory of any free container host, which suits DuckDB; one public URL |
| AI | **OpenRouter** free models | Rate limited (about 20 requests a minute) | One API for many models, with fallback |
| CI | GitHub Actions | Free for public repositories | Tests on every push with a real PostgreSQL |

Alternatives considered:
- Neon would also work as the database.
- Render and Koyeb give 512 MB of memory, which is too little.
- Fly.io and Cloud Run need a card.

Consequences of the free tiers:
- Uploads are lost when the Space restarts. Demo workspaces expire after 12 hours anyway.
- The first visit after a quiet period is slow while things wake up.
- Free AI models can take minutes. Daleel shows its deterministic summary at once.

## DEC-024. A setup wizard instead of a deployment manual

- **Choice:**
  - `npm run setup`: an interactive Node script with no dependencies that guides account creation, checks keys and writes the settings files.
  - `npm run deploy`: packages the last commit and pushes it to the Space.
  - `npm run setup:check`: checks everything once it is running.
- **Why:** The owner asked for the same experience as a previous project, where following the terminal was enough. A wizard removes the error prone parts:
  - typing connection strings by hand
  - inventing passwords
  - forgetting a variable
  - pasting a key with a stray space
- **Safety:**
  - Keys are hidden while typed.
  - Files are written with owner only permissions and are ignored by git.
  - The Hugging Face token is saved only if you agree.
  - The deploy script never prints the token, even in errors.
- **What deploy sends:**
  - only committed files
  - without PDFs, images and the social media folder (Hugging Face rejects plain binary files, and the app reads the extracted text)
  - with the short README header that tells Hugging Face to build the Dockerfile on port 7860
- **Preview:** `npm run deploy:dry-run` shows what would be sent, without sending it.

**Testing note (2026-11-06):** the wizard was run end to end with scripted answers, including a wrong OpenRouter key (rejected, then asked again) and the real key (accepted). The deploy dry run packed 109 files (1.5 MB). The live Hugging Face API calls (create Space, add secrets) and the Docker build could not be run from the build machine. They follow Hugging Face's documented API, and if anything fails the wizard falls back to printing the list to paste.

## Production reference (a real bank)

This is not part of the free demo. It is how the same code would run inside a bank, in line with SBP's cloud outsourcing framework (REG-017):
- on premises, or with an onshore provider approved by SBP
- PostgreSQL with a streaming replica
- S3 compatible storage with object lock for raw files
- `AI_PROVIDER=ollama`, so no data leaves the bank
- single sign on, with `DEMO_PERSONAS=false`
- separate worker processes (`daleel worker`)
