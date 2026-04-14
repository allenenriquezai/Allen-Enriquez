"""
generate_eps_system_map.py — Generate EPS Sales Operations PDF.

Shows the full business lifecycle organized by department.
Designed for the team to understand how everything connects.

Usage:
    python3 tools/generate_eps_system_map.py
"""

import math
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

OUT_DIR = Path(__file__).parent.parent / "projects" / "eps" / ".tmp"
OUT_FILE = OUT_DIR / "EPS_Operations_System_Map.pdf"

# --- Colors ---
BG = HexColor("#0F1117")
CARD_BG = HexColor("#1A1D27")
CARD_BORDER = HexColor("#2A2D37")
BLUE = HexColor("#02B3E9")
GREEN = HexColor("#22C55E")
AMBER = HexColor("#F59E0B")
RED = HexColor("#EF4444")
PURPLE = HexColor("#A855F7")
PINK = HexColor("#EC4899")
CYAN = HexColor("#06B6D4")
WHITE = HexColor("#FFFFFF")
GRAY = HexColor("#9CA3AF")
DARK_GRAY = HexColor("#4B5563")
CARD_TEXT = HexColor("#E5E7EB")

W, H = landscape(A4)


def bg(c):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)


def rrect(c, x, y, w, h, r=6, fill=CARD_BG, border=CARD_BORDER, bw=1):
    c.setFillColor(fill)
    c.setStrokeColor(border)
    c.setLineWidth(bw)
    c.roundRect(x, y, w, h, r, fill=1, stroke=1)


def txt(c, x, y, text, size=10, color=WHITE, font="Helvetica", mw=None):
    c.setFont(font, size)
    c.setFillColor(color)
    if mw:
        while c.stringWidth(text, font, size) > mw and size > 5:
            size -= 0.5
            c.setFont(font, size)
    c.drawString(x, y, text)


def txt_c(c, x, y, text, size, color, font, w):
    c.setFont(font, size)
    c.setFillColor(color)
    tw = c.stringWidth(text, font, size)
    c.drawString(x + (w - tw) / 2, y, text)


