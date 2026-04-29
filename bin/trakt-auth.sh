#!/usr/bin/env bash
# One-time Trakt OAuth2 setup.
# Run locally to obtain a refresh token; the encrypted token file
# (.trakt-token.enc) is committed to the repo and decrypted at runtime
# by update-trakt.py via the TRAKT_TOKEN_KEY GitHub Secret.
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

# Build the JSON body via python json.dumps so a " in any client_id /
# secret can't break the request. Pipe through curl --data @- so the body
# is never an argv argument.
export AUTH_CODE REDIRECT_URI
BODY=$(python3 -c '
import json, os
print(json.dumps({
    "code": os.environ["AUTH_CODE"],
    "client_id": os.environ["TRAKT_CLIENT_ID"],
    "client_secret": os.environ["TRAKT_CLIENT_SECRET"],
    "redirect_uri": os.environ["REDIRECT_URI"],
    "grant_type": "authorization_code",
}))
')

BODY_FILE=$(mktemp)
HTTP_CODE=$(printf '%s' "${BODY}" | curl -s -o "${BODY_FILE}" -w "%{http_code}" -X POST "https://api.trakt.tv/oauth/token" \
  -H "Content-Type: application/json" \
  --data-binary @-)

RESPONSE=$(cat "${BODY_FILE}")
rm -f "${BODY_FILE}"

if [ "${HTTP_CODE}" != "200" ]; then
  echo "Token exchange failed: ${HTTP_CODE}"
  exit 1
fi

ACCESS_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")
REFRESH_TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('refresh_token',''))")

if [ -z "$ACCESS_TOKEN" ] || [ -z "$REFRESH_TOKEN" ]; then
  echo "ERROR: Token exchange failed — no access_token / refresh_token in response."
  exit 1
fi

# Write the refresh token to a mode-600 tempfile instead of echoing it to
# stdout. Avoids leakage via terminal scrollback, recorded sessions, or
# screen-share tools — same pattern as bin/whoop-auth.sh and bin/spotify-auth.sh.
umask 077
SECRETS_FILE=$(mktemp)
{
  echo "TRAKT_REFRESH_TOKEN = ${REFRESH_TOKEN}"
} > "${SECRETS_FILE}"

echo ""
echo "=== Success! ==="
echo ""
echo "Access token (truncated):  ${ACCESS_TOKEN:0:20}..."
echo "Refresh token saved to: ${SECRETS_FILE}"
echo ""
echo "Next steps:"
echo "  1. Encrypt the refresh token into .trakt-token.enc:"
echo "       export TRAKT_TOKEN_KEY=\"<a strong passphrase>\""
echo "       cat ${SECRETS_FILE} | awk -F'= ' '{print \$2}' | bash bin/trakt-encrypt.sh"
echo "  2. Add TRAKT_TOKEN_KEY (and TRAKT_CLIENT_ID / TRAKT_CLIENT_SECRET) as GitHub Secrets."
echo "  3. shred -u ${SECRETS_FILE}    # or rm — the secret is no longer needed locally."
echo ""
echo "Quick test — fetching your recently watched shows..."

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
echo "Done. The refresh token rotates on every use — bin/update-trakt.py handles re-encryption."
