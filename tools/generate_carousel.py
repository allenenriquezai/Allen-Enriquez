#!/usr/bin/env python3
"""
Carousel image generator for Allen's personal brand.
Hormozi-style: white background, bold black text, brand blue accent, clean layout.

Usage:
    python3 tools/generate_carousel.py --topic "4 Levels of AI" --slides 6 --handle "@allenenriquez"
    python3 tools/generate_carousel.py --topic "Stop chasing leads" --slides 5 --copy-file copy.txt

Output: projects/personal/content/carousels/<topic-slug>/slide_01.png, slide_02.png, ...

Copy file format (one section per slide, separated by --- Slide N ---):
    Use || to split header from body text on any slide.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- Config ---

WIDTH = 1080
HEIGHT = 1350  # 4:5 ratio — optimal for IG/FB feed

BRAND_BLUE = (2, 179, 233)  # #02B3E9

# Profile header
PROFILE_PHOTO_PATH = Path(__file__).resolve().parent.parent / "projects" / "personal" / "assets" / "profile.png"
PROFILE_NAME = "Allen Enriquez"
PROFILE_HANDLE = "@allenenriquezz"
PROFILE_PHOTO_SIZE = 100  # diameter
PROFILE_BORDER_WIDTH = 5

# Colors
BG = (255, 255, 255)
TEXT_PRIMARY = (15, 15, 15)       # near-black
TEXT_SECONDARY = (80, 80, 80)     # dark gray for body
TEXT_MUTED = (160, 160, 160)      # light gray for counters/handle
ACCENT = BRAND_BLUE
ACCENT_BAR_HEIGHT = 8

# Layout
PADDING_X = 100
PADDING_TOP = 120
PADDING_BOTTOM = 120
MAX_TEXT_WIDTH = WIDTH - PADDING_X * 2

# Font paths — clean bold sans-serif (Dan Martell / Hormozi style)
# Helvetica Bold for both header and body — clean, large, readable
FONT_HEADER_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Arial.ttf",
]
FONT_BODY_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/Arial.ttf",
]


def load_font(paths: list[str], size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load first available font from path list."""
    for path in paths:
        try:
            index = 1 if bold and path.endswith(".ttc") else 0
            return ImageFont.truetype(path, size, index=index)
        except (OSError, IndexError):
            continue
    return ImageFont.load_default()


def slugify(text: str) -> str:
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


def draw_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    color: tuple,
    max_width: int,
    y_start: int,
    line_spacing: int = 16,
    align: str = "left",
) -> int:
    """Draw wrapped text starting at y_start. Returns y position after last line."""
    lines = wrap_text(draw, text, font, max_width)
    if not lines:
        return y_start

    y = y_start
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        line_h = bbox[3] - bbox[1]

        if align == "center":
            x = (WIDTH - line_w) // 2
        else:
            x = PADDING_X

        draw.text((x, y), line, fill=color, font=font)
        y += line_h + line_spacing

    return y


def draw_accent_bar(draw: ImageDraw.ImageDraw, y: int, width: int = 80):
    """Draw a short horizontal accent bar."""
    x_start = PADDING_X
    draw.rectangle(
        [x_start, y, x_start + width, y + ACCENT_BAR_HEIGHT],
        fill=ACCENT,
    )


