"""Project registry I/O + fuzzy match.

Classifier returns a project_hint (free text from email subject/body). We match
it against known project aliases. If no match and confidence is high enough,
auto-create a new project entry.
"""
import re
from datetime import date
from typing import Optional

import config


def _normalize(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _slugify(s: str) -> str:
    s = _normalize(s).replace(" ", "-")
    return re.sub(r"-+", "-", s)[:64]


def find_project(project_hint: str) -> Optional[dict]:
    """Return project dict if hint matches any alias (fuzzy). None otherwise."""
    if not project_hint:
        return None
    norm_hint = _normalize(project_hint)
    registry = config.load_registry()
    for proj in registry["projects"]:
        for alias in proj["aliases"]:
            norm_alias = _normalize(alias)
            # Exact match or substring either direction
            if norm_alias == norm_hint:
                return proj
            if norm_alias in norm_hint or norm_hint in norm_alias:
                # Guard against tiny overlaps (e.g., "pura" matching just "pura")
                if len(norm_alias) >= 6 and len(norm_hint) >= 6:
                    return proj
    return None


def create_project(project_hint: str) -> dict:
    """Add a new project entry to the registry. Persist to disk."""
    registry = config.load_registry()

    # Check if slug collides
    base_slug = _slugify(project_hint)
    existing_slugs = {p["id"] for p in registry["projects"]}
    slug = base_slug
    i = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{i}"
        i += 1

    new_proj = {
        "id": slug,
        "display_name": project_hint.strip()[:80],
        "aliases": [project_hint.strip()],
        "label_id": None,
        "status": "upcoming",
        "created_at": date.today().isoformat(),
        "city": None,
        "auto_created": True,
    }
    registry["projects"].append(new_proj)
    config.save_registry(registry)
    return new_proj


def update_label_id(project_id: str, label_id: str) -> None:
    registry = config.load_registry()
    for p in registry["projects"]:
        if p["id"] == project_id:
            p["label_id"] = label_id
            break
    config.save_registry(registry)


def project_label_name(project: dict) -> str:
    rules = config.load_routing_rules()
    bucket_cfg = rules["buckets"]["project"]
    status = project.get("status", "unknown")
    if status == "upcoming":
        prefix = bucket_cfg.get("label_prefix_upcoming", "1. Projects/A. Upcoming/")
    elif status == "completed":
        prefix = bucket_cfg.get("label_prefix_completed", "1. Projects/C. Completed/")
    elif status == "active":
        prefix = bucket_cfg.get("label_prefix_active", "1. Projects/B. Ongoing/")
    else:
        prefix = bucket_cfg.get("label_prefix_unknown", "1. Projects/D. Unknown/")
    return f"{prefix}{project['display_name']}"
