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
from datetime import date

EXPIRY_THRESHOLDS = (30, 14, 7, 1)
ALLOWED_KEYS = {
    "id", "label", "project", "env_vars", "repos",
    "type", "expires", "rotation_days", "renew_url", "notes",
}
REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "..", "admin", "registry.local.json")
STATUS_FILE = os.path.join(os.path.dirname(__file__), "..", "admin", "status.json")
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
            if not isinstance(exp, str):
                raise ValueError(f"entry {entry['id']} has a missing or non-string 'expires'")
            date.fromisoformat(exp)  # raises ValueError if malformed
    return reg["integrations"]


def load_registry():
    """Load + validate the registry from EXPIRY_REGISTRY env, else the local file.

    An empty / unset value exits cleanly (code 0): this is the state of the
    EXPIRY_REGISTRY secret before it's first populated, and it means "no
    credentials tracked yet" — a no-op, not an error. It MUST short-circuit
    here so main() never reaches orphan-cleanup with an empty registry (which
    would close every open expiry issue)."""
    raw = os.environ.get("EXPIRY_REGISTRY")
    if raw is None:
        try:
            with open(REGISTRY_FILE, encoding="utf-8") as f:
                raw = f.read()
        except FileNotFoundError:
            print("::error::EXPIRY_REGISTRY not set and admin/registry.local.json missing",
                  file=sys.stderr)
            sys.exit(1)
    if not raw.strip():
        print("EXPIRY_REGISTRY is empty — no credentials tracked yet; nothing to check.")
        sys.exit(0)
    return validate_registry(json.loads(raw))


def gh(*args):
    """Run a gh CLI command; return stdout or raise on failure."""
    is_write = args and args[0] == "issue" and len(args) > 1 and args[1] in ("create", "close", "comment", "edit")
    if DRY_RUN and is_write:
        print(f"[dry-run] would run: gh {' '.join(args)}")
        return ""
    result = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"gh {' '.join(args)} failed: {result.stderr.strip()}", file=sys.stderr)
        raise RuntimeError(result.stderr.strip())
    return result.stdout


def ensure_label(name, color, description):
    """Create the label if missing. No-op if it already exists."""
    if DRY_RUN:
        print(f"[dry-run] would ensure label: {name}")
        return
    result = subprocess.run(
        ["gh", "label", "create", name, "--color", color, "--description", description],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"WARN: could not create label {name}: {result.stderr.strip()}", file=sys.stderr)


def open_expiry_issues():
    """Return {id: {"number": int, "band": int}} for open expiry-warning issues.

    The current band is read from an <!-- expiry-band:N --> marker in the body;
    a missing marker defaults to the widest threshold so a legacy issue never
    looks 'already escalated'."""
    raw = gh("issue", "list", "--label", "expiry-warning", "--state", "open",
             "--json", "number,title,body")
    data = json.loads(raw or "[]")
    out = {}
    for issue in data:
        title = issue["title"]
        if title.startswith(TITLE_PREFIX):
            cid = title[len(TITLE_PREFIX):].strip()
            match = _BAND_RE.search(issue.get("body") or "")
            band = int(match.group(1)) if match else max(EXPIRY_THRESHOLDS)
            out[cid] = {"number": issue["number"], "band": band}
    return out


def build_body(entry, days, band):
    """Render the issue body. Carries the fix and a machine-readable band marker."""
    state = "has **EXPIRED**" if days < 0 else f"expires in **{days} day(s)**"
    lines = [
        f"Credential `{entry['id']}` {state}.",
        "",
        f"- **What:** {entry.get('label', '—')}",
        f"- **Project:** {entry.get('project', '—')}",
        f"- **Env vars:** {', '.join(entry.get('env_vars') or []) or '—'}",
        f"- **Repos:** {', '.join(entry.get('repos') or []) or '—'}",
        f"- **Expires:** `{entry.get('expires')}`",
    ]
    if entry.get("rotation_days"):
        lines.append(f"- **Rotation cadence:** {entry['rotation_days']} days")
    if entry.get("renew_url"):
        lines.append(f"- **Renew:** {entry['renew_url']}")
    if entry.get("notes"):
        lines.append(f"- **Notes:** {entry['notes']}")
    lines += [
        "",
        "### What to do",
        "Rotate/renew the credential, update its `expires` date in "
        "`admin/registry.local.json`, then run `./bin/push-registry.sh`. "
        "This issue auto-closes on the next run once the date is pushed out.",
        "",
        "---",
        "_Auto-opened by `bin/check-expiry.py`._",
        f"<!-- expiry-band:{band} -->",
    ]
    return "\n".join(lines)


