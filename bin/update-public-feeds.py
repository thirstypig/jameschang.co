#!/usr/bin/env python3
"""Fetch public-API feeds and update /now/index.html.

Each feed is wrapped independently so one outage doesn't break the others.
All endpoints are unauthenticated.

Feeds:
  - GitHub public activity for thirstypig
  - MLB Stats API for the Dodgers (team 119)
  - Letterboxd RSS for thirstypig
  - Fantastic Leagues team standings (TODO: wire once server endpoint deployed)
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
NOW_HTML = os.path.join(REPO_ROOT, "now", "index.html")
USER_AGENT = "jameschang.co/1.0 (personal dashboard; +https://jameschang.co)"

GITHUB_USER = "thirstypig"
MLB_TEAM_ID = 119  # Los Angeles Dodgers
LETTERBOXD_USER = "thirstypig"


# ------------------------ helpers ------------------------

def fetch_json(url, timeout=15):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def fetch_text(url, timeout=15):
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def relative_time(iso_str):
    if not iso_str:
        return ""
    try:
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        t = datetime.fromisoformat(iso_str)
    except ValueError:
        return ""
    delta = datetime.now(timezone.utc) - t
    minutes = int(delta.total_seconds() / 60)
    if minutes < 60:
        return f"{minutes}m ago" if minutes > 0 else "just now"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days}d ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks}w ago"
    months = days // 30
    return f"{months}mo ago"


def escape_html(s):
    if s is None:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;"))


def replace_marker(content, marker_name, html):
    pattern = rf"(<!-- {marker_name}-START -->).*?(<!-- {marker_name}-END -->)"
    replacement = f"<!-- {marker_name}-START -->\n{html}\n        <!-- {marker_name}-END -->"
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count == 0:
        print(f"WARNING: {marker_name}-START / -END markers not found in now/index.html")
        return content
    return new_content


# ------------------------ GitHub ------------------------

def github_block():
    """Recent public push/release/PR activity across the user's repos."""
    try:
        events = fetch_json(f"https://api.github.com/users/{GITHUB_USER}/events/public?per_page=100")
    except (HTTPError, URLError) as e:
        print(f"GitHub fetch failed: {e}")
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent = []
    repo_counts = Counter()
    commit_count = 0

    for ev in events:
        try:
            t = datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        if t < cutoff:
            break
        repo = ev.get("repo", {}).get("name", "")
        repo_counts[repo] += 1
        etype = ev.get("type")
        if etype == "PushEvent":
            payload = ev.get("payload") or {}
            commits = payload.get("commits") or []
            commit_count += len(commits)
            if commits:
                last = commits[-1]
                recent.append({
                    "type": "push",
                    "time": ev["created_at"],
                    "repo": repo,
                    "summary": last.get("message", "").split("\n")[0],
                    "url": f"https://github.com/{repo}/commit/{last.get('sha', '')[:7]}",
                })
        elif etype == "PullRequestEvent":
            payload = ev.get("payload") or {}
            pr = payload.get("pull_request") or {}
            recent.append({
                "type": "pr",
                "time": ev["created_at"],
                "repo": repo,
                "summary": f'PR {payload.get("action", "")}: {pr.get("title", "")}',
                "url": pr.get("html_url"),
            })
        elif etype == "ReleaseEvent":
            payload = ev.get("payload") or {}
            rel = payload.get("release") or {}
            recent.append({
                "type": "release",
                "time": ev["created_at"],
                "repo": repo,
                "summary": f'Released {rel.get("tag_name", "")}',
                "url": rel.get("html_url"),
            })

    if not recent and commit_count == 0:
        return None

    num_repos = len(repo_counts)
    parts = []
    parts.append(f'        <p class="gh-summary"><strong>Shipping:</strong> {commit_count} commits across {num_repos} repo{"s" if num_repos != 1 else ""} this week.</p>')
    parts.append('        <ul class="gh-list">')
    for item in recent[:5]:
        repo_short = item["repo"].split("/")[-1]
        summary = escape_html(item["summary"])[:80]
        rel = relative_time(item["time"])
        url = escape_html(item.get("url") or f"https://github.com/{item['repo']}")
        parts.append(
            f'          <li><a href="{url}" rel="noopener" target="_blank"><code>{escape_html(repo_short)}</code> &mdash; {summary}</a> <span class="gh-when">&middot; {rel}</span></li>'
        )
    parts.append('        </ul>')
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    parts.append(f'        <p class="feed-updated">Auto-updated {now} via <a href="https://docs.github.com/en/rest/activity/events">GitHub Events API</a>.</p>')
    return "\n".join(parts)


# ------------------------ MLB / Dodgers ------------------------

