#!/usr/bin/env node
// Daleel setup wizard:  npm run setup
//
// Walks you through every account and setting, checks keys as you paste them,
// and writes:
//   backend/.env   settings for running Daleel on your own computer
//   .env.deploy    settings for the free cloud deployment (Hugging Face Space),
//                  plus your Hugging Face token if you want `npm run deploy`
// Both files are ignored by git and readable only by you.
//
// Run it again at any time: your previous answers become the defaults.
// `npm run setup:check` checks the saved settings without changing anything.

import crypto from "node:crypto";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import {
  BACKEND_ENV, DEPLOY_ENV, ROOT, ask, bullet, c, choose, closePrompts, confirm, fail, link, mask, ok, pause,
  readEnv, say, step, title, warn, writeEnv,
} from "./lib.mjs";

const FREE_MODELS = "nvidia/nemotron-3.5-super-vl:free,dots-studio/dots-3-note-preview:free,google/gemma-4-31b-it:free,openrouter/free";
const HF_API = "https://huggingface.co/api";

if (Number(process.versions.node.split(".")[0]) < 18) {
  console.error("Daleel setup needs Node 18 or newer (it uses the built in fetch).");
  process.exit(1);
}

const previousLocal = readEnv(BACKEND_ENV);
const previousCloud = readEnv(DEPLOY_ENV);
const previous = { ...previousLocal, ...previousCloud };

if (process.argv.includes("--check")) {
  await check();
  process.exit(0);
}

await main().finally(closePrompts);

// ---------------------------------------------------------------------------------------------

