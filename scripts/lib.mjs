// Small helpers shared by the setup wizard and the deploy script.
// No dependencies: only Node's own modules, so `npm run setup` works right after cloning.

import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export const BACKEND_ENV = path.join(ROOT, "backend", ".env");
export const DEPLOY_ENV = path.join(ROOT, ".env.deploy");

const color = process.stdout.isTTY && !process.env.NO_COLOR;
const paint = (code) => (s) => (color ? `\x1b[${code}m${s}\x1b[0m` : String(s));
export const c = {
  bold: paint("1"), dim: paint("2"), green: paint("32"), yellow: paint("33"), red: paint("31"),
  cyan: paint("36"), gold: paint("33;1"),
};

export function title(text) {
  const line = "=".repeat(Math.min(72, text.length + 4));
  console.log(`\n${c.gold(line)}\n${c.gold("  " + text)}\n${c.gold(line)}`);
}
export function step(n, total, text) {
  console.log(`\n${c.cyan(c.bold(`Step ${n} of ${total}`))}  ${c.bold(text)}`);
}
export const say = (...lines) => lines.forEach((l) => console.log(l));
export const ok = (t) => console.log(`${c.green("  OK")}  ${t}`);
export const warn = (t) => console.log(`${c.yellow("  !")}   ${t}`);
export const fail = (t) => console.log(`${c.red("  X")}   ${t}`);
export const bullet = (t) => console.log(`   - ${t}`);
export const link = (t) => c.cyan(t);

// Input: every line typed (or pasted, or piped) goes into a queue, and each question
// takes the next line. Nothing is lost if answers arrive faster than the questions.
let rl;
let muted = false;
const queue = [];
const waiting = [];
let closed = false;

function rli() {
  if (!rl) {
    const tty = Boolean(process.stdin.isTTY);
    rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal: tty });
    if (tty) {
      // While a secret is typed, readline's echo is swallowed so the key never shows.
      const write = rl._writeToOutput.bind(rl);
      rl._writeToOutput = (s) => { if (!muted) write(s); };
    }
    rl.on("line", (line) => (waiting.length ? waiting.shift()(line) : queue.push(line)));
    rl.on("close", () => {
      closed = true;
      while (waiting.length) waiting.shift()(null);
    });
    rl.on("SIGINT", () => {
      console.log(c.yellow("\n\nSetup cancelled. Nothing was written."));
      process.exit(130);
    });
  }
  return rl;
}

function nextLine() {
  rli();
  if (queue.length) return Promise.resolve(queue.shift());
  if (closed) return Promise.resolve(null);
  return new Promise((resolve) => waiting.push(resolve));
}

export function closePrompts() {
  if (rl) rl.close();
}

/** Ask a question. Secret answers are not shown while typing. */
export async function ask(question, { def = "", secret = false, validate } = {}) {
  const shownDefault = def ? c.dim(` [${secret ? mask(def) : def}]`) : "";
  process.stdout.write(`${c.bold("?")} ${question}${shownDefault} `);
  if (secret && process.stdin.isTTY) muted = true;
  const raw = await nextLine();
  if (muted) {
    muted = false;
    process.stdout.write("\n");
  } else if (!process.stdin.isTTY) {
    process.stdout.write("\n");
  }
  if (raw === null) {
    console.log(c.yellow("\nInput ended before setup finished. Nothing was written."));
    process.exit(1);
  }
  const value = raw.trim() || def;
  if (validate) {
    const problem = await validate(value);
    if (problem) {
      fail(problem);
      return ask(question, { def, secret, validate });
    }
  }
  return value;
}

export async function confirm(question, def = true) {
  const answer = (await ask(`${question} ${c.dim(def ? "(Y/n)" : "(y/N)")}`)).toLowerCase();
  if (!answer) return def;
  return answer.startsWith("y");
}

export async function choose(question, options, defIndex = 0) {
  say(`${c.bold("?")} ${question}`);
  options.forEach((o, i) => say(`   ${c.bold(String(i + 1))}. ${o.label}${o.hint ? c.dim(`  ${o.hint}`) : ""}`));
  const answer = await ask("Type a number", {
    def: String(defIndex + 1),
    validate: (v) => (Number(v) >= 1 && Number(v) <= options.length ? null : `Choose a number from 1 to ${options.length}.`),
  });
  return options[Number(answer) - 1].value;
}

export async function pause(text = "Press Enter when you are done") {
  await ask(c.dim(text));
}

export function mask(value) {
  if (!value) return "";
  return value.length <= 8 ? "********" : `${value.slice(0, 4)}...${value.slice(-4)}`;
}

/** Read a .env file into an object (simple KEY=value lines; # comments ignored). */
export function readEnv(file) {
  if (!fs.existsSync(file)) return {};
  const out = {};
  for (const line of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/);
    if (m) out[m[1]] = m[2].replace(/^"(.*)"$/, "$1");
  }
  return out;
}

/** Write a .env file with comments. sections: [{ title, entries: [[key, value, note]] }] */
export function writeEnv(file, header, sections) {
  const lines = [...header.map((h) => `# ${h}`), ""];
  for (const s of sections) {
    lines.push(`# ---- ${s.title}`);
    for (const [key, value, note] of s.entries) {
      if (note) lines.push(`# ${note}`);
      lines.push(`${key}=${/[\s#"']/.test(value) ? JSON.stringify(value) : value}`);
    }
    lines.push("");
  }
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, lines.join("\n"), { mode: 0o600 });
}
