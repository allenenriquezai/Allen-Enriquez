"""Generate lead magnet PDF for cold call follow-ups."""
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUT = "/Users/allenenriquez/Desktop/Allen Enriquez/projects/personal/sales-assets/lead-magnet.pdf"
BRAND = HexColor("#02B3E9")
DARK = HexColor("#0F172A")
GREY = HexColor("#475569")
LIGHT = HexColor("#F1F5F9")

styles = {
    "title": ParagraphStyle(
        "title", fontName="Helvetica-Bold", fontSize=28, leading=34,
        textColor=DARK, alignment=TA_LEFT, spaceAfter=8,
    ),
    "subtitle": ParagraphStyle(
        "subtitle", fontName="Helvetica", fontSize=14, leading=18,
        textColor=GREY, alignment=TA_LEFT, spaceAfter=20,
    ),
    "section_num": ParagraphStyle(
        "section_num", fontName="Helvetica-Bold", fontSize=11, leading=13,
        textColor=BRAND, alignment=TA_LEFT, spaceAfter=4,
    ),
    "section_title": ParagraphStyle(
        "section_title", fontName="Helvetica-Bold", fontSize=18, leading=22,
        textColor=DARK, alignment=TA_LEFT, spaceAfter=6,
    ),
    "label": ParagraphStyle(
        "label", fontName="Helvetica-Bold", fontSize=10, leading=12,
        textColor=BRAND, alignment=TA_LEFT, spaceAfter=2,
    ),
    "body": ParagraphStyle(
        "body", fontName="Helvetica", fontSize=11, leading=16,
        textColor=DARK, alignment=TA_LEFT, spaceAfter=8,
    ),
    "footer": ParagraphStyle(
        "footer", fontName="Helvetica", fontSize=9, leading=12,
        textColor=GREY, alignment=TA_CENTER,
    ),
    "cta_title": ParagraphStyle(
        "cta_title", fontName="Helvetica-Bold", fontSize=16, leading=20,
        textColor=white, alignment=TA_LEFT, spaceAfter=6,
    ),
    "cta_body": ParagraphStyle(
        "cta_body", fontName="Helvetica", fontSize=11, leading=15,
        textColor=white, alignment=TA_LEFT, spaceAfter=4,
    ),
}


def section(num, title, problem, fix):
    return [
        Paragraph(f"PROBLEM #{num}", styles["section_num"]),
        Paragraph(title, styles["section_title"]),
        Paragraph("THE PROBLEM", styles["label"]),
        Paragraph(problem, styles["body"]),
        Paragraph("THE FIX", styles["label"]),
        Paragraph(fix, styles["body"]),
        Spacer(1, 14),
    ]


def cta_box():
    inner = [
        [Paragraph("Want me to fix one of these for you?", styles["cta_title"])],
        [Paragraph("I help painting companies set up these systems. First setup is fast — usually 72 hours. No long contracts. No big team needed.", styles["cta_body"])],
        [Paragraph("Book a free 15-minute call:", styles["cta_body"])],
        [Paragraph("<b>calendar.app.google/your-link-here</b>", styles["cta_body"])],
        [Paragraph("Or reply to this email.", styles["cta_body"])],
    ]
    t = Table(inner, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), DARK),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ("TOPPADDING", (0, 0), (0, 0), 18),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
    ]))
    return t


def header_band():
    t = Table([[""]], colWidths=[7.5 * inch], rowHeights=[8])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND)]))
    return t


def build():
    doc = SimpleDocTemplate(
        OUT, pagesize=LETTER,
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
        topMargin=0.4 * inch, bottomMargin=0.4 * inch,
    )

    story = []
    story.append(header_band())
    story.append(Spacer(1, 18))
    story.append(Paragraph("5 Things Slowing Down Your Sales", styles["title"]))
    story.append(Paragraph("And how to fix them with AI — for painting companies.", styles["subtitle"]))

    sections = [
        (1, "Slow Quotes",
         "Most painters take 30 to 60 minutes to write one quote. That's 5 to 10 hours a week just typing. Some leads wait days. By then, they hired the painter who replied first.",
         "An AI quote builder. You type the job in plain words. It writes the full quote in 5 minutes. Same look every time. Same price logic every time. You hit send."),
        (2, "Slow Lead Response",
         "A lead fills out your form at 9pm. You see it the next morning. They already booked a call with someone else. The first painter to reply wins most of the time.",
         "Speed-to-lead automation. The second a lead comes in, AI sends a text and an email. Books a call slot. You wake up with a meeting on the calendar."),
        (3, "Leads Going Cold",
         "You quote 20 jobs. 5 say yes right away. 15 go quiet. You forget to follow up. That's $20K to $50K of lost work every month.",
         "Auto follow-up. AI sends 4 to 6 messages over 2 weeks. Different angle each time. You only step in when they reply. Most quiet leads close on the third or fourth touch."),
        (4, "Messy CRM",
         "Half your deals live in your head. Half live in text messages. Half live in email. You can't see who needs what. You miss deposits. You forget callbacks.",
         "AI that updates your CRM for you. Every call, email, and text gets logged. Next step gets set. You open the CRM in the morning and see one list — who to call today, in order."),
        (5, "Doing Admin Yourself",
         "You spend 2 hours a day on quotes, follow-ups, scheduling, and invoices. That's 10 hours a week not selling. Not running jobs. Not with your family.",
         "Stack the systems above. The admin runs itself. You spend your time on the parts that actually grow the business — sales, site visits, hiring."),
    ]
    for s in sections:
        story.extend(section(*s))

    story.append(Spacer(1, 8))
    story.append(cta_box())
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Allen Enriquez — Sales manager at a painting company. Built these systems for my own job. Closed $114K last month using them.",
        styles["footer"],
    ))

    doc.build(story)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    build()
