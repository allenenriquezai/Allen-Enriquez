import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { SB_ROOT, requireEnv } from "../lib/env.js";
import { loadIdentity, type Domain } from "../lib/identity.js";

const client = new Anthropic({ apiKey: requireEnv("ANTHROPIC_API_KEY") });

const STATE_FILES_BY_DOMAIN: Record<Domain, string[]> = {
  build: ["repo.json", "automations.json", "content-hub.json"],
  reach: ["content.json", "content-hub.json", "repo.json"],
  serve: ["content.json", "content-hub.json", "repo.json"],
};

function parseDomain(): Domain {
  const args = process.argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--domain") return args[++i] as Domain;
  }
  throw new Error("--domain required (build|reach|serve)");
}

function loadState(domain: Domain): string {
  const files = STATE_FILES_BY_DOMAIN[domain];
  const parts: string[] = [];
  for (const f of files) {
    const p = path.join(SB_ROOT, "state", f);
    if (!fs.existsSync(p)) continue;
    const json = fs.readFileSync(p, "utf8");
    parts.push(`=== state/${f} ===\n${json.slice(0, 30000)}`);
  }
  return parts.join("\n\n");
}

function loadStandard(domain: Domain): string {
  const p = path.join(SB_ROOT, "domains", domain, "standard.md");
  return fs.existsSync(p) ? fs.readFileSync(p, "utf8") : "";
}

const SYSTEM = `You audit Allen's systems against a domain standard.

You receive: (1) Allen's identity, (2) the domain "standard.md" (what good looks like), (3) JSON snapshots of Allen's actual repo/content/automation state.

Find concrete gaps — places Allen's reality lags the standard. Score each gap by impact × ease (1-5 each). Sort by impact * ease descending.

Output strict markdown with this shape — no preamble, no closing summary:

# {DOMAIN} Audit — {YYYY-MM-DD}

## Top gaps (impact × ease)

1. **{One-line gap headline}** — {1-2 sentences. What standard says vs what state shows. Cite a real path/name from the state JSON.}
   Fix: {one concrete action, ≤25 words}.
   Impact {1-5} × Ease {1-5} = {product}.

(repeat 5-8 times)

## Quick wins (today)
- {bullet — only items with ease ≥4 and impact ≥3}

## Deferred (low priority)
- {bullet — items skipped, with one-line reason}

Rules:
- Cite real things from the state JSON. No invented files.
- If a gap is generic ("write more tests"), drop it. Find specific, action-ready gaps tied to Allen's Q2 anchor.
- Skip if standard.md is empty/stub — say so once and stop.
- **CRITICAL: \`top_dirs\` shows ON-DISK file counts (includes gitignored files). \`git_tracked\` shows what is actually committed to git. NEVER claim a file is "tracked", "committed", or "in the repo" unless it appears in \`git_tracked.suspicious_tracked\` or you can infer it from \`git_tracked.byTopDir\`. A file showing in \`top_dirs\` but not in \`git_tracked\` is correctly gitignored — do not flag it as a tracking gap.**
- If proposing a \`.gitignore\` change, verify the path is in \`git_tracked.suspicious_tracked\` first. Otherwise drop the gap.`;

async function main() {
  const domain = parseDomain();
  const identity = loadIdentity();
  const standard = loadStandard(domain);
  const state = loadState(domain);
  const today = new Date().toISOString().slice(0, 10);

  const userMsg = `IDENTITY:\n${identity}\n\nDOMAIN: ${domain.toUpperCase()}\n\nSTANDARD (domains/${domain}/standard.md):\n${standard}\n\nSTATE:\n${state}\n\nToday's date: ${today}`;

  console.log(`[audit:${domain}] calling Sonnet...`);
  const res = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 4000,
    system: SYSTEM,
    messages: [{ role: "user", content: userMsg }],
  });
  const text = res.content
    .filter((b): b is Anthropic.TextBlock => b.type === "text")
    .map((b) => b.text)
    .join("");

  const out = path.join(SB_ROOT, "audits", `${domain}-${today}.md`);
  fs.writeFileSync(out, text);
  console.log(`[audit:${domain}] wrote ${path.relative(SB_ROOT, out)} (${text.length} chars)`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
