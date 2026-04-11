"""
Generate the lead magnet PDF: 5 AI Automations That Save 10+ Hours a Week
Hormozi style — bold, simple, one automation per page.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "lead-magnet-5-ai-automations.pdf")

# Colors
BG = HexColor("#0a0a0a")
WHITE = HexColor("#f5f5f5")
GOLD = HexColor("#fbbf24")
GRAY = HexColor("#a3a3a3")
DARK_CARD = HexColor("#161616")
GREEN = HexColor("#22c55e")

W, H = A4

def draw_bg(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)

def draw_text(c, text, x, y, size=14, color=WHITE, font="Helvetica-Bold", max_width=None):
    c.setFillColor(color)
    c.setFont(font, size)
    if max_width:
        # Simple word wrap
        words = text.split()
        lines = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if c.stringWidth(test, font, size) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        for i, line in enumerate(lines):
            c.drawString(x, y - i * (size + 4), line)
        return len(lines) * (size + 4)
    else:
        c.drawString(x, y, text)
        return size + 4

def draw_centered(c, text, y, size=14, color=WHITE, font="Helvetica-Bold"):
    c.setFillColor(color)
    c.setFont(font, size)
    tw = c.stringWidth(text, font, size)
    c.drawString((W - tw) / 2, y, text)

def draw_card(c, x, y, w, h):
    c.setFillColor(DARK_CARD)
    c.roundRect(x, y, w, h, 10, fill=1, stroke=0)

# ─── PAGES ───

def cover_page(c):
    draw_bg(c)
    # Eyebrow
    draw_centered(c, "FREE GUIDE", H - 120, size=12, color=GOLD, font="Helvetica-Bold")
    # Title
    draw_centered(c, "5 AI Automations", H - 170, size=38, color=WHITE)
    draw_centered(c, "That Save 10+ Hours", H - 215, size=38, color=GOLD)
    draw_centered(c, "a Week", H - 260, size=38, color=GOLD)
    # Subtitle
    draw_centered(c, "Copy each one in 10 minutes.", H - 310, size=16, color=GRAY, font="Helvetica")
    draw_centered(c, "No coding. No experience. No cost.", H - 332, size=16, color=GRAY, font="Helvetica")
    # Author
    draw_centered(c, "By Allen Enriquez", H - 400, size=14, color=WHITE, font="Helvetica")
    draw_centered(c, "Sales Manager | AI Automation Builder", H - 420, size=12, color=GRAY, font="Helvetica")
    # Bottom
    draw_centered(c, "allenenriquez.com", 60, size=11, color=GRAY, font="Helvetica")

def intro_page(c):
    draw_bg(c)
    margin = 50
    mw = W - 2 * margin
    y = H - 80
    draw_text(c, "Before we start.", margin, y, size=28, color=GOLD)
    y -= 50
    paras = [
        "I'm Allen. I manage sales for a painting company in Australia.",
        "I work remotely from the Philippines. Just me and an assistant.",
        "We bring in $60-100K in revenue every month.",
        "",
        "I'm not a tech guy. I'm a sales guy.",
        "I got tired of doing the same tasks every day.",
        "So I built AI to do them for me.",
        "",
        "These 5 automations saved me the most time.",
        "Each one took less than 10 minutes to set up.",
        "I'm giving them to you for free.",
        "",
        "You don't need to code. You don't need to be technical.",
        "If you can write an email, you can do this.",
        "",
        "Let's go.",
    ]
    for p in paras:
        if p == "":
            y -= 16
        else:
            h = draw_text(c, p, margin, y, size=14, color=WHITE if not p.startswith("I'm not") and not p.startswith("Let's") else GOLD, font="Helvetica", max_width=mw)
            y -= h + 2

def automation_page(c, number, title, problem, solution_steps, result, tool_suggestion):
    draw_bg(c)
    margin = 50
    mw = W - 2 * margin
    y = H - 70

    # Number badge
    c.setFillColor(GOLD)
    c.circle(margin + 20, y, 22, fill=1, stroke=0)
    c.setFillColor(BG)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(margin + 20, y - 8, str(number))

    # Title
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(margin + 55, y - 8, title)
    y -= 60

    # Problem
    draw_text(c, "THE PROBLEM", margin, y, size=11, color=GOLD, font="Helvetica-Bold")
    y -= 24
    h = draw_text(c, problem, margin, y, size=14, color=GRAY, font="Helvetica", max_width=mw)
    y -= h + 20

    # How it works
    draw_text(c, "HOW IT WORKS", margin, y, size=11, color=GOLD, font="Helvetica-Bold")
    y -= 28

    for i, step in enumerate(solution_steps):
        # Step card
        card_h = 50
        draw_card(c, margin, y - card_h + 16, mw, card_h)
        # Step number
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(margin + 14, y - 8, f"Step {i+1}")
        # Step text
        draw_text(c, step, margin + 80, y - 8, size=13, color=WHITE, font="Helvetica", max_width=mw - 94)
        y -= card_h + 8

    y -= 12

    # Result
    draw_text(c, "THE RESULT", margin, y, size=11, color=GREEN, font="Helvetica-Bold")
    y -= 24
    draw_text(c, result, margin, y, size=15, color=WHITE, font="Helvetica-Bold", max_width=mw)
    y -= 40

    # Tool
    draw_text(c, "TOOLS YOU CAN USE", margin, y, size=11, color=GRAY, font="Helvetica-Bold")
    y -= 22
    draw_text(c, tool_suggestion, margin, y, size=13, color=GRAY, font="Helvetica", max_width=mw)

def next_steps_page(c):
    draw_bg(c)
    margin = 50
    mw = W - 2 * margin
    y = H - 80

    draw_text(c, "What to do next.", margin, y, size=28, color=GOLD)
    y -= 50

    steps = [
        ("1.", "Pick one automation from this guide.", "Just one. Don't try all five at once."),
        ("2.", "Set it up today.", "It takes 10 minutes. Not tomorrow. Today."),
        ("3.", "Watch my YouTube tutorials.", "I show you how to set up each one step by step. Free."),
        ("4.", "DM me if you get stuck.", "I reply to everyone. Facebook or Instagram. I'll help you."),
        ("5.", "Want me to build it for you?", "I set up full AI systems for people. Free setup. DM me."),
    ]

    for num, title, desc in steps:
        c.setFillColor(GOLD)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(margin, y, num)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin + 30, y, title)
        y -= 24
        draw_text(c, desc, margin + 30, y, size=13, color=GRAY, font="Helvetica", max_width=mw - 30)
        y -= 36

    y -= 20
    draw_card(c, margin, y - 80, mw, 100)
    draw_centered(c, "Follow Allen Enriquez", y + 4, size=16, color=GOLD)
    draw_centered(c, "YouTube  |  Facebook  |  Instagram  |  TikTok", y - 22, size=13, color=GRAY, font="Helvetica")
    draw_centered(c, "DM me \"AUTOMATE\" on any platform — I'll help you get started.", y - 48, size=13, color=WHITE, font="Helvetica")

    draw_centered(c, "allenenriquez.com", 60, size=11, color=GRAY, font="Helvetica")

# ─── AUTOMATIONS ───

automations = [
    {
        "title": "Auto-Reply to New Leads",
        "problem": "A new lead messages you. You're busy. You reply 3 hours later. They already went with someone else. Speed wins deals. Slow replies lose them.",
        "steps": [
            "Connect your inbox or message app to an AI tool.",
            "AI reads the message and writes a reply in your voice.",
            "Reply sends within 60 seconds. You review later.",
        ],
        "result": "Every lead gets a reply in under 1 minute. No more lost deals because you were busy.",
        "tools": "ChatGPT + Zapier, n8n, or Make.com. Free tiers work fine.",
    },
    {
        "title": "Follow-Up Sequences",
        "problem": "You sent a quote. They didn't reply. You forget to follow up. Or you follow up too late. 80% of sales happen after the 5th follow-up. Most people stop at 1.",
        "steps": [
            "Set up a simple tracker (spreadsheet or CRM).",
            "AI checks daily: who hasn't replied in 48 hours?",
            "AI drafts a follow-up message. You approve and send.",
        ],
        "result": "Nobody falls through the cracks. Follow-ups happen every time, on time, without you remembering.",
        "tools": "Google Sheets + ChatGPT, Pipedrive, HubSpot free, or any CRM.",
    },
    {
        "title": "Quote Builder",
        "problem": "You get a request. You calculate. You type it up. You format it. You attach it to an email. It takes 30-45 minutes. Every. Single. Time.",
        "steps": [
            "Create a template with your standard pricing.",
            "AI takes the job details and fills in the template.",
            "You review for 2 minutes. Hit send.",
        ],
        "result": "Quotes go out in 5 minutes instead of 45. Clients get them while they're still thinking about you.",
        "tools": "ChatGPT + Google Docs. Or build a simple prompt template.",
    },
    {
        "title": "Email Drafts on Autopilot",
        "problem": "You write 20+ emails a day. Most say the same things with small changes. Client updates, meeting confirms, thank yous, proposals. Hours of typing.",
        "steps": [
            "Give AI 5-10 examples of emails you've sent before.",
            "Tell it the context: who, what, tone.",
            "AI writes the draft. You edit if needed. Send.",
        ],
        "result": "Every email takes 30 seconds instead of 10 minutes. Same quality. Your voice. Just faster.",
        "tools": "ChatGPT, Claude, or any AI assistant. No special tools needed.",
    },
    {
        "title": "Daily Briefing",
        "problem": "You start your day by checking 5 apps. Email, CRM, calendar, messages, spreadsheets. By the time you know what to do, 30 minutes are gone.",
        "steps": [
            "Connect your key apps to one AI summary tool.",
            "AI pulls: new leads, overdue tasks, today's meetings, pending replies.",
            "You get one summary every morning. That's your to-do list.",
        ],
        "result": "You know exactly what to do the moment you sit down. No more wasted mornings figuring out where to start.",
        "tools": "ChatGPT + Zapier, n8n, or a simple script. Google Sheets as the hub.",
    },
]

# ─── BUILD PDF ───

c = canvas.Canvas(OUTPUT, pagesize=A4)

cover_page(c)
c.showPage()

intro_page(c)
c.showPage()

for i, auto in enumerate(automations):
    automation_page(
        c,
        number=i + 1,
        title=auto["title"],
        problem=auto["problem"],
        solution_steps=auto["steps"],
        result=auto["result"],
        tool_suggestion=auto["tools"],
    )
    c.showPage()

next_steps_page(c)
c.showPage()

c.save()
print(f"✓ PDF saved to: {OUTPUT}")