def badge(c, x, y, text, color, size=7):
    c.setFont("Helvetica-Bold", size)
    tw = c.stringWidth(text, "Helvetica-Bold", size)
    pw = tw + 10
    c.setFillColor(color)
    c.roundRect(x, y - 3, pw, size + 7, 4, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.drawString(x + 5, y, text)
    return pw


def arrow_h(c, x1, y1, x2, color=DARK_GRAY, w=1.5):
    c.setStrokeColor(color)
    c.setLineWidth(w)
    c.line(x1, y1, x2, y1)
    c.line(x2, y1, x2 - 4, y1 + 3)
    c.line(x2, y1, x2 - 4, y1 - 3)


def stage_box(c, x, y, w, h, text, color):
    rrect(c, x, y, w, h, 4, CARD_BG, color)
    c.setFont("Helvetica-Bold", 6.5)
    c.setFillColor(CARD_TEXT)
    tw = c.stringWidth(text, "Helvetica-Bold", 6.5)
    if tw > w - 4:
        c.setFont("Helvetica-Bold", 5.5)
        tw = c.stringWidth(text, "Helvetica-Bold", 5.5)
    c.drawString(x + (w - tw) / 2, y + (h - 6) / 2, text)


def dept_header(c, x, y, w, h, num, name, mission, color):
    """Draw a department header bar."""
    c.setFillColor(color)
    c.roundRect(x, y, w, h, 5, fill=1, stroke=0)
    # Dept number
    txt(c, x + 8, y + h - 15, f"DEPT {num}", 8, WHITE, "Helvetica-Bold")
    txt(c, x + 55, y + h - 15, name, 11, WHITE, "Helvetica-Bold")
    txt(c, x + 8, y + 4, mission, 7, HexColor("#FFFFFFCC"))


def agent_row(c, x, y, name, desc, color, is_tool=False):
    """Draw an agent/tool entry."""
    # Dot
    c.setFillColor(color)
    c.circle(x + 5, y + 4, 3, fill=1, stroke=0)
    # Border
    c.setStrokeColor(color)
    c.setLineWidth(0.8)
    label = "TOOL" if is_tool else "AGENT"
    c.setFont("Helvetica-Bold", 6)
    lw = c.stringWidth(label, "Helvetica-Bold", 6)
    # Name
    txt(c, x + 11, y, name, 8, WHITE, "Helvetica-Bold")
    nw = c.stringWidth(name, "Helvetica-Bold", 8)
    # Type badge
    badge(c, x + 14 + nw, y, label, DARK_GRAY if is_tool else color, 5)
    # Description
    txt(c, x + 11, y - 11, desc, 7, GRAY)
    return 24


# ============================================================
# PAGE 1: Department Structure
# ============================================================

def draw_page1(c):
    bg(c)

    txt(c, 30, H - 38, "EPS Sales Operations", 26, BLUE, "Helvetica-Bold")
    txt(c, 30, H - 56, "Department Structure — Organised by Business Lifecycle", 12, GRAY)

    # --- Four department columns ---
    col_w = (W - 70) / 4 - 5
    col_gap = 10
    top_y = H - 80

    # === DEPT 1: LEAD GENERATION ===
    d1_x = 30
    dept_header(c, d1_x, top_y - 25, col_w, 25, "1", "LEAD GEN", "Find new opportunities", PURPLE)

    agents1 = [
        ("EstimateOne Agent", "Scrape E1 daily for tenders + builders", PURPLE, False),
        ("Cold Calls Agent", "Batch process cold leads", PINK, False),
        ("tender_batch.py", "Daily auto: scrape → filter → CRM", PURPLE, True),
        ("crm_monitor.py", "Pipeline health scan", AMBER, True),
    ]

    ay = top_y - 55
    for name, desc, col, is_tool in agents1:
        agent_row(c, d1_x + 5, ay, name, desc, col, is_tool)
        ay -= 26

    # Pipedrive stages
    txt(c, d1_x + 5, ay - 5, "PIPEDRIVE STAGES:", 6, DARK_GRAY, "Helvetica-Bold")
    ay -= 18
    for stage in ["E1 LEADS INBOX", "COLD CALL LEADS"]:
        stage_box(c, d1_x + 5, ay, col_w - 15, 14, stage, PURPLE)
        ay -= 18

    # === DEPT 2: SALES ===
    d2_x = d1_x + col_w + col_gap
    dept_header(c, d2_x, top_y - 25, col_w, 25, "2", "SALES", "Qualify, quote, follow up, close", BLUE)

    agents2 = [
        ("CRM Agent", "Pipedrive read/write specialist", AMBER, False),
        ("Quote Agent", "Intake → line items → Google Doc", GREEN, False),
        ("Email Agent", "Draft + send via Gmail", BLUE, False),
        ("QA Agent", "Two-stage review gate", RED, False),
        ("Call Notes Agent", "Transcript → notes → post to deal", PURPLE, False),
        ("Site Visit Agent", "SM8 + calendar + booking", GREEN, False),
    ]

    ay = top_y - 55
    for name, desc, col, is_tool in agents2:
        agent_row(c, d2_x + 5, ay, name, desc, col, is_tool)
        ay -= 26

    txt(c, d2_x + 5, ay - 5, "PIPEDRIVE STAGES:", 6, DARK_GRAY, "Helvetica-Bold")
    ay -= 18
    for stage in ["NEW", "SITE VISIT", "QUOTE IN PROGRESS", "QUOTE SENT", "NEGOTIATION", "LATE FOLLOW UP", "DEPOSIT PROCESS"]:
        stage_box(c, d2_x + 5, ay, col_w - 15, 13, stage, BLUE)
        ay -= 16

    # === DEPT 3: OPERATIONS ===
    d3_x = d2_x + col_w + col_gap
    dept_header(c, d3_x, top_y - 25, col_w, 25, "3", "OPERATIONS", "Deliver the work", CYAN)

    agents3 = [
        ("Site Visit Agent", "Schedule on SM8 (shared)", GREEN, False),
        ("crm_sync.py", "EOD Pipedrive ↔ SM8 sync", CYAN, True),
        ("push_sm8_job.py", "Quote data → SM8 job card", CYAN, True),
        ("schedule_sm8_visit.py", "3-calendar check + booking", CYAN, True),
    ]

    ay = top_y - 55
    for name, desc, col, is_tool in agents3:
        agent_row(c, d3_x + 5, ay, name, desc, col, is_tool)
        ay -= 26

    txt(c, d3_x + 5, ay - 5, "PROJECT PHASES:", 6, DARK_GRAY, "Helvetica-Bold")
    ay -= 18
    for stage in ["NEW", "PENDING BOOKING", "BOOKED", "FIX-UPS", "COMPLETED", "VARIATIONS", "FINAL INVOICE"]:
        stage_box(c, d3_x + 5, ay, col_w - 15, 13, stage, CYAN)
        ay -= 16

    # === DEPT 4: RETENTION ===
    d4_x = d3_x + col_w + col_gap
    dept_header(c, d4_x, top_y - 25, col_w, 25, "4", "RETENTION", "Repeat business + reviews", PINK)

    agents4 = [
        ("reengage_campaign.py", "Weekly scan: clients + lost deals", PINK, True),
        ("Email Agent", "Send re-engagement emails (shared)", BLUE, False),
    ]

    ay = top_y - 55
    for name, desc, col, is_tool in agents4:
        agent_row(c, d4_x + 5, ay, name, desc, col, is_tool)
        ay -= 26

    txt(c, d4_x + 5, ay - 5, "RE-ENGAGEMENT PHASES:", 6, DARK_GRAY, "Helvetica-Bold")
    ay -= 18
    for stage in ["NEW / FOR REVIEW", "ADDED TO SEQUENCE", "CONTACT MADE", "GOOGLE REVIEW DONE", "INTERESTED / CROSS-SELL", "NOT INTERESTED"]:
        stage_box(c, d4_x + 5, ay, col_w - 15, 13, stage, PINK)
        ay -= 16

    # Win-back idea
    ay -= 8
    rrect(c, d4_x + 5, ay - 5, col_w - 15, 18, border=DARK_GRAY)
    txt(c, d4_x + 12, ay, "IDEA: Win-Back Lost Deals Agent", 7, AMBER, "Helvetica-Bold")

    # --- Flow arrows between departments ---
    arrow_y = top_y - 12
    arrow_h(c, d1_x + col_w, arrow_y, d2_x, PURPLE, 2)
    arrow_h(c, d2_x + col_w, arrow_y, d3_x, BLUE, 2)
    arrow_h(c, d3_x + col_w, arrow_y, d4_x, CYAN, 2)

    # Footer
    txt(c, 30, 20, "EPS Sales Operations — Enriquez OS", 8, DARK_GRAY)
    txt(c, W - 100, 20, "Page 1 of 2", 8, DARK_GRAY)


# ============================================================
# PAGE 2: Daily Automations + Campaign
# ============================================================

def draw_page2(c):
    bg(c)

    txt(c, 30, H - 38, "Daily Automations", 26, BLUE, "Helvetica-Bold")
    txt(c, 30, H - 56, "What runs every day without Allen touching anything", 12, GRAY)

    # --- Three automation blocks ---
    block_w = (W - 80) / 3 - 5
    block_h = 130

    # 6AM Block
    b1_x = 30
    b1_y = H - 90 - block_h
    rrect(c, b1_x, b1_y, block_w, block_h, border=PURPLE)
    c.setFillColor(PURPLE)
    c.roundRect(b1_x, b1_y + block_h - 3, block_w, 3, 2, fill=1, stroke=0)
    txt(c, b1_x + 12, b1_y + block_h - 20, "6:00 AM — E1 Scrape", 11, PURPLE, "Helvetica-Bold")
    txt(c, b1_x + 12, b1_y + block_h - 32, "Dept 1: Lead Gen", 7, GRAY)

    steps1 = [
        "Scrape E1 for new leads + open tenders",
        "Filter by trades: Painting + Building Cleaning",
        "Download tender documents (plans, specs)",
        "Analyze specs with AI (~$0.01/tender)",
        "Create Pipedrive deals for new tenders",
        "Update Google Sheet tender inbox",
    ]
    sy = b1_y + block_h - 48
    for i, step in enumerate(steps1):
        txt(c, b1_x + 12, sy, f"{i+1}. {step}", 7, CARD_TEXT)
        sy -= 12

    # EOD Block
    b2_x = b1_x + block_w + 15
    rrect(c, b2_x, b1_y, block_w, block_h, border=AMBER)
    c.setFillColor(AMBER)
    c.roundRect(b2_x, b1_y + block_h - 3, block_w, 3, 2, fill=1, stroke=0)
    txt(c, b2_x + 12, b1_y + block_h - 20, "End of Day — CRM Sweep", 11, AMBER, "Helvetica-Bold")
    txt(c, b2_x + 12, b1_y + block_h - 32, "Cross-Department", 7, GRAY)

    steps2 = [
        "Flag follow-ups due tomorrow",
        "Flag stale deals (no activity 2+ weeks)",
        "Flag quotes sent with no response",
        "Sync ServiceM8 ↔ Pipedrive data",
        "Surface pending deposits",
        "Generate daily summary",
    ]
    sy = b1_y + block_h - 48
    for i, step in enumerate(steps2):
        txt(c, b2_x + 12, sy, f"{i+1}. {step}", 7, CARD_TEXT)
        sy -= 12

    # Weekly Block
    b3_x = b2_x + block_w + 15
    rrect(c, b3_x, b1_y, block_w, block_h, border=PINK)
    c.setFillColor(PINK)
    c.roundRect(b3_x, b1_y + block_h - 3, block_w, 3, 2, fill=1, stroke=0)
    txt(c, b3_x + 12, b1_y + block_h - 20, "Weekly — Re-engagement", 11, PINK, "Helvetica-Bold")
    txt(c, b3_x + 12, b1_y + block_h - 32, "Dept 4: Retention", 7, GRAY)

    steps3 = [
        "Scan completed projects (30+ days old)",
        "Scan re-engagement boards for new clients",
        "Scan lost deals (last 6 months)",
        "Draft check-in emails (template)",
        "Draft win-back emails (template)",
        "Allen reviews + approves → send",
    ]
    sy = b1_y + block_h - 48
    for i, step in enumerate(steps3):
        txt(c, b3_x + 12, sy, f"{i+1}. {step}", 7, CARD_TEXT)
        sy -= 12

    # --- Tender Campaign ---
    tc_y = b1_y - 30
    txt(c, 30, tc_y, "TENDER CAMPAIGN — Multi-Angle Attack", 14, BLUE, "Helvetica-Bold")

    angles = [
        ("ANGLE 1", "Quote Every Tender", BLUE,
         ["E1 scrape finds painting/cleaning tenders",
          "AI analyzes specs → generates quotes",
          "Allen reviews → sends same day"]),
        ("ANGLE 2", "Cold Call Builders", PINK,
         ["29 new builders from E1 directory",
          "Loaded into Pipedrive Leads inbox",
          "Team calls through the list"]),
        ("ANGLE 3", "Follow Up Everything", GREEN,
         ["Every quote gets 2-week follow-up",
          "CRM flags when follow-ups due",
          "No tender goes unanswered"]),
        ("ANGLE 4", "Relationship Play", AMBER,
         ["Builder gets: quote + call + follow-up",
          "Three touches vs competitor's one",
          "Repeat business builds naturally"]),
    ]

    aw = (W - 80) / 4 - 5
    ah = 70
    for idx, (label, title, col, points) in enumerate(angles):
        x = 30 + idx * (aw + 10)
        ay = tc_y - ah - 10
        rrect(c, x, ay, aw, ah, border=col)
        c.setFillColor(col)
        c.roundRect(x, ay + ah - 3, aw, 3, 2, fill=1, stroke=0)

        badge(c, x + 8, ay + ah - 18, label, col, 6)
        txt(c, x + 55, ay + ah - 18, title, 8, WHITE, "Helvetica-Bold")

        py = ay + ah - 32
        for point in points:
            txt(c, x + 8, py, f"• {point}", 7, CARD_TEXT, mw=aw - 16)
            py -= 11

    # --- Cost ---
    cost_y = tc_y - ah - 50
    rrect(c, 30, cost_y - 25, W - 60, 25)
    txt(c, 45, cost_y - 12, "DAILY COST:", 10, WHITE, "Helvetica-Bold")
    costs = [("E1 Scrape", "$0"), ("Spec Analysis", "~$0.10"), ("CRM Ops", "$0"),
             ("Quotes", "$0"), ("SM8 Sync", "$0")]
    cx = 170
    for label, val in costs:
        txt(c, cx, cost_y - 8, label, 7, GRAY)
        txt(c, cx, cost_y - 18, val, 8, GREEN if val == "$0" else AMBER, "Helvetica-Bold")
        cx += 110
    txt(c, cx + 10, cost_y - 8, "TOTAL/DAY", 7, WHITE, "Helvetica-Bold")
    txt(c, cx + 10, cost_y - 18, "~$0.10", 10, GREEN, "Helvetica-Bold")

    txt(c, 30, 20, "EPS Sales Operations — Enriquez OS", 8, DARK_GRAY)
    txt(c, W - 100, 20, "Page 2 of 2", 8, DARK_GRAY)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT_FILE), pagesize=landscape(A4))
    draw_page1(c)
    c.showPage()
    draw_page2(c)
    c.save()
    print(f"PDF generated: {OUT_FILE}")
    print(f"  Pages: 2 | Size: {OUT_FILE.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