def draw_handle(draw: ImageDraw.ImageDraw, handle: str):
    """Draw handle text at bottom of slide."""
    font = load_font(FONT_BODY_PATHS, 28, bold=True)
    bbox = draw.textbbox((0, 0), handle, font=font)
    hw = bbox[2] - bbox[0]
    draw.text(
        ((WIDTH - hw) // 2, HEIGHT - PADDING_BOTTOM + 20),
        handle,
        fill=TEXT_MUTED,
        font=font,
    )


def draw_profile_header(img: Image.Image, draw: ImageDraw.ImageDraw, y_start: int = 100) -> int:
    """Draw circular profile photo + name + handle. Returns y after header."""
    photo_size = PROFILE_PHOTO_SIZE
    border = PROFILE_BORDER_WIDTH

    # Load and crop photo to circle
    if PROFILE_PHOTO_PATH.exists():
        photo = Image.open(PROFILE_PHOTO_PATH).convert("RGBA")
        # Crop to square (center crop)
        w, h = photo.size
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        photo = photo.crop((left, top, left + side, top + side))
        photo = photo.resize((photo_size, photo_size), Image.LANCZOS)

        # Create circular mask
        mask = Image.new("L", (photo_size, photo_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse([0, 0, photo_size - 1, photo_size - 1], fill=255)

        # Draw blue border circle on img
        border_size = photo_size + border * 2
        photo_x = PADDING_X
        border_x = photo_x - border
        border_y = y_start - border
        draw.ellipse(
            [border_x, border_y, border_x + border_size, border_y + border_size],
            fill=ACCENT,
        )

        # Paste circular photo
        img.paste(photo, (photo_x, y_start), mask)
    else:
        photo_x = PADDING_X
        border_size = photo_size + border * 2

    # Name — bold, right of photo
    name_font = load_font(FONT_HEADER_PATHS, 52, bold=True)
    handle_font = load_font(FONT_BODY_PATHS, 32)

    text_x = photo_x + photo_size + border + 24
    name_y = y_start + 10
    draw.text((text_x, name_y), PROFILE_NAME, fill=TEXT_PRIMARY, font=name_font)

    # Handle — below name
    handle_y = name_y + 52
    draw.text((text_x, handle_y), PROFILE_HANDLE, fill=TEXT_SECONDARY, font=handle_font)

    return y_start + photo_size + border * 2 + 30


def draw_slide_counter(draw: ImageDraw.ImageDraw, current: int, total: int):
    """Draw slide counter at top-right."""
    font = load_font(FONT_BODY_PATHS, 26)
    text = f"{current}/{total}"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(
        (WIDTH - PADDING_X - tw, PADDING_TOP - 50),
        text,
        fill=TEXT_MUTED,
        font=font,
    )


def draw_swipe_dots(draw: ImageDraw.ImageDraw, current: int, total: int):
    """Draw swipe indicator dots at very bottom."""
    dot_y = HEIGHT - 40
    dot_r = 5
    dot_spacing = 16
    total_w = total * dot_r * 2 + (total - 1) * dot_spacing
    start_x = (WIDTH - total_w) // 2

    for i in range(total):
        cx = start_x + i * (dot_r * 2 + dot_spacing) + dot_r
        if i == current - 1:
            draw.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=ACCENT)
        else:
            draw.ellipse([cx - dot_r, dot_y - dot_r, cx + dot_r, dot_y + dot_r], fill=(220, 220, 220))


# --- Slide renderers ---

def measure_text_block(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int, line_spacing: int = 16) -> int:
    """Measure total height of a wrapped text block."""
    lines = wrap_text(draw, text, font, max_width)
    if not lines:
        return 0
    total = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        total += bbox[3] - bbox[1]
    total += line_spacing * (len(lines) - 1)
    return total


def render_title_slide(text: str, slide_num: int, total: int, handle: str, show_profile: bool = True) -> Image.Image:
    """Slide 1: optional profile header + hook/title. Big bold header, optional subtitle, accent bar."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    if "||" in text:
        header, subtitle = text.split("||", 1)
        header = header.strip()
        subtitle = subtitle.strip()
    else:
        header = text
        subtitle = ""

    if show_profile:
        profile_bottom = draw_profile_header(img, draw, y_start=PADDING_TOP + 60)
        safe_top = profile_bottom + 40
    else:
        # Accent bar at top
        draw.rectangle([0, 0, WIDTH, 12], fill=ACCENT)
        safe_top = 60

    safe_bottom = HEIGHT - 160
    safe_h = safe_bottom - safe_top

    header_font = load_font(FONT_HEADER_PATHS, 110, bold=True)

    if subtitle:
        sub_font = load_font(FONT_BODY_PATHS, 56, bold=True)
        header_h = measure_text_block(draw, header, header_font, MAX_TEXT_WIDTH, 16)
        bar_gap = 30 + ACCENT_BAR_HEIGHT + 30
        subtitle_h = measure_text_block(draw, subtitle, sub_font, MAX_TEXT_WIDTH, 14)
        total_block = header_h + bar_gap + subtitle_h

        block_y = safe_top + (safe_h - total_block) // 2
        header_bottom = draw_text_block(draw, header, header_font, TEXT_PRIMARY, MAX_TEXT_WIDTH, block_y, line_spacing=16, align="left")
        draw_accent_bar(draw, header_bottom + 30)
        draw_text_block(draw, subtitle, sub_font, TEXT_SECONDARY, MAX_TEXT_WIDTH, header_bottom + 30 + ACCENT_BAR_HEIGHT + 30, line_spacing=14, align="left")
    else:
        header_h = measure_text_block(draw, header, header_font, MAX_TEXT_WIDTH, 16)
        header_y = safe_top + (safe_h - header_h) // 2
        draw_text_block(draw, header, header_font, TEXT_PRIMARY, MAX_TEXT_WIDTH, header_y, line_spacing=16, align="left")

    draw_swipe_dots(draw, slide_num, total)

    return img


def render_content_slide(text: str, slide_num: int, total: int, content_num: int, content_total: int, handle: str) -> Image.Image:
    """Middle slides: header/body split, accent bar, slide counter. Auto-scales if text overflows."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    safe_top = 100
    safe_bottom = 100
    max_usable_h = HEIGHT - safe_top - safe_bottom

    # Slide counter top-right
    draw_slide_counter(draw, content_num, content_total)

    if "||" in text:
        header, body = text.split("||", 1)
        header = header.strip()
        body = body.strip()

        # Start at target sizes, scale down if needed (min 66/42 to stay readable)
        h_size, b_size = 90, 54
        while h_size >= 66:
            header_font = load_font(FONT_HEADER_PATHS, h_size, bold=True)
            body_font = load_font(FONT_BODY_PATHS, b_size, bold=True)
            header_h = measure_text_block(draw, header, header_font, MAX_TEXT_WIDTH, 14)
            bar_gap = 24 + ACCENT_BAR_HEIGHT + 28
            body_h = measure_text_block(draw, body, body_font, MAX_TEXT_WIDTH, 18)
            total_block = header_h + bar_gap + body_h
            if total_block <= max_usable_h:
                break
            h_size -= 6
            b_size -= 4

        block_y = (HEIGHT - total_block) // 2
        header_bottom = draw_text_block(draw, header, header_font, TEXT_PRIMARY, MAX_TEXT_WIDTH, block_y, line_spacing=14, align="left")
        draw_accent_bar(draw, header_bottom + 24)
        draw_text_block(draw, body, body_font, TEXT_SECONDARY, MAX_TEXT_WIDTH, header_bottom + 24 + ACCENT_BAR_HEIGHT + 28, line_spacing=18, align="left")
    else:
        b_size = 76
        while b_size >= 54:
            body_font = load_font(FONT_HEADER_PATHS, b_size, bold=True)
            total_h = measure_text_block(draw, text, body_font, MAX_TEXT_WIDTH, 16)
            if total_h <= max_usable_h:
                break
            b_size -= 6
        y_start = (HEIGHT - total_h) // 2
        draw_text_block(draw, text, body_font, TEXT_PRIMARY, MAX_TEXT_WIDTH, y_start, line_spacing=16, align="left")

    draw_swipe_dots(draw, slide_num, total)

    return img


def render_cta_slide(text: str, slide_num: int, total: int, handle: str, show_profile: bool = True) -> Image.Image:
    """Last slide: optional profile header + CTA."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    if show_profile:
        profile_bottom = draw_profile_header(img, draw, y_start=PADDING_TOP + 60)
        safe_top = profile_bottom + 40
    else:
        draw.rectangle([0, 0, WIDTH, 12], fill=ACCENT)
        safe_top = 60

    safe_bottom = HEIGHT - 160
    safe_h = safe_bottom - safe_top

    cta_font = load_font(FONT_HEADER_PATHS, 84, bold=True)
    total_h = measure_text_block(draw, text, cta_font, MAX_TEXT_WIDTH, 16)
    y_start = safe_top + (safe_h - total_h) // 4
    draw_text_block(draw, text, cta_font, TEXT_PRIMARY, MAX_TEXT_WIDTH, y_start, line_spacing=16, align="left")

    draw_swipe_dots(draw, slide_num, total)

    return img


# --- Main generation ---

def generate_carousel(
    topic: str,
    num_slides: int,
    handle: str = "@allenenriquezz",
    copy: list[str] | None = None,
    show_profile: bool = True,
) -> Path:
    """Generate all carousel slides and save to projects/personal/content/carousels/<slug>/."""
    slug = slugify(topic)
    base = Path(__file__).resolve().parent.parent / "projects" / "personal" / "content" / "carousels" / slug
    base.mkdir(parents=True, exist_ok=True)

    if copy is None:
        # Placeholder copy — in production, agent provides real copy
        copy = [topic.upper()]
        for i in range(num_slides - 2):
            copy.append(f"POINT {i+1} || Write your point here. Max 15 words. One idea only.")
        copy.append("Follow for daily posts. I'm teaching everything for free.")

    if len(copy) != num_slides:
        raise ValueError(f"Expected {num_slides} slide texts, got {len(copy)}")

    content_total = num_slides - 2  # exclude title + CTA for counter

    for i, text in enumerate(copy):
        slide_num = i + 1

        if slide_num == 1:
            img = render_title_slide(text, slide_num, num_slides, handle, show_profile=show_profile)
        elif slide_num == num_slides:
            img = render_cta_slide(text, slide_num, num_slides, handle, show_profile=show_profile)
        else:
            content_num = slide_num - 1  # 1-based content counter
            img = render_content_slide(text, slide_num, num_slides, content_num, content_total, handle)

        path = base / f"slide_{slide_num:02d}.png"
        img.save(path, "PNG")
        print(f"  [{slide_num}/{num_slides}] {path}")

    # Save copy for reference
    copy_path = base / "copy.txt"
    with open(copy_path, "w") as f:
        for i, text in enumerate(copy):
            f.write(f"--- Slide {i+1} ---\n{text}\n\n")
    print(f"  Copy saved to {copy_path}")

    return base


def main():
    parser = argparse.ArgumentParser(description="Generate Hormozi-style carousel PNGs")
    parser.add_argument("--topic", required=True, help="Carousel topic / hook text")
    parser.add_argument("--slides", type=int, default=7, help="Number of slides (default: 7)")
    parser.add_argument("--handle", default="@allenenriquezz", help="Social handle (default: @allenenriquezz)")
    parser.add_argument(
        "--copy-file",
        default=None,
        help="Path to a text file with slide copy (separated by '--- Slide N ---')",
    )
    parser.add_argument("--no-profile", action="store_true", help="Skip profile header on title and CTA slides")

    args = parser.parse_args()

    if args.slides < 3:
        parser.error("Need at least 3 slides (title + 1 content + CTA)")

    copy = None
    if args.copy_file:
        with open(args.copy_file) as f:
            raw = f.read()
        sections = re.split(r"---\s*Slide\s*\d+\s*---\n?", raw)
        copy = [s.strip() for s in sections if s.strip()]

    print(f"\nGenerating {args.slides}-slide carousel: \"{args.topic}\"")
    print(f"Handle: {args.handle}\n")

    output = generate_carousel(
        topic=args.topic,
        num_slides=args.slides,
        handle=args.handle,
        copy=copy,
        show_profile=not args.no_profile,
    )

    print(f"\nDone. Files in: {output}/")


if __name__ == "__main__":
    main()
