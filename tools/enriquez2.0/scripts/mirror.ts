import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import { REPO_ROOT, SB_ROOT } from "../lib/env.js";

const SKIP_DIRS = new Set([
  "node_modules",
  ".git",
  ".next",
  "dist",
  "build",
  ".tmp",
  "raw",
  "__pycache__",
  ".venv",
  "venv",
  ".turbo",
  ".cache",
]);

interface DirSummary {
  path: string;
  files: number;
  subdirs: number;
  byExt: Record<string, number>;
}

function walkDir(dir: string, out: DirSummary[]): DirSummary {
  const summary: DirSummary = { path: path.relative(REPO_ROOT, dir) || ".", files: 0, subdirs: 0, byExt: {} };
  let entries: fs.Dirent[];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return summary;
  }
  for (const e of entries) {
    if (SKIP_DIRS.has(e.name) || e.name.startsWith(".")) continue;
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      summary.subdirs++;
      walkDir(full, out);
    } else if (e.isFile()) {
      summary.files++;
      const ext = path.extname(e.name).toLowerCase() || "(none)";
      summary.byExt[ext] = (summary.byExt[ext] ?? 0) + 1;
    }
  }
  out.push(summary);
  return summary;
}

function readJsonSafe<T>(p: string): T | null {
  try {
    return JSON.parse(fs.readFileSync(p, "utf8")) as T;
  } catch {
    return null;
  }
}

function indexPackages() {
  const tools = path.join(REPO_ROOT, "tools");
  const out: Array<{ name: string; path: string; deps: string[]; scripts: string[] }> = [];
  if (!fs.existsSync(tools)) return out;
  for (const sub of fs.readdirSync(tools, { withFileTypes: true })) {
    if (!sub.isDirectory()) continue;
    const pkgPath = path.join(tools, sub.name, "package.json");
    if (!fs.existsSync(pkgPath)) continue;
    const pkg = readJsonSafe<{ name?: string; dependencies?: Record<string, string>; scripts?: Record<string, string> }>(pkgPath);
    if (!pkg) continue;
    out.push({
      name: pkg.name ?? sub.name,
      path: path.relative(REPO_ROOT, pkgPath),
      deps: Object.keys(pkg.dependencies ?? {}),
      scripts: Object.keys(pkg.scripts ?? {}),
    });
  }
  return out;
}

function indexSkills() {
  const dirs = [
    path.join(REPO_ROOT, ".claude/skills"),
  ];
  const out: Array<{ name: string; path: string; description: string }> = [];
  for (const root of dirs) {
    if (!fs.existsSync(root)) continue;
    for (const sub of fs.readdirSync(root, { withFileTypes: true })) {
      if (!sub.isDirectory()) continue;
      const md = path.join(root, sub.name, "SKILL.md");
      if (!fs.existsSync(md)) continue;
      const txt = fs.readFileSync(md, "utf8");
      const desc = (txt.match(/^description:\s*(.+)$/m)?.[1] ?? "").slice(0, 200);
      out.push({ name: sub.name, path: path.relative(REPO_ROOT, md), description: desc });
    }
  }
  return out;
}

function indexAutomations() {
  const dir = path.join(REPO_ROOT, "automation");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".plist"))
    .map((f) => ({ name: f, path: path.relative(REPO_ROOT, path.join(dir, f)) }));
}

function indexProjects() {
  const dir = path.join(REPO_ROOT, "projects");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => {
      const ctx = path.join(dir, d.name, "CONTEXT.md");
      return { name: d.name, hasContext: fs.existsSync(ctx) };
    });
}

function indexClaudeMd() {
  const p = path.join(REPO_ROOT, "CLAUDE.md");
  if (!fs.existsSync(p)) return null;
  const txt = fs.readFileSync(p, "utf8");
  return { path: "CLAUDE.md", lines: txt.split("\n").length, bytes: txt.length };
}

