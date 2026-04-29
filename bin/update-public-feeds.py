#!/usr/bin/env python3
"""Fetch public-API feeds and update /now/index.html.

Each feed is wrapped independently so one outage doesn't break the others.
All endpoints are unauthenticated.

Feeds:
  - MLB Stats API for the Dodgers (team 119)
  - Letterboxd RSS for thirstypig
  - Goodreads RSS (currently-reading + read shelves)
  - Fantastic Leagues team standings
"""

import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

from _shared import (
    escape_html,
    relative_time,
    replace_marker,
    record_heartbeat,
    fetch_json,
    fetch_text,
    content_changed,
    format_update_time,
    read_now_html,
    write_now_html,
)

MLB_TEAM_ID = 119  # Los Angeles Dodgers
LETTERBOXD_USER = "thirstypig"
GOODREADS_USER_ID = "33966778"
FBST_API_BASE = "https://app.thefantasticleagues.com/api/public"
FBST_LEAGUE_SLUG = "ogba-2026"
FBST_MY_TEAM = "Los Doyers"
PT = ZoneInfo("America/Los_Angeles")


# ------------------------ MLB / Dodgers ------------------------

def mlb_block():
    try:
        today = datetime.now(timezone.utc).date()
        season_start = today.replace(month=3, day=1)
        season_end = today.replace(month=11, day=15)
        if today < season_start or today > season_end:
            # offseason — show simple team link, no record
            return (
                '        <p>Off-season. '
                '<a href="https://www.mlb.com/dodgers" rel="noopener" target="_blank">Dodgers</a> &middot; '
                'next season: March.</p>'
            )

        # Single API call: hydrate=team,linescore gives us record + scores
        start = (today - timedelta(days=3)).isoformat()
        end = (today + timedelta(days=5)).isoformat()
        sched = fetch_json(
            f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&teamId={MLB_TEAM_ID}"
            f"&startDate={start}&endDate={end}&hydrate=linescore,team"
        )
        record = None
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
                our_side = g.get("teams", {}).get("home" if is_home else "away", {})
                opp_side = g.get("teams", {}).get("away" if is_home else "home", {})
                opp_team = opp_side.get("team", {}) or {}
                them = opp_team.get("abbreviation") or opp_team.get("teamName") or "TBD"
                our_score = our_side.get("score")
                their_score = opp_side.get("score")

                if not record:
                    lr = our_side.get("leagueRecord", {})
                    if lr.get("wins") is not None:
                        record = f"{lr['wins']}-{lr['losses']}"

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
                        local = gt.astimezone(PT)
                        next_game = {
                            "summary": f"{local.strftime('%a %-I:%M%p')} {'vs' if is_home else '@'} {them}",
                            "time": game_date,
                            "live": status == "Live",
                        }

        parts = []
        line = '<strong>Dodgers:</strong>'
        if record:
            line += f' {record}'
        parts.append(f'        <p>{line}.')
        extras = []
        if last_game:
            extras.append(f'Last: {escape_html(last_game["summary"])}')
        if next_game:
            label = "Live" if next_game.get("live") else "Next"
            extras.append(f'{label}: {escape_html(next_game["summary"])}')
        if extras:
            parts[-1] += ' ' + ' &middot; '.join(extras) + '.'
        parts[-1] += '</p>'
        now = format_update_time()
        parts.append(f'        <p class="feed-updated">Auto-updated {now} via <a href="https://www.mlb.com/dodgers">MLB Stats API</a>.</p>')
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

    parts = ['        <ul>']
    for item in items[:3]:
        title_el = item.find("title")
        link_el = item.find("link")
        pub_el = item.find("pubDate")

        title = title_el.text if title_el is not None else "Untitled"
        link = link_el.text if link_el is not None else "#"
        when = ""
        if pub_el is not None and pub_el.text:
            try:
                t = datetime.strptime(pub_el.text, "%a, %d %b %Y %H:%M:%S %z")
                when = relative_time(t.isoformat())
            except ValueError:
                pass
        parts.append(
            f'          <li><a href="{escape_html(link)}" rel="noopener" target="_blank">{escape_html(title)}</a>'
            + (f' <span class="when">&middot; {when}</span>' if when else '')
            + '</li>'
        )
    parts.append('        </ul>')
    now = format_update_time()
    parts.append(f'        <p class="feed-updated">Auto-updated {now} via <a href="https://letterboxd.com/{LETTERBOXD_USER}/">Letterboxd</a>.</p>')
    return "\n".join(parts)


# ------------------------ Goodreads ------------------------

def goodreads_reading_block():
    """Currently reading books from Goodreads RSS."""
    try:
        xml = fetch_text(f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}?shelf=currently-reading")
    except (HTTPError, URLError) as e:
        print(f"Goodreads currently-reading fetch failed: {e}")
        return None

    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        print(f"Goodreads XML parse failed: {e}")
        return None

    items = root.findall(".//item")
    if not items:
        return None

    parts = ['        <p><strong>Currently reading</strong></p>']
    parts.append('        <ul>')
    for item in items[:3]:
        title_el = item.find("title")
        link_el = item.find("link")
        author_el = item.find("author_name")

        title = title_el.text.strip() if title_el is not None and title_el.text else "Untitled"
        link = link_el.text.strip() if link_el is not None and link_el.text else "#"
        author = author_el.text.strip() if author_el is not None and author_el.text else ""

        line = f'          <li><a href="{escape_html(link)}" rel="noopener" target="_blank"><em>{escape_html(title)}</em></a>'
        if author:
            line += f' <span class="when">&mdash; {escape_html(author)}</span>'
        line += '</li>'
        parts.append(line)

    parts.append('        </ul>')
    return "\n".join(parts)


