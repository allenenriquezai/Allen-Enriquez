"""Single-message classifier (Haiku 4.5) for Ryan's inbox.

Adapted from tools/gmail_inbox_audit.py lines 318-377 (batch classifier).
This version classifies ONE message per call since the webhook fires per-message.
Uses prompt caching on the system prompt for cost amortization across calls.
"""
from __future__ import annotations
import json
import re
import time
from typing import Optional

import anthropic

import config


_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.anthropic_api_key())
    return _client


def classify(
    from_addr: str,
    subject: str,
    snippet: str,
    body_text: Optional[str] = None,
    mailbox: str = config.DEFAULT_MAILBOX,
) -> dict:
    """Classify one email. Returns:
        {category, project_hint, confidence, reason, took_ms}
    """
    system_prompt = config.load_classifier_prompt(mailbox)

    # Truncate body — snippet is usually enough; body_text added for borderline cases
    content_parts = [
        f"From: {from_addr[:200]}",
        f"Subject: {subject[:200]}",
        f"Snippet: {snippet[:500]}",
    ]
    if body_text:
        content_parts.append(f"Body: {body_text[:1500]}")
    user_msg = "\n".join(content_parts)

    start = time.time()
    last_exc: Optional[Exception] = None
    for attempt in range(4):
        try:
            resp = _get_client().messages.create(
                model="claude-haiku-4-5",
                max_tokens=400,
                system=[{
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_msg}],
            )
            text = resp.content[0].text.strip()
            text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
            parsed = json.loads(text)
            usage = getattr(resp, "usage", None)
            usage_dict = {
                "input_tokens": getattr(usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(usage, "output_tokens", 0) or 0,
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
            } if usage is not None else {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
            return {
                "category": parsed.get("category", "other"),
                "project_hint": parsed.get("project_hint"),
                "confidence": float(parsed.get("confidence", 0.0)),
                "reason": parsed.get("reason", ""),
                "took_ms": int((time.time() - start) * 1000),
                "usage": usage_dict,
            }
        except (anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
            last_exc = e
            wait = 2 ** attempt + 0.5
            time.sleep(wait)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            last_exc = e
            break

    # Fallthrough: classify as 'other' on persistent failure, surface in audit
    return {
        "category": "other",
        "project_hint": None,
        "confidence": 0.0,
        "reason": f"classifier_error: {type(last_exc).__name__}: {last_exc}" if last_exc else "unknown_error",
        "took_ms": int((time.time() - start) * 1000),
        "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0},
    }
