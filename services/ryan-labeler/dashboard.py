"""Live HTML dashboard for Ryan — branded, interactive, Gmail-linked."""
from __future__ import annotations
from datetime import datetime, timezone

from briefer import (
    fetch_overnight_messages,
    fetch_calendar_today,
    fetch_team_daily_today,
    fetch_inbox_grouped,
    fetch_upcoming_calendar,
    find_urgent,
    _pt_now,
)


def _fmt_time(start: str) -> str:
    if "T" not in start:
        return "all day"
    try:
        dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        return dt.strftime("%-I:%M %p").lstrip("0")
    except Exception:
        return start


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def _gmail_link(thread_id: str) -> str:
    if thread_id:
        return f"https://mail.google.com/mail/u/0/#all/{thread_id}"
    return "https://mail.google.com/mail/u/0/"


def _nav_tabs_html(token: str, active: str = "dashboard") -> str:
    def _tab(label: str, href: str, key: str) -> str:
        cls = "dtab active" if active == key else "dtab"
        return f'<a class="{cls}" href="{href}?token={token}">{label}</a>'
    return (
        '<div class="tabs-bar">'
        + _tab("Dashboard", "/dashboard", "dashboard")
        + _tab("Inbox", "/inbox", "inbox")
        + _tab("Calendar", "/calendar", "calendar")
        + _tab("Morning Brief", "/brief-preview", "morning")
        + _tab("Evening Brief", "/evening-brief-preview", "evening")
        + '</div>'
    )


def render_dashboard(token: str = "ryan-sc") -> str:
    messages   = fetch_overnight_messages(hours_back=14)
    events     = fetch_calendar_today()
    team_daily = fetch_team_daily_today(hours_back=14)
    urgent     = find_urgent(messages)

    pt        = _pt_now()
    date_str  = pt.strftime("%A, %B %-d")
    time_str  = pt.strftime("%-I:%M %p PT")

    urgent_count = len(urgent)
    total_count  = len(messages)
    cal_count    = len(events)
    td_count     = len(team_daily)

    # ── Urgent cards ──────────────────────────────────────────────────────────
    if urgent:
        urgent_html = ""
        for u in urgent[:10]:
            reasons = "; ".join(u.get("reasons", []))
            link = _gmail_link(u.get("thread_id", ""))
            urgent_html += f"""
        <a class="card card-urgent" href="{link}" target="_blank" rel="noopener">
          <div class="card-subj">{_esc(u['subject'][:88])}</div>
          <div class="card-meta">{_esc(u['from'][:60])}</div>
          <div class="card-tag">{_esc(reasons)}</div>
        </a>"""
    else:
        urgent_html = '<div class="empty">Nothing urgent right now</div>'

    # ── Calendar cards ────────────────────────────────────────────────────────
    if events:
        cal_html = ""
        for e in events[:10]:
            t   = _fmt_time(e["start"])
            loc = f'<div class="event-loc">{_esc(e["location"])}</div>' if e["location"] else ""
            cal_html += f"""
        <div class="cal-card">
          <div class="event-time">{t}</div>
          <div class="event-body">
            <div class="event-title">{_esc(e['title'])}</div>
            {loc}
          </div>
        </div>"""
    else:
        cal_html = '<div class="empty">No events today</div>'

    # ── Team report cards ─────────────────────────────────────────────────────
    if team_daily:
        td_html = ""
        for t in team_daily[:6]:
            sender = t["from"].split("<")[0].strip() or t["from"][:40]
            link   = _gmail_link(t.get("thread_id", ""))
            td_html += f"""
        <a class="card card-team" href="{link}" target="_blank" rel="noopener">
          <div class="team-sender">{_esc(sender[:30])}</div>
          <div class="card-subj">{_esc(t['subject'][:70])}</div>
        </a>"""
    else:
        td_html = '<div class="empty">No reports yet today</div>'

    urgent_badge   = "badge-warn" if urgent_count > 0 else "badge-zero"
    cal_badge      = "badge-blue" if cal_count > 0 else "badge-zero"
    td_badge       = "badge-ok"   if td_count > 0 else "badge-warn"
    urgent_num_cls = "num-warn"   if urgent_count > 0 else ""
    td_num_cls     = "num-ok"     if td_count > 0 else "num-warn"
    tabs_html      = _nav_tabs_html(token, active="dashboard")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>SC-Incorporated — Ryan</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&family=Roboto+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root {{
  --blue:        #02B3E9;
  --blue-glow:   rgba(2,179,233,0.45);
  --blue-soft:   rgba(2,179,233,0.12);
  --blue-border: rgba(2,179,233,0.25);
  --btn-blue:    #5ABEF8;
  --orange:      #FF8A3D;
  --orange-soft: rgba(255,138,61,0.12);
  --green:       #10b981;
  --green-soft:  rgba(16,185,129,0.10);
  --navy:        #0a1220;
  --navy-2:      #0f1a2e;
  --navy-3:      #162341;
  --white:       #ffffff;
  --grey:        #c6d1e3;
  --grey-dim:    #8592ab;
  --mono:        'Roboto Mono', monospace;
  --sans:        'Montserrat', sans-serif;
}}
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html, body {{
  background: var(--navy);
  color: var(--white);
  font-family: var(--sans);
  font-weight: 300;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  overflow-x: hidden;
  min-height: 100vh;
}}

