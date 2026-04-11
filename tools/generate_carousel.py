#!/usr/bin/env python3
"""
Carousel image generator for Allen's personal brand.
Generates slide PNGs using Hormozi-style copy (3rd grade, bold claims, short sentences).

Usage:
    python3 tools/generate_carousel.py --topic "AI won't replace you" --slides 7 --style dark --handle "@allenenriquez"
    python3 tools/generate_carousel.py --topic "Stop chasing leads" --slides 5 --style light

Output: .tmp/carousels/<topic-slug>/slide_01.png, slide_02.png, ...
"""

from __future__ import annotations

import argparse
import os
import re
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# --- Config ---

WIDTH = 1080
HEIGHT = 1080

STYLES = {
    "dark": {"bg": (0, 0, 0), "text": (255, 255, 255), "accent": (200, 200, 200)},
    "light": {"bg": (255, 255, 255), "text": (0, 0, 0), "accent": (80, 80, 80)},
}

# macOS system fonts — fallback chain
FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Arial.ttf",
]

# --- Slide copy templates ---
# Hook patterns from Hormozi style guide
HOOK_PATTERNS = [
    "Most {audience} get this wrong.",
    "Stop doing this. Seriously.",
    "{number} things that actually work.",
    "I tried this. Here's what happened.",
    "Everyone says {common}. They're wrong.",
    "This one change made all the difference.",
]

CTA_TEMPLATES = [
    "Save this. Share it.\nFollow for more.",
    "Tag someone who needs this.",
    "Follow for daily tips\nthat actually work.",
    "Save this post.\nCome back when you're ready.",
    "Share this with someone\nwho's stuck.",
]


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a system font at the given size."""
    for path in FONT_PATHS:
        try:
            # .ttc files have multiple faces — index 0 is regular, 1 is bold (usually)
            index = 1 if bold and path.endswith(".ttc") else 0
            return ImageFont.truetype(path, size, index=index)
        except (OSError, IndexError):
            continue
    # absolute fallback
    return ImageFont.load_default()


def slugify(text: str) -> str:
    """Convert topic to filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)
    return lines


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    color: tuple,
    max_width: int,
    y_center: int,
    line_spacing: int = 20,
) -> int:
    """Draw word-wrapped, horizontally centered text around a vertical center point. Returns bottom y."""
    lines = wrap_text(draw, text, font, max_width)
    if not lines:
        return y_center

    # Calculate total height
    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])

    total_height = sum(line_heights) + line_spacing * (len(lines) - 1)
    y = y_center - total_height // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        draw.text((x, y), line, fill=color, font=font)
        y += line_heights[i] + line_spacing

    return y


