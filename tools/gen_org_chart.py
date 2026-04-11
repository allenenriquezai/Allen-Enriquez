#!/usr/bin/env python3
"""
Generate the Enriquez OS company structure PDF.
Visual org chart showing departments, agents, data flows, and self-improvement loops.
v2 — includes Delivery dept, 4th intel agent, QA tiers, content buffer, push Allen mechanism.
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
import os

OUTPUT = os.path.join(os.path.dirname(__file__), "enriquez-os-company-structure.pdf")

# Colors
BG = HexColor("#0a0a0a")
WHITE = HexColor("#f5f5f5")
GOLD = HexColor("#fbbf24")
GRAY = HexColor("#737373")
LIGHT_GRAY = HexColor("#a3a3a3")
DARK_CARD = HexColor("#161616")
CARD_BORDER = HexColor("#2a2a2a")
GREEN = HexColor("#22c55e")
BLUE = HexColor("#3b82f6")
PURPLE = HexColor("#a855f7")
RED = HexColor("#ef4444")
ORANGE = HexColor("#f97316")
TEAL = HexColor("#14b8a6")
CYAN = HexColor("#06b6d4")

W, H = landscape(A4)


def draw_bg(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)


def draw_rounded_rect(c, x, y, w, h, r=8, fill_color=DARK_CARD, stroke_color=None):
    c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(1.5)
        c.roundRect(x, y, w, h, r, fill=1, stroke=1)
    else:
        c.roundRect(x, y, w, h, r, fill=1, stroke=0)


def draw_text(c, text, x, y, size=10, color=WHITE, font="Helvetica-Bold", align="left"):
    c.setFillColor(color)
    c.setFont(font, size)
    if align == "center":
        tw = c.stringWidth(text, font, size)
        c.drawString(x - tw / 2, y, text)
    elif align == "right":
        tw = c.stringWidth(text, font, size)
        c.drawString(x - tw, y, text)
    else:
        c.drawString(x, y, text)


def draw_line(c, x1, y1, x2, y2, color=CARD_BORDER, width=1, dash=None):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    if dash:
        c.setDash(dash)
    c.line(x1, y1, x2, y2)
    if dash:
        c.setDash([])


def draw_agent_box(c, x, y, name, role, color=GOLD, w=145, h=36):
    draw_rounded_rect(c, x, y, w, h, r=6, fill_color=DARK_CARD, stroke_color=color)
    c.setFillColor(color)
    c.circle(x + 12, y + h / 2, 4, fill=1, stroke=0)
    draw_text(c, name, x + 22, y + h - 13, size=8, color=WHITE, font="Helvetica-Bold")
    draw_text(c, role, x + 22, y + 6, size=6.5, color=LIGHT_GRAY, font="Helvetica")


def draw_dept_header(c, x, y, title, color, w=160):
    c.setFillColor(color)
    c.setStrokeColor(color)
    c.setLineWidth(2)
    c.line(x, y, x + w, y)
    draw_text(c, title, x, y + 6, size=11, color=color, font="Helvetica-Bold")


# ─── PAGE 1: COVER ───

def page_cover(c):
    draw_bg(c)

    draw_text(c, "ENRIQUEZ OS", W / 2, H - 100, size=42, color=GOLD, align="center")
    draw_text(c, "Company Structure & Agent Organization", W / 2, H - 130, size=14, color=LIGHT_GRAY, font="Helvetica", align="center")
    draw_text(c, "v2 — April 2026", W / 2, H - 150, size=10, color=GRAY, font="Helvetica", align="center")

    # Two-domain diagram
    # Allen at top
    draw_rounded_rect(c, W / 2 - 90, H - 200, 180, 36, r=8, fill_color=DARK_CARD, stroke_color=GOLD)
    draw_text(c, "ALLEN ENRIQUEZ", W / 2, H - 190, size=13, color=GOLD, align="center")

    # EA
    draw_line(c, W / 2, H - 200, W / 2, H - 220, color=GOLD, width=1.5)
    draw_rounded_rect(c, W / 2 - 90, H - 256, 180, 34, r=8, fill_color=DARK_CARD, stroke_color=BLUE)
    draw_text(c, "EA / COO", W / 2, H - 244, size=11, color=BLUE, align="center")
    draw_text(c, "Orchestrates both domains", W / 2, H - 256, size=7, color=GRAY, font="Helvetica", align="center")

    # Lines down
    draw_line(c, W / 2, H - 256, W / 2 - 170, H - 275, color=BLUE, width=1.5)
    draw_line(c, W / 2, H - 256, W / 2 + 170, H - 275, color=BLUE, width=1.5)

    # Personal Brand box
    pb_x = W / 2 - 330
    pb_y = H - 380
    draw_rounded_rect(c, pb_x, pb_y, 310, 95, r=10, fill_color=DARK_CARD, stroke_color=ORANGE)
    draw_text(c, "PERSONAL BRAND", pb_x + 155, pb_y + 75, size=14, color=ORANGE, align="center")
    draw_text(c, "AI Automation Educator + Service Provider", pb_x + 155, pb_y + 58, size=8, color=WHITE, font="Helvetica", align="center")
    items_pb = [
        "Brand Manager  |  Intelligence (4 agents)",
        "Content Production  |  Sales  |  Delivery",
        "17 agents  |  Self-improving loops",
    ]
    iy = pb_y + 42
    for item in items_pb:
        draw_text(c, item, pb_x + 155, iy, size=7, color=GRAY, font="Helvetica", align="center")
        iy -= 14

    # EPS box
    eps_x = W / 2 + 20
    draw_rounded_rect(c, eps_x, pb_y, 310, 95, r=10, fill_color=DARK_CARD, stroke_color=RED)
    draw_text(c, "EPS (DAY JOB)", eps_x + 155, pb_y + 75, size=14, color=RED, align="center")
    draw_text(c, "Painting & Cleaning — Brisbane AU", eps_x + 155, pb_y + 58, size=8, color=WHITE, font="Helvetica", align="center")
    items_eps = [
        "Quotes  |  Emails  |  CRM  |  Calls  |  Tenders",
        "QA Gate  |  EstimateOne Scraper",
        "6 agents  |  Own tone, own workflows",
    ]
    iy = pb_y + 42
    for item in items_eps:
        draw_text(c, item, eps_x + 155, iy, size=7, color=GRAY, font="Helvetica", align="center")
        iy -= 14

    # Shared note
    share_y = pb_y - 25
    draw_rounded_rect(c, W / 2 - 220, share_y, 440, 22, r=4, fill_color=HexColor("#111111"), stroke_color=CARD_BORDER)
    draw_text(c, "SHARED: Allen's schedule, preferences  |  NOT SHARED: Brand, content, sales, tone, clients",
              W / 2, share_y + 6, size=7, color=LIGHT_GRAY, font="Helvetica", align="center")

    # Design principles
    dp_y = share_y - 40
    draw_text(c, "DESIGN PRINCIPLES", W / 2, dp_y, size=12, color=GOLD, align="center")
    principles = [
        ("1", "LESS INPUT FROM ALLEN", "System runs itself. Allen records + closes. Everything else automated."),
        ("2", "ACCURACY (95-100%)", "Wrong output = Allen fixes it = more input. Non-negotiable floor."),
        ("3", "SPEED", "Fast output = Allen isn't waiting. Waiting = wasted time."),
        ("4", "COST", "Near $0. Haiku over Sonnet. Local over API. Free tiers first."),
        ("5", "SCALABILITY", "Works for 1 deal or 50. Works now, works at 10x volume."),
    ]
    py = dp_y - 22
    for num, title, desc in principles:
        draw_text(c, num, W / 2 - 350, py, size=10, color=GOLD, font="Helvetica-Bold")
        draw_text(c, title, W / 2 - 330, py, size=9, color=WHITE, font="Helvetica-Bold")
        tw = c.stringWidth(title, "Helvetica-Bold", 9)
        draw_text(c, desc, W / 2 - 330 + tw + 12, py, size=7.5, color=GRAY, font="Helvetica")
        py -= 17

    # Page index
    draw_text(c, "P2: Org Chart  |  P3: Self-Improvement Loops  |  P4: Push Allen System  |  P5: Agent Registry  |  P6: EPS Operations",
              W / 2, 25, size=7, color=GRAY, font="Helvetica", align="center")


# ─── PAGE 2: ORG CHART (updated with Delivery + 4 intel agents) ───

def page_org_chart(c):
    draw_bg(c)

    draw_text(c, "PERSONAL BRAND — ORG CHART", 30, H - 35, size=18, color=GOLD)
    draw_text(c, "Every box except Allen is an AI agent", 30, H - 52, size=10, color=LIGHT_GRAY, font="Helvetica")

    # ─── TOP ROW ───
    top_y = H - 105

    # Allen
    draw_rounded_rect(c, 20, top_y, 155, 44, r=8, fill_color=DARK_CARD, stroke_color=GOLD)
    draw_text(c, "ALLEN", 38, top_y + 28, size=11, color=GOLD)
    draw_text(c, "Director / Talent", 38, top_y + 14, size=7, color=WHITE, font="Helvetica")
    draw_text(c, "Records. Closes. Approves.", 38, top_y + 4, size=6, color=GRAY, font="Helvetica")

    draw_line(c, 175, top_y + 22, 200, top_y + 22, color=GOLD, width=1.5)

    # EA
    draw_rounded_rect(c, 200, top_y, 155, 44, r=8, fill_color=DARK_CARD, stroke_color=BLUE)
    draw_text(c, "EA / COO", 218, top_y + 28, size=11, color=BLUE)
    draw_text(c, "Main Claude Session", 218, top_y + 14, size=7, color=WHITE, font="Helvetica")
    draw_text(c, "Routes. Syncs. Advises. Pushes Allen.", 218, top_y + 4, size=6, color=GRAY, font="Helvetica")

    draw_line(c, 355, top_y + 22, 380, top_y + 22, color=BLUE, width=1.5)

    # Brand Manager
    draw_rounded_rect(c, 380, top_y, 155, 44, r=8, fill_color=DARK_CARD, stroke_color=PURPLE)
    draw_text(c, "BRAND MANAGER", 398, top_y + 28, size=11, color=PURPLE)
    draw_text(c, "Creative Dir / Universal QA", 398, top_y + 14, size=7, color=WHITE, font="Helvetica")
    draw_text(c, "Approves all public-facing output.", 398, top_y + 4, size=6, color=GRAY, font="Helvetica")

    draw_line(c, 535, top_y + 22, 560, top_y + 22, color=PURPLE, width=1.5)

    # Intelligence
    draw_rounded_rect(c, 560, top_y, 155, 44, r=8, fill_color=DARK_CARD, stroke_color=TEAL)
    draw_text(c, "INTELLIGENCE", 578, top_y + 28, size=11, color=TEAL)
    draw_text(c, "Feeds ALL departments", 578, top_y + 14, size=7, color=WHITE, font="Helvetica")
    draw_text(c, "Research + Track + Validate", 578, top_y + 4, size=6, color=GRAY, font="Helvetica")

    # ─── DEPARTMENTS ───
    dept_y = top_y - 32

    # Column positions
    col1 = 20    # Content Production
    col2 = 188   # Sales
    col3 = 370   # Delivery
    col4 = 545   # Intelligence
    col_w = 158

    # Vertical lines
    for cx in [col1 + 75, col2 + 85, col3 + 75, col4 + 75]:
        draw_line(c, cx, top_y, cx, dept_y, color=CARD_BORDER, width=0.8)

    # ─── CONTENT PRODUCTION ───
    draw_dept_header(c, col1, dept_y - 8, "CONTENT PRODUCTION", ORANGE, w=col_w)
    agents_cp = [
        ("Content Manager", "Calendar, assignments, repurpose"),
        ("Content Writer", "Scripts, captions, Hormozi voice"),
        ("Video Editor", "Long-form + short-form editing"),
        ("Visual Generator", "Carousels, thumbnails, PDFs"),
    ]
    ay = dept_y - 52
    for name, role in agents_cp:
        draw_agent_box(c, col1, ay, name, role, color=ORANGE, w=col_w, h=34)
        ay -= 40

    # ─── SALES ───
    draw_dept_header(c, col2, dept_y - 8, "SALES", GREEN, w=col_w + 10)
    agents_sales = [
        ("Outreach (Setter)", "Cold DMs, qualify, book calls"),
        ("ManyChat Auto", "Inbound triggers \u2192 auto-DM"),
        ("Follow-Up Agent", "Sequences \u2014 day 1, 3, 7"),
        ("Lead Enrichment", "Research prospects pre-contact"),
        ("CRM Agent", "Pipeline, deals, tracking"),
    ]
    ay = dept_y - 52
    for name, role in agents_sales:
        draw_agent_box(c, col2, ay, name, role, color=GREEN, w=col_w + 10, h=34)
        ay -= 40

    # ─── DELIVERY ───
    draw_dept_header(c, col3, dept_y - 8, "DELIVERY", CYAN, w=col_w)
    agents_del = [
        ("Intake Agent", "Discovery form \u2192 scope \u2192 proposal"),
        ("Project Manager", "Track deliverables, timelines"),
        ("Builder Agent", "Build automation for client"),
        ("Delivery QA", "Test + verify before handoff"),
    ]
    ay = dept_y - 52
    for name, role in agents_del:
        draw_agent_box(c, col3, ay, name, role, color=CYAN, w=col_w, h=34)
        ay -= 40

    # ─── INTELLIGENCE ───
    draw_dept_header(c, col4, dept_y - 8, "INTELLIGENCE UNIT", TEAL, w=col_w + 15)
    agents_intel = [
        ("Competitor Researcher", "What they do + what works"),
        ("ICP / Market Researcher", "Audience pain + language"),
        ("Market & Service", "Validate offer, pricing, PMF"),
        ("Performance Analyst", "Rolling avg, post-mortems"),
    ]
    ay = dept_y - 52
    for name, role in agents_intel:
        draw_agent_box(c, col4, ay, name, role, color=TEAL, w=col_w + 15, h=34)
        ay -= 40

    # Intel output box
    ay -= 8
    draw_rounded_rect(c, col4 + 5, ay, col_w + 5, 32, r=6, fill_color=HexColor("#0d2a2a"), stroke_color=TEAL)
    draw_text(c, "reference/intel/", col4 + 14, ay + 18, size=7, color=TEAL, font="Helvetica-Bold")
    draw_text(c, "7 living docs \u2014 auto-updated weekly", col4 + 14, ay + 6, size=6, color=GRAY, font="Helvetica")

    # Intel feeds all (dashed)
    feed_y = dept_y - 100
    for target_x in [col1 + 80, col2 + 90, col3 + 80]:
        draw_line(c, col4, feed_y, target_x, feed_y, color=TEAL, width=0.7, dash=[3, 3])

    # ─── QA TIERS ───
    qa_y = 62
    draw_rounded_rect(c, 20, qa_y - 5, W - 40, 50, r=8, fill_color=HexColor("#1a0a2a"), stroke_color=PURPLE)
    draw_text(c, "QA TIERS (Brand Manager)", 35, qa_y + 30, size=9, color=PURPLE, font="Helvetica-Bold")
    draw_text(c, "Tier 1 AUTO-APPROVE: Carousels, FB posts, follow-ups using approved templates", 35, qa_y + 16, size=7, color=LIGHT_GRAY, font="Helvetica")
    draw_text(c, "Tier 2 SPOT-CHECK: Outreach DMs, new template variants, repurposed content", 35, qa_y + 4, size=7, color=LIGHT_GRAY, font="Helvetica")
    draw_text(c, "Tier 3 FULL REVIEW: YouTube scripts, landing pages, proposals, anything new or client-facing", 350, qa_y + 16, size=7, color=WHITE, font="Helvetica")
    draw_text(c, "As calibration builds, more items move from Tier 3 \u2192 Tier 2 \u2192 Tier 1", 350, qa_y + 4, size=7, color=GOLD, font="Helvetica")

    # Legend
    draw_text(c, "17 Personal Brand Agents  |  5 Departments  |  4 Self-Improvement Loops  |  7 Living Intel Docs  |  1 Human",
              W / 2, 25, size=7, color=GRAY, font="Helvetica", align="center")


# ─── PAGE 3: SELF-IMPROVEMENT LOOPS ───

def page_data_flow(c):
    draw_bg(c)

    draw_text(c, "SELF-IMPROVEMENT LOOPS", 30, H - 35, size=18, color=GOLD)
    draw_text(c, "How the system gets better without Allen touching it", 30, H - 52, size=10, color=LIGHT_GRAY, font="Helvetica")

    # Loop 1: Content Performance
    loop_y = H - 95
    draw_dept_header(c, 30, loop_y, "1. CONTENT PERFORMANCE LOOP", ORANGE, w=280)
    steps = [
        ("Content Production", "publishes content", ORANGE),
        ("Performance Analyst", "tracks metrics (CTR, views, engagement)", TEAL),
        ("", "updates content-whats-working.md", TEAL),
        ("Content Manager", "reads latest intel before planning", ORANGE),
        ("", "next content is based on what WORKED", GOLD),
    ]
    sy = loop_y - 28
    for agent, action, color in steps:
        if agent:
            draw_text(c, agent, 40, sy, size=8, color=color, font="Helvetica-Bold")
            draw_text(c, f"  \u2192  {action}", 40 + c.stringWidth(agent, "Helvetica-Bold", 8), sy, size=8, color=LIGHT_GRAY, font="Helvetica")
        else:
            draw_text(c, f"     \u2192  {action}", 40, sy, size=8, color=LIGHT_GRAY, font="Helvetica")
        sy -= 17
    sy -= 6
    draw_rounded_rect(c, 35, sy - 6, 340, 20, r=4, fill_color=HexColor("#1a1a0a"), stroke_color=GOLD)
    draw_text(c, "RATCHET: 3 misses in a row \u2192 playbook rewrites itself from latest winners", 42, sy, size=7, color=GOLD, font="Helvetica-Bold")

    # Loop 2: Sales Feedback
    loop2_y = H - 95
    draw_dept_header(c, 430, loop2_y, "2. SALES \u2192 MARKETING FEEDBACK", GREEN, w=280)
    steps2 = [
        ("Sales", "closes (or loses) a deal", GREEN),
        ("CRM Agent", "tags deal with content source", GREEN),
        ("Performance Analyst", "tracks which content \u2192 closed deals", TEAL),
        ("", "updates ads-whats-working.md", TEAL),
        ("Content Production", "doubles down on content that CONVERTS", ORANGE),
    ]
    sy = loop2_y - 28
    for agent, action, color in steps2:
        if agent:
            draw_text(c, agent, 440, sy, size=8, color=color, font="Helvetica-Bold")
            draw_text(c, f"  \u2192  {action}", 440 + c.stringWidth(agent, "Helvetica-Bold", 8), sy, size=8, color=LIGHT_GRAY, font="Helvetica")
        else:
            draw_text(c, f"     \u2192  {action}", 440, sy, size=8, color=LIGHT_GRAY, font="Helvetica")
        sy -= 17
    sy -= 6
    draw_rounded_rect(c, 435, sy - 6, 370, 20, r=4, fill_color=HexColor("#0a1a0a"), stroke_color=GREEN)
    draw_text(c, "RESULT: Marketing stops guessing. Only makes content that drives revenue.", 442, sy, size=7, color=GREEN, font="Helvetica-Bold")

    # Loop 3: Intelligence
    loop3_y = H - 290
    draw_dept_header(c, 30, loop3_y, "3. INTELLIGENCE LOOP", TEAL, w=280)
    steps3 = [
        ("Competitor Researcher", "scans what competitors post + sell", TEAL),
        ("ICP Researcher", "monitors audience pain points + language", TEAL),
        ("Market & Service", "validates offer positioning + pricing", TEAL),
        ("", "writes to reference/intel/ (7 living docs)", TEAL),
        ("ALL departments", "read latest intel before doing ANY work", GOLD),
    ]
    sy = loop3_y - 28
    for agent, action, color in steps3:
        if agent:
            draw_text(c, agent, 40, sy, size=8, color=color, font="Helvetica-Bold")
            draw_text(c, f"  \u2192  {action}", 40 + c.stringWidth(agent, "Helvetica-Bold", 8), sy, size=8, color=LIGHT_GRAY, font="Helvetica")
        else:
            draw_text(c, f"     \u2192  {action}", 40, sy, size=8, color=LIGHT_GRAY, font="Helvetica")
        sy -= 17

    # Loop 4: Review Gate Ratchet
    loop4_y = H - 290
    draw_dept_header(c, 430, loop4_y, "4. REVIEW GATE RATCHET", PURPLE, w=280)
    steps4 = [
        ("Week 1-4:", "Allen approves everything", PURPLE),
        ("Week 5-8:", "Allen spot-checks 1 in 3", PURPLE),
        ("Week 9+:", "Allen only reviews flagged items", PURPLE),
        ("Brand Manager", "handles routine QA automatically", PURPLE),
        ("", "Allen's time freed for closing + recording", GOLD),
    ]
    sy = loop4_y - 28
    for agent, action, color in steps4:
        if agent:
            draw_text(c, agent, 440, sy, size=8, color=color, font="Helvetica-Bold")
            draw_text(c, f"  {action}", 440 + c.stringWidth(agent, "Helvetica-Bold", 8), sy, size=8, color=LIGHT_GRAY, font="Helvetica")
        else:
            draw_text(c, f"     {action}", 440, sy, size=8, color=LIGHT_GRAY, font="Helvetica")
        sy -= 17

    # Living Docs
    docs_y = 85
    draw_dept_header(c, 30, docs_y + 45, "LIVING INTELLIGENCE DOCS (reference/intel/)", TEAL, w=400)
    docs = [
        ("content-whats-working.md", "Best hooks, formats, topics by performance data"),
        ("ads-whats-working.md", "Ad creative, targeting, CTA that converts"),
        ("outreach-whats-working.md", "DM templates, response rates, best openers"),
        ("competitor-moves.md", "What competitors do + gaps we can exploit"),
        ("icp-language.md", "Exact words our audience uses for their pain"),
        ("market-validation.md", "Offer tests, pricing data, PMF signals, objections"),
        ("performance-scorecard.md", "Rolling averages per content type + format"),
    ]
    dy = docs_y
    for fname, desc in docs:
        draw_text(c, fname, 40, dy, size=7, color=TEAL, font="Helvetica-Bold")
        draw_text(c, f" \u2014 {desc}", 40 + c.stringWidth(fname, "Helvetica-Bold", 7), dy, size=7, color=GRAY, font="Helvetica")
        dy -= 14


# ─── PAGE 4: PUSH ALLEN SYSTEM ───

def page_push_allen(c):
    draw_bg(c)

    draw_text(c, "PUSH ALLEN SYSTEM", 30, H - 35, size=18, color=GOLD)
    draw_text(c, "The EA's job is to push Allen to do MORE, not wait for instructions", 30, H - 52, size=10, color=LIGHT_GRAY, font="Helvetica")

    # Concept
    cy = H - 90
    draw_text(c, "THE PROBLEM", 30, cy, size=12, color=RED, font="Helvetica-Bold")
    draw_text(c, "Allen is the bottleneck. If Allen doesn't record, the content machine has nothing to process.", 30, cy - 20, size=9, color=LIGHT_GRAY, font="Helvetica")
    draw_text(c, "If Allen doesn't close, revenue doesn't come in. The system must PUSH Allen, not wait for him.", 30, cy - 36, size=9, color=LIGHT_GRAY, font="Helvetica")

    # Mechanisms
    my = cy - 75
    draw_text(c, "HOW THE EA PUSHES ALLEN", 30, my, size=12, color=GOLD, font="Helvetica-Bold")

    mechanisms = [
        ("CONTENT BUFFER ALERT", "EA tracks how many weeks of raw content are recorded ahead. If buffer drops below 1 week, EA flags it at session start: \"Buffer is low. Block 2 hours this week to batch record.\"", ORANGE),
        ("DAILY SCORECARD", "EA starts every session with: content published today, leads generated, follow-ups sent, deals in pipeline. Numbers, not vibes. Allen sees what's moving and what's stuck.", BLUE),
        ("WEEKLY REVIEW PUSH", "Every Monday, EA runs a 5-min review: what worked last week (from Performance Analyst), what's planned this week, what's overdue. No new work until Allen reviews.", PURPLE),
        ("RECORDING PROMPT", "When Content Manager has scripts ready but no raw footage, EA pushes: \"3 scripts are waiting. Your topics: [list]. Want to record today or schedule for tomorrow?\"", ORANGE),
        ("OUTREACH ACCOUNTABILITY", "EA tracks DMs sent vs target (30-50/day). If Allen falls behind, EA flags it. If outreach agent has drafted messages waiting, EA surfaces them.", GREEN),
        ("CLOSE THE LOOP", "When a lead replies, EA escalates immediately: \"[Name] replied to your DM. They're interested in [X]. Here's context. Respond now — speed to lead wins.\"", GREEN),
        ("AUTONOMOUS CONTENT", "Carousels, FB group posts, LinkedIn posts DON'T need Allen to record. Content Manager can generate these from existing scripts + intel. EA should push these out without waiting.", ORANGE),
    ]

    for title, desc, color in mechanisms:
        my -= 8
        draw_rounded_rect(c, 25, my - 30, W - 50, 38, r=6, fill_color=DARK_CARD, stroke_color=color)
        draw_text(c, title, 38, my - 2, size=8, color=color, font="Helvetica-Bold")
        # Word wrap the description
        words = desc.split()
        line = ""
        lx = 38
        ly = my - 16
        for w in words:
            test = f"{line} {w}".strip()
            if c.stringWidth(test, "Helvetica", 7) < W - 90:
                line = test
            else:
                draw_text(c, line, lx, ly, size=7, color=LIGHT_GRAY, font="Helvetica")
                ly -= 11
                line = w
        if line:
            draw_text(c, line, lx, ly, size=7, color=LIGHT_GRAY, font="Helvetica")
        my -= 38

    # North star
    draw_rounded_rect(c, 25, 22, W - 50, 28, r=6, fill_color=HexColor("#1a1a0a"), stroke_color=GOLD)
    draw_text(c, "NORTH STAR: Every week, Allen does LESS than the week before. The system does MORE.",
              W / 2, 32, size=9, color=GOLD, font="Helvetica-Bold", align="center")


# ─── PAGE 5: AGENT REGISTRY ───

def page_agent_registry(c):
    draw_bg(c)

    draw_text(c, "AGENT REGISTRY", 30, H - 35, size=18, color=GOLD)
    draw_text(c, "Every agent, department, job, inputs, outputs", 30, H - 52, size=10, color=LIGHT_GRAY, font="Helvetica")

    ty = H - 78
    cols = [30, 95, 230, 420, 590]
    headers = ["Dept", "Agent", "Job", "Reads", "Outputs"]
    for i, h in enumerate(headers):
        draw_text(c, h, cols[i], ty, size=8, color=GOLD, font="Helvetica-Bold")
    ty -= 4
    draw_line(c, 30, ty, W - 30, ty, color=CARD_BORDER)

    rows = [
        ("INTEL", "competitor-researcher", "Monitor competitor content + offers", "Web, social platforms", "competitor-moves.md"),
        ("INTEL", "icp-researcher", "Track audience pain + language", "FB groups, forums, trends", "icp-language.md"),
        ("INTEL", "market-service", "Validate offer, pricing, PMF", "Web, competitor pricing", "market-validation.md"),
        ("INTEL", "performance-analyst", "Rolling averages, post-mortems", "Analytics, CRM data", "performance-scorecard.md"),
        ("CONTENT", "content-manager", "Plan calendar, assign, repurpose", "intel/, content-calendar.md", "Production schedule"),
        ("CONTENT", "content-writer", "Scripts, captions, posts", "intel/, hormozi-style-guide", "Scripts, copy"),
        ("CONTENT", "video-editor", "Edit long + short-form video", "content-formats.md, footage", "Final video + timeline"),
        ("CONTENT", "visual-generator", "Carousels, thumbnails, PDFs", "content-formats.md, intel/", "PNGs, PDFs"),
        ("SALES", "outreach-agent", "Cold DMs, qualify, book calls", "outreach.md, intel/", "DM drafts, log"),
        ("SALES", "manychat-auto", "Inbound triggers \u2192 auto-DM", "manychat-setup.md", "Auto-DMs"),
        ("SALES", "follow-up-agent", "Timed follow-up sequences", "outreach.md, CRM", "Follow-up msgs"),
        ("SALES", "lead-enrichment", "Research prospects pre-contact", "Web, social profiles", "Prospect profiles"),
        ("SALES", "crm-agent", "Pipeline tracking, deal mgmt", "CRM data, intel/", "Pipeline updates"),
        ("DELIVER", "intake-agent", "Discovery \u2192 scope \u2192 proposal", "Brand agent, templates", "Proposal doc"),
        ("DELIVER", "project-manager", "Track deliverables + timelines", "Client scope, calendar", "Status updates"),
        ("DELIVER", "builder-agent", "Build automation for client", "Scope doc, tools/", "Working system"),
        ("DELIVER", "delivery-qa", "Test + verify before handoff", "Deliverables, scope", "QA pass/fail"),
        ("EPS", "eps-quote-agent", "Quote creation pipeline", "calculate_quote.py", "Quote doc"),
        ("EPS", "eps-email-agent", "Client emails", "Deal context", "Sent emails"),
        ("EPS", "eps-crm-agent", "Pipedrive specialist", "Pipedrive API", "CRM updates"),
        ("EPS", "eps-call-notes", "Transcript \u2192 notes \u2192 deal", "JustCall", "Deal notes"),
        ("EPS", "eps-qa-agent", "Reviews quotes + emails", "Doc + email draft", "QA pass/fail"),
        ("EPS", "eps-e1-scraper", "Tenders + builders \u2192 Sheet", "EstimateOne", "Sheet data"),
    ]

    dept_colors = {"INTEL": TEAL, "CONTENT": ORANGE, "SALES": GREEN, "DELIVER": CYAN, "EPS": RED}

    ty -= 13
    for dept, agent, job, reads, outputs in rows:
        color = dept_colors.get(dept, WHITE)
        draw_text(c, dept, cols[0], ty, size=6, color=color, font="Helvetica-Bold")
        draw_text(c, agent, cols[1], ty, size=6, color=WHITE, font="Helvetica")
        draw_text(c, job, cols[2], ty, size=6, color=LIGHT_GRAY, font="Helvetica")
        draw_text(c, reads, cols[3], ty, size=5.5, color=GRAY, font="Helvetica")
        draw_text(c, outputs, cols[4], ty, size=5.5, color=GRAY, font="Helvetica")
        ty -= 13
        if ty < 40:
            break

    draw_text(c, "23 agents total  |  5 departments  |  7 living intel docs  |  4 self-improvement loops  |  1 human",
              30, 22, size=8, color=GOLD, font="Helvetica-Bold")


# ─── PAGE 6: EPS OPERATIONS ───

def page_eps(c):
    draw_bg(c)

    draw_text(c, "EPS — OPERATIONS", 30, H - 35, size=18, color=RED)
    draw_text(c, "Essential Property Solutions  |  Painting & Cleaning  |  Brisbane AU", 30, H - 52, size=10, color=LIGHT_GRAY, font="Helvetica")
    draw_text(c, "Allen = Sales Manager  |  Remote from Philippines  |  Separate domain from Personal Brand", 30, H - 67, size=8, color=GRAY, font="Helvetica")

    # Stack
    stack_y = H - 100
    draw_text(c, "TECH STACK", 30, stack_y, size=10, color=RED, font="Helvetica-Bold")
    stack_items = [
        ("Pipedrive", "Sales CRM \u2014 pipeline, deals, quotes"),
        ("JustCall", "Calls & comms, integrated with Pipedrive"),
        ("ServiceM8", "Job management for operations team"),
        ("EstimateOne", "Commercial tender platform (scraped daily)"),
        ("Google Workspace", "Docs, Sheets, Drive"),
        ("Gmail", "Client emails via sales@epsolution.com.au"),
    ]
    sy = stack_y - 20
    for name, desc in stack_items:
        draw_text(c, name, 40, sy, size=8, color=WHITE, font="Helvetica-Bold")
        draw_text(c, f"  \u2014  {desc}", 40 + c.stringWidth(name, "Helvetica-Bold", 8), sy, size=8, color=GRAY, font="Helvetica")
        sy -= 16

    # Agent structure
    agent_y = H - 110
    agent_x = 430

    draw_text(c, "AGENT STRUCTURE", agent_x, agent_y, size=10, color=RED, font="Helvetica-Bold")

    ay = agent_y - 28
    draw_rounded_rect(c, agent_x, ay, 190, 36, r=8, fill_color=DARK_CARD, stroke_color=GOLD)
    draw_text(c, "ALLEN \u2014 Sales Manager", agent_x + 15, ay + 22, size=9, color=GOLD)
    draw_text(c, "Closes deals. Reviews. Approves.", agent_x + 15, ay + 8, size=7, color=GRAY, font="Helvetica")

    draw_line(c, agent_x + 95, ay, agent_x + 95, ay - 12, color=CARD_BORDER)

    ay -= 50
    draw_rounded_rect(c, agent_x, ay, 190, 36, r=8, fill_color=DARK_CARD, stroke_color=PURPLE)
    draw_text(c, "QA AGENT", agent_x + 15, ay + 22, size=9, color=PURPLE)
    draw_text(c, "Nothing client-facing ships without QA", agent_x + 15, ay + 8, size=7, color=GRAY, font="Helvetica")

    draw_line(c, agent_x + 95, ay, agent_x + 95, ay - 12, color=CARD_BORDER)

    ay -= 48
    agents = [
        ("Quote Agent", "Intake \u2192 line items \u2192 Google Doc"),
        ("Email Agent", "Draft + send client emails"),
        ("CRM Agent", "Pipedrive specialist"),
        ("Call Notes", "Transcript \u2192 notes \u2192 deal"),
        ("Cold Calls", "Batch process cold leads"),
        ("E1 Scraper", "Tenders + builders \u2192 Sheet"),
    ]
    for name, role in agents:
        draw_rounded_rect(c, agent_x, ay, 190, 36, r=6, fill_color=DARK_CARD, stroke_color=RED)
        draw_text(c, name, agent_x + 12, ay + 22, size=8, color=WHITE, font="Helvetica-Bold")
        draw_text(c, role, agent_x + 12, ay + 8, size=6.5, color=LIGHT_GRAY, font="Helvetica")
        ay -= 42

    # Workflow
    wf_y = H - 260
    draw_text(c, "DAILY WORKFLOW", 30, wf_y, size=10, color=RED, font="Helvetica-Bold")
    workflow = [
        ("6:00 AM", "E1 Scraper runs (launchd)", "Auto"),
        ("8:00 AM", "Briefing: overdue tasks, new leads", "Auto \u2192 Allen reviews"),
        ("9:00 AM", "Allen takes calls, AI processes notes", "Allen talks, AI writes"),
        ("Ongoing", "Quote Agent generates from call context", "Allen reviews, QA checks"),
        ("Ongoing", "Email Agent drafts follow-ups", "Allen approves, AI sends"),
        ("5:00 PM", "Cold call batch processing", "Allen calls, AI logs"),
    ]
    wy = wf_y - 22
    for time, action, mode in workflow:
        draw_text(c, time, 40, wy, size=8, color=RED, font="Helvetica-Bold")
        draw_text(c, action, 110, wy, size=8, color=WHITE, font="Helvetica")
        draw_text(c, f"({mode})", 110 + c.stringWidth(action, "Helvetica", 8) + 8, wy, size=7, color=GRAY, font="Helvetica")
        wy -= 17

    # Tone
    cs_y = wf_y - 180
    draw_text(c, "COMMUNICATION STYLE (different from personal brand)", 30, cs_y, size=10, color=RED, font="Helvetica-Bold")
    style_rules = [
        "Spartan. Simple English (3rd-5th grade). Bullet points.",
        "Straightforward, neutral, problem-focused. No fluff.",
        "Focus on client's problem, not features. Short and scannable.",
        "NOT educator voice. This is professional services communication.",
    ]
    sry = cs_y - 18
    for rule in style_rules:
        draw_text(c, f"\u2022  {rule}", 40, sry, size=8, color=LIGHT_GRAY, font="Helvetica")
        sry -= 15

    draw_text(c, "6 agents  |  QA gate  |  Own tone  |  Separate from personal brand",
              30, 25, size=8, color=RED, font="Helvetica-Bold")


# ─── BUILD PDF ───
c = canvas.Canvas(OUTPUT, pagesize=landscape(A4))

page_cover(c)
c.showPage()

page_org_chart(c)
c.showPage()

page_data_flow(c)
c.showPage()

page_push_allen(c)
c.showPage()

page_agent_registry(c)
c.showPage()

page_eps(c)
c.showPage()

c.save()
print(f"PDF saved to: {OUTPUT}")
