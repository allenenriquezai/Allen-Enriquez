"""Runtime config loader for sc-incorporated labeler service.

Reads configs from disk when running locally (CONFIG_DIR=./config or the repo
path). On Railway, the same files are baked into the image under /app/config.
Credentials come from env-base64 pickles on Railway; from pickle files locally.

Multi-mailbox: same service handles Ryan + Joseph (and future SC team). Pass
`mailbox` (e.g. "ryan", "joseph") to credential and state loaders. Routing
rules and classifier prompt resolve overlay files first
(`routing_rules.{mailbox}.json`) and fall back to base.
"""
from __future__ import annotations
import json
import os
import pickle
from functools import lru_cache
from pathlib import Path

from google.oauth2.credentials import Credentials


CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", Path(__file__).parent / "config"))

RYAN_EMAIL = "ryan@sc-incorporated.com"
JOSEPH_EMAIL = "joseph@sc-incorporated.com"
ALLEN_AI_EMAIL = "allenenriquez.ai@gmail.com"

DEFAULT_MAILBOX = "ryan"

# Mailbox registry — single source of truth for per-mailbox config.
# brief_greeting_name = first name used in "Good morning {name}" copy.
MAILBOXES: dict[str, dict] = {
    "ryan": {
        "email": RYAN_EMAIL,
        "token_env": "RYAN_GMAIL_TOKEN",
        "token_path_env": "RYAN_TOKEN_PATH",
        "token_path_default": "projects/personal/clients/ryan/token_ryan.pickle",
        "brief_recipient": RYAN_EMAIL,
        "brief_greeting_name": "Ryan",
    },
    "joseph": {
        "email": JOSEPH_EMAIL,
        "token_env": "JOSEPH_GMAIL_TOKEN",
        "token_path_env": "JOSEPH_TOKEN_PATH",
        "token_path_default": "projects/personal/clients/joseph/token_joseph.pickle",
        "brief_recipient": JOSEPH_EMAIL,
        "brief_greeting_name": "Joseph",
    },
}


def mailbox_config(mailbox: str) -> dict:
    if mailbox not in MAILBOXES:
        raise ValueError(f"Unknown mailbox: {mailbox!r}. Valid: {list(MAILBOXES)}")
    return MAILBOXES[mailbox]


@lru_cache(maxsize=1)
def load_registry() -> dict:
    return json.loads((CONFIG_DIR / "project_registry.json").read_text())


@lru_cache(maxsize=4)
def load_routing_rules(mailbox: str = DEFAULT_MAILBOX) -> dict:
    """Load routing rules. Per-mailbox overlay merges over base.

    Overlay file path: `routing_rules.{mailbox}.json`. Top-level keys in the
    overlay replace top-level keys in base; bucket dicts are deep-merged so
    Joseph can add `company_bills` without restating Ryan's buckets.
    """
    base = json.loads((CONFIG_DIR / "routing_rules.json").read_text())
    overlay_path = CONFIG_DIR / f"routing_rules.{mailbox}.json"
    if not overlay_path.exists():
        return base
    overlay = json.loads(overlay_path.read_text())
    return _merge_routing_rules(base, overlay)


def _merge_routing_rules(base: dict, overlay: dict) -> dict:
    """Shallow merge for top-level keys; deep merge for `buckets` dict."""
    merged = dict(base)
    for k, v in overlay.items():
        if k == "buckets" and isinstance(v, dict) and isinstance(base.get("buckets"), dict):
            merged_buckets = dict(base["buckets"])
            merged_buckets.update(v)
            merged["buckets"] = merged_buckets
        else:
            merged[k] = v
    return merged


@lru_cache(maxsize=4)
def load_classifier_prompt(mailbox: str = DEFAULT_MAILBOX) -> str:
    """Load classifier prompt. Per-mailbox overlay file replaces base if present."""
    overlay_path = CONFIG_DIR / f"classifier_prompt.{mailbox}.md"
    if overlay_path.exists():
        return overlay_path.read_text()
    return (CONFIG_DIR / "classifier_prompt.md").read_text()


def _state_path(mailbox: str) -> Path:
    """Per-mailbox state file. `ryan` uses legacy `state.json` for backward compat."""
    if mailbox == "ryan":
        return CONFIG_DIR / "state.json"
    return CONFIG_DIR / f"state.{mailbox}.json"


def load_state(mailbox: str = DEFAULT_MAILBOX) -> dict:
    p = _state_path(mailbox)
    if not p.exists():
        return {
            "last_history_id": None,
            "last_brief_sent_at": None,
            "label_ids": {},
            "run_log": [],
        }
    return json.loads(p.read_text())


def save_state(state: dict, mailbox: str = DEFAULT_MAILBOX) -> None:
    p = _state_path(mailbox)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2))


def save_registry(registry: dict) -> None:
    p = CONFIG_DIR / "project_registry.json"
    p.write_text(json.dumps(registry, indent=2))
    load_registry.cache_clear()


def _load_token_from_env(env_var: str) -> Credentials | None:
    """On Railway, token pickle is base64 in env (from Railway secret)."""
    import base64
    raw = os.environ.get(env_var)
    if not raw:
        return None
    data = base64.b64decode(raw)
    return pickle.loads(data)


def _load_token_from_file(path: Path) -> Credentials | None:
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def gmail_creds(mailbox: str = DEFAULT_MAILBOX) -> Credentials:
    """Mailbox Gmail OAuth creds. Env var on Railway, pickle file locally."""
    cfg = mailbox_config(mailbox)
    creds = _load_token_from_env(cfg["token_env"])
    if creds is None:
        local = Path(os.environ.get(
            cfg["token_path_env"],
            Path(__file__).parent.parent.parent / cfg["token_path_default"],
        ))
        creds = _load_token_from_file(local)
    if creds is None:
        raise RuntimeError(
            f"No Gmail credentials for mailbox={mailbox!r}. "
            f"Set {cfg['token_env']} env or {cfg['token_path_env']}."
        )
    return creds


def calendar_creds(mailbox: str = DEFAULT_MAILBOX) -> Credentials:
    """Same token as Gmail — single OAuth grants both scopes."""
    return gmail_creds(mailbox)


# ── Backward-compat shims so existing callers keep working ─────────────────
def ryan_gmail_creds() -> Credentials:
    return gmail_creds("ryan")


def ryan_calendar_creds() -> Credentials:
    return calendar_creds("ryan")


def allen_ai_gmail_creds() -> Credentials:
    creds = _load_token_from_env("ALLEN_AI_GMAIL_TOKEN")
    if creds is None:
        local = Path(os.environ.get(
            "ALLEN_AI_TOKEN_PATH",
            Path(__file__).parent.parent.parent / "projects/personal/token_personal_ai.pickle",
        ))
        creds = _load_token_from_file(local)
    if creds is None:
        raise RuntimeError("No Allen .ai Gmail credentials.")
    return creds


def anthropic_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    eps_env = Path(__file__).parent.parent.parent / "projects/eps/.env"
    if eps_env.exists():
        for line in eps_env.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("ANTHROPIC_API_KEY not set.")


def audit_dir() -> Path:
    p = CONFIG_DIR / "audit"
    p.mkdir(parents=True, exist_ok=True)
    return p
