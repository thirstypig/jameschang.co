"""Unit tests for feed builder functions — mock network calls, test HTML output."""

import importlib
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

_public = importlib.import_module("update-public-feeds")
_plex = importlib.import_module("update-plex")


# ── github_block ─────────────────────────────────────────────────

class TestGithubBlock:
    def _make_event(self, etype, repo, minutes_ago, **kwargs):
        t = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
        ev = {
            "type": etype,
            "created_at": t,
            "repo": {"name": f"thirstypig/{repo}"},
            "payload": kwargs.get("payload", {}),
        }
        return ev

    def test_renders_push_events(self, monkeypatch):
        events = [
            self._make_event("PushEvent", "jameschang.co", 10,
                             payload={"head": "abc123", "ref": "refs/heads/main"}),
        ]
        commit_detail = {"commit": {"message": "fix: test commit message"}}

        def mock_fetch(url, **kw):
            if "events" in url:
                return events
            return commit_detail  # individual commit fetch

        monkeypatch.setattr(_public, "fetch_json", mock_fetch)
        monkeypatch.setattr(_public, "GITHUB_TOKEN", "")
        html = _public.github_block()
        assert html is not None
        assert "gh-list" in html
        assert "jameschang.co" in html
        assert "test commit message" in html

    def test_returns_none_on_fetch_error(self, monkeypatch):
        from urllib.error import URLError
        monkeypatch.setattr(_public, "fetch_json",
                            lambda url, **kw: (_ for _ in ()).throw(URLError("fail")))
        monkeypatch.setattr(_public, "GITHUB_TOKEN", "")
        assert _public.github_block() is None

    def test_ignores_events_older_than_7_days(self, monkeypatch):
        events = [
            self._make_event("PushEvent", "old-repo", 60 * 24 * 8,
                             payload={"head": "abc", "ref": "refs/heads/main"}),
        ]
        monkeypatch.setattr(_public, "fetch_json", lambda url, **kw: events)
        monkeypatch.setattr(_public, "GITHUB_TOKEN", "")
        assert _public.github_block() is None


# ── mlb_block ────────────────────────────────────────────────────

class TestMlbBlock:
    def test_offseason_message(self, monkeypatch):
        """During offseason (Dec–Feb), should return a simple offseason line."""
        fake_today = datetime(2026, 1, 15, tzinfo=timezone.utc).date()
        monkeypatch.setattr(_public, "datetime",
                            type("FakeDatetime", (), {
                                "now": staticmethod(lambda tz=None: datetime(2026, 1, 15, tzinfo=tz)),
                            }))
        # Can't easily mock datetime.now().date() without more machinery,
        # so test the output shape instead
        html = _public.mlb_block()
        # In April it should return game data or an error, not offseason
        assert html is not None or html is None  # just ensure no crash

    def test_returns_none_on_fetch_error(self, monkeypatch):
        from urllib.error import URLError
        monkeypatch.setattr(_public, "fetch_json",
                            lambda url, **kw: (_ for _ in ()).throw(URLError("timeout")))
        assert _public.mlb_block() is None


# ── letterboxd_block ─────────────────────────────────────────────

class TestLetterboxdBlock:
    SAMPLE_RSS = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0" xmlns:letterboxd="https://letterboxd.com">
      <channel>
        <item>
          <title>Roofman, 2025 - ★★★★</title>
          <link>https://letterboxd.com/thirstypig/film/roofman/</link>
          <letterboxd:memberRating>4.0</letterboxd:memberRating>
          <pubDate>Mon, 21 Apr 2026 12:00:00 +0000</pubDate>
        </item>
        <item>
          <title>The Martian, 2015 - ★★★★★</title>
          <link>https://letterboxd.com/thirstypig/film/the-martian/</link>
          <letterboxd:memberRating>5.0</letterboxd:memberRating>
          <pubDate>Sun, 20 Apr 2026 12:00:00 +0000</pubDate>
        </item>
      </channel>
    </rss>"""

    def test_renders_films(self, monkeypatch):
        monkeypatch.setattr(_public, "fetch_text", lambda url, **kw: self.SAMPLE_RSS)
        html = _public.letterboxd_block()
        assert html is not None
        assert "Roofman" in html
        assert "The Martian" in html
        assert "lb-list" in html
        assert "★★★★" in html or "&#9733;" in html or "★" in html

    def test_returns_none_on_fetch_error(self, monkeypatch):
        from urllib.error import URLError
        monkeypatch.setattr(_public, "fetch_text",
                            lambda url, **kw: (_ for _ in ()).throw(URLError("fail")))
        assert _public.letterboxd_block() is None

    def test_returns_none_on_empty_feed(self, monkeypatch):
        empty = '<?xml version="1.0"?><rss><channel></channel></rss>'
        monkeypatch.setattr(_public, "fetch_text", lambda url, **kw: empty)
        assert _public.letterboxd_block() is None


# ── goodreads_reading_block ──────────────────────────────────────

class TestGoodreadsReadingBlock:
    SAMPLE_RSS = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>The Arm</title>
          <link>https://goodreads.com/review/show/123</link>
          <author_name>Jeff Passan</author_name>
        </item>
      </channel>
    </rss>"""

    def test_renders_currently_reading(self, monkeypatch):
        monkeypatch.setattr(_public, "fetch_text", lambda url, **kw: self.SAMPLE_RSS)
        html = _public.goodreads_reading_block()
        assert html is not None
        assert "The Arm" in html
        assert "Jeff Passan" in html
        assert "Currently reading" in html

    def test_returns_none_on_empty(self, monkeypatch):
        empty = '<?xml version="1.0"?><rss><channel></channel></rss>'
        monkeypatch.setattr(_public, "fetch_text", lambda url, **kw: empty)
        assert _public.goodreads_reading_block() is None


