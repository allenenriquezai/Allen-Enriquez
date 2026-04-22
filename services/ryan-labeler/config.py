"""Runtime config loader for ryan-labeler.

Reads configs from disk when running locally (CONFIG_DIR=./config or the repo
path). In Cloud Run, the same files are baked into the image under /app/config.
Credentials come from Secret Manager in Cloud Run; from pickle files locally.
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
ALLEN_AI_EMAIL = "allenenriquez.ai@gmail.com"


@lru_cache(maxsize=1)
def load_registry() -> dict:
    return json.loads((CONFIG_DIR / "project_registry.json").read_text())


@lru_cache(maxsize=1)
def load_routing_rules() -> dict:
    return json.loads((CONFIG_DIR / "routing_rules.json").read_text())


@lru_cache(maxsize=1)
def load_classifier_prompt() -> str:
    return (CONFIG_DIR / "classifier_prompt.md").read_text()


def load_state() -> dict:
    p = CONFIG_DIR / "state.json"
    if not p.exists():
        return {
            "last_history_id": None,
            "last_brief_sent_at": None,
            "label_ids": {},
            "run_log": [],
        }
    return json.loads(p.read_text())


def save_state(state: dict) -> None:
    p = CONFIG_DIR / "state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2))


def save_registry(registry: dict) -> None:
    p = CONFIG_DIR / "project_registry.json"
    p.write_text(json.dumps(registry, indent=2))
    load_registry.cache_clear()


def _load_token_from_env(env_var: str) -> Credentials | None:
    """In Cloud Run, token pickle is base64 in env (from Secret Manager)."""
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


def ryan_gmail_creds() -> Credentials:
    """Ryan's Gmail OAuth creds. Env var in Cloud Run, pickle file locally."""
    creds = _load_token_from_env("RYAN_GMAIL_TOKEN")
    if creds is None:
        local = Path(os.environ.get(
            "RYAN_TOKEN_PATH",
            Path(__file__).parent.parent.parent / "projects/personal/clients/ryan/token_ryan.pickle",
        ))
        creds = _load_token_from_file(local)
    if creds is None:
        raise RuntimeError("No Ryan Gmail credentials. Set RYAN_GMAIL_TOKEN env or RYAN_TOKEN_PATH.")
    return creds


def ryan_calendar_creds() -> Credentials:
    """Same token as Gmail — single OAuth grants both scopes."""
    return ryan_gmail_creds()


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
