import fs from "node:fs";
import path from "node:path";
import Anthropic from "@anthropic-ai/sdk";
import { SB_ROOT, requireEnv } from "../lib/env.js";
import { loadIdentity, type Domain } from "../lib/identity.js";

const client = new Anthropic({ apiKey: requireEnv("ANTHROPIC_API_KEY") });

function parseDomain(): Domain {
  const args = process.argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--domain") return args[++i] as Domain;
  }
  throw new Error("--domain required (build|reach|serve)");
}

interface PromotedItem {
  line: string;
  title: string;
  url: string;
  why: string;
  source: string;
}

function extractPromoted(inboxText: string): { promoted: PromotedItem[]; updated: string } {
  const lines = inboxText.split("\n");
  const promoted: PromotedItem[] = [];
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.startsWith("|")) continue;
    if (!/\|\s*promote\s*\|/i.test(line)) continue;
    const cells = line.split("|").map((c) => c.trim());
    // | date | title | source | why | link | status |
    const title = cells[2] ?? "";
    const source = cells[3] ?? "";
    const why = cells[4] ?? "";
    const linkCell = cells[5] ?? "";
    const url = linkCell.match(/\(([^)]+)\)/)?.[1] ?? "";
    promoted.push({ line, title, url, why, source });
    lines[i] = line.replace(/\|\s*promote\s*\|/i, "| distilled |");
  }
  return { promoted, updated: lines.join("\n") };
}

const SYSTEM = `You update a domain "standard.md" — Allen's "what good looks like" one-pager — by folding in a small set of promoted items from his inbox.

You receive: (1) Allen's identity, (2) current standard.md, (3) the promoted items (title, why, source, URL).

Output a NEW full standard.md (replaces the old). Rules:
- Keep one-pager length. Cut the weakest existing line if you must.
- Sections: Principles / Patterns / Anti-patterns / Reference Links.
- Each new pattern or anti-pattern is a single concrete bullet — name the principle, give the action.
- Append every promoted URL to "Reference Links" with one-line context.
- Update the "Last updated" date to today.
- Concrete > abstract. Link the bullet to a real thing Allen can do or avoid.
- Do not include any commentary, explanation, or fences — output the markdown only.`;

async function main() {
  const domain = parseDomain();
  const today = new Date().toISOString().slice(0, 10);
  const inboxPath = path.join(SB_ROOT, "domains", domain, "inbox.md");
  const standardPath = path.join(SB_ROOT, "domains", domain, "standard.md");
  const archiveDir = path.join(SB_ROOT, "domains", domain, "archive");
  fs.mkdirSync(archiveDir, { recursive: true });

  const inboxText = fs.readFileSync(inboxPath, "utf8");
  const { promoted, updated } = extractPromoted(inboxText);

  if (promoted.length === 0) {
    console.log(`[distill:${domain}] no items marked [promote] — nothing to do`);
    return;
  }

  const standard = fs.readFileSync(standardPath, "utf8");
  const identity = loadIdentity();

  const promotedBlock = promoted
    .map((p, i) => `${i + 1}. title: ${p.title}\n   source: ${p.source}\n   why: ${p.why}\n   url: ${p.url}`)
    .join("\n");

  console.log(`[distill:${domain}] folding ${promoted.length} promoted items via Sonnet...`);
  const res = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 4000,
    system: SYSTEM,
    messages: [
      {
        role: "user",
        content: `IDENTITY:\n${identity}\n\nCURRENT standard.md (domains/${domain}/standard.md):\n${standard}\n\nPROMOTED ITEMS:\n${promotedBlock}\n\nToday's date: ${today}`,
      },
    ],
  });
  const text = res.content
    .filter((b): b is Anthropic.TextBlock => b.type === "text")
    .map((b) => b.text)
    .join("");

  // archive old standard
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  fs.writeFileSync(path.join(archiveDir, `standard-${stamp}.md`), standard);
  fs.writeFileSync(standardPath, text);
  fs.writeFileSync(inboxPath, updated);

  console.log(`[distill:${domain}] standard.md updated (archived to archive/standard-${stamp}.md)`);
  console.log(`[distill:${domain}] inbox: marked ${promoted.length} as distilled`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
