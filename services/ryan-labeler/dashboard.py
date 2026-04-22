"""Ryan app — 3-tab: Today, Projects, Calendar."""
from __future__ import annotations
import time
from datetime import datetime, timezone, timedelta, date as _date

from briefer import (
    fetch_overnight_messages,
    fetch_team_daily_today,
    fetch_inbox_sections,
    fetch_upcoming_calendar,
    find_urgent,
    _pt_now,
)

# ── In-memory cache ───────────────────────────────────────────────────────────
_cache: dict[str, dict] = {}
_CACHE_TTL = 300  # 5 minutes


def _cache_get(key: str):
    e = _cache.get(key)
    if e and time.monotonic() < e["exp"]:
        return e["data"]
    return None


def _cache_set(key: str, data) -> None:
    _cache[key] = {"data": data, "exp": time.monotonic() + _CACHE_TTL}


def warm_all_caches() -> None:
    """Pre-populate all 3 page data caches. Called by APScheduler every 5 min."""
    for key, fn in [
        ("today", _fetch_today_data),
        ("inbox", _fetch_inbox_data),
        ("calendar", _fetch_calendar_data),
    ]:
        try:
            _cache_set(key, fn())
        except Exception:
            pass


def _fetch_today_data() -> dict:
    msgs = fetch_overnight_messages(hours_back=14)
    urgent = find_urgent(msgs)
    team = fetch_team_daily_today(hours_back=14)
    return {"urgent": urgent, "team": team, "total": len(msgs)}


def _fetch_inbox_data() -> dict:
    return fetch_inbox_sections(hours_back=168)


def _fetch_calendar_data() -> dict:
    return {"events": fetch_upcoming_calendar(days_ahead=28)}


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _fmt_rel_time(ts_ms: int) -> str:
    if not ts_ms:
        return ""
    dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    now_pt = _pt_now()
    dt_pt = dt.astimezone(now_pt.tzinfo)
    today = now_pt.date()
    msg_date = dt_pt.date()
    if msg_date == today:
        return dt_pt.strftime("%-I:%M %p")
    elif msg_date == today - timedelta(days=1):
        return "Yesterday"
    elif (today - msg_date).days < 7:
        return dt_pt.strftime("%a")
    else:
        return dt_pt.strftime("%b %-d")


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


# ── Shared CSS ────────────────────────────────────────────────────────────────