def render_slide(
    text: str,
    style: dict,
    slide_num: int,
    total: int,
    handle: str = "",
    is_title: bool = False,
    is_cta: bool = False,
) -> Image.Image:
    """Render a single carousel slide as a PIL Image."""
    img = Image.new("RGB", (WIDTH, HEIGHT), style["bg"])
    draw = ImageDraw.Draw(img)

    padding = 80
    max_text_width = WIDTH - padding * 2

    if is_title:
        # Title slide — big bold text + handle at bottom
        title_font = get_font(72, bold=True)
        draw_centered_text(draw, text, title_font, style["text"], max_text_width, HEIGHT // 2 - 40)

        if handle:
            handle_font = get_font(32)
            bbox = draw.textbbox((0, 0), handle, font=handle_font)
            hw = bbox[2] - bbox[0]
            draw.text(((WIDTH - hw) // 2, HEIGHT - 140), handle, fill=style["accent"], font=handle_font)

    elif is_cta:
        # CTA slide — medium bold text
        cta_font = get_font(56, bold=True)
        draw_centered_text(draw, text, cta_font, style["text"], max_text_width, HEIGHT // 2)

        if handle:
            handle_font = get_font(32)
            bbox = draw.textbbox((0, 0), handle, font=handle_font)
            hw = bbox[2] - bbox[0]
            draw.text(((WIDTH - hw) // 2, HEIGHT - 140), handle, fill=style["accent"], font=handle_font)

    else:
        # Content slide — slide number + text
        num_font = get_font(28)
        num_text = f"{slide_num - 1}/{total - 2}"
        bbox = draw.textbbox((0, 0), num_text, font=num_font)
        nw = bbox[2] - bbox[0]
        draw.text(((WIDTH - nw) // 2, 60), num_text, fill=style["accent"], font=num_font)

        body_font = get_font(60, bold=True)
        draw_centered_text(draw, text, body_font, style["text"], max_text_width, HEIGHT // 2)

    # Swipe indicator dots at bottom
    dot_y = HEIGHT - 60
    dot_spacing = 20
    dot_r = 6
    total_dot_width = total * dot_r * 2 + (total - 1) * dot_spacing
    start_x = (WIDTH - total_dot_width) // 2

    for i in range(total):
        cx = start_x + i * (dot_r * 2 + dot_spacing) + dot_r
        if i == slide_num - 1:
            draw.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=style["text"])
        else:
            draw.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=style["accent"])

    return img


def generate_copy(topic: str, num_slides: int) -> list[str]:
    """Generate slide copy for a carousel. Returns list of strings, one per slide."""
    slides = []

    # Slide 1 — hook/title
    slides.append(topic.upper())

    # Middle slides — one idea per slide, max 15 words, simple language
    # These are placeholder prompts — in production, an LLM agent would write these
    # For now, generate simple structural placeholders the user fills in
    content_count = num_slides - 2  # minus title and CTA

    prompts = [
        f"[Slide {i+1}] Write your point here. Max 15 words. One idea only."
        for i in range(content_count)
    ]

    slides.extend(prompts)

    # Last slide — CTA
    import random
    slides.append(random.choice(CTA_TEMPLATES))

    return slides


def generate_carousel(
    topic: str,
    num_slides: int,
    style_name: str = "dark",
    handle: str = "",
    copy: list[str] | None = None,
) -> Path:
    """Generate all carousel slides and save to .tmp/carousels/<slug>/."""
    style = STYLES[style_name]
    slug = slugify(topic)

    # Output dir
    base = Path(__file__).resolve().parent.parent / ".tmp" / "carousels" / slug
    base.mkdir(parents=True, exist_ok=True)

    # Generate copy if not provided
    if copy is None:
        copy = generate_copy(topic, num_slides)

    if len(copy) != num_slides:
        raise ValueError(f"Expected {num_slides} slide texts, got {len(copy)}")

    for i, text in enumerate(copy):
        slide_num = i + 1
        is_title = (slide_num == 1)
        is_cta = (slide_num == num_slides)

        img = render_slide(
            text=text,
            style=style,
            slide_num=slide_num,
            total=num_slides,
            handle=handle,
            is_title=is_title,
            is_cta=is_cta,
        )

        path = base / f"slide_{slide_num:02d}.png"
        img.save(path, "PNG")
        print(f"  [{slide_num}/{num_slides}] {path}")

    # Also write copy to a text file for easy editing
    copy_path = base / "copy.txt"
    with open(copy_path, "w") as f:
        for i, text in enumerate(copy):
            f.write(f"--- Slide {i+1} ---\n{text}\n\n")
    print(f"  Copy saved to {copy_path}")

    return base


def main():
    parser = argparse.ArgumentParser(description="Generate carousel slide PNGs")
    parser.add_argument("--topic", required=True, help="Carousel topic / hook text")
    parser.add_argument("--slides", type=int, default=7, help="Number of slides (default: 7)")
    parser.add_argument("--style", choices=["dark", "light"], default="dark", help="dark or light (default: dark)")
    parser.add_argument("--handle", default="", help="Social handle shown on title/CTA slides")
    parser.add_argument(
        "--copy-file",
        default=None,
        help="Path to a text file with slide copy (one section per slide, separated by '--- Slide N ---')",
    )

    args = parser.parse_args()

    if args.slides < 3:
        parser.error("Need at least 3 slides (title + 1 content + CTA)")

    # Load custom copy if provided
    copy = None
    if args.copy_file:
        with open(args.copy_file) as f:
            raw = f.read()
        # Parse sections split by --- Slide N ---
        sections = re.split(r"---\s*Slide\s*\d+\s*---\n?", raw)
        copy = [s.strip() for s in sections if s.strip()]

    print(f"\nGenerating {args.slides}-slide carousel: \"{args.topic}\"")
    print(f"Style: {args.style} | Handle: {args.handle or '(none)'}\n")

    output = generate_carousel(
        topic=args.topic,
        num_slides=args.slides,
        style_name=args.style,
        handle=args.handle,
        copy=copy,
    )

    print(f"\nDone. Files in: {output}/")
    print("Edit copy.txt, then re-run with --copy-file to regenerate with your text.")


if __name__ == "__main__":
    main()
