#!/usr/bin/env bash
# One-time Trakt OAuth2 setup.
# Run locally to obtain a refresh token, then store it as TRAKT_REFRESH_TOKEN
# in GitHub Secrets (repo → Settings → Secrets → Actions).
#
# Usage:
#   export TRAKT_CLIENT_ID="your-client-id"
#   export TRAKT_CLIENT_SECRET="your-client-secret"
#   bash bin/trakt-auth.sh

set -euo pipefail

: "${TRAKT_CLIENT_ID:?Set TRAKT_CLIENT_ID first}"
: "${TRAKT_CLIENT_SECRET:?Set TRAKT_CLIENT_SECRET first}"

REDIRECT_URI="urn:ietf:wg:oauth:2.0:oob"
AUTH_URL="https://trakt.tv/oauth/authorize?response_type=code&client_id=${TRAKT_CLIENT_ID}&redirect_uri=${REDIRECT_URI}"

echo ""
echo "=== Trakt OAuth Setup ==="
echo ""
echo "1. Opening your browser to authorize the app..."
echo "   If it doesn't open, visit this URL manually:"
echo ""
echo "   ${AUTH_URL}"
echo ""

# Try to open browser (macOS / Linux)
if command -v open &>/dev/null; then
  open "${AUTH_URL}"
elif command -v xdg-open &>/dev/null; then
  xdg-open "${AUTH_URL}"
fi

echo "2. After approving, Trakt will show you a PIN/code."
echo "   Paste it here:"
echo ""
read -rp "   Authorization code: " AUTH_CODE

echo ""
echo "3. Exchanging code for tokens..."

RESPONSE=$(curl -s -X POST "https://api.trakt.tv/oauth/token" \
  -H "Content-Type: application/json" \
  -d "{
    \"code\": \"${AUTH_CODE}\",
    \"client_id\": \"${TRAKT_CLIENT_ID}\",
    \"client_secret\": \"${TRAKT_CLIENT_SECRET}\",
    \"redirect_uri\": \"${REDIRECT_URI}\",
    \"grant_type\": \"authorization_code\"
  }")

ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
REFRESH_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('refresh_token',''))")

if [ -z "$ACCESS_TOKEN" ] || [ -z "$REFRESH_TOKEN" ]; then
  echo "ERROR: Token exchange failed."
  echo "Response: ${RESPONSE}"
  exit 1
fi

echo ""
echo "=== Success! ==="
echo ""
echo "Access token:  ${ACCESS_TOKEN:0:20}... (truncated)"
echo "Refresh token: ${REFRESH_TOKEN:0:20}... (truncated)"
echo ""
echo "4. Now add this as a GitHub Secret:"
echo ""
echo "   Secret name:  TRAKT_REFRESH_TOKEN"
echo "   Secret value: ${REFRESH_TOKEN}"
echo ""
echo "   Go to: https://github.com/thirstypig/jameschang.co/settings/secrets/actions"
echo ""
echo "5. Quick test — fetching your recently watched shows..."

TEST=$(curl -s "https://api.trakt.tv/users/me/history/shows?limit=3" \
  -H "Content-Type: application/json" \
  -H "trakt-api-version: 2" \
  -H "trakt-api-key: ${TRAKT_CLIENT_ID}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")

echo "$TEST" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if not data:
    print('   No watch history found. Watch something on Trakt first!')
else:
    for item in data[:3]:
        show = item.get('show', {}).get('title', '?')
        ep = item.get('episode', {})
        s = ep.get('season', '?')
        e = ep.get('number', '?')
        title = ep.get('title', '')
        print(f'   {show} S{s:02d}E{e:02d} — {title}')
    print(f'   ({len(data)} items returned)')
"

echo ""
echo "Done. The refresh token does not rotate — store it once in GitHub Secrets."