/* ── Radial glow background ── */
.bg-glow {{
  position: fixed;
  top: -30vh; left: 50%;
  transform: translateX(-50%);
  width: 120vw; height: 100vh;
  background: radial-gradient(ellipse at center, var(--blue-soft) 0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
}}

/* ── Header ── */
header {{
  background: rgba(10,18,32,0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--blue-border);
  padding: 16px 32px;
  display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 10;
}}
.logo {{ display: flex; align-items: center; gap: 14px; }}
.logo-mark {{
  width: 42px; height: 42px;
  background: var(--blue-soft);
  border: 1px solid var(--blue-border);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--mono); font-weight: 700; font-size: 14px;
  color: var(--blue);
  box-shadow: 0 0 20px var(--blue-glow);
  letter-spacing: -0.5px; flex-shrink: 0;
}}
.logo-text h1 {{
  font-family: var(--mono); font-weight: 700;
  font-size: 15px; letter-spacing: 0.12em; color: var(--white);
  text-shadow: 0 0 20px var(--blue-glow);
}}
.logo-sub {{
  font-size: 11px; font-weight: 300; color: var(--grey-dim);
  margin-top: 3px; display: flex; align-items: center; gap: 7px;
  letter-spacing: 0.02em;
}}
.pulse {{
  width: 6px; height: 6px; background: var(--green);
  border-radius: 50%; display: inline-block;
  animation: pulse 2.5s ease-in-out infinite;
}}
@keyframes pulse {{ 0%,100%{{ opacity:1 }} 50%{{ opacity:0.2 }} }}
.header-right {{ display: flex; align-items: center; gap: 16px; }}
.ts {{ font-family: var(--mono); font-size: 11px; color: var(--grey-dim); }}
.btn-refresh {{
  background: transparent;
  border: 1px solid var(--blue-border);
  border-radius: 999px;
  color: var(--grey-dim);
  font-family: var(--mono); font-weight: 500;
  font-size: 11px; letter-spacing: 0.08em;
  padding: 8px 20px; cursor: pointer;
  transition: all .2s;
}}
.btn-refresh:hover {{
  border-color: var(--blue); color: var(--blue);
  box-shadow: 0 0 16px var(--blue-glow);
}}
.btn-refresh.loading {{ opacity: 0.4; pointer-events: none; }}

/* ── Stats bar ── */
.stats-bar {{
  background: var(--navy-2);
  border-bottom: 1px solid var(--blue-border);
  padding: 20px 32px;
  display: flex; align-items: center; flex-wrap: wrap; gap: 0;
  position: relative; z-index: 1;
}}
.stat {{
  display: flex; align-items: center; gap: 14px;
  padding: 8px 32px 8px 0;
}}
.stat:first-child {{ padding-left: 0; }}
.stat-num {{
  font-family: var(--mono); font-weight: 700;
  font-size: 36px; color: var(--white); line-height: 1;
}}
.num-warn {{ color: var(--orange); text-shadow: 0 0 20px rgba(255,138,61,0.4); }}
.num-ok   {{ color: var(--green);  text-shadow: 0 0 20px rgba(16,185,129,0.3); }}
.stat-label {{
  font-size: 10px; font-weight: 600; color: var(--grey-dim);
  text-transform: uppercase; letter-spacing: 0.1em; line-height: 1.5;
}}
.stat-div {{
  width: 1px; height: 40px; background: var(--blue-border);
  margin-right: 32px; flex-shrink: 0;
}}
@media (max-width: 600px) {{
  .stat-div {{ display: none; }}
  .stat {{ padding: 8px 20px 8px 0; }}
  .stat-num {{ font-size: 28px; }}
}}

