---
category: integration-issues
title: Plex home server API via relay for GitHub Actions
problem_type: network-reachability
components:
  - bin/update-plex.py
  - .github/workflows/plex-sync.yml
symptoms:
  - Plex API calls from GitHub Actions time out (home server not reachable from cloud)
  - Direct server URL (192.168.x.x:32400) is RFC 1918, unreachable from CI
  - Remote URL (dynamic home IP) blocked by ISP firewall / NAT
root_cause: >
  Plex Media Server runs on a home LAN with no inbound port forwarding.
  GitHub Actions runners cannot reach RFC 1918 addresses or dynamic home
  IPs behind consumer firewalls. The relay infrastructure exists for this
  scenario but its URL format is non-obvious.
fix_summary: >
  Use the Plex relay URL (https://{ip-dashed}.{hash}.plex.direct:8443)
  as the connection target. Discovered via plex.tv/api/v2/resources API.
  Static token stored as plain GitHub Secret (no rotation needed).
tags:
  - plex
  - relay
  - home-server
  - github-actions
  - network
  - api
resolved: 2026-04-22
---

# Plex home server API via relay for GitHub Actions

## Symptoms

Adding a Plex watch history feed to the /now page. The Plex Media Server runs on a home Mac Mini. GitHub Actions runners cannot reach it — direct IP times out, local IP is RFC 1918.

## Investigation

1. **Discovery API** — `plex.tv/api/v2/resources?includeHttps=1&includeRelay=1` (authenticated with Plex token) returns three connection URIs per server:

   | Type | URI | Reachable from CI? |
   |------|-----|-------------------|
   | LOCAL | `https://192-168-4-26.{hash}.plex.direct:32400` | No (RFC 1918) |
   | REMOTE | `https://181-215-169-206.{hash}.plex.direct:24587` | No (timed out — ISP firewall) |
   | RELAY | `https://74-207-254-8.{hash}.plex.direct:8443` | **Yes** |

2. **REMOTE attempt** — dynamic home IP behind NAT, no port forwarding. Times out.

3. **RELAY attempt** — Plex operates relay servers that proxy requests to home servers through an existing outbound connection. Worked immediately.

4. **Auth model** — Plex tokens are static (no OAuth rotation). Stored as a plain GitHub Secret, unlike WHOOP (encrypted rotating token) or Trakt (encrypted rotating token).

5. **Data quirk** — the `year` field is `null` for movies when accessed via relay. The script handles this gracefully (no parentheses shown when year is missing).

## Root cause

Plex's API runs on a home LAN server with no inbound port forwarding. The relay URL (`https://{ip-dashed}.{server-hash}.plex.direct:8443`) is the only path from a cloud CI runner to a home server without VPN or tunnel infrastructure.

## Fix

Use the relay URL as `PLEX_URL` in GitHub Secrets:

```
https://74-207-254-8.f6a25566ea224397978bdf85d2f196c7.plex.direct:8443
```

The session history endpoint:
```
GET {PLEX_URL}/status/sessions/history/all?X-Plex-Token={token}&sort=viewedAt:desc
```

Returns JSON with `MediaContainer.Metadata[]` containing:
- `type`: "movie" or "episode"
- `title`: movie or episode title
- `grandparentTitle`: show name (for episodes)
- `parentIndex`: season number
- `index`: episode number
- `viewedAt`: Unix timestamp

Required GitHub Secrets:

| Secret | Value | Rotates? |
|--------|-------|----------|
| `PLEX_URL` | Relay URL | Only if home IP changes |
| `PLEX_TOKEN` | Static Plex auth token | No |

## Key insight

The relay URL format embeds the home server's public IP as dashed octets. If the ISP assigns a new IP, the relay URL breaks. The staleness check workflow (48-hour heartbeat) will catch this — at that point, re-run the discovery API to get the updated relay URL.

## Prevention

1. **IP change detection** — if the Plex feed goes stale (>48h), re-run: `curl -s "https://plex.tv/api/v2/resources?includeHttps=1&includeRelay=1" -H "X-Plex-Token: {token}" -H "Accept: application/json"` and update the `PLEX_URL` secret with the new relay URI.

2. **Don't depend on `year` field** — it's null via relay. Only trust `title`, `type`, `viewedAt`, `grandparentTitle`, `parentIndex`, `index`.

3. **Token revocation** — the static token is invalidated if the Plex account password changes or the device is removed at `plex.tv/devices`. Re-extract from `Preferences.xml` on the server or from the browser's XML view.

4. **Alternatives if relay dies** — Plex relay is best-effort. Fallbacks: port forwarding, Cloudflare Tunnel, Tailscale funnel, or run the sync script locally via cron.

## Related

- `docs/solutions/integration-issues/oauth2-refresh-token-rotation-encrypted-committed-file.md` — the WHOOP pattern (rotating tokens, encrypted file). Plex is simpler: static token, plain secret.
- `docs/solutions/integration-issues/openssl-pbkdf2-iteration-count-mismatch.md` — the Trakt pattern (also rotating tokens). Plex avoids this entirely.
