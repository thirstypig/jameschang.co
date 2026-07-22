#!/usr/bin/env python3
"""Fetch project TLDR blocks + GitHub shipping events and update /now/index.html.

Called by the GitHub Action on a daily cron (7:00 AM PT). For each project in
bin/projects-config.json:

  1. Fetches the repo's CLAUDE.md (via TLDR_FETCH_TOKEN) and extracts the
     <!-- now-tldr -->...<!-- /now-tldr --> block.
  2. Filters the global user-events feed for recent PushEvent/PullRequestEvent/
     ReleaseEvent activity in that project's shipping_repos and renders a
     "Recently shipped" line showing the single most recent item.
  3. Renders an Auto-updated timestamp line.
  4. Splices the combined block into <!-- TLDR-{slug}-START -->...<!-- TLDR-{slug}-END -->
     in now/index.html.

Fail-safe: if a project's TLDR can't be fetched, that project is skipped
entirely — existing HTML fallback is preserved. If the events fetch fails,
shipping lines are omitted but TLDR + timestamp still render.
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _shared import (
    content_changed,
    escape_html,
    fetch_json,
    format_update_time,
    read_now_html,
    record_heartbeat,
    relative_time_html,
    replace_marker,
    safe_url,
    write_now_html,
    REPO_ROOT,
    USER_AGENT,
)

CONFIG_PATH = os.path.join(REPO_ROOT, "bin", "projects-config.json")
TLDR_PATTERN = re.compile(r"<!-- now-tldr -->\s*(.*?)\s*<!-- /now-tldr -->", re.DOTALL)
EVENT_WINDOW = timedelta(days=14)  # how far back to look for shipping events
EVENTS_PER_PROJECT = 1
MAX_COMMIT_ENRICHMENTS = 15  # hard cap on per-run GitHub /commits/{sha} fetches
ACTIVE_THRESHOLD_DAYS = 7  # most-recent shipping event within this window → active
SELF_SLUG = "jameschang-co"  # always pinned to the bottom of its section

_BADGE_SAFE_RE = re.compile(r"[^a-z0-9-]")

# Tabler outline icon SVG strings (MIT) — inlined to avoid CDN dependency.
_ICON_ATTRS = ('class="nb-proj-badge-icon" width="12" height="12" viewBox="0 0 24 24" '
               'fill="none" stroke="currentColor" stroke-width="2" '
               'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"')
_SVG_CODE  = (f'<svg {_ICON_ATTRS}>'
              '<path d="M7 8l-4 4 4 4"/><path d="M17 8l4 4-4 4"/><path d="M14 4l-4 16"/></svg>')
_SVG_GLOBE = (f'<svg {_ICON_ATTRS}>'
              '<circle cx="12" cy="12" r="9"/>'
              '<path d="M3.6 9h16.8M3.6 15h16.8M11.5 3a17 17 0 0 0 0 18M12.5 3a17 17 0 0 1 0 18"/></svg>')
_SVG_LOCK  = (f'<svg {_ICON_ATTRS}>'
              '<path d="M5 13a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-6z"/>'
              '<circle cx="12" cy="16" r="1"/><path d="M8 13V7a4 4 0 0 1 8 0v6"/></svg>')
_SVG_CLOCK = (f'<svg {_ICON_ATTRS}>'
              '<circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 15"/></svg>')


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["projects"]


def fetch_file(repo, path, token):
    """Fetch a raw file from GitHub. Returns string or None on failure."""
    url = f"https://raw.githubusercontent.com/{repo}/HEAD/{path}"
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError) as e:
        print(f"  fetch failed for {repo}/{path}: {e}", file=sys.stderr)
        return None


def extract_tldr(markdown):
    """Return TLDR block content from markdown, or None if absent.

    The TLDR block is embedded directly into the rendered HTML, so any
    markdown emphasis (**bold**) and inline code (`code`) tokens are
    converted to <strong> and <code> tags here. HTML entities in the
    raw text are escaped first so that authoring something like
    `<VenueChips>` in CLAUDE.md doesn't leak into the page as a real tag.
    """
    if not markdown:
        return None
    m = TLDR_PATTERN.search(markdown)
    if not m:
        return None
    raw = m.group(1).strip()
    return _render_markdown_inline(raw)


_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_MD_CODE_RE = re.compile(r"`([^`]+)`")


def _render_markdown_inline(text):
    """Convert basic inline markdown (**bold**, `code`) to HTML.

    Escapes HTML entities first so author-written angle brackets in
    CLAUDE.md TLDRs (e.g., a literal <VenueChips> reference) render
    as text rather than breaking the page. Order matters: escape, then
    apply the bold/code regexes against the escaped text.
    """
    out = escape_html(text)
    out = _MD_BOLD_RE.sub(r"<strong>\1</strong>", out)
    out = _MD_CODE_RE.sub(r"<code>\1</code>", out)
    return out


def shipping_repos_for(projects):
    """Union of every repo whose events attribute to some project, in config
    order, de-duplicated. Falls back to a project's `repo` if it declares no
    `shipping_repos` — mirrors the same fallback in events_for_project()."""
    seen = []
    for p in projects:
        for r in (p.get("shipping_repos") or [p["repo"]]):
            if r not in seen:
                seen.append(r)
    return seen


# Per-run tally of repo-events fetches: a 200 (even empty) counts as _ok, an
# HTTP/URL error counts as _err. main() uses these to tell an isolated single-repo
# failure (some ok, some err — expected, stay the course) apart from a SYSTEMIC
# failure (zero ok, all err — usually a dead TLDR_FETCH_TOKEN, which 401s every
# request). Only the systemic case skips the heartbeat so the monitor can flag it.
_events_ok = 0
_events_err = 0


def fetch_repo_events(repo, token):
    """Fetch recent events for ONE repo via /repos/{repo}/events.

    Unlike the public /users/{user}/events feed (which only returns PUBLIC
    events to a PAT), the per-repo endpoint returns events for PRIVATE repos
    too, as long as the token can read the repo. This is why private projects
    like Aleph (alephco.io-app) are now classified correctly instead of being
    permanently stuck as back-burner. Returns a list of raw event dicts (same
    shape the user-events feed produced) or [] on failure."""
    url = f"https://api.github.com/repos/{repo}/events?per_page=100"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    global _events_ok, _events_err
    try:
        data = fetch_json(url, headers=headers, timeout=15) or []
        _events_ok += 1  # a 200 (even with an empty list) is a real success
        return data
    except (HTTPError, URLError) as e:
        _events_err += 1
        print(f"  events fetch failed for {repo}: {e}", file=sys.stderr)
        return []


def fetch_github_events(token, repos):
    """Aggregate recent events across all shipping repos into one flat list,
    identical in shape to what parse_events() expects.

    Per-repo fetch (vs. the old single /users/thirstypig/events call) means
    private-repo activity is included, and the prior global 100-event cap
    becomes a per-repo cap — so an active project's events can no longer be
    pushed off the list by churn in a different repo. A single repo failing
    is isolated (skipped, returns []), never fatal to the whole run."""
    all_events = []
    for repo in repos:
        all_events.extend(fetch_repo_events(repo, token))
    return all_events


def _parse_iso(ts):
    """Parse an ISO-8601 timestamp into a UTC datetime, tolerating both Z
    and +00:00 suffixes. Returns None on failure."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def parse_events(events, token):
    """Group recent events by repo. Returns {repo_name: [event_dict, ...]}.

    Each event dict: {time, summary, url, _repo, _head_sha?}. Events within a
    repo are ordered newest-first by their `time` field (datetime-parsed, not
    lex-compared, so mixed Z / +00:00 suffixes sort correctly). PushEvents
    include a _head_sha for commit-message enrichment.
    """
    if not events:
        return {}
    cutoff = datetime.now(timezone.utc) - EVENT_WINDOW
    by_repo = defaultdict(list)
    for ev in events:
        t = _parse_iso(ev.get("created_at"))
        if t is None or t < cutoff:
            continue
        repo = ev.get("repo", {}).get("name", "")
        if not repo:
            continue
        etype = ev.get("type")
        payload = ev.get("payload") or {}
        # _repo is stamped on construction so enrichment can attribute the
        # entry back to its repo by direct field lookup — avoids the prior
        # O(N²) `if entry in lst` identity-equality scan that broke silently
        # if any future refactor copied the entry dict.
        entry = {"time": ev["created_at"], "url": None, "summary": None, "_repo": repo}
        if etype == "PushEvent":
            sha = payload.get("head")
            ref = payload.get("ref", "").replace("refs/heads/", "")
            entry["summary"] = f"Pushed to {ref}" if ref else "Pushed"
            entry["url"] = f"https://github.com/{repo}/commit/{sha}" if sha else f"https://github.com/{repo}"
            entry["_head_sha"] = sha
        elif etype == "PullRequestEvent":
            pr = payload.get("pull_request") or {}
            html_url = pr.get("html_url")
            title = pr.get("title")
            # Public-events endpoint strips payload.pull_request for private-
            # repo events, leaving no URL or title. The merge commit still
            # arrives as a PushEvent with full data, so dropping these loses
            # nothing and avoids rendering "(untitled)" dead links.
            if not html_url or not title:
                continue
            action = payload.get("action", "")
            entry["summary"] = f"PR {action}: {title}"
            entry["url"] = html_url
        elif etype == "ReleaseEvent":
            rel = payload.get("release") or {}
            entry["summary"] = f"Released {rel.get('tag_name', '')}"
            entry["url"] = rel.get("html_url")
        else:
            continue
        by_repo[repo].append(entry)
    # Enrich the most-recent N push events per repo with the first line of
    # the commit message. Time-sort first so the "first N" we enrich match
    # the "first N" that events_for_project will surface.
    enriched = 0
    for events_list in by_repo.values():
        events_list.sort(key=lambda e: _parse_iso(e["time"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        for entry in events_list[:EVENTS_PER_PROJECT]:
            sha = entry.pop("_head_sha", None)
            if not sha or not entry["summary"].startswith("Pushed"):
                continue
            if enriched >= MAX_COMMIT_ENRICHMENTS:
                break
            try:
                headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                commit = fetch_json(f"https://api.github.com/repos/{entry['_repo']}/commits/{sha}", headers=headers, timeout=15)
                first_line = ((commit.get("commit") or {}).get("message") or "").split("\n")[0].strip()
                if first_line:
                    entry["summary"] = first_line
                enriched += 1
            except (HTTPError, URLError):
                pass
    return by_repo


def events_for_project(project, events_by_repo):
    """Return up to EVENTS_PER_PROJECT most recent events attributed to this project."""
    shipping_repos = project.get("shipping_repos") or [project["repo"]]
    merged = []
    for r in shipping_repos:
        merged.extend(events_by_repo.get(r, []))
    # Parse to datetime for correctness — lex-sort works only when every
    # timestamp shares the same tz suffix, which is fragile.
    merged.sort(key=lambda e: _parse_iso(e["time"]) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return merged[:EVENTS_PER_PROJECT]


def render_shipping_list(events):
    """Render the notebook-design shipped line, or empty string if no events.

    Emits <p class="nb-card-shipped"> with an accent "↑ shipped:" label, the
    event link, and a bare <time data-rel> element (data-rel drives the live-
    relative upgrade in script.js — no class needed). Matches the static
    placeholder format in now/index.html.
    """
    if not events:
        return ""
    items = []
    for ev in events:
        # Truncate raw text first, then escape — slicing escaped HTML by char
        # count can split mid-entity (`&amp;` → `&am`).
        summary = escape_html((ev["summary"] or "")[:90])
        url = escape_html(safe_url(ev["url"]))
        when = relative_time_html(ev["time"])
        items.append(f'<a href="{url}" rel="noopener" target="_blank">{summary}</a> &middot; {when}')
    return (
        '          <p class="nb-card-shipped"><span class="accent">&uarr; shipped:</span> '
        + ' &middot; '.join(items)
        + '</p>\n'
    )


def render_badge(status, maturity=None):
    """Return badge span: inline SVG icon + 'Status · Maturity' label.

    Icon selection: shipping → code, live+public → globe, live+private → lock,
    blocked → clock. CSS modifier (nb-proj-badge--{status}) drives border/icon
    color via notebook.css color tokens. Returns '' if status is falsy.
    """
    if not status:
        return ""
    safe = _BADGE_SAFE_RE.sub("", status.lower())
    if not safe:
        return ""
    safe_maturity = _BADGE_SAFE_RE.sub("", (maturity or "").lower())
    if safe == "live" and safe_maturity == "private":
        icon = _SVG_LOCK
    elif safe == "live":
        icon = _SVG_GLOBE
    elif safe == "blocked":
        icon = _SVG_CLOCK
    else:
        icon = _SVG_CODE
    label = escape_html(status.capitalize())
    if safe_maturity:
        label += f" &middot; {escape_html(maturity.capitalize())}"
    return f'<span class="nb-proj-badge nb-proj-badge--{safe}">{icon}{label}</span>'


def render_activity_box(events):
    """Render the .nb-proj-activity inset for the most recent shipped item.

    Shows the activity link + live-relative timestamp when events exist;
    falls back to a muted "no recent activity" label when empty.
    """
    if not events:
        return (
            '          <div class="nb-proj-activity nb-proj-activity--empty">\n'
            '            <span class="nb-proj-activity-label">no recent activity</span>\n'
            '          </div>'
        )
    ev = events[0]
    summary = escape_html((ev["summary"] or "")[:90])
    url = escape_html(safe_url(ev["url"]))
    when = relative_time_html(ev["time"])
    return (
        '          <div class="nb-proj-activity">\n'
        '            <span class="nb-proj-activity-label">&#8593; shipped</span>\n'
        '            <div class="nb-proj-activity-body">\n'
        f'              <a href="{url}" rel="noopener" target="_blank">{summary}</a>\n'
        f'              &middot; {when}\n'
        '            </div>\n'
        '          </div>'
    )


def most_recent_event_time(project, events_by_repo):
    """Return the datetime of the most recent shipping event for a project,
    or None if the project has no events in the current window."""
    shipping_repos = project.get("shipping_repos") or [project["repo"]]
    latest = None
    for r in shipping_repos:
        for ev in events_by_repo.get(r, []):
            t = _parse_iso(ev["time"])
            if t and (latest is None or t > latest):
                latest = t
    return latest


def classify_projects(events_by_slug, threshold_days=ACTIVE_THRESHOLD_DAYS):
    """Split projects into (active_slugs, backburner_slugs) by recency.

    `events_by_slug` is a mapping {slug: most_recent_event_datetime_or_None}.
    A project is "active" if its most recent event is strictly within
    `threshold_days` of now. A project with no events is back-burner.

    Edge case pinned: an event exactly `threshold_days` old (delta ==
    threshold) is back-burner — the comparison is strict less-than.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_days)
    active, backburner = [], []
    for slug, latest in events_by_slug.items():
        if latest is not None and latest > cutoff:
            active.append(slug)
        else:
            backburner.append(slug)
    return active, backburner


def pin_self_last(slug, *lists):
    """Move `slug` to the end of whichever list it appears in.

    jameschang.co gets cron commits constantly, so without this it floats
    to the top of the active section on every run.
    """
    for lst in lists:
        if slug in lst:
            lst.remove(slug)
            lst.append(slug)


def render_card(project, shipping_events, now_str):
    """Render the full <article class="nb-proj-card"> markup for a project.

    Both active and back-burner cards use the same format; visual separation
    comes from the grid container (.nb-grid-1 vs .nb-grid-3), not card size.
    desc and next_up come from projects-config.json; the shipped item comes
    from live GitHub events. TLDR markers are preserved inside the card so
    future tooling can identify per-project boundaries.
    """
    name = escape_html(project.get("name", project["slug"]))
    url = escape_html(safe_url(project.get("url"), fallback="#"))
    url_label = escape_html(project.get("url_label", "").strip())
    desc = escape_html(project.get("desc", ""))
    next_up = escape_html(project.get("next_up", ""))
    roadmap_items = project.get("roadmap_items") or []
    slug = project["slug"]

    badge_html = render_badge(project.get("status_badge", ""), project.get("maturity"))
    activity_html = render_activity_box(shipping_events)

    lines = [
        '        <article class="nb-proj-card">',
        '          <div class="nb-proj-head">',
        '            <div class="nb-proj-title">',
        f'              <h3 class="nb-proj-name"><a href="{url}">{name}</a></h3>',
    ]
    if url_label:
        lines.append(f'              <span class="nb-proj-domain">{url_label} &#8599;</span>')
    lines.append('            </div>')
    if badge_html:
        lines.append(f'            {badge_html}')
    lines += [
        '          </div>',
        f'          <!-- TLDR-{slug}-START -->',
    ]
    # Activity-first: shipped item before description so returning visitors
    # see the delta immediately without reading the full project summary.
    lines.append(activity_html)
    if desc:
        lines.append(f'          <p class="nb-proj-desc">{desc}</p>')
    if next_up:
        lines += [
            '          <p class="nb-proj-next">',
            '            <span class="nb-proj-next-label">next up</span>',
            f'            {next_up}',
            '          </p>',
        ]
    if roadmap_items:
        lines += [
            '          <div class="nb-proj-roadmap">',
            '            <p class="nb-proj-roadmap-label">what&#39;s coming next</p>',
            '            <ul>',
        ]
        for item in roadmap_items:
            safe_item = escape_html(item)
            lines.append(f'              <li>{safe_item}</li>')
        lines += [
            '            </ul>',
            '          </div>',
        ]
    lines += [
        f'          <p class="feed-updated">Auto-updated {now_str} via GitHub events.</p>',
        f'          <!-- TLDR-{slug}-END -->',
        '        </article>',
    ]
    return "\n".join(lines)


def render_eyebrow(label, count):
    noun = "project" if count == 1 else "projects"
    return f"{label} &middot; {count} {noun}"


def render_block(tldr_html, shipping_html, now_str):
    """Assemble the full replacement HTML for a project's TLDR marker block.

    Sits inside an <article class="nb-card"> — emits .nb-card-body for the
    TLDR copy and .nb-card-shipped (via render_shipping_list) for the shipping
    line, matching the rest of the notebook design system. The trailing
    .feed-updated line keeps the generic "auto-updated" footer convention
    used by every cron-managed feed.
    """
    return (
        f"\n"
        f'          <p class="nb-card-body">{tldr_html}</p>\n'
        f'          <div class="nb-card-footer">\n'
        f"{shipping_html}"
        f'          <p class="feed-updated">Auto-updated {now_str} via CLAUDE.md + GitHub events.</p>\n'
        f'          </div>\n'
        f"        "
    )


def main():
    projects = load_config()
    token = os.environ.get("TLDR_FETCH_TOKEN", "").strip() or None
    if not token:
        print("WARNING: TLDR_FETCH_TOKEN not set — GitHub Events for private repos may be missing.")

    events_raw = fetch_github_events(token, shipping_repos_for(projects))

    if _events_ok == 0 and _events_err > 0:
        # EVERY repo events fetch errored — systemic, not isolated. The usual cause
        # is a revoked/expired TLDR_FETCH_TOKEN (a bad token 401s every request,
        # public or private). Leaving /now untouched keeps the last-good active/
        # back-burner classification and skips the heartbeat so the staleness
        # monitor flags it after 48h — instead of silently reclassifying every
        # project as back-burner behind a fresh heartbeat. An isolated single-repo
        # failure (some ok, some err) is NOT this case and proceeds normally.
        print(
            "All GitHub event fetches failed — leaving /now unchanged and skipping "
            "the heartbeat so the staleness monitor can flag it. Check TLDR_FETCH_TOKEN.",
            file=sys.stderr,
        )
        return

    events_by_repo = parse_events(events_raw, token)

    old_content = read_now_html()
    now_str = format_update_time()

    # desc + next_up come from projects-config.json (editorial); shipped item
    # comes from live GitHub events. No CLAUDE.md fetch needed for /now cards.
    rendered = {}  # slug → (project, shipping_events, latest_dt)
    for project in projects:
        slug = project["slug"]
        shipping_events = events_for_project(project, events_by_repo)
        latest_dt = most_recent_event_time(project, events_by_repo)
        rendered[slug] = (project, shipping_events, latest_dt)
        print(f"  {slug}: {len(shipping_events)} event{'s' if len(shipping_events) != 1 else ''}")

    events_by_slug = {slug: data[2] for slug, data in rendered.items()}
    active_slugs, backburner_slugs = classify_projects(events_by_slug)

    def _active_key(s):
        dt = events_by_slug.get(s)
        return dt or datetime.min.replace(tzinfo=timezone.utc)

    def _backburner_key(s):
        dt = events_by_slug.get(s)
        if dt is not None:
            return (0, -dt.timestamp(), s)
        return (1, 0, s)

    active_slugs.sort(key=_active_key, reverse=True)
    backburner_slugs.sort(key=_backburner_key)
    pin_self_last(SELF_SLUG, active_slugs, backburner_slugs)

    active_cards = "\n".join(
        render_card(rendered[s][0], rendered[s][1], now_str)
        for s in active_slugs
    )
    backburner_cards = "\n".join(
        render_card(rendered[s][0], rendered[s][1], now_str)
        for s in backburner_slugs
    )

    new_content = old_content
    new_content, ok1 = replace_marker(new_content, "ACTIVE-PROJECTS", active_cards)
    new_content, ok2 = replace_marker(new_content, "BACKBURNER-PROJECTS", backburner_cards)
    new_content, _ = replace_marker(
        new_content, "ACTIVE-EYEBROW", render_eyebrow("where the time is going", len(active_slugs))
    )
    new_content, _ = replace_marker(
        new_content, "BACKBURNER-EYEBROW", render_eyebrow("shipping but not daily", len(backburner_slugs))
    )

    if not (ok1 and ok2):
        record_heartbeat("projects", error="ACTIVE-PROJECTS or BACKBURNER-PROJECTS markers missing")
        print("ERROR: ACTIVE-PROJECTS / BACKBURNER-PROJECTS markers missing in now/index.html.")
        return

    if not content_changed(old_content, new_content):
        record_heartbeat("projects")
        print("No meaningful changes.")
        return

    write_now_html(new_content)
    record_heartbeat("projects")
    print(
        f"Updated now/index.html. Active: {len(active_slugs)} "
        f"({', '.join(active_slugs) or 'none'}); back-burner: {len(backburner_slugs)} "
        f"({', '.join(backburner_slugs) or 'none'})."
    )


if __name__ == "__main__":
    main()