async function main() {
  title("Daleel setup");
  say(
    "This wizard prepares everything Daleel needs. It takes about 10 minutes.",
    "You will create up to three free accounts, paste a few keys, and choose some settings.",
    "",
    `${c.bold("Nothing leaves your computer")} except checks against the services you choose`,
    "(OpenRouter to test your AI key, Hugging Face if you let the wizard set up your Space).",
    "Keys you paste are hidden while you type, and saved only in files that git ignores.",
  );
  if (Object.keys(previous).length) say("", c.dim("Found earlier settings: they are shown as defaults. Press Enter to keep them."));

  const target = await choose("Where will Daleel run?", [
    { label: "On my computer only", hint: "for development and trying it out", value: "local" },
    { label: "Free cloud demo only", hint: "Supabase database + Hugging Face Space", value: "cloud" },
    { label: "Both", hint: "recommended", value: "both" },
  ], 2);
  const local = target !== "cloud";
  const cloud = target !== "local";
  const total = cloud ? 6 : 4;
  const s = {};

  // 1. AI ------------------------------------------------------------------------------------
  step(1, total, "AI breakdown");
  say(
    "Daleel writes a plain language breakdown of the results with an AI model.",
    "The model never sees a number, and if it is unavailable Daleel shows a deterministic summary instead.",
  );
  s.AI_PROVIDER = await choose("Which AI should Daleel use?", [
    { label: "OpenRouter free models", hint: "recommended for the demo, costs nothing", value: "openrouter" },
    { label: "Ollama on this computer", hint: "nothing leaves the machine; needs a strong GPU", value: "ollama" },
    { label: "No AI", hint: "deterministic summaries only", value: "off" },
  ], ["openrouter", "ollama", "off"].indexOf(previous.AI_PROVIDER || "openrouter"));

  if (s.AI_PROVIDER === "openrouter") {
    say(
      "",
      `1. Create a free account at ${link("https://openrouter.ai")} (Sign in, top right).`,
      `2. Open ${link("https://openrouter.ai/keys")} and click ${c.bold("Create API key")}. Any name works, for example "daleel".`,
      "3. Copy the key (it starts with sk-or-) and paste it below.",
    );
    s.OPENROUTER_API_KEY = await ask("OpenRouter API key:", {
      def: previous.OPENROUTER_API_KEY, secret: true,
      validate: async (v) => (v.startsWith("sk-or-") ? await checkOpenRouter(v) : "That does not look like an OpenRouter key (it should start with sk-or-)."),
    });
    s.AI_MODELS = previous.AI_MODELS || FREE_MODELS;
    if (await confirm("Use the recommended free models (tried in order, with automatic fallback)?", true)) s.AI_MODELS = FREE_MODELS;
    else s.AI_MODELS = await ask("Model ids, comma separated (see openrouter.ai/models):", { def: s.AI_MODELS });
  } else if (s.AI_PROVIDER === "ollama") {
    say("", `Install Ollama from ${link("https://ollama.com")}, then run for example: ${c.bold("ollama pull qwen3.6:27b")}`);
    s.OLLAMA_BASE_URL = await ask("Ollama address:", { def: previous.OLLAMA_BASE_URL || "http://localhost:11434/v1" });
    s.OLLAMA_MODEL = await ask("Ollama model:", { def: previous.OLLAMA_MODEL || "qwen3.6:27b" });
    if (cloud) warn("A Hugging Face Space cannot reach Ollama on your computer. The cloud demo will use deterministic summaries.");
  }

  // 2. Database ------------------------------------------------------------------------------
  step(2, total, "Database (PostgreSQL)");
  say(
    "Daleel keeps results, approvals and the audit log in PostgreSQL. It connects as its own role,",
    `${c.bold("daleel_app")}, which cannot bypass row level security: the database itself keeps every workspace separate.`,
  );
  if (local) {
    say("", c.bold("On your computer:"),
      "  With Docker, `docker compose up` starts its own database and you can keep the default below.",
      "  Without Docker, install PostgreSQL 16 or newer, then run once:",
      c.dim("    psql -U postgres -c \"CREATE DATABASE daleel\""),
      c.dim("    psql -U postgres -d daleel -f infra/db-init.sql"));
    s.DATABASE_URL = await ask("Local database address:", {
      def: previousLocal.DATABASE_URL || "postgresql://daleel_app:daleel_local_dev@localhost:5432/daleel",
      validate: (v) => (/^postgres(ql)?:\/\//.test(v) ? null : "It should start with postgresql://"),
    });
  }
  if (cloud) await supabase(s);

  // 3. Security ------------------------------------------------------------------------------
  step(3, total, "Security");
  s.JWT_SECRET = previous.JWT_SECRET && previous.JWT_SECRET.length >= 32 ? previous.JWT_SECRET
    : crypto.randomBytes(48).toString("base64url");
  ok(`Session signing secret ready (${mask(s.JWT_SECRET)}). It was generated for you; you never need to type it.`);
  say(c.dim("  Daleel refuses to start in production with a weak secret, so this one is long and random."));

  // 4. Features ------------------------------------------------------------------------------
  step(4, total, "Features");
  s.ALLOW_UPLOADS = (await confirm("Let visitors upload their own files? (No = only the built in sample files)",
    (previous.ALLOW_UPLOADS ?? "true") === "true")) ? "true" : "false";
  if (s.ALLOW_UPLOADS === "true") {
    s.MAX_UPLOAD_MB = await ask("Largest upload, in MB:", {
      def: previous.MAX_UPLOAD_MB || (cloud ? "20" : "50"),
      validate: (v) => (Number(v) >= 1 && Number(v) <= 500 ? null : "Choose a number between 1 and 500."),
    });
  }
  s.DEMO_PERSONAS = (await confirm(
    "Demo mode: let one visitor switch between the preparer and the approver to try four eyes approval?",
    (previous.DEMO_PERSONAS ?? "true") === "true")) ? "true" : "false";
  s.SESSION_HOURS = await ask("How long a demo session lasts, in hours:", {
    def: previous.SESSION_HOURS || "12",
    validate: (v) => (Number(v) >= 1 && Number(v) <= 168 ? null : "Choose between 1 and 168 hours."),
  });

  // 5 and 6. Cloud ---------------------------------------------------------------------------
  let hf = {};
  if (cloud) {
    step(5, total, "Hugging Face Space (free hosting)");
    hf = await huggingface(s);
    step(6, total, "Saving and pushing settings");
  }

  // Write files ------------------------------------------------------------------------------
  say("");
  if (local) {
    writeEnv(BACKEND_ENV, ["Daleel settings for running on this computer. Written by `npm run setup`.",
      "Never commit this file. Run `npm run setup` again to change it."], [
      { title: "Core", entries: [["ENVIRONMENT", "development"], ["DATABASE_URL", s.DATABASE_URL],
        ["JWT_SECRET", s.JWT_SECRET, "Signs demo session tokens"]] },
      { title: "AI", entries: aiEntries(s) },
      { title: "Features", entries: featureEntries(s, "http://localhost:5173,http://localhost:7860") },
    ]);
    ok(`Wrote ${c.bold("backend/.env")} (local settings)`);
  }
  if (cloud) {
    const secrets = [["DATABASE_URL", s.CLOUD_DATABASE_URL], ["JWT_SECRET", s.JWT_SECRET]];
    if (s.AI_PROVIDER === "openrouter") secrets.push(["OPENROUTER_API_KEY", s.OPENROUTER_API_KEY]);
    const variables = [["ENVIRONMENT", "production"], ["AI_PROVIDER", s.AI_PROVIDER === "ollama" ? "off" : s.AI_PROVIDER],
      ...(s.AI_PROVIDER === "openrouter" ? [["AI_MODELS", s.AI_MODELS]] : []),
      ...featureEntries(s, hf.url).map(([k, v]) => [k, v])];
    writeEnv(DEPLOY_ENV, ["Daleel cloud settings. Written by `npm run setup`. Never commit this file.",
      "SECRETS go in the Space's Settings > Variables and secrets > New secret.",
      "VARIABLES go in the same page > New variable."], [
      { title: "SECRETS (paste as secrets)", entries: secrets },
      { title: "VARIABLES (paste as variables)", entries: variables },
      { title: "Used by `npm run deploy` only (not for the Space)", entries: [
        ["HF_SPACE", hf.space || ""], ["SUPABASE_URI", s.SUPABASE_URI || "", "As pasted from Supabase (no password)"],
        ...(hf.saveToken ? [["HF_TOKEN", hf.token]] : [])] },
    ]);
    ok(`Wrote ${c.bold(".env.deploy")} (cloud settings)`);
    if (hf.token && hf.space) {
      await pushSettings(hf, secrets, variables);
    } else {
      printPasteList(secrets, variables, hf.space);
    }
  }

  // Next steps -------------------------------------------------------------------------------
  title("Done. What to do next");
  if (local) {
    say(c.bold("Run on this computer"), "  With Docker:", c.dim("    docker compose up --build"),
      "  Without Docker (two terminals):",
      c.dim("    cd backend && uv sync && uv run daleel serve"),
      c.dim("    cd web && pnpm install && pnpm dev"),
      `  Then open ${link("http://localhost:5173")} (or ${link("http://localhost:7860")} with Docker).`, "");
  }
  if (cloud) {
    say(c.bold("Publish the cloud demo"),
      `  ${c.bold("npm run deploy")}   sends the code to your Space. The first build takes 5 to 10 minutes.`,
      `  Then open ${link(hf.url || "your Space URL")}.`,
      `  ${c.bold("npm run setup:check")}   checks everything once it is running.`, "");
  }
  say(c.dim("Keep backend/.env and .env.deploy private. To change anything, run npm run setup again."));
}

// ---------------------------------------------------------------------------------------------

async function checkOpenRouter(key) {
  try {
    const r = await fetch("https://openrouter.ai/api/v1/key", { headers: { Authorization: `Bearer ${key}` } });
    if (r.status === 401 || r.status === 403) return "OpenRouter rejected this key. Copy it again from openrouter.ai/keys.";
    if (!r.ok) {
      warn(`Could not check the key right now (HTTP ${r.status}); keeping it.`);
      return null;
    }
    const d = (await r.json()).data || {};
    ok(`OpenRouter key works${d.is_free_tier ? " (free tier: free models only)" : ""}.`);
    return null;
  } catch {
    warn("Could not reach OpenRouter to check the key (offline?). Keeping it; check later with npm run setup:check.");
    return null;
  }
}

async function supabase(s) {
  say("", c.bold("In the cloud: Supabase (free PostgreSQL)"),
    `1. Create a free account at ${link("https://supabase.com")} and click ${c.bold("New project")}.`,
    "   Pick a region near your users (for Pakistan: Mumbai or Singapore). Save the database password it asks for.",
    "2. When the project is ready, open SQL Editor (left menu) and run the SQL below. It creates Daleel's own",
    "   database role with a password generated for you just now:");
  const prevPassword = (previousCloud.DATABASE_URL || "").match(/daleel_app[^:]*:([^@]+)@.*supabase/)?.[1];
  const password = prevPassword || crypto.randomBytes(24).toString("base64url");
  const sql = [
    `CREATE ROLE daleel_app LOGIN PASSWORD '${password}' NOSUPERUSER NOBYPASSRLS NOCREATEROLE;`,
    "GRANT CREATE, USAGE ON SCHEMA public TO daleel_app;",
  ];
  say("", ...sql.map((l) => `   ${c.green(l)}`), "");
  if (prevPassword) say(c.dim("   (Same password as last time. If the role already exists, you can skip this step.)"));
  await pause("   Press Enter once the SQL has run");
  say("3. Click Connect (top of the project page), choose Session pooler, and copy the URI.",
    c.dim("   It looks like postgresql://postgres.abcd1234:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"));
  const uri = await ask("Paste the Session pooler URI:", {
    def: previous.SUPABASE_URI,
    validate: (v) => {
      try {
        const u = new URL(v.replace(/^postgres:/, "postgresql:"));
        if (!/^postgres(ql)?:$/.test(u.protocol)) return "It should start with postgresql://";
        if (!u.hostname.includes("supabase")) return "That does not look like a Supabase address.";
        return null;
      } catch {
        return "That is not a valid address. Copy the whole URI from Supabase.";
      }
    },
  });
  const u = new URL(uri.replace(/^postgres:/, "postgresql:"));
  // Pooler user names carry the project reference: postgres.<ref> becomes daleel_app.<ref>.
  const ref = decodeURIComponent(u.username).split(".")[1];
  u.username = ref ? `daleel_app.${ref}` : "daleel_app";
  u.password = encodeURIComponent(password);
  u.searchParams.set("sslmode", "require");
  s.CLOUD_DATABASE_URL = u.toString();
  s.SUPABASE_URI = uri;
  ok(`Daleel will connect as ${c.bold(u.username)} to ${u.hostname} (password hidden).`);
  if (await confirm("Test the connection now? (needs uv and the backend installed)", false)) testDatabase(s.CLOUD_DATABASE_URL);
}

function testDatabase(url) {
  try {
    const out = execFileSync("uv", ["run", "--project", "backend", "python", "-c",
      "import os, psycopg; c = psycopg.connect(os.environ['DB'], connect_timeout=10); " +
      "r = c.execute('select current_user, (select rolbypassrls from pg_roles where rolname = current_user)').fetchone(); " +
      "print(r[0], r[1])"], { cwd: ROOT, env: { ...process.env, DB: url }, stdio: ["ignore", "pipe", "pipe"] }).toString().trim();
    const [user, bypass] = out.split(" ");
    if (bypass === "True") warn(`Connected as ${user}, but this role can bypass row level security. Use the daleel_app role.`);
    else ok(`Connected as ${user}; row level security applies.`);
  } catch (e) {
    fail(`Could not connect: ${String(e.stderr || e.message).split("\n").filter(Boolean).slice(-1)[0]}`);
    say(c.dim("   Check that the SQL ran, and that you copied the Session pooler URI. You can continue and fix it later."));
  }
}

async function huggingface(s) {
  say("Hugging Face Spaces runs Daleel for free (2 CPUs, 16 GB of memory). The free tier sleeps after two",
    "days without visitors and wakes on the next visit.", "",
    `1. Create a free account at ${link("https://huggingface.co/join")}.`,
    `2. Create an access token at ${link("https://huggingface.co/settings/tokens")}:`,
    `   click ${c.bold("Create new token")}, choose ${c.bold("Write")}, name it "daleel-deploy".`,
    "   With the token the wizard can create the Space and add every setting for you.");
  const auto = await confirm("Let the wizard create the Space and add the settings for you?", true);
  let token = "";
  let user = previous.HF_SPACE?.split("/")[0] || "";
  if (auto) {
    token = await ask("Hugging Face token (starts with hf_):", {
      def: previous.HF_TOKEN, secret: true,
      validate: async (v) => {
        if (!v.startsWith("hf_")) return "Hugging Face tokens start with hf_.";
        try {
          const r = await fetch(`${HF_API}/whoami-v2`, { headers: { Authorization: `Bearer ${v}` } });
          if (r.status === 401) return "Hugging Face rejected this token.";
          if (r.ok) {
            const who = await r.json();
            user = who.name;
            const role = who.auth?.accessToken?.role;
            if (role && role !== "write" && role !== "fineGrained") return "This token is read only. Create one with Write access.";
            ok(`Signed in to Hugging Face as ${c.bold(user)}.`);
          }
        } catch {
          warn("Could not reach Hugging Face to check the token; keeping it.");
        }
        return null;
      },
    });
  } else {
    say("", `   Create the Space yourself: ${link("https://huggingface.co/new-space")}`,
      `   Space name: ${c.bold("daleel")}   SDK: ${c.bold("Docker")} (Blank)   Hardware: ${c.bold("CPU basic, free")}   Visibility: Public`);
    await pause();
  }
  if (!user) user = await ask("Your Hugging Face username:", { validate: (v) => (/^[\w.-]+$/.test(v) ? null : "Letters, numbers, dot, dash or underscore only.") });
  const name = await ask("Space name:", {
    def: previous.HF_SPACE?.split("/")[1] || "daleel",
    validate: (v) => (/^[\w.-]{1,96}$/.test(v) ? null : "Letters, numbers, dot, dash or underscore only."),
  });
  const space = `${user}/${name}`;
  const url = `https://${`${user}-${name}`.toLowerCase().replace(/[._]/g, "-")}.hf.space`;
  ok(`Your demo will live at ${link(url)}`);
  const saveToken = token ? await confirm("Save the token in .env.deploy so `npm run deploy` can push updates?", true) : false;
  s.PUBLIC_URL = url;
  return { token, space, url, saveToken };
}

async function pushSettings(hf, secrets, variables) {
  const headers = { Authorization: `Bearer ${hf.token}`, "Content-Type": "application/json" };
  const [owner, name] = hf.space.split("/");
  try {
    const r = await fetch(`${HF_API}/repos/create`, {
      method: "POST", headers,
      body: JSON.stringify({ type: "space", name, organization: undefined, private: false, sdk: "docker" }),
    });
    if (r.ok) ok(`Created the Space ${c.bold(hf.space)}.`);
    else if (r.status === 409) ok(`The Space ${c.bold(hf.space)} already exists; updating its settings.`);
    else throw new Error(`HTTP ${r.status}: ${(await r.text()).slice(0, 120)}`);
  } catch (e) {
    fail(`Could not create the Space automatically (${e.message}).`);
    return printPasteList(secrets, variables, hf.space);
  }
  let failed = false;
  for (const [kind, list] of [["secrets", secrets], ["variables", variables]]) {
    for (const [key, value] of list) {
      try {
        const r = await fetch(`${HF_API}/spaces/${owner}/${name}/${kind}`, { method: "POST", headers, body: JSON.stringify({ key, value }) });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        ok(`${kind === "secrets" ? "Secret" : "Variable"} ${c.bold(key)} set`);
      } catch (e) {
        failed = true;
        fail(`${key}: ${e.message}`);
      }
    }
  }
  if (failed) printPasteList(secrets, variables, hf.space);
}

function printPasteList(secrets, variables, space) {
  title("Paste these into your Space");
  say(`Open ${link(`https://huggingface.co/spaces/${space || "<you>/<space>"}/settings`)} and scroll to ${c.bold("Variables and secrets")}.`, "");
  say(c.bold("New secret") + c.dim("  (hidden after saving)"));
  for (const [k, v] of secrets) say(`   ${c.bold(k.padEnd(20))} ${v}`);
  say("", c.bold("New variable") + c.dim("  (visible)"));
  for (const [k, v] of variables) say(`   ${c.bold(k.padEnd(20))} ${v}`);
  say("", c.dim("The same list is saved in .env.deploy."));
}

function aiEntries(s) {
  if (s.AI_PROVIDER === "openrouter") return [["AI_PROVIDER", "openrouter"], ["OPENROUTER_API_KEY", s.OPENROUTER_API_KEY], ["AI_MODELS", s.AI_MODELS]];
  if (s.AI_PROVIDER === "ollama") return [["AI_PROVIDER", "ollama"], ["OLLAMA_BASE_URL", s.OLLAMA_BASE_URL], ["OLLAMA_MODEL", s.OLLAMA_MODEL]];
  return [["AI_PROVIDER", "off"]];
}

function featureEntries(s, origins) {
  return [
    ["ALLOW_UPLOADS", s.ALLOW_UPLOADS, "false = visitors can only run the built in samples"],
    ...(s.MAX_UPLOAD_MB ? [["MAX_UPLOAD_MB", s.MAX_UPLOAD_MB]] : []),
    ["DEMO_PERSONAS", s.DEMO_PERSONAS, "true = one visitor can switch between preparer and approver"],
    ["SESSION_HOURS", s.SESSION_HOURS],
    ["CORS_ORIGINS", origins || ""],
    ...(s.PUBLIC_URL && origins && !origins.includes("localhost") ? [["PUBLIC_URL", s.PUBLIC_URL]] : []),
  ];
}

// ---------------------------------------------------------------------------------------------

async function check() {
  title("Daleel settings check");
  const local = readEnv(BACKEND_ENV);
  const deploy = readEnv(DEPLOY_ENV);
  if (!Object.keys(local).length && !Object.keys(deploy).length) {
    fail("No settings found. Run npm run setup first.");
    return;
  }
  for (const [label, env, required] of [["backend/.env", local, ["DATABASE_URL", "JWT_SECRET"]],
    [".env.deploy", deploy, ["DATABASE_URL", "JWT_SECRET", "CORS_ORIGINS"]]]) {
    if (!Object.keys(env).length) continue;
    say(c.bold(`\n${label}`));
    for (const key of required) (env[key] ? ok : fail)(`${key} ${env[key] ? "is set" : "is missing"}`);
    if ((env.JWT_SECRET || "").length < 32) fail("JWT_SECRET is shorter than 32 characters.");
    if (env.AI_PROVIDER === "openrouter") {
      if (!env.OPENROUTER_API_KEY) fail("OPENROUTER_API_KEY is missing.");
      else await checkOpenRouter(env.OPENROUTER_API_KEY);
    }
  }
  const url = deploy.PUBLIC_URL || deploy.CORS_ORIGINS;
  if (url && url.startsWith("https://")) {
    say(c.bold(`\nCloud demo at ${url}`));
    try {
      const r = await fetch(`${url}/health`);
      if (r.ok) {
        const h = await r.json();
        ok(`Running: version ${h.version}, AI ${h.ai_provider}${h.ai_configured ? "" : " (no key)"}, uploads ${h.allow_uploads ? "on" : "off"}.`);
      } else warn(`The Space answered HTTP ${r.status}. It may still be building or asleep; try again in a few minutes.`);
    } catch {
      warn("Could not reach the Space yet. If you just deployed, the build takes 5 to 10 minutes.");
    }
  }
  say("");
}