def compute_status(integrations, today=None):
    """Bare urgency counts for the public `/admin/` doorbell — NO ids, NO dates.

    Disjoint bands. Expired (days < 0) folds into within_7 (most urgent).
    `expires:"UNKNOWN"` -> needs_date. Entries >30 days out are uncounted."""
    today = today or _today()
    within_7 = within_14 = within_30 = needs_date = 0
    for entry in integrations:
        exp = entry.get("expires")
        if exp == "UNKNOWN":
            needs_date += 1
            continue
        days = days_until(exp, today)
        if days <= 7:
            within_7 += 1
        elif days <= 14:
            within_14 += 1
        elif days <= 30:
            within_30 += 1
    return {"expiry": {"within_7": within_7, "within_14": within_14,
                       "within_30": within_30, "needs_date": needs_date}}


def write_status_json(integrations, today=None):
    """Write the public doorbell file (counts only). Prints under DRY_RUN
    instead of touching the tree."""
    status = compute_status(integrations, today)
    if DRY_RUN:
        print(f"[dry-run] status.json would be: {json.dumps(status['expiry'], sort_keys=True)}")
        return
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, indent=2, sort_keys=True)
        f.write("\n")


def main():
    integrations = load_registry()
    ensure_label("expiry-warning", "D93F0B", "A tracked credential is approaching expiry")

    try:
        open_issues = open_expiry_issues()
    except RuntimeError as e:
        err = str(e)
        # Transient GitHub API errors (5xx, gateway timeout) — skip this run
        # rather than fail the workflow. Tomorrow's run catches real expiries.
        if any(x in err for x in ("504", "503", "502", "500", "Timeout", "timeout")):
            print(f"GitHub API transient error — skipping run: {err}", file=sys.stderr)
            sys.exit(0)
        raise

    today = _today()
    opened = escalated = closed = 0
    active_ids = set()

    for entry in integrations:
        cid = entry["id"]
        active_ids.add(cid)
        if entry.get("expires") == "UNKNOWN":
            existing = open_issues.get(cid)
            if existing is not None:
                gh("issue", "close", str(existing["number"]),
                   "--comment", f"`{cid}` no longer has a tracked expiry date (set to UNKNOWN). "
                                f"Auto-closed by `bin/check-expiry.py`.")
                print(f"CLOSE #{existing['number']}: {cid} (expiry cleared to UNKNOWN)")
                closed += 1
            else:
                print(f"SKIP (no date): {cid}")
            continue

        days = days_until(entry["expires"], today)
        band = band_for(days)
        existing = open_issues.get(cid)

        if band is not None and existing is None:
            gh("issue", "create", "--title", f"{TITLE_PREFIX}{cid}",
               "--body", build_body(entry, days, band), "--label", "expiry-warning")
            print(f"OPEN: {cid} ({days}d, band {band})")
            opened += 1
        elif band is not None and existing is not None:
            if band < existing["band"]:
                gh("issue", "edit", str(existing["number"]),
                   "--body", build_body(entry, days, band))
                gh("issue", "comment", str(existing["number"]),
                   "--body", f"⏰ Escalation: `{cid}` now expires in **{days} day(s)** "
                             f"(was tracking at the {existing['band']}-day mark).")
                print(f"ESCALATE #{existing['number']}: {cid} → band {band}")
                escalated += 1
            else:
                # No 'widen' branch by design: if a credential is partially renewed
                # (band widens but is still within a threshold) the body may go stale
                # until it re-tightens or fully renews (which closes it). Fail-safe:
                # this over-warns, never under-warns.
                print(f"OPEN-ISSUE (no change): {cid} ({days}d, band {band})")
        elif band is None and existing is not None:
            gh("issue", "close", str(existing["number"]),
               "--comment", f"`{cid}` is no longer near expiry (now {days} days out). "
                            f"Auto-closed by `bin/check-expiry.py`.")
            print(f"CLOSE #{existing['number']}: {cid} renewed")
            closed += 1
        else:
            print(f"OK: {cid} ({days}d)")

    # Orphan cleanup: close issues for ids removed from the registry.
    for cid, meta in open_issues.items():
        if cid not in active_ids:
            gh("issue", "close", str(meta["number"]),
               "--comment", f"`{cid}` is no longer in the expiry registry (removed). "
                            f"Auto-closed by `bin/check-expiry.py`.")
            print(f"CLOSE #{meta['number']}: {cid} (orphan)")
            closed += 1

    write_status_json(integrations, today)

    tag = "[dry-run] " if DRY_RUN else ""
    print(f"\n{tag}Summary: {opened} opened, {escalated} escalated, {closed} closed.")


if __name__ == "__main__":
    main()
