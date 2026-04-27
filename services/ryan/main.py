"""FastAPI entrypoint for ryan-labeler Cloud Run service.

Endpoints:
- GET  /health  — liveness + last-run info
- POST /label   — classify + label a single Gmail message (called by n8n)
- POST /brief   — compose + send daily morning brief (called by Cloud Scheduler)
"""
from __future__ import annotations
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

import config
from briefer import run_brief, run_evening_brief, add_task, toggle_task, delete_task
from classifier import classify
from dashboard import render_dashboard, render_inbox, render_calendar, render_thread, render_tasks_html, warm_all_caches
from bid_extractor import extract_bid_due
from labeler import fetch_message, route_and_label

log = logging.getLogger(__name__)


def _fire_morning_brief() -> None:
    try:
        result = run_brief()
        log.info("morning brief sent: %s", result.get("status"))
    except Exception as e:
        log.error("morning brief failed: %s", e)


def _fire_evening_brief() -> None:
    try:
        result = run_evening_brief()
        log.info("evening brief sent: %s", result.get("status"))
    except Exception as e:
        log.error("evening brief failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler(timezone="America/Los_Angeles")
    # 6:30 AM PT — coalesce+max_instances=1 prevents catch-up fires on restart
    scheduler.add_job(_fire_morning_brief, CronTrigger(hour=6, minute=30, timezone="America/Los_Angeles"),
                      coalesce=True, max_instances=1, misfire_grace_time=300)
    # 6:00 PM PT
    scheduler.add_job(_fire_evening_brief, CronTrigger(hour=18, minute=0, timezone="America/Los_Angeles"),
                      coalesce=True, max_instances=1, misfire_grace_time=300)
    # Cache warm-up every 5 min so page loads are instant
    scheduler.add_job(warm_all_caches, "interval", minutes=5)
    scheduler.start()
    log.info("scheduler started — morning 06:30 PT, evening 18:00 PT, cache warm every 5 min")
    yield
    scheduler.shutdown()


app = FastAPI(title="ryan-labeler", version="0.1.0", lifespan=lifespan)


class LabelRequest(BaseModel):
    message_id: str
    thread_id: Optional[str] = None
    dry_run: bool = False
    mailbox: str = config.DEFAULT_MAILBOX  # "ryan" | "joseph"


class LabelResponse(BaseModel):
    message_id: str
    bucket: str
    project: Optional[str] = None
    skip_inbox: bool
    confidence: float
    applied: bool
    error: Optional[str] = None
    took_ms: int
    mailbox: str = config.DEFAULT_MAILBOX


class TaskRequest(BaseModel):
    text: Optional[str] = None
    id: Optional[str] = None


def _append_audit(entry: dict) -> None:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = config.audit_dir() / f"{day}.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


@app.get("/health")
def health() -> dict:
    out = {"ok": True, "service": "ryan-labeler", "mailboxes": {}}
    for mb in config.MAILBOXES:
        try:
            state = config.load_state(mb)
            out["mailboxes"][mb] = {
                "last_brief_sent_at": state.get("last_brief_sent_at"),
                "last_evening_brief_sent_at": state.get("last_evening_brief_sent_at"),
                "run_log_tail": state.get("run_log", [])[-3:],
            }
        except Exception as e:
            out["mailboxes"][mb] = {"error": str(e)}
    # Backward-compat: top-level keys still report Ryan
    ryan_state = out["mailboxes"].get("ryan", {})
    out["last_brief_sent_at"] = ryan_state.get("last_brief_sent_at")
    out["run_log_tail"] = ryan_state.get("run_log_tail", [])
    return out


def _apply_sender_overrides(classification: dict, from_addr: str, mailbox: str) -> dict:
    """Apply per-mailbox sender_overrides defined in routing_rules JSON.

    Each rule shape:
      {match_from_contains: [...], if_category_in: [...] or if_category_not_in: [...],
       then_force_category: "..."}
    First matching rule wins. Falls back to legacy hardcoded office-sender logic
    if no rules defined for the mailbox.
    """
    rules = config.load_routing_rules(mailbox)
    overrides = (rules.get("sender_overrides") or {}).get("rules") or []
    from_lower = from_addr.lower()
    for rule in overrides:
        needles = rule.get("match_from_contains") or []
        if not any(n.lower() in from_lower for n in needles):
            continue
        if "if_category_in" in rule and classification["category"] not in rule["if_category_in"]:
            continue
        if "if_category_not_in" in rule and classification["category"] in rule["if_category_not_in"]:
            continue
        forced = rule.get("then_force_category")
        if forced and forced != classification["category"]:
            return {**classification, "category": forced,
                    "reason": f"sender-override:{rule.get('id', '')} → {forced}"}
    return classification


@app.post("/label", response_model=LabelResponse)
def label(req: LabelRequest) -> LabelResponse:
    start = datetime.now(timezone.utc)
    if req.mailbox not in config.MAILBOXES:
        raise HTTPException(status_code=400, detail=f"unknown mailbox: {req.mailbox}")

    try:
        msg = fetch_message(req.message_id, mailbox=req.mailbox)
    except Exception as e:
        took = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        return LabelResponse(
            message_id=req.message_id,
            bucket="skip",
            skip_inbox=False,
            confidence=1.0,
            applied=False,
            error=f"message_not_found: {e}",
            took_ms=took,
            mailbox=req.mailbox,
        )

    # Skip self-sent briefs — allenenriquez.ai@gmail.com is the brief sender
    if config.ALLEN_AI_EMAIL in msg["from"].lower():
        took = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
        return LabelResponse(
            message_id=req.message_id,
            bucket="skip",
            skip_inbox=False,
            confidence=1.0,
            applied=False,
            error="skip: from brief sender",
            took_ms=took,
            mailbox=req.mailbox,
        )

    result = classify(
        from_addr=msg["from"],
        subject=msg["subject"],
        snippet=msg["snippet"],
        mailbox=req.mailbox,
    )

    # Per-mailbox sender overrides (Joseph excludes himself, Ryan includes joseph@)
    result = _apply_sender_overrides(result, msg["from"], req.mailbox)

    # Pass from_addr through so labeler can apply sub_label_by_sender_contains
    # (e.g. ADP / Acrisure on Joseph's company_bills bucket).
    result_for_routing = {**result, "_from": msg["from"]}

    routing = route_and_label(
        req.message_id, result_for_routing, dry_run=req.dry_run, mailbox=req.mailbox,
    )

    # Bid due date extraction → inbox owner's calendar
    if result["category"] == "bid_invite" and routing.get("applied") and not req.dry_run:
        try:
            extract_bid_due(
                msg_id=req.message_id,
                from_addr=msg["from"],
                subject=msg["subject"],
                snippet=msg["snippet"],
                mailbox=req.mailbox,
            )
        except Exception as e:
            log.warning("bid extraction failed: %s", e)

    audit_entry = {
        "ts": start.isoformat(),
        "mailbox": req.mailbox,
        "message_id": req.message_id,
        "thread_id": req.thread_id or msg.get("thread_id"),
        "from": msg["from"][:120],
        "subject": msg["subject"][:160],
        "classification": result,
        "routing": routing,
    }
    _append_audit(audit_entry)

    return LabelResponse(
        message_id=req.message_id,
        bucket=result["category"],
        project=routing.get("project"),
        skip_inbox=routing.get("skip_inbox", False),
        confidence=result["confidence"],
        applied=routing.get("applied", req.dry_run),
        error=routing.get("error"),
        took_ms=result["took_ms"],
        mailbox=req.mailbox,
    )


@app.post("/brief")
def brief(dry_run: bool = False) -> dict:
    try:
        return run_brief(dry_run=dry_run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"brief failed: {e}")


@app.post("/evening-brief")
def evening_brief(dry_run: bool = False) -> dict:
    try:
        return run_evening_brief(dry_run=dry_run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"evening brief failed: {e}")


_DASHBOARD_TOKEN = os.environ.get("DASHBOARD_TOKEN", "ryan-sc")


def _check_token(token: str) -> None:
    if token != _DASHBOARD_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(token: str = "", refresh: bool = False) -> HTMLResponse:
    _check_token(token)
    try:
        return HTMLResponse(content=render_dashboard(token=token, refresh=refresh))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"dashboard failed: {e}")


