import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { SB_ROOT, requireEnv } from "../lib/env.js";
import { loadIdentity, type Domain } from "../lib/identity.js";

const client = new Anthropic({ apiKey: requireEnv("ANTHROPIC_API_KEY") });

const DOMAINS: Domain[] = ["build", "reach", "serve"];

function loadInbox(domain: Domain): string {
  const p = path.join(SB_ROOT, "domains", domain, "inbox.md");
  if (!fs.existsSync(p)) return "";
  const lines = fs.readFileSync(p, "utf8").split("\n");
  const newRows = lines.filter((l) => l.startsWith("|") && /\|\s*new\s*\|/i.test(l));
  return `=== ${domain} inbox (${newRows.length} new items) ===\n${newRows.join("\n")}`;
}

function loadContentHubState(): string {
  const p = path.join(SB_ROOT, "state", "content-hub.json");
  if (!fs.existsSync(p)) return "";
  const raw = fs.readFileSync(p, "utf8");
  return `=== content-hub state (Allen's actual posting cadence + pipeline) ===\n${raw.slice(0, 20000)}`;
}

const SYSTEM = `You scan Allen's three domain inboxes for OPPORTUNITIES — items proposing a NEW move he should make. Not gaps in current systems (the audit handles that). Not pure information.

You receive: (1) Allen's identity (who, becoming, Q2 anchor), (2) the unprocessed inbox rows for BUILD, REACH, SERVE.

For each candidate item, decide:
- Does it propose a NEW MOVE Allen could make? (a market, niche, tool, content cadence, sales motion, script pattern, audience)
- How directly does it serve the Q2 anchor (first paid client by June 2026, 10k followers as engine)?
- Is the first step concrete and within Allen's reach this week?
- If "content-hub state" is present below, prefer moves that close REAL gaps Allen has shipped/not-shipped: empty schedule slots this week, top-performing posts to repeat, stuck projects, dead platforms.

Drop:
- Pure intel/news ("X company shipped Y") with no implied action.
- Items already represented in the standard.md.
- Generic advice ("post more, engage more").
- Anything score < 6 on Q2-proximity.

Output strict markdown, no preamble:

# Opportunities — {YYYY-MM-DD}

## Top moves (Q2-anchor proximity)

1. **{One-line move headline}** — {1-2 sentences. What the move is. Why it serves Q2.}
   First step: {one concrete action ≤25 words, doable this week}.
   Effort: {S/M/L} · Q2 proximity: {1-10}.
   Source: {source} [link]({url}).

(repeat 3-7 times max — quality over quantity)

## Considered, dropped
- **{title}** — {reason in ≤15 words}.
(2-4 bullets only — show your filtering)

Rules:
- Cite real items from the inboxes. Never invent URLs.
- If fewer than 3 real opportunities exist, output fewer. Don't pad.
- "First step" must be specific (e.g. "Draft 3 LinkedIn posts modeled after Saurav's 52-post cadence" — not "engage more on LinkedIn").`;

async function main() {
  const today = new Date().toISOString().slice(0, 10);
  const identity = loadIdentity();
  const inboxes = DOMAINS.map(loadInbox).filter((s) => s.length > 0).join("\n\n");
  const contentState = loadContentHubState();

  if (!inboxes) {
    console.log("[opportunities] no inbox content — run `npm run ingest` first");
    return;
  }

  console.log("[opportunities] calling Sonnet...");
  const userMsg = `IDENTITY:\n${identity}\n\nINBOXES:\n${inboxes}${contentState ? `\n\n${contentState}` : ""}\n\nToday's date: ${today}`;
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

  const dir = path.join(SB_ROOT, "opportunities");
  fs.mkdirSync(dir, { recursive: true });
  const out = path.join(dir, `${today}.md`);
  fs.writeFileSync(out, text);
  console.log(`[opportunities] wrote opportunities/${today}.md (${text.length} chars)`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
