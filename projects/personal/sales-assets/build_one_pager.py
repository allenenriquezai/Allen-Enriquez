"""Generate one-pager PDF: what the AI quote builder does."""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUT = "/Users/allenenriquez/Desktop/Allen Enriquez/projects/personal/sales-assets/one-pager-quote-builder.pdf"
BRAND = HexColor("#02B3E9")
DARK = HexColor("#0F172A")
GREY = HexColor("#475569")
LIGHT = HexColor("#F1F5F9")
RED = HexColor("#ef4444")
GREEN = HexColor("#16a34a")

S = {
    "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=26, leading=30, textColor=DARK, spaceAfter=6),
    "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=13, leading=17, textColor=GREY, spaceAfter=18),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=DARK, spaceAfter=8),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=15, textColor=DARK, spaceAfter=6),
    "ba_label": ParagraphStyle("ba_label", fontName="Helvetica-Bold", fontSize=11, leading=13, textColor=white, alignment=TA_CENTER),
    "ba_metric": ParagraphStyle("ba_metric", fontName="Helvetica-Bold", fontSize=22, leading=24, textColor=DARK, alignment=TA_CENTER),
    "ba_label_dark": ParagraphStyle("ba_label_dark", fontName="Helvetica-Bold", fontSize=10, leading=12, textColor=GREY, alignment=TA_CENTER),
    "footer": ParagraphStyle("footer", fontName="Helvetica", fontSize=9, leading=12, textColor=GREY, alignment=TA_CENTER),
    "cta_t": ParagraphStyle("cta_t", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=white),
    "cta_b": ParagraphStyle("cta_b", fontName="Helvetica", fontSize=11, leading=15, textColor=white),
}


def header_band():
    t = Table([[""]], colWidths=[7.5 * inch], rowHeights=[8])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND)]))
    return t


def before_after():
    headers = [
        Paragraph("BEFORE", S["ba_label"]),
        Paragraph("AFTER", S["ba_label"]),
    ]
    rows = [
        ("45 min per quote", "5 min per quote"),
        ("Inconsistent pricing", "Same logic every time"),
        ("Different look every time", "Same branded format"),
        ("Sent next day", "Sent same day"),
        ("Lost to faster painters", "First quote in"),
    ]
    data = [headers]
    for b, a in rows:
        data.append([
            Paragraph(b, ParagraphStyle("b", fontName="Helvetica", fontSize=10.5, leading=14, textColor=DARK)),
            Paragraph(a, ParagraphStyle("a", fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=DARK)),
        ])
    t = Table(data, colWidths=[3.4 * inch, 3.4 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), RED),
        ("BACKGROUND", (1, 0), (1, 0), GREEN),
        ("TOPPADDING", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("BACKGROUND", (0, 1), (-1, -1), white),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#CBD5E1")),
        ("INNERGRID", (0, 1), (-1, -1), 0.25, HexColor("#E2E8F0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 1), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 10),
    ]))
    return t


def cta():
    inner = [
        [Paragraph("72-hour setup. Free 15-min call to scope it.", S["cta_t"])],
        [Paragraph("calendar.app.google/your-link-here", S["cta_b"])],
        [Paragraph("allenenriquez006@gmail.com  •  +63 945 420 3195", S["cta_b"])],
    ]
    t = Table(inner, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 18),
        ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ("TOPPADDING", (0, 0), (0, 0), 16),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 16),
    ]))
    return t


def build():
    doc = SimpleDocTemplate(OUT, pagesize=LETTER,
                            leftMargin=0.5 * inch, rightMargin=0.5 * inch,
                            topMargin=0.4 * inch, bottomMargin=0.4 * inch)
    s = []
    s.append(header_band())
    s.append(Spacer(1, 14))
    s.append(Paragraph("AI Quote Builder", S["title"]))
    s.append(Paragraph("For painting companies. Cuts quote time from 45 minutes to 5.", S["sub"]))

    s.append(Paragraph("What it does", S["h2"]))
    s.append(Paragraph(
        "You type the job in plain words — rooms, square footage, paint type, prep work. The AI writes the full quote in 5 minutes. Same branded format every time. Same pricing logic every time. You review it, hit send, and the customer gets it in their inbox.",
        S["body"]))
    s.append(Spacer(1, 8))

    s.append(Paragraph("Before vs after", S["h2"]))
    s.append(before_after())
    s.append(Spacer(1, 16))

    s.append(Paragraph("What you get", S["h2"]))
    s.append(Paragraph("• Quote builder set up on your existing tools (Google Docs, Sheets, or your CRM)", S["body"]))
    s.append(Paragraph("• Pricing logic dialled to your numbers (your rates, your margins)", S["body"]))
    s.append(Paragraph("• Branded quote template (your logo, colours, fonts)", S["body"]))
    s.append(Paragraph("• 30 minutes of training so you and your team can use it day one", S["body"]))
    s.append(Paragraph("• 14 days of free tweaks after launch", S["body"]))
    s.append(Spacer(1, 12))

    s.append(Paragraph("Real result", S["h2"]))
    s.append(Paragraph(
        "I run this same system at my own painting company in Brisbane. Last month: $114K in new sales. 80+ active deals. Zero face-to-face meetings. The system handles the volume so I can focus on closing.",
        S["body"]))
    s.append(Spacer(1, 16))

    s.append(cta())
    s.append(Spacer(1, 10))
    s.append(Paragraph("Allen Enriquez — sales manager, EPS Painting & Cleaning", S["footer"]))

    doc.build(s)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
