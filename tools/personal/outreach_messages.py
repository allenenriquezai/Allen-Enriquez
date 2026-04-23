"""PH outreach message generator — template loader, Haiku renderer, queue formatter."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

import anthropic

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "projects" / "personal" / "templates" / "outreach"

HAIKU_MODEL = "claude-haiku-4-5-20251001"
HAIKU_TEMPERATURE = 0.7
HAIKU_MAX_TOKENS = 500

MAX_WORDS_PER_SENTENCE = 15

_SEGMENT_TO_PREFIX = {
    "recruitment": "recruitment",
    "real_estate": "realestate",
    "realestate": "realestate",
}

_CHANNEL_TO_SLUG = {
    "email": "email",
    "fb": "fb",
    "facebook": "fb",
    "fb_dm": "fb",
}


def banned_words() -> set[str]:
    return {
        "leverage",
        "utilize",
        "synergy",
        "optimize",
        "paradigm",
        "scalable",
        "ecosystem",
        "ideate",
        "disrupt",
        "holistic",
        "pivot",
        "bandwidth",
        "deep-dive",
        "deep dive",
        "circle back",
        "low-hanging fruit",
        "value-add",
        "value add",
        "stakeholder",
    }


def _template_path(segment: str, channel: str, touch: int) -> Path:
    seg = _SEGMENT_TO_PREFIX.get(segment.lower().strip())
    chan = _CHANNEL_TO_SLUG.get(channel.lower().strip())
    if not seg:
        raise ValueError(f"Unknown segment: {segment}")
    if not chan:
        raise ValueError(f"Unknown channel: {channel}")
    if touch not in (1, 2, 3):
        raise ValueError(f"Touch must be 1, 2, or 3. Got: {touch}")
    return TEMPLATE_DIR / f"{seg}_{chan}_t{touch}.md"


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    fm_raw, body = parts[1], parts[2]
    fm: dict = {}
    current_list_key: Optional[str] = None
    for line in fm_raw.splitlines():
        if not line.strip():
            current_list_key = None
            continue
        if line.lstrip().startswith("- ") and current_list_key:
            fm[current_list_key].append(line.lstrip()[2:].strip())
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                fm[key] = []
                current_list_key = key
            else:
                current_list_key = None
                if val.isdigit():
                    fm[key] = int(val)
                else:
                    fm[key] = val.strip('"').strip("'")
    return fm, body.lstrip("\n")


def load_template(segment: str, channel: str, touch: int) -> dict:
    path = _template_path(segment, channel, touch)
    raw = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(raw)
    return {"frontmatter": fm, "body": body}


def _split_subject_body(text: str) -> tuple[Optional[str], str]:
    lines = text.splitlines()
    subject: Optional[str] = None
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper().startswith("SUBJECT:"):
            subject = stripped.split(":", 1)[1].strip()
            body_start = i + 1
        break
    body = "\n".join(lines[body_start:]).lstrip("\n")
    return subject, body


def _sentence_word_counts(text: str) -> list[int]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+|\n+", cleaned)
    counts = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        words = re.findall(r"[A-Za-z0-9'\-]+", s)
        if words:
            counts.append(len(words))
    return counts


def _contains_banned(text: str) -> Optional[str]:
    lower = text.lower()
    for word in banned_words():
        pattern = r"\b" + re.escape(word) + r"\b"
        if re.search(pattern, lower):
            return word
    return None


def _validate_body(body: str) -> tuple[bool, str]:
    bad = _contains_banned(body)
    if bad:
        return False, f"banned_word:{bad}"
    counts = _sentence_word_counts(body)
    for c in counts:
        if c > MAX_WORDS_PER_SENTENCE:
            return False, f"long_sentence:{c}_words"
    return True, "ok"


def _fallback_fill(body: str, prospect: dict, segment_cfg: dict) -> str:
    pain_points = segment_cfg.get("pain_points") or []
    tokens = {
        "first_name": (prospect.get("Name") or prospect.get("first_name") or "").split()[0] if (prospect.get("Name") or prospect.get("first_name")) else "there",
        "company": prospect.get("Company") or prospect.get("company") or "your team",
        "personal_hook_reference": prospect.get("Personal Hook") or prospect.get("personal_hook") or "",
        "pain_point": pain_points[0] if pain_points else "",
        "offer_line": segment_cfg.get("offer_line") or "",
    }
    out = body
    for key, val in tokens.items():
        out = out.replace("{" + key + "}", str(val))
    lines = [ln for ln in out.splitlines() if ln.strip() or not tokens["personal_hook_reference"]]
    return "\n".join(lines).strip() + "\n"


def _build_system_prompt() -> str:
    return (
        "You are Allen Enriquez writing a cold outreach message. "
        "Allen is a sales manager at EPS Painting who built an AI sales system using Claude Code. "
        "He now helps PH service businesses set up the same. "
        "Voice rules — NON-NEGOTIABLE:\n"
        "- 3rd grade reading level. If a 9-year-old can't understand it, rewrite.\n"
        "- Max 10 words per sentence. Hard cap at 15 words.\n"
        "- No jargon. No corporate speak. No filler.\n"
        "- Confident but not arrogant. Direct. Say what you mean.\n"
        "- Use 'you' and 'I'. Never 'we' or 'one'.\n"
        "- Never use these words: leverage, utilize, synergy, optimize, paradigm, "
        "scalable, ecosystem, ideate, disrupt, holistic, pivot, bandwidth, "
        "deep-dive, circle back, low-hanging fruit, value-add, stakeholder.\n"
        "- No emojis. Ever.\n"
        "Preserve the INTENT of the template skeleton, but sound like a real human "
        "wrote it — not a template. Vary phrasing. Do not invent facts about the "
        "prospect. If the personal hook is empty, skip that sentence — never "
        "fabricate one. Fill token variables from the prospect facts. Output ONLY "
        "the final message. No commentary, no preamble, no explanation."
    )


def _build_user_prompt(
    template_body: str,
    frontmatter: dict,
    prospect: dict,
    segment_cfg: dict,
    channel: str,
    touch: int,
) -> str:
    first_name = ""
    name_raw = prospect.get("Name") or prospect.get("first_name") or ""
    if name_raw:
        first_name = name_raw.split()[0]
    company = prospect.get("Company") or prospect.get("company") or ""
    hook = prospect.get("Personal Hook") or prospect.get("personal_hook") or ""
    pain_points = segment_cfg.get("pain_points") or []
    offer_line = segment_cfg.get("offer_line") or ""
    lead_magnet = segment_cfg.get("lead_magnet") or ""

    goal = frontmatter.get("goal", "")
    reminders = frontmatter.get("voice_reminders", [])
    reminder_text = "\n".join(f"- {r}" for r in reminders) if reminders else ""

    channel_label = "email" if channel == "email" else "Facebook DM"
    subject_rule = (
        "Start with a line 'SUBJECT: <subject>' (under 60 chars, no ALL CAPS). "
        "Then blank line. Then the body."
        if channel == "email"
        else "No subject line. Body only."
    )

    prospect_facts = (
        f"- First name: {first_name or '(unknown — use a safe neutral opener)'}\n"
        f"- Company: {company or '(unknown)'}\n"
        f"- Personal hook reference: {hook or '(none — SKIP that sentence, do not invent)'}"
    )

    segment_facts = (
        f"- Segment offer line: {offer_line}\n"
        f"- Pain points (pick the one that fits best, or rotate for variety): "
        f"{pain_points}\n"
        f"- Lead magnet (if needed): {lead_magnet}"
    )

    return (
        f"Channel: {channel_label}\n"
        f"Touch: {touch}\n"
        f"Goal of this message: {goal}\n\n"
        f"VOICE REMINDERS FOR THIS TOUCH:\n{reminder_text}\n\n"
        f"PROSPECT FACTS:\n{prospect_facts}\n\n"
        f"SEGMENT FACTS:\n{segment_facts}\n\n"
        f"TEMPLATE SKELETON (rewrite in Allen's voice — do NOT copy verbatim):\n"
        f"---\n{template_body.strip()}\n---\n\n"
        f"FORMAT RULE: {subject_rule}\n\n"
        f"Output the final message only. No commentary."
    )


def _call_haiku(api_key: str, system: str, user: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=HAIKU_MAX_TOKENS,
        temperature=HAIKU_TEMPERATURE,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def render_message(
    prospect: dict,
    segment_cfg: dict,
    channel: str,
    touch: int,
    anthropic_api_key: str,
) -> dict:
    segment = segment_cfg.get("segment") or segment_cfg.get("key") or ""
    if not segment:
        if "recruitment" in (segment_cfg.get("label", "").lower()):
            segment = "recruitment"
        elif "real estate" in (segment_cfg.get("label", "").lower()):
            segment = "real_estate"
        else:
            segment = prospect.get("segment") or prospect.get("Segment") or "recruitment"

    tpl = load_template(segment, channel, touch)
    frontmatter = tpl["frontmatter"]
    body_skeleton = tpl["body"]

    system = _build_system_prompt()
    user = _build_user_prompt(body_skeleton, frontmatter, prospect, segment_cfg, channel, touch)

    subject: Optional[str] = None
    body: str = ""
    try:
        raw = _call_haiku(anthropic_api_key, system, user)
    except Exception:
        raw = ""

    if raw:
        if channel == "email":
            subject, body = _split_subject_body(raw)
        else:
            subject, body = None, raw.strip()

        ok, _ = _validate_body(body)
        if not ok:
            try:
                retry_user = user + "\n\nYour last output broke a voice rule. Rewrite. Shorter sentences. No banned words. No jargon."
                raw2 = _call_haiku(anthropic_api_key, system, retry_user)
                if channel == "email":
                    subject, body = _split_subject_body(raw2)
                else:
                    subject, body = None, raw2.strip()
                ok2, _ = _validate_body(body)
                if not ok2:
                    raise ValueError("retry failed validation")
            except Exception:
                body = ""

    if not body:
        filled = _fallback_fill(body_skeleton, prospect, segment_cfg)
        if channel == "email":
            subject, body = _split_subject_body(filled)
        else:
            subject, body = None, filled.strip()

    return {"subject": subject, "body": body.strip() + "\n"}


def generate_queue_markdown(queue: list[dict], limits: dict) -> str:
    today = date.today().isoformat()
    email_items = [q for q in queue if q.get("channel") == "email"]
    fb_items = [q for q in queue if q.get("channel") in ("fb", "facebook", "fb_dm")]

    email_limit = limits.get("email_per_day", "?")
    fb_limit = limits.get("fb_dm_per_day", "?")

    lines: list[str] = []
    lines.append(f"# PH Outreach Queue — {today}")
    lines.append(
        f"Emails: {len(email_items)} / {email_limit} limit | "
        f"FB DMs: {len(fb_items)} / {fb_limit} limit"
    )
    lines.append(
        "Send top to bottom. Run `python3 tools/outreach.py log-sent --ids X,Y,Z` when done."
    )
    lines.append("")

    counter = 0

    if email_items:
        lines.append("---")
        lines.append("## EMAILS")
        for item in email_items:
            counter += 1
            lines.extend(_format_entry(counter, item))

    if fb_items:
        lines.append("---")
        lines.append("## FB DMs")
        for item in fb_items:
            counter += 1
            lines.extend(_format_entry(counter, item))

    lines.append("---")
    lines.append("## Log-sent checklist")
    all_ids = [str(q.get("row_num")) for q in queue if q.get("row_num") is not None]
    for item in queue:
        rn = item.get("row_num")
        touch = item.get("touch")
        ch = "EMAIL" if item.get("channel") == "email" else "FB"
        name = (item.get("prospect") or {}).get("Name", "")
        lines.append(f"- [ ] Row {rn} — {ch} T{touch} — {name}")
    if all_ids:
        lines.append("")
        lines.append(f"Copy-paste: `--ids {','.join(all_ids)}`")

    return "\n".join(lines) + "\n"


def _format_entry(counter: int, item: dict) -> list[str]:
    prospect = item.get("prospect") or {}
    channel = item.get("channel")
    touch = item.get("touch")
    row_num = item.get("row_num")
    subject = item.get("subject")
    body = item.get("body") or ""

    name = prospect.get("Name") or ""
    company = prospect.get("Company") or ""
    email_addr = prospect.get("Email") or ""
    fb_url = prospect.get("FB URL") or prospect.get("FB Profile") or ""

    channel_label = "EMAIL" if channel == "email" else "FB DM"

    out: list[str] = []
    out.append("")
    out.append(f"## {counter}. {channel_label} T{touch} — Row {row_num}")
    if name or company:
        out.append(f"Prospect: {name}{' — ' + company if company else ''}")
    if channel == "email":
        if email_addr:
            out.append(f"To: {email_addr}")
        if subject:
            out.append(f"Subject: {subject}")
    else:
        if fb_url:
            out.append(f"Profile: [{fb_url}]({fb_url})")
    out.append("")
    out.append(body.rstrip())
    out.append("")
    if fb_url and channel == "email":
        out.append(f"[Copy prospect profile link]({fb_url})")
    out.append("---")
    return out
