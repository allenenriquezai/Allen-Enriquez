import fs from "node:fs";
import path from "node:path";
import { marked } from "marked";
import { SB_ROOT } from "../lib/env.js";

const today = new Date().toISOString().slice(0, 10);

const sections: Array<{ title: string; file: string }> = [
  { title: "Daily Brief", file: `briefs/${today}.md` },
  { title: "Blind Spots (Scout)", file: `scout/${today}.md` },
  { title: "Opportunities", file: `opportunities/${today}.md` },
  { title: "Audit — BUILD", file: `audits/build-${today}.md` },
  { title: "Audit — REACH", file: `audits/reach-${today}.md` },
  { title: "Audit — SERVE", file: `audits/serve-${today}.md` },
  { title: "Inbox — BUILD", file: `domains/build/inbox.md` },
  { title: "Inbox — REACH", file: `domains/reach/inbox.md` },
  { title: "Inbox — SERVE", file: `domains/serve/inbox.md` },
];

const css = `
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    background: #0a0e1a;
    color: #e2e8f0;
    margin: 0;
    padding: 0;
    line-height: 1.6;
  }
  .layout { display: flex; min-height: 100vh; }
  nav.toc {
    width: 260px;
    background: #0f172a;
    border-right: 1px solid #1e293b;
    padding: 24px 18px;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
  }
  nav.toc h2 { font-size: 13px; color: #22d3ee; text-transform: uppercase; margin: 0 0 12px; letter-spacing: 0.5px; }
  nav.toc a {
    display: block;
    color: #94a3b8;
    text-decoration: none;
    padding: 8px 10px;
    border-radius: 4px;
    font-size: 13px;
    margin-bottom: 2px;
  }
  nav.toc a:hover { background: #1e293b; color: #f1f5f9; }
  main { flex: 1; padding: 40px 56px; max-width: 1100px; }
  h1 { color: #f1f5f9; border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-top: 48px; font-size: 28px; }
  h1:first-child { margin-top: 0; }
  h2 { color: #22d3ee; margin-top: 32px; font-size: 22px; }
  h3 { color: #a78bfa; font-size: 18px; }
  a { color: #60a5fa; }
  a:hover { color: #93c5fd; }
  code { background: #1e293b; padding: 2px 6px; border-radius: 3px; color: #fbbf24; font-size: 13px; }
  pre { background: #1e293b; padding: 14px; border-radius: 6px; overflow-x: auto; border-left: 3px solid #3b82f6; }
  pre code { background: transparent; padding: 0; }
  blockquote { border-left: 3px solid #fbbf24; background: #1e293b; padding: 8px 16px; margin: 16px 0; color: #cbd5e1; }
  table { border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 13px; }
  th, td { border: 1px solid #334155; padding: 8px 12px; text-align: left; vertical-align: top; }
  th { background: #1e293b; color: #22d3ee; }
  tr:nth-child(even) td { background: #0f172a; }
  ul, ol { padding-left: 24px; }
  li { margin: 4px 0; }
  hr { border: none; border-top: 1px solid #334155; margin: 32px 0; }
  .section { padding-bottom: 24px; border-bottom: 1px solid #1e293b; margin-bottom: 24px; }
  header.top { background: linear-gradient(90deg,#1e3a8a,#0e7490); padding: 24px 56px; }
  header.top h1 { border: none; margin: 0; color: #f1f5f9; font-size: 32px; }
  header.top .meta { color: #cbd5e1; font-size: 13px; margin-top: 4px; }
`;

let body = `<header class="top"><h1>Enriquez<span style="color:#22d3ee">2.0</span> — ${today}</h1><div class="meta">All outputs · brief · scout · opportunities · audits · inboxes</div></header>`;
let toc = "";
const tocItems: Array<[string, string]> = [];

for (const s of sections) {
  const fp = path.join(SB_ROOT, s.file);
  if (!fs.existsSync(fp)) continue;
  const md = fs.readFileSync(fp, "utf8");
  const html = marked.parse(md, { async: false }) as string;
  const id = s.title.toLowerCase().replace(/[^a-z0-9]+/g, "-");
  tocItems.push([id, s.title]);
  body += `<main><section class="section" id="${id}"><h1>${s.title}</h1><div class="meta" style="color:#64748b;font-size:12px;margin-bottom:16px;">${s.file}</div>${html}</section></main>`;
}

toc = `<nav class="toc"><h2>Sections</h2>${tocItems.map(([id, t]) => `<a href="#${id}">${t}</a>`).join("")}</nav>`;

const fullHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Enriquez2.0 — ${today}</title><style>${css}</style></head><body><div class="layout">${toc}<div style="flex:1">${body}</div></div></body></html>`;

const outDir = path.join(SB_ROOT, "briefs");
const outFile = path.join(outDir, `${today}.html`);
fs.writeFileSync(outFile, fullHtml);
console.log(`[render] wrote briefs/${today}.html (${fullHtml.length} chars)`);