/* ── Grid ── */
.grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  padding: 32px;
  max-width: 1400px;
  position: relative; z-index: 1;
}}
@media (max-width: 900px) {{
  .grid {{ grid-template-columns: 1fr; padding: 20px; gap: 16px; }}
}}
@media (max-width: 600px) {{
  header {{ padding: 14px 16px; }}
  .stats-bar {{ padding: 16px; }}
  .ts {{ display: none; }}
}}

/* ── Section ── */
.section {{
  background: var(--navy-2);
  border: 1px solid var(--blue-border);
  border-radius: 16px;
  overflow: hidden;
  display: flex; flex-direction: column;
}}
.section-hdr {{
  padding: 16px 20px;
  border-bottom: 1px solid var(--blue-border);
  background: rgba(2,179,233,0.04);
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
}}
.section-title {{
  font-family: var(--mono); font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.14em; color: var(--grey-dim);
}}
.badge {{
  font-family: var(--mono); font-size: 11px; font-weight: 700;
  padding: 3px 10px; border-radius: 999px;
}}
.badge-warn {{ background: rgba(255,138,61,.12); color: var(--orange);  border: 1px solid rgba(255,138,61,.3); }}
.badge-ok   {{ background: var(--green-soft);    color: var(--green);   border: 1px solid rgba(16,185,129,.3); }}
.badge-blue {{ background: var(--blue-soft);     color: var(--blue);    border: 1px solid var(--blue-border); }}
.badge-zero {{ background: transparent; color: var(--grey-dim); border: 1px solid rgba(255,255,255,0.08); }}
.section-body {{ padding: 14px; overflow-y: auto; max-height: 520px; }}

/* ── Cards ── */
.card {{
  display: block;
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.07);
  background: var(--navy-3);
  margin-bottom: 10px;
  text-decoration: none;
  transition: border-color .15s, box-shadow .15s, transform .12s;
}}
.card:last-child {{ margin-bottom: 0; }}
.card:hover {{
  border-color: var(--blue-border);
  box-shadow: 0 0 20px rgba(2,179,233,0.12);
  transform: translateY(-2px);
}}
.card-urgent {{ border-left: 3px solid var(--orange); }}
.card-urgent:hover {{
  border-color: rgba(255,138,61,0.4);
  border-left-color: var(--orange);
  box-shadow: 0 0 20px rgba(255,138,61,0.12);
}}
.card-subj  {{
  font-family: var(--sans); font-size: 13px; font-weight: 600;
  color: var(--white); margin-bottom: 5px; line-height: 1.4;
}}
.card-meta  {{ font-size: 12px; color: var(--grey-dim); font-weight: 300; }}
.card-tag   {{
  font-family: var(--mono); font-size: 10px; font-weight: 500;
  color: var(--orange); margin-top: 7px; letter-spacing: 0.04em;
}}

/* ── Calendar ── */
.cal-card {{
  padding: 14px 16px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.07);
  background: var(--navy-3);
  margin-bottom: 10px;
  display: flex; gap: 16px; align-items: flex-start;
}}
.cal-card:last-child {{ margin-bottom: 0; }}
.event-time  {{
  font-family: var(--mono); font-size: 12px; font-weight: 700;
  color: var(--blue); min-width: 64px; padding-top: 2px;
  text-shadow: 0 0 12px var(--blue-glow);
}}
.event-body  {{ flex: 1; min-width: 0; }}
.event-title {{ font-size: 13px; font-weight: 600; color: var(--white); line-height: 1.4; }}
.event-loc   {{ font-size: 11px; color: var(--grey-dim); margin-top: 4px; font-weight: 300; }}

/* ── Team ── */
.card-team {{
  border: 1px solid rgba(16,185,129,0.15);
  background: rgba(16,185,129,0.04);
}}
.card-team:hover {{
  border-color: rgba(16,185,129,0.4);
  box-shadow: 0 0 20px rgba(16,185,129,0.1);
}}
.team-sender {{
  font-family: var(--mono); font-size: 10px; font-weight: 700;
  color: var(--green); margin-bottom: 5px;
  text-transform: uppercase; letter-spacing: 0.08em;
}}

