"""Unit tests for bin/update-trakt.py — Trakt TV feed rendering."""

import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

_trakt = importlib.import_module("update-trakt")
build_html = _trakt.build_html
fetch_recent_shows = _trakt.fetch_recent_shows


# ── build_html ───────────────────────────────────────────────────

class TestBuildHtml:
    def test_single_show(self):
        shows = [{
            "show": "Pluribus",
            "season": 1,
            "episode": 9,
            "episode_title": "La Chica o El Mundo",
            "watched_at": "2026-04-20T18:41:00.000Z",
            "url": "https://trakt.tv/shows/pluribus",
        }]
        html = build_html(shows)
        assert "Pluribus" in html
        assert "S01E09" in html
        assert "La Chica o El Mundo" in html
        assert "trakt.tv/shows/pluribus" in html
        assert "trakt-list" in html

    def test_multiple_shows(self):
        shows = [
            {"show": "Show A", "season": 2, "episode": 3, "episode_title": "Ep", "watched_at": None, "url": ""},
            {"show": "Show B", "season": 1, "episode": 1, "episode_title": "Pilot", "watched_at": None, "url": ""},
        ]
        html = build_html(shows)
        assert "Show A" in html
        assert "Show B" in html
        assert html.count("<li>") == 2

    def test_empty_shows_returns_fallback(self):
        html = build_html([])
        assert "No shows tracked recently" in html
        assert "trakt-list" not in html

    def test_html_escapes_show_title(self):
        shows = [{
            "show": "Tom & Jerry's <Show>",
            "season": 1,
            "episode": 1,
            "episode_title": "",
            "watched_at": None,
            "url": "",
        }]
        html = build_html(shows)
        assert "Tom &amp; Jerry&#39;s &lt;Show&gt;" in html
        assert "<Show>" not in html  # raw HTML not present

    def test_episode_without_title(self):
        shows = [{
            "show": "Test",
            "season": 3,
            "episode": 5,
            "episode_title": "",
            "watched_at": None,
            "url": "",
        }]
        html = build_html(shows)
        assert "S03E05" in html
        assert "ldquo" not in html  # no quotes around empty title

    def test_show_without_season_episode(self):
        shows = [{
            "show": "Movie Night",
            "season": None,
            "episode": None,
            "episode_title": "",
            "watched_at": None,
            "url": "",
        }]
        html = build_html(shows)
        assert "Movie Night" in html
        assert "S00" not in html  # no season/episode formatting

    def test_auto_updated_line_present(self):
        html = build_html([])
        assert "Auto-updated" in html
        assert "Trakt" in html


# ── fetch_recent_shows (deduplication logic) ─────────────────────

class TestFetchDeduplication:
    """Test the deduplication logic without making API calls.

    fetch_recent_shows calls api_get internally, so we mock it
    to test the show-deduplication and limit logic.
    """

    def test_deduplicates_by_show_name(self, monkeypatch):
        fake_data = [
            {"show": {"title": "Pluribus", "ids": {"slug": "pluribus"}},
             "episode": {"season": 1, "number": 9, "title": "Ep 9"},
             "watched_at": "2026-04-20T18:41:00Z"},
            {"show": {"title": "Pluribus", "ids": {"slug": "pluribus"}},
             "episode": {"season": 1, "number": 8, "title": "Ep 8"},
             "watched_at": "2026-04-20T18:40:00Z"},
            {"show": {"title": "The West Wing", "ids": {"slug": "the-west-wing"}},
             "episode": {"season": 7, "number": 22, "title": "Tomorrow"},
             "watched_at": "2026-04-19T20:00:00Z"},
        ]
        monkeypatch.setattr(_trakt, "api_get", lambda token, path, params=None: fake_data)
        monkeypatch.setenv("TRAKT_CLIENT_ID", "fake")

        shows = fetch_recent_shows("fake_token")
        assert len(shows) == 2
        assert shows[0]["show"] == "Pluribus"
        assert shows[0]["episode"] == 9  # most recent episode
        assert shows[1]["show"] == "The West Wing"

    def test_limits_to_five_shows(self, monkeypatch):
        fake_data = [
            {"show": {"title": f"Show {i}", "ids": {"slug": f"show-{i}"}},
             "episode": {"season": 1, "number": 1, "title": "Pilot"},
             "watched_at": f"2026-04-{20-i:02d}T00:00:00Z"}
            for i in range(10)
        ]
        monkeypatch.setattr(_trakt, "api_get", lambda token, path, params=None: fake_data)
        monkeypatch.setenv("TRAKT_CLIENT_ID", "fake")

        shows = fetch_recent_shows("fake_token")
        assert len(shows) == 5

    def test_empty_api_response(self, monkeypatch):
        monkeypatch.setattr(_trakt, "api_get", lambda token, path, params=None: [])
        monkeypatch.setenv("TRAKT_CLIENT_ID", "fake")

        shows = fetch_recent_shows("fake_token")
        assert shows == []
