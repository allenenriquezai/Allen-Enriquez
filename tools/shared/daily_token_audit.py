#!/usr/bin/env python3
"""Daily token-cost audit. Runs ccusage, writes report, flags anomalies."""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
REPORT_DIR = ROOT / ".tmp" / "token-audit"
MEMORY_DIR = Path.home() / ".claude" / "projects" / "-Users-allenenriquez-Desktop-Allen-Enriquez" / "memory"
SKILLS_DIR = ROOT / ".claude" / "skills"

# PH timezone
PH_TZ = timezone(timedelta(hours=8))

# Thresholds that trigger report alerts
DAILY_SPEND_ALERT = 80.00       # $USD
OPUS_PCT_ALERT = 90             # Opus > this % of spend
SPEND_DOUBLED_VS_YESTERDAY = 1.8  # multiplier
SKILL_BODY_MAX_KB = 5           # any SKILL.md larger = flag

REPORT_DIR.mkdir(parents=True, exist_ok=True)


def run_ccusage(days_back: int = 8) -> dict:
    """Run ccusage daily JSON for the last N days. Returns parsed data."""
    since = (datetime.now(PH_TZ) - timedelta(days=days_back)).strftime("%Y%m%d")
    result = subprocess.run(
        ["npx", "ccusage@latest", "daily", "--since", since, "--breakdown", "--json"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ccusage failed: {result.stderr}")
    return json.loads(result.stdout)


def count_skills_over_size() -> list[tuple[str, int]]:
    """Return list of (skill_name, kb) for skills with SKILL.md > threshold."""
    oversized = []
    if not SKILLS_DIR.exists():
        return oversized
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        kb = skill_md.stat().st_size / 1024
        if kb > SKILL_BODY_MAX_KB:
            oversized.append((skill_dir.name, round(kb, 1)))
    return sorted(oversized, key=lambda x: -x[1])


def count_memory_files() -> int:
    if not MEMORY_DIR.exists():
        return 0
    return len(list(MEMORY_DIR.glob("*.md")))


def analyze(data: dict) -> dict:
    days = data.get("daily", [])
    if not days:
        return {"error": "no data returned"}

    today_str = datetime.now(PH_TZ).strftime("%Y-%m-%d")
    yesterday_str = (datetime.now(PH_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")

    today = next((d for d in days if d["date"] == today_str), None)
    yesterday = next((d for d in days if d["date"] == yesterday_str), None)

    # Focus report on yesterday (complete day)
    focus = yesterday or today
    if not focus:
        return {"error": "no recent day found"}

    total_cost = focus["totalCost"]
    opus_cost = 0.0
    sonnet_cost = 0.0
    haiku_cost = 0.0
    for m in focus.get("modelBreakdowns", []):
        name = m["modelName"]
        c = m["cost"]
        if "opus" in name:
            opus_cost += c
        elif "sonnet" in name:
            sonnet_cost += c
        elif "haiku" in name:
            haiku_cost += c

    opus_pct = (opus_cost / total_cost * 100) if total_cost > 0 else 0

    prior_7 = [d for d in days if d["date"] < focus["date"]][-7:]
    avg_prior = (
        sum(d["totalCost"] for d in prior_7) / len(prior_7) if prior_7 else 0
    )

    spend_ratio = (total_cost / avg_prior) if avg_prior > 0 else 1.0

    alerts = []
    if total_cost >= DAILY_SPEND_ALERT:
        alerts.append(f"DAILY SPEND HIGH: ${total_cost:.2f}")
    if opus_pct >= OPUS_PCT_ALERT:
        alerts.append(f"OPUS DOMINANCE: {opus_pct:.0f}% of spend")
    if spend_ratio >= SPEND_DOUBLED_VS_YESTERDAY:
        alerts.append(
            f"SPEND SPIKE: {spend_ratio:.1f}x vs 7-day avg (${avg_prior:.2f})"
        )

    return {
        "date": focus["date"],
        "total_cost": total_cost,
        "opus_cost": opus_cost,
        "sonnet_cost": sonnet_cost,
        "haiku_cost": haiku_cost,
        "opus_pct": opus_pct,
        "avg_prior_7": avg_prior,
        "spend_ratio": spend_ratio,
        "alerts": alerts,
    }


def write_report(result: dict, oversized_skills: list, memory_count: int) -> Path:
    date_str = datetime.now(PH_TZ).strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{date_str}.md"

    lines = [
        f"# Token Audit — {date_str}",
        "",
        f"**Focus date:** {result.get('date', 'n/a')}",
        f"**Daily spend:** ${result.get('total_cost', 0):.2f}",
        f"**7-day avg:** ${result.get('avg_prior_7', 0):.2f}",
        f"**Spend ratio:** {result.get('spend_ratio', 0):.2f}x",
        "",
        "## Model breakdown",
        f"- Opus 4.7: ${result.get('opus_cost', 0):.2f} ({result.get('opus_pct', 0):.0f}%)",
        f"- Sonnet 4.6: ${result.get('sonnet_cost', 0):.2f}",
        f"- Haiku 4.5: ${result.get('haiku_cost', 0):.2f}",
        "",
        "## System health",
        f"- Memory files: {memory_count}",
        f"- Skills with body > {SKILL_BODY_MAX_KB}KB: {len(oversized_skills)}",
    ]
    if oversized_skills:
        for name, kb in oversized_skills:
            lines.append(f"  - `{name}` ({kb} KB)")

    lines.extend(["", "## Alerts"])
    if result.get("alerts"):
        for a in result["alerts"]:
            lines.append(f"- {a}")
    else:
        lines.append("- None")

    report_path.write_text("\n".join(lines) + "\n")
    return report_path


def main() -> int:
    try:
        data = run_ccusage(days_back=8)
    except Exception as e:
        print(f"ccusage error: {e}", file=sys.stderr)
        return 1

    result = analyze(data)
    if "error" in result:
        print(f"analysis error: {result['error']}", file=sys.stderr)
        return 1

    oversized = count_skills_over_size()
    mem_count = count_memory_files()
    report_path = write_report(result, oversized, mem_count)

    print(f"Report: {report_path}")
    print(f"Spend: ${result['total_cost']:.2f} | Opus: {result['opus_pct']:.0f}% | Alerts: {len(result['alerts'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