.empty {{
  font-size: 13px; color: var(--grey-dim); font-weight: 300;
  padding: 32px 16px; text-align: center; line-height: 1.6;
}}

/* ── Tabs bar ── */
.tabs-bar {{
  background: var(--navy-2);
  border-bottom: 1px solid var(--blue-border);
  padding: 0 32px;
  display: flex; align-items: stretch;
  position: sticky; top: 74px; z-index: 9;
}}
.dtab {{
  display: flex; align-items: center;
  padding: 0 20px; height: 44px;
  font-family: var(--mono); font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--grey-dim); text-decoration: none;
  border-bottom: 2px solid transparent;
  transition: color .15s, border-color .15s; white-space: nowrap;
}}
.dtab:hover {{ color: var(--blue); }}
.dtab.active {{ color: var(--blue); border-bottom-color: var(--blue); }}
@media (max-width: 600px) {{
  .tabs-bar {{ padding: 0 16px; top: 62px; }}
  .dtab {{ padding: 0 12px; font-size: 10px; height: 40px; }}
}}
</style>
</head>
<body>

<div class="bg-glow"></div>

<header>
  <div class="logo">
    <div class="logo-mark">SC</div>
    <div class="logo-text">
      <h1>SC-INCORPORATED</h1>
      <div class="logo-sub">
        <span class="pulse"></span>
        {date_str} &middot; {time_str}
      </div>
    </div>
  </div>
  <div class="header-right">
    <span class="ts">auto-refresh 5 min</span>
    <button class="btn-refresh" id="refreshBtn" onclick="doRefresh()">&#8635; REFRESH</button>
  </div>
</header>

{tabs_html}

<div class="stats-bar">
  <div class="stat">
    <div class="stat-num {urgent_num_cls}">{urgent_count}</div>
    <div class="stat-label">urgent<br>items</div>
  </div>
  <div class="stat-div"></div>
  <div class="stat">
    <div class="stat-num">{total_count}</div>
    <div class="stat-label">emails<br>overnight</div>
  </div>
  <div class="stat-div"></div>
  <div class="stat">
    <div class="stat-num">{cal_count}</div>
    <div class="stat-label">cal<br>events</div>
  </div>
  <div class="stat-div"></div>
  <div class="stat">
    <div class="stat-num {td_num_cls}">{td_count}</div>
    <div class="stat-label">team<br>reports</div>
  </div>
</div>

<div class="grid">
  <div class="section">
    <div class="section-hdr">
      <span class="section-title">Urgent</span>
      <span class="badge {urgent_badge}">{urgent_count}</span>
    </div>
    <div class="section-body">{urgent_html}</div>
  </div>

  <div class="section">
    <div class="section-hdr">
      <span class="section-title">Today&rsquo;s Calendar</span>
      <span class="badge {cal_badge}">{cal_count}</span>
    </div>
    <div class="section-body">{cal_html}</div>
  </div>

  <div class="section">
    <div class="section-hdr">
      <span class="section-title">Team Reports</span>
      <span class="badge {td_badge}">{td_count}</span>
    </div>
    <div class="section-body">{td_html}</div>
  </div>
</div>