def mlb_block():
    try:
        today = datetime.now(timezone.utc).date()
        season_start = today.replace(month=3, day=1)
        season_end = today.replace(month=11, day=15)
        if today < season_start or today > season_end:
            # offseason — show simple team link, no record
            return (
                '        <p class="mlb-line">Off-season. '
                '<a href="https://www.mlb.com/dodgers" rel="noopener" target="_blank">Dodgers</a> &middot; '
                'next season: March.</p>'
            )

        standings = fetch_json("https://statsapi.mlb.com/api/v1/standings?leagueId=104&season=" + str(today.year))
        record = None
        games_back = None
        for rec in standings.get("records", []):
            for team in rec.get("teamRecords", []):
                if team.get("team", {}).get("id") == MLB_TEAM_ID:
                    record = f"{team.get('wins', 0)}-{team.get('losses', 0)}"
                    games_back = team.get("gamesBack")
                    break
            if record:
                break

        # Recent + upcoming games
        start = (today - timedelta(days=3)).isoformat()
        end = (today + timedelta(days=5)).isoformat()
        sched = fetch_json(
            f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId={MLB_TEAM_ID}"
            f"&startDate={start}&endDate={end}&hydrate=linescore"
        )
        last_game = None
        next_game = None
        for date_entry in sched.get("dates", []):
            for g in date_entry.get("games", []):
                status = g.get("status", {}).get("abstractGameState")
                game_date = g.get("gameDate")
                try:
                    gt = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
                except Exception:
                    continue
                is_home = g.get("teams", {}).get("home", {}).get("team", {}).get("id") == MLB_TEAM_ID
                them = g.get("teams", {}).get("away" if is_home else "home", {}).get("team", {}).get("abbreviation") or "TBD"
                our_score = g.get("teams", {}).get("home" if is_home else "away", {}).get("score")
                their_score = g.get("teams", {}).get("away" if is_home else "home", {}).get("score")

                if status == "Final":
                    our = our_score if our_score is not None else 0
                    their = their_score if their_score is not None else 0
                    result = "W" if our > their else "L" if our < their else "T"
                    last_game = {
                        "summary": f"{result} {our}-{their} {'vs' if is_home else '@'} {them}",
                        "time": game_date,
                    }
                elif status in ("Preview", "Live"):
                    if not next_game:
                        local = gt.astimezone(timezone(timedelta(hours=-7)))  # PT
                        next_game = {
                            "summary": f"{local.strftime('%a %-I:%M%p')} {'vs' if is_home else '@'} {them}",
                            "time": game_date,
                            "live": status == "Live",
                        }

        parts = []
        line = '<strong>Dodgers:</strong>'
        if record:
            line += f' {record}'
            if games_back and games_back != "-" and games_back != "0.0":
                line += f' ({games_back} GB)'
        parts.append(f'        <p class="mlb-line">{line}.')
        extras = []
        if last_game:
            extras.append(f'Last: {escape_html(last_game["summary"])}')
        if next_game:
            label = "Live" if next_game.get("live") else "Next"
            extras.append(f'{label}: {escape_html(next_game["summary"])}')
        if extras:
            parts[-1] += ' ' + ' &middot; '.join(extras) + '.'
        parts[-1] += '</p>'
        return "\n".join(parts)
    except (HTTPError, URLError, KeyError) as e:
        print(f"MLB fetch failed: {e}")
        return None


# ------------------------ Letterboxd ------------------------

def letterboxd_block():
    try:
        xml = fetch_text(f"https://letterboxd.com/{LETTERBOXD_USER}/rss/")
    except (HTTPError, URLError) as e:
        print(f"Letterboxd fetch failed: {e}")
        return None

    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        print(f"Letterboxd XML parse failed: {e}")
        return None

    ns = {"letterboxd": "https://letterboxd.com"}
    items = root.findall(".//item")
    if not items:
        return None  # graceful-fail

    parts = ['        <p class="lb-heading"><strong>Recently watched</strong></p>']
    parts.append('        <ul class="lb-list">')
    for item in items[:3]:
        title_el = item.find("title")
        link_el = item.find("link")
        rating_el = item.find("letterboxd:memberRating", ns)
        pub_el = item.find("pubDate")

        title = title_el.text if title_el is not None else "Untitled"
        link = link_el.text if link_el is not None else "#"
        rating_text = ""
        if rating_el is not None and rating_el.text:
            try:
                stars = float(rating_el.text)
                full = int(stars)
                half = stars - full >= 0.5
                rating_text = " " + ("\u2605" * full) + ("\u00bd" if half else "")
            except ValueError:
                pass
        when = ""
        if pub_el is not None and pub_el.text:
            try:
                t = datetime.strptime(pub_el.text, "%a, %d %b %Y %H:%M:%S %z")
                when = relative_time(t.isoformat())
            except ValueError:
                pass
        parts.append(
            f'          <li><a href="{escape_html(link)}" rel="noopener" target="_blank">{escape_html(title)}</a>'
            f'<span class="lb-rating">{escape_html(rating_text)}</span>'
            + (f' <span class="lb-when">&middot; {when}</span>' if when else '')
            + '</li>'
        )
    parts.append('        </ul>')
    now = datetime.now(timezone.utc).strftime("%B %d, %Y")
    parts.append(f'        <p class="feed-updated">Auto-updated {now} via <a href="https://letterboxd.com/{LETTERBOXD_USER}/">Letterboxd</a>.</p>')
    return "\n".join(parts)


# ------------------------ Main ------------------------

def main():
    with open(NOW_HTML, "r", encoding="utf-8") as f:
        content = f.read()

    gh = github_block()
    if gh:
        content = replace_marker(content, "GITHUB", gh)
        print(f"  GitHub: rendered")
    else:
        content = replace_marker(content, "GITHUB", '        <p class="feed-empty">No recent activity.</p>')

    mlb = mlb_block()
    if mlb:
        content = replace_marker(content, "MLB", mlb)
        print(f"  MLB: rendered")
    else:
        content = replace_marker(content, "MLB", '        <p class="feed-empty">MLB data unavailable.</p>')

    lb = letterboxd_block()
    if lb:
        content = replace_marker(content, "LETTERBOXD", lb)
        print(f"  Letterboxd: rendered")
    else:
        content = replace_marker(content, "LETTERBOXD", '        <p class="feed-empty">No films logged yet. <a href="https://letterboxd.com/thirstypig/">Letterboxd</a>.</p>')

    with open(NOW_HTML, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated {NOW_HTML}.")


if __name__ == "__main__":
    main()
