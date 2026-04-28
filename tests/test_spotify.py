"""Unit tests for bin/update-spotify.py — Spotify feed rendering and state."""

import importlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

_spotify = importlib.import_module("update-spotify")
build_html = _spotify.build_html
load_state = _spotify.load_state
save_state = _spotify.save_state
fetch_recent_tracks = _spotify.fetch_recent_tracks
fetch_current_podcast = _spotify.fetch_current_podcast


# ── build_html ───────────────────────────────────────────────────

class TestSpotifyBuildHtml:
    def test_tracks_only(self):
        tracks = [
            {"name": "Brick House", "artists": "Commodores", "played_at": None, "url": "https://spotify.com/track/1"},
            {"name": "Sweet Thing", "artists": "Rufus, Chaka Khan", "played_at": None, "url": ""},
        ]
        html = build_html(tracks, None)
        assert "Brick House" in html
        assert "Commodores" in html
        assert "Sweet Thing" in html
        assert "<ul>" in html
        assert "nb-feed-podcast" not in html

    def test_podcast_and_tracks(self):
        tracks = [{"name": "Song", "artists": "Artist", "played_at": None, "url": ""}]
        podcast = {
            "show": "Baseball Tonight",
            "episode": "Big Episode",
            "url": "https://spotify.com/ep/1",
            "captured_at": "2026-04-20T12:00:00+00:00",
        }
        html = build_html(tracks, podcast)
        assert "Baseball Tonight" in html
        assert "Big Episode" in html
        assert "nb-feed-podcast" in html
        assert "<ul>" in html

    def test_podcast_only_no_tracks(self):
        podcast = {"show": "Show", "episode": "Ep", "url": "", "captured_at": None}
        html = build_html([], podcast)
        assert "nb-feed-podcast" in html
        assert "<ul>" not in html

    def test_empty_returns_fallback(self):
        html = build_html([], None)
        assert "Nothing recent" in html
        assert "feed-empty" in html

    def test_html_escapes_track_names(self):
        tracks = [{"name": "Rock & Roll", "artists": "Led <Zep>", "played_at": None, "url": ""}]
        html = build_html(tracks, None)
        assert "Rock &amp; Roll" in html
        assert "Led &lt;Zep&gt;" in html
        assert "<Zep>" not in html

    def test_auto_updated_line_present(self):
        html = build_html([], None)
        assert "Auto-updated" in html
        assert "Spotify Web API" in html


# ── load_state / save_state ──────────────────────────────────────

class TestSpotifyState:
    def test_load_missing_file(self, monkeypatch):
        monkeypatch.setattr(_spotify, "STATE_FILE", "/tmp/nonexistent-spotify-state.json")
        assert load_state() == {}

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        state_file = str(tmp_path / ".spotify-state.json")
        monkeypatch.setattr(_spotify, "STATE_FILE", state_file)

        save_state({"last_podcast": {"show": "Test"}})
        result = load_state()
        assert result["last_podcast"]["show"] == "Test"

    def test_load_corrupt_json(self, tmp_path, monkeypatch):
        state_file = tmp_path / ".spotify-state.json"
        state_file.write_text("{corrupt!!!")
        monkeypatch.setattr(_spotify, "STATE_FILE", str(state_file))
        assert load_state() == {}


# ── fetch_recent_tracks ──────────────────────────────────────────

class TestFetchRecentTracks:
    def test_parses_api_response(self, monkeypatch):
        fake_response = {
            "items": [
                {
                    "track": {
                        "name": "Espresso",
                        "artists": [{"name": "Sabrina Carpenter"}],
                        "external_urls": {"spotify": "https://spotify.com/track/abc"},
                    },
                    "played_at": "2026-04-20T12:00:00Z",
                }
            ]
        }
        monkeypatch.setattr(_spotify, "api_get", lambda token, path, params=None: fake_response)
        tracks = fetch_recent_tracks("fake_token")
        assert len(tracks) == 1
        assert tracks[0]["name"] == "Espresso"
        assert tracks[0]["artists"] == "Sabrina Carpenter"
        assert tracks[0]["url"] == "https://spotify.com/track/abc"

    def test_empty_response(self, monkeypatch):
        monkeypatch.setattr(_spotify, "api_get", lambda token, path, params=None: None)
        assert fetch_recent_tracks("fake") == []


# ── fetch_current_podcast ────────────────────────────────────────

class TestFetchCurrentPodcast:
    def test_returns_podcast_when_playing(self, monkeypatch):
        fake_response = {
            "is_playing": True,
            "item": {
                "type": "episode",
                "name": "Great Episode",
                "show": {"name": "Great Show"},
                "external_urls": {"spotify": "https://spotify.com/ep/1"},
            },
        }
        monkeypatch.setattr(_spotify, "api_get", lambda token, path, params=None: fake_response)
        result = fetch_current_podcast("fake_token")
        assert result is not None
        assert result["episode"] == "Great Episode"
        assert result["show"] == "Great Show"

    def test_returns_none_when_not_playing(self, monkeypatch):
        monkeypatch.setattr(_spotify, "api_get", lambda token, path, params=None: {"is_playing": False})
        assert fetch_current_podcast("fake") is None

    def test_returns_none_when_playing_music_not_podcast(self, monkeypatch):
        fake_response = {"is_playing": True, "item": {"type": "track", "name": "Song"}}
        monkeypatch.setattr(_spotify, "api_get", lambda token, path, params=None: fake_response)
        assert fetch_current_podcast("fake") is None

    def test_returns_none_on_empty_response(self, monkeypatch):
        monkeypatch.setattr(_spotify, "api_get", lambda token, path, params=None: None)
        assert fetch_current_podcast("fake") is None