_CSS = """
:root{--blue:#02B3E9;--blue-glow:rgba(2,179,233,0.45);--blue-soft:rgba(2,179,233,0.12);
  --blue-border:rgba(2,179,233,0.25);--orange:#FF8A3D;--green:#10b981;
  --green-soft:rgba(16,185,129,0.10);--navy:#0a1220;--navy-2:#0f1a2e;--navy-3:#162341;
  --white:#ffffff;--grey:#c6d1e3;--grey-dim:#8592ab;
  --mono:'Roboto Mono',monospace;--sans:'Montserrat',sans-serif;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body{background:var(--navy);color:var(--white);font-family:var(--sans);font-weight:300;
  line-height:1.6;-webkit-font-smoothing:antialiased;overflow-x:hidden;min-height:100vh;}
.bg-glow{position:fixed;top:-30vh;left:50%;transform:translateX(-50%);
  width:120vw;height:100vh;pointer-events:none;z-index:0;
  background:radial-gradient(ellipse at center,var(--blue-soft) 0%,transparent 60%);}
header{background:rgba(10,18,32,0.92);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border-bottom:1px solid var(--blue-border);padding:14px 20px;
  display:flex;align-items:center;justify-content:space-between;
  position:sticky;top:0;z-index:10;}
.logo{display:flex;align-items:center;gap:12px;}
.logo-mark{width:36px;height:36px;background:var(--blue-soft);border:1px solid var(--blue-border);
  border-radius:9px;display:flex;align-items:center;justify-content:center;
  font-family:var(--mono);font-weight:700;font-size:13px;color:var(--blue);
  box-shadow:0 0 16px var(--blue-glow);flex-shrink:0;}
.logo-text h1{font-family:var(--mono);font-weight:700;font-size:14px;letter-spacing:0.12em;
  color:var(--white);text-shadow:0 0 16px var(--blue-glow);}
.logo-sub{font-size:10px;font-weight:300;color:var(--grey-dim);margin-top:2px;
  display:flex;align-items:center;gap:6px;}
.pulse{width:5px;height:5px;background:var(--green);border-radius:50%;display:inline-block;
  animation:pulse 2.5s ease-in-out infinite;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.2}}
.ts{font-family:var(--mono);font-size:10px;color:var(--grey-dim);}
.tabs-bar{background:var(--navy-2);border-bottom:1px solid var(--blue-border);
  display:flex;align-items:stretch;position:sticky;top:64px;z-index:9;
  overflow-x:auto;-webkit-overflow-scrolling:touch;}
.dtab{display:flex;align-items:center;justify-content:center;flex:1;min-height:44px;
  font-family:var(--mono);font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.08em;color:var(--grey-dim);text-decoration:none;
  border-bottom:2px solid transparent;transition:color .15s,border-color .15s;
  white-space:nowrap;padding:0 16px;}
.dtab:hover{color:var(--blue);}
.dtab.active{color:var(--blue);border-bottom-color:var(--blue);}
.page-body{max-width:680px;margin:0 auto;padding:20px 16px 40px;position:relative;z-index:1;}
.stabs{display:flex;background:var(--navy-3);border-radius:10px;padding:4px;
  margin-bottom:20px;gap:2px;}
.stab{flex:1;min-height:44px;border:none;background:transparent;color:var(--grey-dim);
  font-family:var(--mono);font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.06em;cursor:pointer;border-radius:8px;transition:all .15s;
  display:flex;align-items:center;justify-content:center;gap:5px;}
.stab.active{background:var(--navy-2);color:var(--blue);box-shadow:0 0 12px rgba(2,179,233,0.2);}
.stab:hover:not(.active){color:var(--white);}
.stab-n{background:var(--blue-soft);color:var(--blue);border:1px solid var(--blue-border);
  border-radius:999px;font-size:9px;font-weight:700;padding:1px 6px;font-family:var(--mono);}
.stab-n.warn{background:rgba(255,138,61,.12);color:var(--orange);border-color:rgba(255,138,61,.3);}
.section{background:var(--navy-2);border:1px solid var(--blue-border);border-radius:14px;
  overflow:hidden;margin-bottom:16px;}
.section:last-child{margin-bottom:0;}
.section-hdr{padding:14px 16px;border-bottom:1px solid var(--blue-border);
  background:rgba(2,179,233,0.04);display:flex;align-items:center;justify-content:space-between;}
.section-title{font-family:var(--mono);font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.12em;color:var(--grey-dim);}
.badge{font-family:var(--mono);font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;}
.badge-warn{background:rgba(255,138,61,.12);color:var(--orange);border:1px solid rgba(255,138,61,.3);}
.badge-ok{background:var(--green-soft);color:var(--green);border:1px solid rgba(16,185,129,.3);}
.badge-blue{background:var(--blue-soft);color:var(--blue);border:1px solid var(--blue-border);}
.badge-zero{background:transparent;color:var(--grey-dim);border:1px solid rgba(255,255,255,0.08);}
.section-body{padding:12px;}
.card{display:block;padding:12px 14px;border-radius:10px;border:1px solid rgba(255,255,255,0.07);
  background:var(--navy-3);margin-bottom:8px;text-decoration:none;
  transition:border-color .15s,box-shadow .15s,transform .1s;}
.card:last-child{margin-bottom:0;}
.card:hover{border-color:var(--blue-border);box-shadow:0 0 16px rgba(2,179,233,0.1);transform:translateY(-1px);}
.card-urgent{border-left:3px solid var(--orange);}
.card-urgent:hover{border-color:rgba(255,138,61,0.35);border-left-color:var(--orange);
  box-shadow:0 0 16px rgba(255,138,61,0.1);}
.card-subj{font-size:13px;font-weight:600;color:var(--white);margin-bottom:4px;line-height:1.4;}
.card-meta{font-size:11px;color:var(--grey-dim);font-weight:300;}
.card-tag{font-family:var(--mono);font-size:10px;font-weight:500;
  color:var(--orange);margin-top:6px;letter-spacing:0.04em;}
.card-team{border:1px solid rgba(16,185,129,0.15);background:rgba(16,185,129,0.04);}
.card-team:hover{border-color:rgba(16,185,129,0.4);box-shadow:0 0 16px rgba(16,185,129,0.1);}
.team-sender{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--green);
  margin-bottom:4px;text-transform:uppercase;letter-spacing:0.08em;}
.proj-card{background:var(--navy-3);border:1px solid rgba(255,255,255,0.07);
  border-left:3px solid var(--blue);border-radius:10px;padding:14px;margin-bottom:10px;}
.proj-card:last-child{margin-bottom:0;}
.proj-hdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
.proj-name{font-family:var(--mono);font-size:11px;font-weight:700;color:var(--blue);
  text-transform:uppercase;letter-spacing:0.08em;}
.proj-count{font-family:var(--mono);font-size:10px;font-weight:700;color:var(--grey-dim);}
.proj-msg{padding:7px 0;border-top:1px solid rgba(255,255,255,0.05);}
.proj-msg:first-of-type{border-top:none;}
.proj-link{display:block;text-decoration:none;}
.proj-link:hover .proj-msg-subj{color:var(--blue);}
.proj-msg-subj{font-size:12px;font-weight:600;color:var(--white);line-height:1.4;transition:color .15s;}
.proj-msg-from{font-size:11px;color:var(--grey-dim);margin-top:2px;}
.cal-day{margin-bottom:20px;}
.cal-day:last-child{margin-bottom:0;}
.cal-day-hdr{font-family:var(--mono);font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:0.1em;color:var(--grey-dim);margin-bottom:10px;padding:0 2px;}
.cal-day-hdr.today{color:var(--blue);}
.cal-card{padding:12px 14px;border-radius:10px;border:1px solid rgba(255,255,255,0.07);
  background:var(--navy-3);margin-bottom:8px;display:flex;gap:14px;align-items:flex-start;}
.cal-card:last-child{margin-bottom:0;}
.cal-card.bid-due{border-left:3px solid var(--orange);}
.event-time{font-family:var(--mono);font-size:11px;font-weight:700;color:var(--blue);
  min-width:56px;padding-top:2px;text-shadow:0 0 10px var(--blue-glow);}
.event-body{flex:1;min-width:0;}
.event-title{font-size:13px;font-weight:600;color:var(--white);line-height:1.4;}
.event-loc{font-size:11px;color:var(--grey-dim);margin-top:3px;}
.event-assignee{font-family:var(--mono);font-size:10px;font-weight:700;
  color:var(--orange);margin-top:4px;letter-spacing:0.04em;}
.empty{font-size:13px;color:var(--grey-dim);font-weight:300;
  padding:28px 12px;text-align:center;line-height:1.6;}
@media(max-width:600px){
  header{padding:12px 14px;}
  .ts{display:none;}
  .logo-text h1{font-size:12px;}
}
/* Thread-row list (Gmail-style) */
.thread-list{background:var(--navy-2);border:1px solid var(--blue-border);border-radius:14px;overflow:hidden;}
.thread-row{display:flex;align-items:center;gap:10px;padding:9px 14px;
  border-bottom:1px solid rgba(255,255,255,0.04);text-decoration:none;transition:background .12s;}
.thread-row:last-child{border-bottom:none;}
.thread-row:hover{background:rgba(2,179,233,0.06);}
.thread-row.unread .tr-sender,.thread-row.unread .tr-subj{font-weight:700;color:var(--white);}
.tr-star{font-size:13px;color:var(--grey-dim);flex-shrink:0;opacity:0.4;}
.tr-sender{font-size:12px;font-weight:600;color:var(--grey);
  width:120px;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tr-body{flex:1;min-width:0;display:flex;align-items:center;gap:5px;overflow:hidden;}
.tr-subj{font-size:12px;font-weight:600;color:var(--grey);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex-shrink:0;max-width:200px;}
.tr-sep{font-size:12px;color:rgba(255,255,255,0.18);flex-shrink:0;}
.tr-snippet{font-size:12px;font-weight:300;color:var(--grey-dim);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.tr-time{font-family:var(--mono);font-size:10px;color:var(--grey-dim);
  flex-shrink:0;text-align:right;min-width:50px;}
.tr-proj-hdr{padding:6px 14px 5px;font-family:var(--mono);font-size:9px;font-weight:700;
  text-transform:uppercase;letter-spacing:0.1em;color:var(--blue);
  background:rgba(2,179,233,0.06);border-bottom:1px solid rgba(2,179,233,0.12);}
/* Calendar grid */
.cgrid{width:100%;border:1px solid var(--blue-border);border-radius:14px;overflow:hidden;background:var(--navy-2);}
.cgrid-row{display:grid;grid-template-columns:repeat(7,1fr);}
.cgrid-hdr-row{border-bottom:1px solid var(--blue-border);background:rgba(2,179,233,0.04);}
.cgrid-hdr{padding:7px 4px;text-align:center;font-family:var(--mono);font-size:9px;
  font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--grey-dim);}
.cgrid-row:not(.cgrid-hdr-row){border-bottom:1px solid rgba(255,255,255,0.04);}
.cgrid-row:last-child{border-bottom:none;}
.cgrid-cell{min-height:80px;padding:6px 4px;border-right:1px solid rgba(255,255,255,0.04);overflow:hidden;}
.cgrid-cell:last-child{border-right:none;}
.cgrid-num{font-family:var(--mono);font-size:11px;font-weight:700;color:var(--grey-dim);
  margin-bottom:3px;width:22px;height:22px;display:flex;align-items:center;justify-content:center;}
.cgrid-past .cgrid-num{opacity:0.3;}
.cgrid-today .cgrid-num{background:var(--blue);color:var(--navy);border-radius:50%;}
.cevt,.cevt-bid{display:block;font-size:8px;font-weight:600;border-radius:3px;
  padding:1px 3px;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.cevt{background:var(--blue-soft);color:var(--blue);}
.cevt-bid{background:rgba(255,138,61,0.15);color:var(--orange);}
.cevt-more{font-size:8px;color:var(--grey-dim);padding:0 2px;}
@media(max-width:480px){
  .cgrid-cell{min-height:56px;padding:4px 2px;}
  .cevt,.cevt-bid{display:none;}
  .tr-body{display:none;}
  .tr-sender{width:auto;flex:1;}
}
"""