<script>
function doRefresh() {{
  var btn = document.getElementById('refreshBtn');
  btn.classList.add('loading');
  btn.textContent = '... LOADING';
  location.reload();
}}
</script>
</body>
</html>"""


# ── Shared page shell ─────────────────────────────────────────────────────────

def _page_shell(token: str, active: str, title: str, body_html: str) -> str:
    pt       = _pt_now()
    date_str = pt.strftime("%A, %B %-d")
    time_str = pt.strftime("%-I:%M %p PT")
    tabs     = _nav_tabs_html(token, active=active)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>SC-Incorporated — {_esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&family=Roboto+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
:root {{
  --blue:#02B3E9;--blue-glow:rgba(2,179,233,0.45);--blue-soft:rgba(2,179,233,0.12);
  --blue-border:rgba(2,179,233,0.25);--orange:#FF8A3D;--orange-soft:rgba(255,138,61,0.12);
  --green:#10b981;--green-soft:rgba(16,185,129,0.10);--navy:#0a1220;--navy-2:#0f1a2e;
  --navy-3:#162341;--white:#ffffff;--grey:#c6d1e3;--grey-dim:#8592ab;
  --mono:'Roboto Mono',monospace;--sans:'Montserrat',sans-serif;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{background:var(--navy);color:var(--white);font-family:var(--sans);font-weight:300;
  line-height:1.6;-webkit-font-smoothing:antialiased;overflow-x:hidden;min-height:100vh;}}
.bg-glow{{position:fixed;top:-30vh;left:50%;transform:translateX(-50%);width:120vw;height:100vh;
  background:radial-gradient(ellipse at center,var(--blue-soft) 0%,transparent 60%);
  pointer-events:none;z-index:0;}}
header{{background:rgba(10,18,32,0.92);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border-bottom:1px solid var(--blue-border);padding:16px 32px;
  display:flex;align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:10;}}
.logo{{display:flex;align-items:center;gap:14px;}}
.logo-mark{{width:42px;height:42px;background:var(--blue-soft);border:1px solid var(--blue-border);
  border-radius:10px;display:flex;align-items:center;justify-content:center;
  font-family:var(--mono);font-weight:700;font-size:14px;color:var(--blue);
  box-shadow:0 0 20px var(--blue-glow);letter-spacing:-0.5px;flex-shrink:0;}}
.logo-text h1{{font-family:var(--mono);font-weight:700;font-size:15px;letter-spacing:0.12em;
  color:var(--white);text-shadow:0 0 20px var(--blue-glow);}}
.logo-sub{{font-size:11px;font-weight:300;color:var(--grey-dim);margin-top:3px;
  display:flex;align-items:center;gap:7px;letter-spacing:0.02em;}}
.pulse{{width:6px;height:6px;background:var(--green);border-radius:50%;display:inline-block;
  animation:pulse 2.5s ease-in-out infinite;}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.2}}}}
.ts{{font-family:var(--mono);font-size:11px;color:var(--grey-dim);}}
.tabs-bar{{background:var(--navy-2);border-bottom:1px solid var(--blue-border);
  padding:0 32px;display:flex;align-items:stretch;position:sticky;top:74px;z-index:9;
  overflow-x:auto;}}
.dtab{{display:flex;align-items:center;padding:0 20px;height:44px;font-family:var(--mono);
  font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;
  color:var(--grey-dim);text-decoration:none;border-bottom:2px solid transparent;
  transition:color .15s,border-color .15s;white-space:nowrap;}}
.dtab:hover{{color:var(--blue);}}
.dtab.active{{color:var(--blue);border-bottom-color:var(--blue);}}
.page-body{{max-width:1400px;padding:32px;position:relative;z-index:1;}}
.section{{background:var(--navy-2);border:1px solid var(--blue-border);border-radius:16px;
  overflow:hidden;margin-bottom:24px;}}
.section-hdr{{padding:16px 20px;border-bottom:1px solid var(--blue-border);
  background:rgba(2,179,233,0.04);display:flex;align-items:center;justify-content:space-between;}}
.section-title{{font-family:var(--mono);font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.14em;color:var(--grey-dim);}}
.badge{{font-family:var(--mono);font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;}}
.badge-warn{{background:rgba(255,138,61,.12);color:var(--orange);border:1px solid rgba(255,138,61,.3);}}
.badge-ok{{background:var(--green-soft);color:var(--green);border:1px solid rgba(16,185,129,.3);}}
.badge-blue{{background:var(--blue-soft);color:var(--blue);border:1px solid var(--blue-border);}}
.badge-zero{{background:transparent;color:var(--grey-dim);border:1px solid rgba(255,255,255,0.08);}}
.section-body{{padding:14px;}}
.card{{display:block;padding:14px 16px;border-radius:10px;border:1px solid rgba(255,255,255,0.07);
  background:var(--navy-3);margin-bottom:10px;text-decoration:none;
  transition:border-color .15s,box-shadow .15s,transform .12s;}}
.card:last-child{{margin-bottom:0;}}
.card:hover{{border-color:var(--blue-border);box-shadow:0 0 20px rgba(2,179,233,0.12);transform:translateY(-2px);}}
.card-urgent{{border-left:3px solid var(--orange);}}
.card-urgent:hover{{border-color:rgba(255,138,61,0.4);border-left-color:var(--orange);
  box-shadow:0 0 20px rgba(255,138,61,0.12);}}
.card-subj{{font-size:13px;font-weight:600;color:var(--white);margin-bottom:5px;line-height:1.4;}}
.card-meta{{font-size:12px;color:var(--grey-dim);font-weight:300;}}
.card-tag{{font-family:var(--mono);font-size:10px;font-weight:500;color:var(--orange);
  margin-top:7px;letter-spacing:0.04em;}}
.card-project{{border-left:3px solid var(--blue);}}
.card-project:hover{{border-left-color:var(--blue);box-shadow:0 0 20px rgba(2,179,233,0.12);}}
.project-group{{margin-bottom:20px;}}
.project-group:last-child{{margin-bottom:0;}}
.project-name{{font-family:var(--mono);font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.1em;color:var(--blue);margin-bottom:10px;padding:0 4px;}}
.empty{{font-size:13px;color:var(--grey-dim);font-weight:300;padding:32px 16px;
  text-align:center;line-height:1.6;}}
.cal-day{{margin-bottom:20px;}}
.cal-day:last-child{{margin-bottom:0;}}
.cal-day-hdr{{font-family:var(--mono);font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.1em;color:var(--grey-dim);margin-bottom:10px;padding:0 4px;}}
.cal-day-hdr.today{{color:var(--blue);}}
.cal-card{{padding:14px 16px;border-radius:10px;border:1px solid rgba(255,255,255,0.07);
  background:var(--navy-3);margin-bottom:8px;display:flex;gap:16px;align-items:flex-start;}}
.cal-card:last-child{{margin-bottom:0;}}
.cal-card.bid-due{{border-left:3px solid var(--orange);}}
.event-time{{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--blue);
  min-width:64px;padding-top:2px;text-shadow:0 0 12px var(--blue-glow);}}
.event-body{{flex:1;min-width:0;}}
.event-title{{font-size:13px;font-weight:600;color:var(--white);line-height:1.4;}}
.event-loc{{font-size:11px;color:var(--grey-dim);margin-top:4px;font-weight:300;}}
.event-assignee{{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--orange);
  margin-top:5px;letter-spacing:0.04em;}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:24px;}}
@media(max-width:900px){{.grid-2{{grid-template-columns:1fr;}}}}
@media(max-width:600px){{
  header{{padding:14px 16px;}} .page-body{{padding:16px;}}
  .tabs-bar{{padding:0 8px;top:62px;}} .dtab{{padding:0 12px;font-size:10px;height:40px;}}
  .ts{{display:none;}}
}}
</style>
</head>
<body>
<div class="bg-glow"></div>
<header>
  <div class="logo">
    <div class="logo-mark">SC</div>
    <div class="logo-text">
      <h1>SC-INCORPORATED</h1>
      <div class="logo-sub"><span class="pulse"></span>{date_str} &middot; {time_str}</div>
    </div>
  </div>
  <span class="ts">auto-refresh 5 min</span>
</header>
{tabs}
<div class="page-body">{body_html}</div>
<script>window.TOKEN="{_esc(token)}";</script>
</body>
</html>"""


