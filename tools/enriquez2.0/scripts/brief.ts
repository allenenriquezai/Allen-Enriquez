import fs from "node:fs";
import path from "node:path";
import { SB_ROOT } from "../lib/env.js";
import type { Domain } from "../lib/identity.js";

const DOMAINS: Domain[] = ["build", "reach", "serve"];

function topInboxItems(domain: Domain, n: number): { lines: string[]; unread: number } {
  const p = path.join(SB_ROOT, "domains", domain, "inbox.md");
  if (!fs.existsSync(p)) return { lines: [], unread: 0 };
  const lines = fs.readFileSync(p, "utf8").split("\n");
  const newRows = lines.filter((l) => l.startsWith("|") && /\|\s*new\s*\|/i.test(l));
  const top = newRows.slice(0, n).map((row) => {
    const c = row.split("|").map((x) => x.trim());
    const title = c[2] ?? "";
    const why = c[4] ?? "";
    const link = c[5] ?? "";
    return `- **${title}** — ${why} ${link}`;
  });
  return { lines: top, unread: newRows.length };
}

function latestAudit(domain: Domain): { path: string; summary: string } | null {
  const dir = path.join(SB_ROOT, "audits");
  if (!fs.existsSync(dir)) return null;
  const matches = fs
    .readdirSync(dir)
    .filter((f) => f.startsWith(`${domain}-`) && f.endsWith(".md"))
    .sort();
  if (matches.length === 0) return null;
  const latest = matches[matches.length - 1];
  const text = fs.readFileSync(path.join(dir, latest), "utf8");
  // Extract Quick wins block + first 3 gap headlines
  const gaps = [...text.matchAll(/^\d+\.\s+\*\*([^*]+)\*\*/gm)].slice(0, 3).map((m) => `  - ${m[1]}`);
  const quickWinsMatch = text.match(/## Quick wins[^\n]*\n([\s\S]*?)(?=\n##|\n---|$)/);
  const quickWins = quickWinsMatch ? quickWinsMatch[1].trim() : "";
  const summary = `Top gaps:\n${gaps.join("\n")}\n\nQuick wins:\n${quickWins}`;
  return { path: `audits/${latest}`, summary };
}

function latestScout(): { path: string; summary: string } | null {
  const dir = path.join(SB_ROOT, "scout");
  if (!fs.existsSync(dir)) return null;
  const matches = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .sort();
  if (matches.length === 0) return null;
  const latest = matches[matches.length - 1];
  const text = fs.readFileSync(path.join(dir, latest), "utf8");
  // Take top 3 blind spots per domain (## BUILD / ## REACH / ## SERVE sections)
  const sections = ["BUILD", "REACH", "SERVE"];
  const out: string[] = [];
  for (const sec of sections) {
    const re = new RegExp(`##\\s+${sec}\\s*\\n([\\s\\S]*?)(?=\\n##\\s|$)`);
    const block = text.match(re)?.[1] ?? "";
    const items = [...block.matchAll(/^\d+\.\s+\*\*([^*]+)\*\*([\s\S]*?)(?=\n\d+\.\s+\*\*|\n##|$)/gm)]
      .slice(0, 3)
      .map((m) => {
        const slug = m[1].trim();
        const why = m[2].split("\n")[0].replace(/^[\s—-]+/, "").trim();
        const urgency = m[2].match(/Urgency:\s*(\d)/)?.[1] ?? "";
        return `  - **${slug}**${urgency ? ` (urgency ${urgency})` : ""} — ${why}`;
      });
    if (items.length) out.push(`**${sec}:**`, ...items);
  }
  const summary = out.length > 0 ? out.join("\n") : "_No blind spots surfaced._";
  return { path: `scout/${latest}`, summary };
}

function latestOpportunities(): { path: string; summary: string } | null {
  const dir = path.join(SB_ROOT, "opportunities");
  if (!fs.existsSync(dir)) return null;
  const matches = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".md"))
    .sort();
  if (matches.length === 0) return null;
  const latest = matches[matches.length - 1];
  const text = fs.readFileSync(path.join(dir, latest), "utf8");
  // Extract Top moves block (first 3 numbered items with headlines)
  const moves = [...text.matchAll(/^\d+\.\s+\*\*([^*]+)\*\*([\s\S]*?)(?=\n\d+\.\s+\*\*|\n##|$)/gm)]
    .slice(0, 3)
    .map((m) => {
      const headline = m[1].trim();
      const firstStep = m[2].match(/First step:\s*(.+)/)?.[1]?.trim() ?? "";
      return `  - **${headline}**${firstStep ? ` — first step: ${firstStep}` : ""}`;
    });
  const summary = moves.length > 0 ? `Top moves:\n${moves.join("\n")}` : "_No moves surfaced._";
  return { path: `opportunities/${latest}`, summary };
}

function main() {
  const today = new Date().toISOString().slice(0, 10);
  const out: string[] = [];
  out.push(`# Daily Brief — ${today}`, "");
  out.push("> Pull-on-demand. Read top inbox items, check audit Quick wins, scan opportunities, decide what to act on today.");
  out.push("");

  const scout = latestScout();
  if (scout) {
    out.push(`## Blind Spots (${scout.path})`, "", scout.summary, "");
  }

  const opps = latestOpportunities();
  if (opps) {
    out.push(`## Opportunities (${opps.path})`, "", opps.summary, "");
  }

  for (const d of DOMAINS) {
    const { lines, unread } = topInboxItems(d, 3);
    const audit = latestAudit(d);
    out.push(`## ${d.toUpperCase()}`, "");
    out.push(`**Inbox:** ${unread} unread`);
    if (lines.length) {
      out.push("", "**Top items:**", ...lines);
    } else {
      out.push("", "_No new items._");
    }
    if (audit) {
      out.push("", `**Latest audit (${audit.path}):**`, "", audit.summary);
    } else {
      out.push("", "_No audit yet._ Run `npm run audit -- --domain " + d + "`.");
    }
    if (unread >= 10) {
      out.push("", `> 🚨 ${unread} items unread in ${d}/inbox.md — promote or archive before standard drifts.`);
    }
    out.push("");
  }

  const dir = path.join(SB_ROOT, "briefs");
  fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, `${today}.md`);
  fs.writeFileSync(file, out.join("\n"));
  console.log(`[brief] wrote briefs/${today}.md`);
  console.log(out.join("\n"));
}

main();
