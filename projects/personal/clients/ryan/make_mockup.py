"""Generate a Gmail-sidebar mockup PNG showing proposed labels for Ryan."""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).parent / "gmail-mockup.png"

W, H = 1400, 900
BG = (242, 245, 249)           # light gray
SIDEBAR_BG = (255, 255, 255)
INBOX_HL = (232, 240, 254)     # selected-label blue tint
ACCENT = (26, 115, 232)        # Google blue
TEXT = (32, 33, 36)
SUBTLE = (95, 99, 104)
DIVIDER = (232, 234, 237)
BADGE = (95, 99, 104)

TITLE_BG = (255, 255, 255)

def font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # top bar (Gmail red-blue accent)
    d.rectangle([0, 0, W, 60], fill=(255, 255, 255))
    d.line([0, 60, W, 60], fill=DIVIDER, width=1)
    d.text((30, 18), "Gmail", font=font(22, True), fill=(218, 58, 47))
    d.text((110, 22), "ryan@sc-incorporated.com", font=font(14), fill=SUBTLE)

    # sidebar
    SIDE_W = 360
    d.rectangle([0, 60, SIDE_W, H], fill=SIDEBAR_BG)
    d.line([SIDE_W, 60, SIDE_W, H], fill=DIVIDER, width=1)

    # compose button
    d.rounded_rectangle([20, 80, 160, 130], radius=24, fill=(194, 231, 255))
    d.text((58, 96), "+  Compose", font=font(14, True), fill=(0, 97, 155))

    y = 160
    def label(y, text, count=None, indent=24, color=ACCENT, bold=False, highlight=False):
        if highlight:
            d.rounded_rectangle([10, y - 6, SIDE_W - 10, y + 24], radius=8, fill=INBOX_HL)
        # dot
        d.ellipse([indent, y + 6, indent + 10, y + 16], fill=color)
        d.text((indent + 22, y), text, font=font(14, bold), fill=TEXT)
        if count is not None:
            d.text((SIDE_W - 60, y), str(count), font=font(13, True), fill=BADGE)
        return y + 36

    y = label(y, "Inbox", count=12, color=(26, 115, 232), bold=True, highlight=True)
    y = label(y, "Starred", color=(249, 171, 0))
    y = label(y, "Sent", color=(95, 99, 104))
    y = label(y, "Drafts", color=(95, 99, 104))

    y += 18
    d.line([18, y, SIDE_W - 18, y], fill=DIVIDER, width=1)
    y += 18
    d.text((24, y), "Labels", font=font(12, True), fill=SUBTLE)
    y += 28

    # Projects parent
    y = label(y, "Projects", count=None, color=(15, 157, 88), bold=True)
    projects = [
        ("Pura Vida Miami", 59),
        ("Deckers Cafe", 58),
        ("Colony Parc II", 44),
        ("Porto's Bakery", 25),
        ("Whole Foods TI", 23),
        ("Angel City FC", 16),
        ("Poly Plaza", 15),
        ("Lounge 1888", 13),
        ("500 Thousand Oaks", 13),
        ("+ auto-added per job", None),
    ]
    for name, cnt in projects:
        if name.startswith("+"):
            d.text((70, y), name, font=font(13), fill=SUBTLE)
            y += 28
        else:
            d.ellipse([62, y + 6, 72, y + 16], fill=(15, 157, 88))
            d.text((84, y), name, font=font(13), fill=TEXT)
            if cnt:
                d.text((SIDE_W - 60, y), str(cnt), font=font(12), fill=BADGE)
            y += 28

    y += 6
    y = label(y, "Bids", count=176, color=(66, 133, 244), bold=True)
    y = label(y, "Vendors", count=374, color=(244, 180, 0), bold=True)
    y = label(y, "Team Daily", count=125, color=(171, 71, 188), bold=True)
    y = label(y, "Admin", count=139, color=(95, 99, 104), bold=True)
    y = label(y, "Promos", count=81, color=(234, 67, 53), bold=True)
    y = label(y, "Review", count=0, color=(255, 145, 0), bold=True)

    # right panel — preview of inbox after sorting
    PX = SIDE_W + 40
    PY = 90

    d.text((PX, PY), "Inbox", font=font(26, True), fill=TEXT)
    d.text((PX, PY + 36), "12 unread, everything else sorted.", font=font(14), fill=SUBTLE)

    d.line([PX, PY + 68, W - 40, PY + 68], fill=DIVIDER, width=1)

    rows = [
        ("Change Order — Deckers Cafe",           "kharene@sc-incorporated.com",  "URGENT",   (234, 67, 53)),
        ("RE: Pura Vida Miami — Long Beach, CA",  "rodneyp@itxconst.com",          "Bids",     (66, 133, 244)),
        ("Daily Accomplishments — Monday",        "joseph@sc-incorporated.com",    "Team Daily",(171, 71, 188)),
        ("Material Price Request — Angel City",    "emarcon@lxhausys.com",         "Vendors",  (244, 180, 0)),
        ("Hourly Notifications — Colony Parc II",  "no-reply@acc.autodesk.com",     "Muted",    (160, 160, 160)),
        ("Re: Whole Foods TI — LA",                "kharene@sc-incorporated.com",   "Projects", (15, 157, 88)),
        ("RE: ADP Payroll — pay run ready",        "no-reply@adp.com",              "Admin",    (95, 99, 104)),
        ("Up to 25% OFF SpringFest",               "lowes@e.lowes.com",             "Promos",   (234, 67, 53)),
    ]

    ry = PY + 88
    for subj, sender, tag, tag_col in rows:
        d.text((PX, ry), subj, font=font(15, True), fill=TEXT)
        d.text((PX, ry + 22), sender, font=font(13), fill=SUBTLE)
        tw = d.textlength(tag, font=font(12, True))
        d.rounded_rectangle([W - 60 - tw - 20, ry + 2, W - 40, ry + 24], radius=12, fill=tag_col)
        d.text((W - 50 - tw - 10, ry + 6), tag, font=font(12, True), fill=(255, 255, 255))
        ry += 62

    # footer
    d.text((PX, H - 40), "mockup — what your Gmail sidebar and inbox will look like after setup",
           font=font(12), fill=SUBTLE)

    img.save(OUT)
    print(f"saved: {OUT}")


if __name__ == "__main__":
    main()
