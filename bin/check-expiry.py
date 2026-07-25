#!/usr/bin/env python3
"""Open / escalate / close GitHub issues as tracked credentials near expiry.

Called by .github/workflows/expiry-check.yml on a daily cron. Reads the
credential registry from the EXPIRY_REGISTRY env var (a GitHub Actions secret;
JSON string). For local runs it falls back to the gitignored
admin/registry.local.json.

One issue per credential id, title "Credential expiring: {id}". Escalates via
an <!-- expiry-band:N --> marker in the body. Auto-closes when the date is
pushed out or the id is removed from the registry.

Local / agent use: set DRY_RUN=1 to print what would happen without making any
gh issue create/close/comment/edit calls. Required for any cold-run check.
"""

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime

EXPIRY_THRESHOLDS = (30, 14, 7, 1)
ALLOWED_KEYS = {
    "id", "label", "project", "env_vars", "repos",
    "type", "expires", "rotation_days", "renew_url", "notes",
}
REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "..", "admin", "registry.local.json")
DRY_RUN = bool(os.environ.get("DRY_RUN"))
TITLE_PREFIX = "Credential expiring: "
_BAND_RE = re.compile(r"<!--\s*expiry-band:(\d+)\s*-->")


def _today():
    """Today's date. Isolated so tests can patch it for deterministic day-math."""
    return date.today()


def days_until(expires_str, today=None):
    """Whole days from `today` to an ISO YYYY-MM-DD date. Negative = past."""
    today = today or _today()
    return (date.fromisoformat(expires_str) - today).days


def band_for(days):
    """The tightest threshold `days` has crossed, or None if outside all of them."""
    crossed = [t for t in EXPIRY_THRESHOLDS if days <= t]
    return min(crossed) if crossed else None


def validate_registry(reg):
    """Return the integrations list. Raise ValueError on any bad shape.

    Every entry needs a truthy `id` and an `expires` that is either the literal
    "UNKNOWN" or a parseable ISO date. Unknown top-level keys fail (typo guard).
    """
    if not isinstance(reg, dict) or not isinstance(reg.get("integrations"), list):
        raise ValueError("registry must be an object with an 'integrations' list")
    seen = set()
    for entry in reg["integrations"]:
        extra = set(entry) - ALLOWED_KEYS
        if extra:
            raise ValueError(f"unknown key(s) {sorted(extra)} in entry {entry.get('id', '?')}")
        if not entry.get("id"):
            raise ValueError("entry missing 'id'")
        if entry["id"] in seen:
            raise ValueError(f"duplicate id {entry['id']}")
        seen.add(entry["id"])
        exp = entry.get("expires")
        if exp != "UNKNOWN":
            date.fromisoformat(exp)  # raises ValueError if malformed / missing
    return reg["integrations"]


def load_registry():
    """Load + validate the registry from EXPIRY_REGISTRY env, else the local file."""
    raw = os.environ.get("EXPIRY_REGISTRY")
    if raw is None:
        try:
            with open(REGISTRY_FILE, encoding="utf-8") as f:
                raw = f.read()
        except FileNotFoundError:
            print("::error::EXPIRY_REGISTRY not set and admin/registry.local.json missing",
                  file=sys.stderr)
            sys.exit(1)
    return validate_registry(json.loads(raw))
