#!/usr/bin/env node
// npm run deploy: publish the committed code to your Hugging Face Space.
//
// What it does:
// 1. Takes the last commit (git archive), so only committed files are published.
// 2. Leaves out what the Space does not need: PDFs, images and social media material
//    (Hugging Face rejects plain binary files, and the app reads the extracted text).
// 3. Adds the short header Hugging Face reads from README.md (Docker SDK, port 7860).
// 4. Pushes it to the Space, which then builds the Dockerfile (5 to 10 minutes).
//
// Needs: git, and HF_SPACE plus HF_TOKEN in .env.deploy (run `npm run setup`).

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { DEPLOY_ENV, ROOT, c, fail, link, ok, readEnv, say, title, warn } from "./lib.mjs";

const dryRun = process.argv.includes("--dry-run");
const env = readEnv(DEPLOY_ENV);
const space = process.env.HF_SPACE || env.HF_SPACE;
const token = process.env.HF_TOKEN || env.HF_TOKEN;
title("Deploy Daleel to Hugging Face");
if (!dryRun && (!space || !token)) {
  fail("HF_SPACE and HF_TOKEN are needed. Run npm run setup (choose the cloud option and save the token).");
  process.exit(1);
}

const git = (args, opts = {}) => execFileSync("git", args, { cwd: ROOT, stdio: ["ignore", "pipe", "pipe"], ...opts }).toString().trim();
if (git(["status", "--porcelain"])) warn("You have uncommitted changes. Only the last commit is deployed.");
const commit = git(["rev-parse", "--short", "HEAD"]);

const dir = fs.mkdtempSync(path.join(os.tmpdir(), "daleel-deploy-"));
try {
  execFileSync("sh", ["-c", `git archive HEAD | tar -x -C "${dir}"`], { cwd: ROOT, stdio: "inherit" });
  const drop = ["social-media", ".github"];
  for (const d of drop) fs.rmSync(path.join(dir, d), { recursive: true, force: true });
  let dropped = 0;
  const walk = (d) => {
    for (const name of fs.readdirSync(d)) {
      const p = path.join(d, name);
      if (fs.statSync(p).isDirectory()) walk(p);
      else if (/\.(pdf|png|jpe?g|gif|xlsx|parquet|zip)$/i.test(name)) {
        fs.rmSync(p);
        dropped += 1;
      }
    }
  };
  walk(dir);
  const readme = fs.readFileSync(path.join(dir, "README.md"), "utf8");
  const header = [
    "---",
    "title: Daleel",
    "emoji: 📗",
    "colorFrom: green",
    "colorTo: yellow",
    "sdk: docker",
    "app_port: 7860",
    "pinned: false",
    "short_description: Islamic bank regulatory compliance tool (synthetic demo)",
    "---",
    "",
  ].join("\n");
  fs.writeFileSync(path.join(dir, "README.md"), header + readme);
  ok(`Prepared commit ${commit} (${dropped} binary files left out, not needed by the app).`);

  if (dryRun) {
    const files = execFileSync("sh", ["-c", "find . -type f | wc -l; du -sh . | cut -f1"], { cwd: dir }).toString().split("\n");
    ok(`Dry run: ${files[0].trim()} files, ${files[1].trim()} would be pushed. README header:`);
    say(c.dim(header));
    say("Nothing was pushed. Run npm run deploy without --dry-run to publish.");
    process.exit(0);
  }
  const run = (args) => execFileSync("git", args, { cwd: dir, stdio: ["ignore", "pipe", "pipe"] });
  run(["init", "-q", "-b", "main"]);
  run(["add", "-A"]);
  run(["-c", "user.name=Daleel deploy", "-c", "user.email=deploy@daleel.local", "commit", "-q", "-m", `Deploy ${commit}`]);
  const [owner, name] = space.split("/");
  const remote = `https://${encodeURIComponent(owner)}:${encodeURIComponent(token)}@huggingface.co/spaces/${owner}/${name}`;
  say(`Pushing to ${c.bold(space)} ...`);
  try {
    run(["push", "--force", "-q", remote, "main"]);
  } catch (e) {
    const message = String(e.stderr || e.message).replaceAll(token, "***");
    fail(`Push failed: ${message.split("\n").filter(Boolean).slice(-2).join(" ")}`);
    say(c.dim("Check that the Space exists, and that the token has Write access."));
    process.exit(1);
  }
  ok("Pushed. Hugging Face is now building the container.");
  const url = `https://${`${owner}-${name}`.toLowerCase().replace(/[._]/g, "-")}.hf.space`;
  say("", `Build logs: ${link(`https://huggingface.co/spaces/${space}?logs=build`)}`,
    `Demo:       ${link(url)}  (ready in about 5 to 10 minutes)`,
    `Then run ${c.bold("npm run setup:check")} to confirm everything is working.`);
} finally {
  fs.rmSync(dir, { recursive: true, force: true });
}