# ── Inbox page ────────────────────────────────────────────────────────────────

def render_inbox(token: str = "ryan-sc") -> str:
    data = fetch_inbox_grouped(hours_back=48)
    urgent   = data["urgent"]
    projects = data["projects"]
    bids     = data["bids"]
    team     = data["team"]
    other    = data["other"]

    def _email_card(m: dict, cls: str = "") -> str:
        link    = _gmail_link(m.get("thread_id", ""))
        sender  = m["from"].split("<")[0].strip() or m["from"][:40]
        reasons = m.get("reasons", [])
        tag     = f'<div class="card-tag">{_esc("; ".join(reasons))}</div>' if reasons else ""
        return f"""<a class="card {cls}" href="{link}" target="_blank" rel="noopener">
          <div class="card-subj">{_esc(m['subject'][:90]) or '(no subject)'}</div>
          <div class="card-meta">{_esc(sender[:60])}</div>{tag}
        </a>"""

    # Urgent section
    if urgent:
        urgent_cards = "".join(_email_card(m, "card-urgent") for m in urgent[:15])
    else:
        urgent_cards = '<div class="empty">Nothing urgent in the last 48 hours</div>'
    urgent_badge = f'badge-warn' if urgent else 'badge-zero'
    urgent_html = f"""<div class="section">
      <div class="section-hdr">
        <span class="section-title">Urgent</span>
        <span class="badge {urgent_badge}">{len(urgent)}</span>
      </div>
      <div class="section-body">{urgent_cards}</div>
    </div>"""

    # Projects section
    if projects:
        proj_html_inner = ""
        for proj_name, msgs in sorted(projects.items()):
            cards = "".join(_email_card(m, "card-project") for m in msgs[:6])
            proj_html_inner += f"""<div class="project-group">
              <div class="project-name">{_esc(proj_name)}</div>
              {cards}
            </div>"""
    else:
        proj_html_inner = '<div class="empty">No project emails in the last 48 hours</div>'
    proj_html = f"""<div class="section">
      <div class="section-hdr">
        <span class="section-title">Projects</span>
        <span class="badge badge-blue">{sum(len(v) for v in projects.values())}</span>
      </div>
      <div class="section-body">{proj_html_inner}</div>
    </div>"""

    # Bids + Team side by side
    bids_cards = "".join(_email_card(m) for m in bids[:8]) or '<div class="empty">No bids</div>'
    team_cards = "".join(_email_card(m) for m in team[:8]) or '<div class="empty">No team reports</div>'
    bottom_html = f"""<div class="grid-2">
      <div class="section">
        <div class="section-hdr">
          <span class="section-title">Bids &amp; Invites</span>
          <span class="badge {'badge-blue' if bids else 'badge-zero'}">{len(bids)}</span>
        </div>
        <div class="section-body">{bids_cards}</div>
      </div>
      <div class="section">
        <div class="section-hdr">
          <span class="section-title">Team Reports</span>
          <span class="badge {'badge-ok' if team else 'badge-zero'}">{len(team)}</span>
        </div>
        <div class="section-body">{team_cards}</div>
      </div>
    </div>"""

    body = urgent_html + proj_html + bottom_html
    return _page_shell(token, active="inbox", title="Inbox", body_html=body)