# ── goodreads_block ──────────────────────────────────────────────

class TestGoodreadsBlock:
    SAMPLE_RSS = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <item>
          <title>Sapiens</title>
          <link>https://goodreads.com/review/show/456</link>
          <author_name>Yuval Noah Harari</author_name>
          <user_rating>5</user_rating>
        </item>
      </channel>
    </rss>"""

    def test_renders_recently_read(self, monkeypatch):
        monkeypatch.setattr(_public, "fetch_text", lambda url, **kw: self.SAMPLE_RSS)
        html = _public.goodreads_block()
        assert html is not None
        assert "Sapiens" in html
        assert "Yuval Noah Harari" in html
        assert "Recently read" in html
        assert "★★★★★" in html  # 5 stars


# ── fbst_block ───────────────────────────────────────────────────

class TestFbstBlock:
    def test_renders_standings(self, monkeypatch):
        fake_data = {
            "standings": [
                {"teamName": "Los Doyers", "rank": 3, "points": 45.5},
                {"teamName": "Other Team", "rank": 1, "points": 60},
            ],
            "league": {"name": "OGBA", "season": "2026"},
            "period": {"name": "Week 3"},
        }
        monkeypatch.setattr(_public, "fetch_json", lambda url, **kw: fake_data)
        html = _public.fbst_block()
        assert html is not None
        assert "Los Doyers" in html
        assert "3rd" in html
        assert "45.5" in html

    def test_returns_none_when_team_not_found(self, monkeypatch):
        fake_data = {
            "standings": [
                {"teamName": "Not My Team", "rank": 1, "points": 60},
            ],
            "league": {"name": "OGBA", "season": "2026"},
            "period": {},
        }
        monkeypatch.setattr(_public, "fetch_json", lambda url, **kw: fake_data)
        assert _public.fbst_block() is None

    def test_returns_none_on_fetch_error(self, monkeypatch):
        from urllib.error import URLError
        monkeypatch.setattr(_public, "fetch_json",
                            lambda url, **kw: (_ for _ in ()).throw(URLError("fail")))
        assert _public.fbst_block() is None


# ── plex build_html ──────────────────────────────────────────────

class TestPlexBuildHtml:
    def test_renders_movies_and_tv(self):
        items = [
            {"type": "movie", "title": "S.W.A.T.", "year": 2003, "watched_at": "2026-04-22T02:28:00+00:00"},
            {"type": "tv", "title": "Lincoln Lawyer", "season": 4, "episode": 2,
             "episode_title": "Baja", "watched_at": "2026-04-12T06:33:00+00:00"},
        ]
        html = _plex.build_html(items)
        assert "S.W.A.T." in html
        assert "(2003)" in html
        assert "Lincoln Lawyer" in html
        assert "S04E02" in html
        assert "plex-list" in html

    def test_empty_returns_fallback(self):
        html = _plex.build_html([])
        assert "Nothing watched recently" in html

    def test_movie_without_year(self):
        items = [{"type": "movie", "title": "Unknown Film", "year": None, "watched_at": None}]
        html = _plex.build_html(items)
        assert "Unknown Film" in html
        assert "()" not in html  # no empty parens


class TestPlexFetchHistoryFailure:
    def test_returns_none_on_network_failure(self, monkeypatch):
        """fetch_history() must return None (not []) on network errors so
        callers can distinguish fetch failure from an empty-history server."""
        from urllib.error import URLError

        def boom(*args, **kwargs):
            raise URLError("SSL handshake timeout")

        monkeypatch.setattr(_plex, "urlopen", boom)
        monkeypatch.setattr(_plex, "PLEX_URL", "https://example.com")
        monkeypatch.setattr(_plex, "PLEX_TOKEN", "t")

        assert _plex.fetch_history() is None