def goodreads_block():
    """Recently read books from Goodreads RSS."""
    try:
        xml = fetch_text(f"https://www.goodreads.com/review/list_rss/{GOODREADS_USER_ID}?shelf=read")
    except (HTTPError, URLError) as e:
        print(f"Goodreads fetch failed: {e}")
        return None

    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        print(f"Goodreads XML parse failed: {e}")
        return None

    items = root.findall(".//item")
    if not items:
        return None

    parts = ['        <p><strong>Recently read</strong></p>']
    parts.append('        <ul>')
    for item in items[:5]:
        title_el = item.find("title")
        link_el = item.find("link")
        author_el = item.find("author_name")

        title = title_el.text.strip() if title_el is not None and title_el.text else "Untitled"
        link = link_el.text.strip() if link_el is not None and link_el.text else "#"
        author = author_el.text.strip() if author_el is not None and author_el.text else ""

        # Rating from user_rating element
        rating_el = item.find("user_rating")
        rating_text = ""
        if rating_el is not None and rating_el.text:
            try:
                stars = int(rating_el.text)
                if stars > 0:
                    rating_text = " " + ("\u2605" * stars)
            except ValueError:
                pass

        line = f'          <li><a href="{escape_html(link)}" rel="noopener" target="_blank"><em>{escape_html(title)}</em></a>'
        if author:
            line += f' <span class="when">&mdash; {escape_html(author)}</span>'
        if rating_text:
            line += f'<span class="when accent">{rating_text}</span>'
        line += '</li>'
        parts.append(line)

    parts.append('        </ul>')
    now = format_update_time()
    parts.append(f'        <p class="feed-updated">Auto-updated {now} via <a href="https://www.goodreads.com/user/show/{GOODREADS_USER_ID}">Goodreads</a>.</p>')
    return "\n".join(parts)


# ------------------------ FBST (my fantasy team) ------------------------

def ordinal(n):
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', 4 -> '4th', ..."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n % 10]}"


def fbst_block():
    """Return the FBST fantasy-team block for my team in the public league."""
    try:
        data = fetch_json(f"{FBST_API_BASE}/leagues/{FBST_LEAGUE_SLUG}/standings")
    except (HTTPError, URLError) as e:
        print(f"FBST fetch failed: {e}")
        return None

    standings = data.get("standings") or []
    if not standings:
        return None

    total = len(standings)
    league = data.get("league", {})
    league_name = league.get("name", "")
    season = league.get("season", "")
    period_name = (data.get("period") or {}).get("name", "")

    me = next((t for t in standings if t.get("teamName") == FBST_MY_TEAM), None)
    if not me:
        print(f"FBST: team '{FBST_MY_TEAM}' not found in standings")
        return None

    rank_str = ordinal(me["rank"])
    points = me["points"]
    # Format points: drop trailing .0 for whole numbers
    points_str = f"{points:g}" if isinstance(points, (int, float)) else str(points)

    now = format_update_time()
    html = (
        f'        <p><strong>Los Doyers:</strong> {rank_str} of {total}'
        f' &middot; {points_str} pts &middot; '
        f'<a href="https://thefantasticleagues.com" rel="noopener" target="_blank">'
        f'{escape_html(league_name)} {season}</a></p>\n'
        f'        <p class="feed-updated">Auto-updated {now} via '
        f'<a href="https://thefantasticleagues.com">The Fantastic Leagues</a>.</p>'
    )
    return html


# ------------------------ Main ------------------------

def main():
    old_content = read_now_html()
    content = old_content

    # Only fetch feeds whose markers are present in the HTML (todo 058).
    # GITHUB events moved into update-projects.py for per-project attribution.
    # LETTERBOXD removed 2026-04-28 per user — section dropped from /now.
    # To revive Letterboxd: (1) restore the <!-- LETTERBOXD-START/END --> marker
    # pair in now/index.html /07 section, (2) re-add the tuple here:
    #     ("LETTERBOXD", letterboxd_block, '<p class="feed-empty">No films logged yet. <a href="https://letterboxd.com/thirstypig/">Letterboxd</a>.</p>'),
    # (3) restore the Letterboxd disclosure paragraph in privacy/index.html
    # (see commit cede613 for the prior wording), and (4) update
    # tests/test_site_e2e.py: add LETTERBOXD back to EXPECTED_MARKERS and add
    # "Letterboxd" to the privacy-policy required list.
    feeds = [
        ("MLB",        mlb_block,         '        <p class="feed-empty">MLB data unavailable.</p>'),
        ("GOODREADS-READING", goodreads_reading_block, '        <p><strong>Currently reading</strong></p>\n        <p class="feed-empty">Nothing on the shelf right now.</p>'),
        ("GOODREADS",  goodreads_block,   '        <p class="feed-empty">No books logged yet. <a href="https://www.goodreads.com/user/show/33966778">Goodreads</a>.</p>'),
        ("FBST",       fbst_block,        '        <p class="feed-empty">FBST standings unavailable.</p>'),
    ]
    for marker, builder, fallback in feeds:
        if f"<!-- {marker}-START -->" not in content:
            continue
        result = builder()
        html = result if result else fallback
        content, _ = replace_marker(content, marker, html)
        record_heartbeat(marker.lower(), error=None if result else f"{marker} returned no data")
        print(f"  {marker}: {'rendered' if result else 'fallback'}")

    if not content_changed(old_content, content):
        print("No meaningful changes.")
        return

    write_now_html(content)
    print("Updated now/index.html.")


if __name__ == "__main__":
    main()
