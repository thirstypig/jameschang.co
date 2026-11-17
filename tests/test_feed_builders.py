"""Unit tests for feed builder functions — mock network calls, test HTML output."""

import importlib
import os
import sys
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

_public = importlib.import_module("update-public-feeds")
_plex = importlib.import_module("update-plex")


# ── mlb_block ────────────────────────────────────────────────────

def _freeze_mlb_today(monkeypatch, iso):
    """Pin mlb_block()'s clock. It short-circuits to an off-season line outside
    Mar 1–Nov 15 BEFORE fetching, so an unpinned test silently changes meaning
    with the calendar (went red 2026-11-16 UTC; would have stayed red to March)."""
    frozen = datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen if tz else frozen.replace(tzinfo=None)

    monkeypatch.setattr(_public, "datetime", _FrozenDatetime)


class TestMlbBlock:
    def test_returns_none_on_fetch_error(self, monkeypatch):
        from urllib.error import URLError
        _freeze_mlb_today(monkeypatch, "2026-06-26T12:00:00")
        monkeypatch.setattr(_public, "fetch_json",
                            lambda url, **kw: (_ for _ in ()).throw(URLError("timeout")))
        assert _public.mlb_block() is None

    def test_off_season_skips_fetch(self, monkeypatch):
        _freeze_mlb_today(monkeypatch, "2026-12-01T12:00:00")
        def _boom(*a, **kw):
            raise AssertionError("off-season must not hit the MLB API")
        monkeypatch.setattr(_public, "fetch_json", _boom)
        assert "Off-season" in _public.mlb_block()


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
        assert "<ul>" in html
        assert "<li>" in html
        # Letterboxd RSS bakes the rating into the title text, so stars survive
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
        # Notebook-design markup: bare <ul>, no feed-named classes
        assert "plex-list" not in html
        assert "plex-heading" not in html
        assert "plex-when" not in html
        assert "<ul" in html
        assert 'class="when"' in html

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


class TestFeedBuildersIdempotency:
    """Feed builders must be deterministic: same input → same output.

    Guards against the trap where cron runs might accidentally corrupt
    or change feed rendering, making content appear/disappear.
    """

    def test_plex_build_html_is_deterministic(self):
        """Same items → identical HTML."""
        items = [
            {
                "type": "tv",
                "title": "Breaking Bad",
                "season": 5,
                "episode": 14,
                "episode_title": "Ozymandias",
                "watched_at": "2026-06-25T12:00:00+00:00",
            },
            {
                "type": "movie",
                "title": "Inception",
                "year": 2010,
                "watched_at": "2026-06-24T18:30:00+00:00",
            },
        ]
        html1 = _plex.build_html(items)
        html2 = _plex.build_html(items)
        assert html1 == html2

    def test_plex_empty_is_deterministic(self):
        """Empty items → consistent fallback."""
        html1 = _plex.build_html([])
        html2 = _plex.build_html([])
        assert html1 == html2

    def test_mlb_block_is_deterministic_with_data(self, monkeypatch):
        """MLB block with mock data → identical output."""
        mock_response = {
            "dates": [
                {
                    "games": [
                        {
                            "status": {"abstractGameState": "Final"},
                            "gameDate": "2026-06-25T22:10:00Z",
                            "teams": {
                                "home": {
                                    "team": {"id": 119, "abbreviation": "LAD"},
                                    "score": 4,
                                    "leagueRecord": {"wins": 45, "losses": 35},
                                },
                                "away": {
                                    "team": {"id": 108, "abbreviation": "LAA"},
                                    "score": 2,
                                },
                            },
                        }
                    ]
                }
            ]
        }
        _freeze_mlb_today(monkeypatch, "2026-06-26T12:00:00")
        monkeypatch.setattr(_public, "fetch_json", lambda *a, **kw: mock_response)
        html1 = _public.mlb_block()
        html2 = _public.mlb_block()
        assert "Off-season" not in html1  # else this compares two constants
        assert html1 == html2


    def test_fbst_block_is_deterministic(self, monkeypatch):
        """FBST standings block with same data → identical output."""
        mock_response = {
            "league": {"name": "OGBA", "season": "2026"},
            "period": {"name": "Regular Season"},
            "standings": [
                {"teamName": "Los Doyers", "rank": 1, "points": 850.5},
                {"teamName": "Other Team", "rank": 2, "points": 820.0},
            ],
        }
        monkeypatch.setattr(_public, "fetch_json", lambda *a, **kw: mock_response)
        html1 = _public.fbst_block()
        html2 = _public.fbst_block()
        assert html1 == html2
