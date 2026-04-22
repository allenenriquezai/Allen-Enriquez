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
from briefer import run_brief, run_evening_brief, run_brief_preview, run_evening_brief_preview
from classifier import classify
from dashboard import render_dashboard, render_inbox, render_calendar
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
    # 6:30 AM PT
    scheduler.add_job(_fire_morning_brief, CronTrigger(hour=6, minute=30, timezone="America/Los_Angeles"))
    # 6:00 PM PT
    scheduler.add_job(_fire_evening_brief, CronTrigger(hour=18, minute=0, timezone="America/Los_Angeles"))
    scheduler.start()
    log.info("scheduler started — morning 06:30 PT, evening 18:00 PT")
    yield
    scheduler.shutdown()


app = FastAPI(title="ryan-labeler", version="0.1.0", lifespan=lifespan)


class LabelRequest(BaseModel):
    message_id: str
    thread_id: Optional[str] = None
    dry_run: bool = False


class LabelResponse(BaseModel):
    message_id: str
    bucket: str
    project: Optional[str] = None
    skip_inbox: bool
    confidence: float
    applied: bool
    error: Optional[str] = None
    took_ms: int


def _append_audit(entry: dict) -> None:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = config.audit_dir() / f"{day}.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


@app.get("/health")
def health() -> dict:
    state = config.load_state()
    return {
        "ok": True,
        "service": "ryan-labeler",
        "last_brief_sent_at": state.get("last_brief_sent_at"),
        "run_log_tail": state.get("run_log", [])[-3:],
    }


@app.post("/label", response_model=LabelResponse)
def label(req: LabelRequest) -> LabelResponse:
    start = datetime.now(timezone.utc)
    try:
        msg = fetch_message(req.message_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"fetch_message failed: {e}")

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
        )

    # Already labeled (e.g., duplicate webhook) — short-circuit to be idempotent
    existing_labels = set(msg.get("label_ids", []))
    already_routed_markers = {"Unimportant", "Bids/Invites", "Vendors/Pricing", "Daily Accomplishments PH", "needs-review"}
    # We'd need to resolve label IDs to names to check; skip the shortcut for now
    # (idempotent modify is safe — Gmail API deduplicates addLabelIds)

    result = classify(
        from_addr=msg["from"],
        subject=msg["subject"],
        snippet=msg["snippet"],
    )

    # Sender overrides: admin@ and joseph@ routing rules
    from_lower = msg["from"].lower()
    office_senders = ["admin@sc-incorporated.com", "joseph@sc-incorporated.com", "ryan@sc-incorporated.com"]
    if any(s in from_lower for s in office_senders):
        if result["category"] in ("bid_invite", "vendor"):
            result = {**result, "category": "other", "reason": "office-sender bid/vendor → archive/review (override)"}
        elif result["category"] not in ("promo", "personal"):
            result = {**result, "category": "office", "reason": "office-sender → office label (override)"}

    routing = route_and_label(req.message_id, result, dry_run=req.dry_run)

    audit_entry = {
        "ts": start.isoformat(),
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
def dashboard(token: str = "") -> HTMLResponse:
    _check_token(token)
    try:
        return HTMLResponse(content=render_dashboard(token=token))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"dashboard failed: {e}")


@app.get("/inbox", response_class=HTMLResponse)
def inbox(token: str = "") -> HTMLResponse:
    _check_token(token)
    try:
        return HTMLResponse(content=render_inbox(token=token))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"inbox failed: {e}")


@app.get("/calendar", response_class=HTMLResponse)
def calendar_view(token: str = "") -> HTMLResponse:
    _check_token(token)
    try:
        return HTMLResponse(content=render_calendar(token=token))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"calendar failed: {e}")


@app.get("/brief-preview", response_class=HTMLResponse)
def brief_preview(token: str = "") -> HTMLResponse:
    _check_token(token)
    try:
        return HTMLResponse(content=run_brief_preview(token=token))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"brief preview failed: {e}")


@app.get("/evening-brief-preview", response_class=HTMLResponse)
def evening_brief_preview(token: str = "") -> HTMLResponse:
    _check_token(token)
    try:
        return HTMLResponse(content=run_evening_brief_preview(token=token))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"evening brief preview failed: {e}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