# ── Calendar page ─────────────────────────────────────────────────────────────

def render_calendar(token: str = "ryan-sc") -> str:
    events = fetch_upcoming_calendar(days_ahead=7)
    pt     = _pt_now()
    today  = pt.strftime("%Y-%m-%d")

    # Group by date
    by_date: dict[str, list] = {}
    for e in events:
        by_date.setdefault(e["date"], []).append(e)

    bid_dues = [e for e in events if e["is_bid_due"]]

    def _day_label(date_str: str) -> str:
        try:
            from datetime import date as _date
            d = _date.fromisoformat(date_str)
            label = d.strftime("%A, %B %-d")
            return f"Today — {label}" if date_str == today else label
        except Exception:
            return date_str

    def _cal_card(e: dict) -> str:
        t   = _fmt_time(e["start"])
        loc = f'<div class="event-loc">{_esc(e["location"])}</div>' if e["location"] else ""
        assignee = f'<div class="event-assignee">&#9654; {_esc(e["assignee"])}</div>' if e.get("assignee") else ""
        cls = "cal-card bid-due" if e["is_bid_due"] else "cal-card"
        return f"""<div class="{cls}">
          <div class="event-time">{t}</div>
          <div class="event-body">
            <div class="event-title">{_esc(e['title'])}</div>
            {loc}{assignee}
          </div>
        </div>"""

    # Build weekly schedule
    if by_date:
        week_html = ""
        for date_str in sorted(by_date):
            day_cls  = "cal-day-hdr today" if date_str == today else "cal-day-hdr"
            day_cards = "".join(_cal_card(e) for e in by_date[date_str])
            week_html += f"""<div class="cal-day">
              <div class="{day_cls}">{_day_label(date_str)}</div>
              {day_cards}
            </div>"""
    else:
        week_html = '<div class="empty">No events in the next 7 days</div>'

    week_section = f"""<div class="section">
      <div class="section-hdr">
        <span class="section-title">This Week</span>
        <span class="badge {'badge-blue' if events else 'badge-zero'}">{len(events)}</span>
      </div>
      <div class="section-body">{week_html}</div>
    </div>"""

    # Bid due dates panel
    if bid_dues:
        bid_cards = "".join(_cal_card(e) for e in bid_dues)
    else:
        bid_cards = '<div class="empty">No bid due dates in the next 7 days</div>'

    bid_section = f"""<div class="section">
      <div class="section-hdr">
        <span class="section-title">Bid Due Dates</span>
        <span class="badge {'badge-warn' if bid_dues else 'badge-zero'}">{len(bid_dues)}</span>
      </div>
      <div class="section-body">{bid_cards}</div>
    </div>"""

    body = week_section + bid_section
    return _page_shell(token, active="calendar", title="Calendar", body_html=body)
