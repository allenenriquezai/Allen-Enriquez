#!/usr/bin/env python3
"""Generate libass karaoke-style subtitles from word-level transcript."""
import json
import re
from pathlib import Path

ROOT = Path("/Users/allenenriquez/Developer/Allen-Enriquez/projects/personal/videos/reel-7-are-you-tired-of-ai-emails")
WORDS_PATH = ROOT / "transcripts" / "words.json"
OUT_PATH = ROOT / "render" / "captions.ass"

MAX_WORDS_PER_LINE = 5
HARD_BREAK = set(".!?")
SOFT_BREAK = set(",:;")
GAP_EXTEND_THRESHOLD = 0.25  # seconds

HERO_WORDS = {
    "BOT", "5", "MINUTES", "GENERIC", "VOICE",
    "STEP", "1", "2", "3", "4", "6",
    "SENT", "EMAILS", "CHATGPT", "PROMPT", "PROJECT", "INSTRUCTIONS", "GPT",
    "SOUNDS", "MACHINE", "YOU",
    "NOW", "FOLLOW", "TIPS",
}

ACCENT = "&HF2B34E&"
WHITE = "&HFFFFFF&"


def load_words():
    with open(WORDS_PATH) as f:
        raw = json.load(f)
    words = []
    for w in raw:
        txt = w["word"].lstrip()  # strip leading space
        words.append({"word": txt, "start": float(w["start"]), "end": float(w["end"])})
    return words


def chunk_lines(words):
    """Group words into lines of max 5 words, respecting phrase boundaries."""
    lines = []
    current = []
    for w in words:
        current.append(w)
        bare = re.sub(r"[^\w]", "", w["word"])
        last_char = w["word"][-1] if w["word"] else ""
        hard = last_char in HARD_BREAK
        soft = last_char in SOFT_BREAK

        should_break = False
        if hard:
            should_break = True
        elif len(current) >= MAX_WORDS_PER_LINE:
            should_break = True
        elif len(current) >= 4 and soft:
            should_break = True

        if should_break:
            lines.append(current)
            current = []
    if current:
        lines.append(current)
    return lines


def extend_line_ends(lines):
    """If gap between consecutive lines is small, extend previous line's end."""
    for i in range(len(lines) - 1):
        cur_end = lines[i][-1]["end"]
        nxt_start = lines[i + 1][0]["start"]
        gap = nxt_start - cur_end
        if 0 < gap < GAP_EXTEND_THRESHOLD:
            # bump the last word's end to next line start
            lines[i][-1]["end"] = nxt_start


def fmt_time(seconds):
    """Format seconds to H:MM:SS.CS (centiseconds)."""
    total_cs = int(round(seconds * 100))
    h = total_cs // 360000
    total_cs %= 360000
    m = total_cs // 6000
    total_cs %= 6000
    s = total_cs // 100
    cs = total_cs % 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def hero_match(word_text):
    """Strip punctuation, uppercase, compare to HERO_WORDS."""
    bare = re.sub(r"[^\w]", "", word_text).upper()
    return bare in HERO_WORDS


def build_dialogue_text(line_words):
    """Build the karaoke text with per-word \\k and hero color overrides.

    Hero words get persistent accent color (locked via \\c override).
    For hero words we emit: {\\kXX\\c&HF2B34E&}WORD  (no reset, so it stays)
    Normal words that follow a hero need to be reset to white: {\\kXX\\c&HFFFFFF&}word
    But karaoke highlighting (SecondaryColour → PrimaryColour transition on \\k)
    works off the style's primary. Using \\c locks the primary for that span.
    Strategy: emit hero words with \\c accent (sticks). Track state so the next
    non-hero word resets to white.
    """
    parts = []
    current_color_is_accent = False
    for w in line_words:
        txt = w["word"]
        dur_cs = max(1, int(round((w["end"] - w["start"]) * 100)))
        is_hero = hero_match(txt)
        tags = [f"\\k{dur_cs}"]
        if is_hero:
            if not current_color_is_accent:
                tags.append(f"\\c{ACCENT}")
            current_color_is_accent = True
        else:
            if current_color_is_accent:
                tags.append(f"\\c{WHITE}")
            current_color_is_accent = False
        tag_str = "{" + "".join(tags) + "}"
        parts.append(f"{tag_str}{txt}")
    # If line ends with hero-accent active, reset at end to prevent bleed
    line_text = " ".join(parts)
    return line_text


HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat,90,&H00FFFFFF,&H00F2B34E,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,0,2,80,80,280,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def main():
    words = load_words()
    lines = chunk_lines(words)
    extend_line_ends(lines)

    dialogue_lines = []
    for line in lines:
        start = fmt_time(line[0]["start"])
        end = fmt_time(line[-1]["end"])
        text = build_dialogue_text(line)
        dialogue_lines.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
        )

    out = HEADER + "\n".join(dialogue_lines) + "\n"
    OUT_PATH.write_text(out, encoding="utf-8")

    print(f"Wrote {OUT_PATH}")
    print(f"Words: {len(words)}  Lines: {len(lines)}")
    print("--- First 3 dialogue lines ---")
    for dl in dialogue_lines[:3]:
        print(dl)


if __name__ == "__main__":
    main()