function indexGitTracked() {
  try {
    const out = execSync("git ls-files", { cwd: REPO_ROOT, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
    const files = out.split("\n").filter(Boolean);
    const byExt: Record<string, number> = {};
    const byTopDir: Record<string, number> = {};
    const suspicious: string[] = [];
    const SUSPICIOUS_RX = /\.(db|db-shm|db-wal|sqlite|sqlite3|pickle|env|key|pem)$/i;
    const SUSPICIOUS_PATH_RX = /(renders\/(frames|caption-frames|frames-transparent)|\/node_modules\/|\.next\/)/;
    for (const f of files) {
      const ext = path.extname(f).toLowerCase() || "(none)";
      byExt[ext] = (byExt[ext] ?? 0) + 1;
      const top = f.split("/")[0];
      byTopDir[top] = (byTopDir[top] ?? 0) + 1;
      if (SUSPICIOUS_RX.test(f) || SUSPICIOUS_PATH_RX.test(f)) suspicious.push(f);
    }
    return {
      total: files.length,
      byExt,
      byTopDir,
      suspicious_tracked: suspicious.slice(0, 100),
      suspicious_count: suspicious.length,
    };
  } catch (e) {
    return { error: (e as Error).message };
  }
}

function indexGitignore() {
  const p = path.join(REPO_ROOT, ".gitignore");
  if (!fs.existsSync(p)) return null;
  const lines = fs.readFileSync(p, "utf8").split("\n").map((l) => l.trim()).filter((l) => l && !l.startsWith("#"));
  return { path: ".gitignore", patterns: lines };
}

function indexContentHubDb() {
  // Prefer canonical content-hub DB, fall back to root copy if present
  const candidates = [
    path.join(REPO_ROOT, "tools", "content-hub", "content_hub.db"),
    path.join(REPO_ROOT, "content-hub.db"),
  ];
  for (const p of candidates) {
    if (!fs.existsSync(p)) continue;
    const stat = fs.statSync(p);
    return { path: path.relative(REPO_ROOT, p), bytes: stat.size, modified: stat.mtime.toISOString() };
  }
  return null;
}

function runContentHubMirror() {
  try {
    execSync("tsx scripts/mirror-content.ts", { cwd: SB_ROOT, stdio: "inherit" });
  } catch (e) {
    console.error("[content-hub] mirror failed:", (e as Error).message);
  }
}

function main() {
  const dirs: DirSummary[] = [];
  walkDir(REPO_ROOT, dirs);
  dirs.sort((a, b) => b.files - a.files);

  const repoState = {
    generated_at: new Date().toISOString(),
    repo_root: REPO_ROOT,
    top_dirs: dirs.slice(0, 40),
    total_dirs: dirs.length,
    total_files: dirs.reduce((s, d) => s + d.files, 0),
    packages: indexPackages(),
    skills: indexSkills(),
    automations: indexAutomations(),
    projects: indexProjects(),
    claude_md: indexClaudeMd(),
    git_tracked: indexGitTracked(),
    gitignore: indexGitignore(),
  };
  fs.writeFileSync(path.join(SB_ROOT, "state/repo.json"), JSON.stringify(repoState, null, 2));
  const tracked = repoState.git_tracked && "total" in repoState.git_tracked ? repoState.git_tracked.total : 0;
  const sus = repoState.git_tracked && "suspicious_count" in repoState.git_tracked ? repoState.git_tracked.suspicious_count : 0;
  console.log(
    `[repo] ${repoState.total_files} files on disk, ${tracked} tracked (${sus} suspicious), ${repoState.packages.length} packages, ${repoState.skills.length} skills, ${repoState.automations.length} automations`,
  );

  const contentState = {
    generated_at: new Date().toISOString(),
    db: indexContentHubDb(),
  };
  fs.writeFileSync(path.join(SB_ROOT, "state/content.json"), JSON.stringify(contentState, null, 2));
  console.log(`[content] db indexed: ${contentState.db?.bytes ?? 0} bytes`);

  const automationsState = {
    generated_at: new Date().toISOString(),
    plists: indexAutomations(),
  };
  fs.writeFileSync(path.join(SB_ROOT, "state/automations.json"), JSON.stringify(automationsState, null, 2));
  console.log(`[automations] ${automationsState.plists.length} plists`);

  runContentHubMirror();
}

main();