_JS_STABS = """
function showStab(name,key){
  document.querySelectorAll('.stab').forEach(function(b){b.classList.remove('active');});
  document.querySelectorAll('[data-tab]').forEach(function(d){d.style.display='none';});
  var btn=document.querySelector('[data-stab="'+name+'"]');
  var tab=document.querySelector('[data-tab="'+name+'"]');
  if(btn)btn.classList.add('active');
  if(tab)tab.style.display='block';
  try{localStorage.setItem(key,name);}catch(e){}
}
function initStabs(key,def){
  var s;try{s=localStorage.getItem(key);}catch(e){}
  showStab(s||def,key);
}
"""


# ── Nav + page shell ──────────────────────────────────────────────────────────

def _nav_html(token: str, active: str) -> str:
    def _tab(label: str, href: str, key: str) -> str:
        cls = "dtab active" if active == key else "dtab"
        return f'<a class="{cls}" href="{href}?token={token}">{label}</a>'
    return (
        '<div class="tabs-bar">'
        + _tab("Today", "/dashboard", "today")
        + _tab("Inbox", "/inbox", "inbox")
        + _tab("Calendar", "/calendar", "calendar")
        + '</div>'
    )


def _page_shell(token: str, active: str, title: str, body_html: str, extra_js: str = "") -> str:
    pt = _pt_now()
    date_str = pt.strftime("%A, %B %-d")
    time_str = pt.strftime("%-I:%M %p PT")
    nav = _nav_html(token, active)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>SC — {_esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600&family=Roboto+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>{_CSS}</style>
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
{nav}
<div class="page-body">{body_html}</div>
<script>{_JS_STABS}{extra_js}</script>
</body>
</html>"""


# ── Today page ────────────────────────────────────────────────────────────────

def render_dashboard(token: str = "ryan-sc") -> str:
    data = _cache_get("today")
    if data is None:
        data = _fetch_today_data()
        _cache_set("today", data)

    urgent = data["urgent"]
    team   = data["team"]

    if urgent:
        urgent_html = ""
        for u in urgent[:15]:
            reasons = "; ".join(u.get("reasons", []))
            link = _gmail_link(u.get("thread_id", ""))
            tag = f'<div class="card-tag">{_esc(reasons)}</div>' if reasons else ""
            urgent_html += (
                f'<a class="card card-urgent" href="{link}" target="_blank" rel="noopener">'
                f'<div class="card-subj">{_esc(u["subject"][:90]) or "(no subject)"}</div>'
                f'<div class="card-meta">{_esc(u["from"][:65])}</div>{tag}</a>'
            )
    else:
        urgent_html = '<div class="empty">Nothing urgent right now</div>'

    if team:
        team_html = ""
        for t in team[:10]:
            sender = t["from"].split("<")[0].strip() or t["from"][:40]
            link = _gmail_link(t.get("thread_id", ""))
            team_html += (
                f'<a class="card card-team" href="{link}" target="_blank" rel="noopener">'
                f'<div class="team-sender">{_esc(sender[:30])}</div>'
                f'<div class="card-subj">{_esc(t["subject"][:80])}</div></a>'
            )
    else:
        team_html = '<div class="empty">No team reports today</div>'

    u_cls = "warn" if urgent else ""
    body = f"""
<div class="stabs">
  <button class="stab" data-stab="urgent" onclick="showStab('urgent','TODAY_TAB')">
    Urgent <span class="stab-n {u_cls}">{len(urgent)}</span>
  </button>
  <button class="stab" data-stab="team" onclick="showStab('team','TODAY_TAB')">
    Team <span class="stab-n">{len(team)}</span>
  </button>
</div>
<div data-tab="urgent">{urgent_html}</div>
<div data-tab="team" style="display:none">{team_html}</div>
"""
    return _page_shell(token, "today", "Today", body, extra_js="initStabs('TODAY_TAB','urgent');")


# ── Inbox page ────────────────────────────────────────────────────────────────

def render_inbox(token: str = "ryan-sc") -> str:
    data = _cache_get("inbox")
    if data is None:
        data = _fetch_inbox_data()
        _cache_set("inbox", data)

    bids    = data["bids"]
    ongoing = data["ongoing"]
    team    = data["team"]
    vendors = data["vendors"]

    def _row(m: dict) -> str:
        sender = m["from"].split("<")[0].strip() or m["from"][:50]
        link = _gmail_link(m.get("thread_id", ""))
        unread_cls = " unread" if "UNREAD" in m.get("label_ids", []) else ""
        t = _fmt_rel_time(m.get("ts_ms", 0))
        snippet = m.get("snippet", "")
        return (
            f'<a class="thread-row{unread_cls}" href="{link}" target="_blank" rel="noopener">'
            f'<span class="tr-star">&#9734;</span>'
            f'<span class="tr-sender">{_esc(sender[:30])}</span>'
            f'<span class="tr-body">'
            f'<span class="tr-subj">{_esc(m["subject"][:70]) or "(no subject)"}</span>'
            f'<span class="tr-sep"> &mdash; </span>'
            f'<span class="tr-snippet">{_esc(snippet)}</span>'
            f'</span>'
            f'<span class="tr-time">{_esc(t)}</span>'
            f'</a>'
        )

    def _thread_list(msgs: list, limit: int = 25, empty: str = "") -> str:
        if not msgs:
            return f'<div class="empty">{empty}</div>'
        return '<div class="thread-list">' + "".join(_row(m) for m in msgs[:limit]) + '</div>'

    bids_html = _thread_list(bids, 25, "No bid invites in the last 7 days")

    if ongoing:
        rows = '<div class="thread-list">'
        for name, msgs in sorted(ongoing.items(), key=lambda x: -len(x[1])):
            rows += f'<div class="tr-proj-hdr">{_esc(name)} &middot; {len(msgs)}</div>'
            rows += "".join(_row(m) for m in msgs[:6])
        proj_html = rows + '</div>'
    else:
        proj_html = '<div class="empty">No ongoing project emails in the last 7 days</div>'

    team_html    = _thread_list(team, 20, "No team reports in the last 7 days")
    vendors_html = _thread_list(vendors, 20, "No vendor emails in the last 7 days")

    bid_cls = "warn" if bids else ""
    n_proj  = sum(len(v) for v in ongoing.values())
    body = f"""
<div class="stabs">
  <button class="stab" data-stab="bids" onclick="showStab('bids','INBOX_TAB')">
    Bids <span class="stab-n {bid_cls}">{len(bids)}</span>
  </button>
  <button class="stab" data-stab="projects" onclick="showStab('projects','INBOX_TAB')">
    Projects <span class="stab-n">{n_proj}</span>
  </button>
  <button class="stab" data-stab="team" onclick="showStab('team','INBOX_TAB')">
    Team <span class="stab-n">{len(team)}</span>
  </button>
  <button class="stab" data-stab="vendors" onclick="showStab('vendors','INBOX_TAB')">
    Vendors <span class="stab-n">{len(vendors)}</span>
  </button>
</div>
<div data-tab="bids">{bids_html}</div>
<div data-tab="projects" style="display:none">{proj_html}</div>
<div data-tab="team" style="display:none">{team_html}</div>
<div data-tab="vendors" style="display:none">{vendors_html}</div>
"""
    return _page_shell(token, "inbox", "Inbox", body, extra_js="initStabs('INBOX_TAB','bids');")


def _render_cal_grid(events: list[dict], today_ds: str) -> str:
    today = _date.fromisoformat(today_ds)
    week_start = today - timedelta(days=today.weekday())  # Monday

    by_date: dict[str, list] = {}
    for e in events:
        if e["date"]:
            by_date.setdefault(e["date"], []).append(e)

    hdr = '<div class="cgrid-row cgrid-hdr-row">' + "".join(
        f'<div class="cgrid-cell cgrid-hdr">{d}</div>'
        for d in ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    ) + '</div>'

    rows_html = ""
    for week in range(4):
        row = '<div class="cgrid-row">'
        for day in range(7):
            d = week_start + timedelta(weeks=week, days=day)
            ds = d.strftime("%Y-%m-%d")
            is_today = ds == today_ds
            is_past = d < today

            cell_events = by_date.get(ds, [])
            pills = ""
            for ev in cell_events[:3]:
                pill_cls = "cevt-bid" if ev["is_bid_due"] else "cevt"
                t = ev["title"][:18] + ("…" if len(ev["title"]) > 18 else "")
                pills += f'<div class="{pill_cls}">{_esc(t)}</div>'
            if len(cell_events) > 3:
                pills += f'<div class="cevt-more">+{len(cell_events) - 3}</div>'

            cell_cls = "cgrid-cell" + (" cgrid-today" if is_today else " cgrid-past" if is_past else "")
            row += f'<div class="{cell_cls}"><div class="cgrid-num">{d.day}</div>{pills}</div>'
        rows_html += row + '</div>'

    return f'<div class="cgrid">{hdr}{rows_html}</div>'


# ── Calendar page ─────────────────────────────────────────────────────────────

def render_calendar(token: str = "ryan-sc") -> str:
    cal_data = _cache_get("calendar")
    if cal_data is None:
        cal_data = _fetch_calendar_data()
        _cache_set("calendar", cal_data)

    events   = cal_data["events"]
    pt       = _pt_now()
    today_ds = pt.strftime("%Y-%m-%d")
    bid_dues = [e for e in events if e["is_bid_due"]]

    grid_html = _render_cal_grid(events, today_ds)

    def _cal_card(e: dict) -> str:
        t = _fmt_time(e["start"])
        assignee = f'<div class="event-assignee">&#9654; {_esc(e["assignee"])}</div>' if e.get("assignee") else ""
        cls = "cal-card bid-due" if e["is_bid_due"] else "cal-card"
        return (
            f'<div class="{cls}">'
            f'<div class="event-time">{t}</div>'
            f'<div class="event-body">'
            f'<div class="event-title">{_esc(e["title"])}</div>'
            f'{assignee}</div></div>'
        )

    bids_html = "".join(_cal_card(e) for e in bid_dues) if bid_dues else \
        '<div class="empty">No bid due dates in the next 4 weeks</div>'

    bid_cls = "warn" if bid_dues else ""
    body = f"""
<div class="stabs">
  <button class="stab" data-stab="grid" onclick="showStab('grid','CAL_TAB')">
    Calendar <span class="stab-n">{len(events)}</span>
  </button>
  <button class="stab" data-stab="bids" onclick="showStab('bids','CAL_TAB')">
    Bid Dues <span class="stab-n {bid_cls}">{len(bid_dues)}</span>
  </button>
</div>
<div data-tab="grid">{grid_html}</div>
<div data-tab="bids" style="display:none">{bids_html}</div>
"""
    return _page_shell(token, "calendar", "Calendar", body, extra_js="initStabs('CAL_TAB','grid');")
