import fs from "node:fs";
import path from "node:path";
import { SB_ROOT } from "./env.js";

const FILES = ["who-i-am.md", "becoming.md", "q2-2026.md", "values.md", "non-negotiables.md"];

export function loadIdentity(): string {
  const parts: string[] = [];
  for (const f of FILES) {
    const p = path.join(SB_ROOT, "identity", f);
    if (fs.existsSync(p)) {
      parts.push(`=== ${f} ===\n${fs.readFileSync(p, "utf8")}`);
    }
  }
  return parts.join("\n\n");
}

export const DOMAIN_DEFINITIONS = {
  build: "How we ship better. Repo structure, Claude Code usage, automation patterns, AI/LLM tooling adoption, dev workflow, agent design.",
  reach: "How we grow audience and clients. Content creation, hooks, short-form video, posting cadence, platform algorithms (TikTok/Reels/Shorts/YouTube), creator strategy.",
  serve: "How we turn audience into paid clients. Offers, pricing, sales delivery SOPs, client onboarding, lead magnets, productized services, consultancy ops.",
} as const;

export type Domain = keyof typeof DOMAIN_DEFINITIONS;
