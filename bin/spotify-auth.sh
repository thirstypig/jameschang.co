#!/usr/bin/env bash
# One-time Spotify OAuth2 setup.
# Run locally to get your refresh token, then store it as a GitHub Secret.
#
# Prerequisites:
#   1. Create a Spotify app at https://developer.spotify.com/dashboard
#   2. Set redirect URI to: https://jameschang.co/spotify/callback/
#   3. Note your Client ID and Client Secret
#
# Usage:
#   ./bin/spotify-auth.sh

set -euo pipefail

echo "=== Spotify OAuth2 Setup ==="
echo ""

read -rp "Spotify Client ID: " CLIENT_ID
read -rp "Spotify Client Secret: " CLIENT_SECRET

REDIRECT_URI="https://jameschang.co/spotify/callback/"
SCOPES="user-read-recently-played user-read-playback-state"
ENCODED_SCOPES="${SCOPES// /%20}"

AUTH_URL="https://accounts.spotify.com/authorize?client_id=${CLIENT_ID}&response_type=code&redirect_uri=${REDIRECT_URI}&scope=${ENCODED_SCOPES}&state=jameschang"

echo ""
echo "Opening your browser to authorize with Spotify..."
echo "If it doesn't open, visit: ${AUTH_URL}"
echo ""

if command -v open &>/dev/null; then
  open "${AUTH_URL}"
fi

echo "After you approve, you'll be redirected to jameschang.co/spotify/callback/"
echo "with an authorization code displayed on the page."
echo ""
read -rp "Paste the authorization code here: " AUTH_CODE

echo ""
echo "Exchanging code for tokens..."

# Spotify supports client_secret_basic — send creds as Basic auth header
CREDS=$(printf "%s:%s" "${CLIENT_ID}" "${CLIENT_SECRET}" | base64)

BODY_FILE=$(mktemp)
HTTP_CODE=$(curl -s -o "${BODY_FILE}" -w "%{http_code}" -X POST "https://accounts.spotify.com/api/token" \
  -H "Authorization: Basic ${CREDS}" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=${AUTH_CODE}" \
  -d "redirect_uri=${REDIRECT_URI}")

RESPONSE=$(cat "${BODY_FILE}")
rm -f "${BODY_FILE}"

if [ "${HTTP_CODE}" != "200" ]; then
  echo "Token exchange failed: ${HTTP_CODE}"
  exit 1
fi

echo "Token exchange successful."

# Extract refresh token
REFRESH_TOKEN=$(echo "${RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('refresh_token', 'NONE'))")
ACCESS_TOKEN=$(echo "${RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token', 'NONE'))")

if [ "${REFRESH_TOKEN}" = "NONE" ]; then
  echo "Token exchange failed: no refresh_token in response. Check that the app's redirect URI exactly matches ${REDIRECT_URI}."
  exit 1
fi

# Write secrets to a mode-600 tempfile instead of echoing them.
umask 077
SECRETS_FILE=$(mktemp)
{
  echo "SPOTIFY_CLIENT_SECRET  = ${CLIENT_SECRET}"
  echo "SPOTIFY_REFRESH_TOKEN  = ${REFRESH_TOKEN}"
} > "${SECRETS_FILE}"

echo ""
echo "=== SUCCESS ==="
echo ""
echo "Add these as GitHub Secrets (Settings → Secrets and variables → Actions):"
echo ""
echo "  SPOTIFY_CLIENT_ID      = ${CLIENT_ID}"
echo ""
echo "Secrets saved to: ${SECRETS_FILE}"
echo "Copy them to GitHub Secrets, then run:"
echo "    shred -u ${SECRETS_FILE}    # or rm"
echo ""
echo "Testing API access..."

PROFILE=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" "https://api.spotify.com/v1/me")
DISPLAY_NAME=$(echo "${PROFILE}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('display_name','unknown'))" 2>/dev/null || echo "unknown")
echo "Authenticated as: ${DISPLAY_NAME}"
echo ""
echo "Done! Add the 3 secrets above to GitHub, then I'll trigger the sync."
