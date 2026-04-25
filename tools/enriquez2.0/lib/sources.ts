import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";
import { SB_ROOT } from "./env.js";
import type { Domain } from "./identity.js";

export interface SourcesConfig {
  rss?: string[];
  github_releases?: string[];
  reddit?: { hot_threshold?: number; subreddits?: string[] };
  youtube?: string[];
}

export function loadSources(domain: Domain): SourcesConfig {
  const p = path.join(SB_ROOT, "domains", domain, "sources.yaml");
  if (!fs.existsSync(p)) return {};
  return YAML.parse(fs.readFileSync(p, "utf8")) as SourcesConfig;
}

export interface RawItem {
  id: string;
  source: string;
  title: string;
  url: string;
  content: string;
  published_at: string;
}