@app.get("/inbox", response_class=HTMLResponse)
def inbox(token: str = "", refresh: bool = False) -> HTMLResponse:
    _check_token(token)
    try:
        return HTMLResponse(content=render_inbox(token=token, refresh=refresh))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"inbox failed: {e}")


@app.get("/calendar", response_class=HTMLResponse)
def calendar_view(token: str = "", refresh: bool = False) -> HTMLResponse:
    _check_token(token)
    try:
        return HTMLResponse(content=render_calendar(token=token, refresh=refresh))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"calendar failed: {e}")



@app.get("/thread", response_class=HTMLResponse)
def thread_view(id: str = "", token: str = "") -> HTMLResponse:
    _check_token(token)
    if not id:
        raise HTTPException(status_code=400, detail="Missing thread id")
    try:
        return HTMLResponse(content=render_thread(id, token))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"thread failed: {e}")


@app.get("/tasks-html")
def tasks_html_fragment(token: str = "") -> HTMLResponse:
    _check_token(token)
    return HTMLResponse(content=render_tasks_html(token))


@app.post("/tasks/add")
def task_add(req: TaskRequest, token: str = "") -> dict:
    _check_token(token)
    if not req.text:
        raise HTTPException(status_code=400, detail="text required")
    task = add_task(req.text)
    return {"ok": True, "task": task}


@app.post("/tasks/toggle")
def task_toggle(req: TaskRequest, token: str = "") -> dict:
    _check_token(token)
    if not req.id:
        raise HTTPException(status_code=400, detail="id required")
    done = toggle_task(req.id)
    return {"ok": True, "done": done}


@app.post("/tasks/delete")
def task_delete(req: TaskRequest, token: str = "") -> dict:
    _check_token(token)
    if not req.id:
        raise HTTPException(status_code=400, detail="id required")
    delete_task(req.id)
    return {"ok": True}


@app.get("/audit/export")
def audit_export(token: str = "", days: int = 7, limit: int = 1000) -> list:
    """Return recent audit entries for local persistence + self-improve analysis."""
    _check_token(token)
    from datetime import timedelta
    entries = []
    audit_path = config.audit_dir()
    today = datetime.now(timezone.utc)
    for i in range(days):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        path = audit_path / f"{day}.jsonl"
        if path.exists():
            for line in path.read_text().splitlines():
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    return entries[-limit:]


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
