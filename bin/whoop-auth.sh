#!/usr/bin/env bash
# One-time WHOOP OAuth2 setup.
# Run locally to get your refresh token, then store it as a GitHub Secret.
#
# Prerequisites:
#   1. Create a WHOOP developer app at https://developer.whoop.com
#   2. Set redirect URI to: https://jameschang.co/whoop/callback/
#   3. Note your Client ID and Client Secret
#
# Usage:
#   chmod +x bin/whoop-auth.sh
#   ./bin/whoop-auth.sh

set -euo pipefail

echo "=== WHOOP OAuth2 Setup ==="
echo ""

read -rp "WHOOP Client ID: " CLIENT_ID
read -rp "WHOOP Client Secret: " CLIENT_SECRET

REDIRECT_URI="https://jameschang.co/whoop/callback/"
SCOPES="read:recovery read:sleep read:workout read:cycles read:profile read:body_measurement offline"

# URL-encode spaces in scopes
ENCODED_SCOPES="${SCOPES// /%20}"

AUTH_URL="https://api.prod.whoop.com/oauth/oauth2/auth?client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}&response_type=code&scope=${ENCODED_SCOPES}&state=jameschang"

echo ""
echo "Opening your browser to authorize with WHOOP..."
echo "If it doesn't open automatically, visit this URL:"
echo ""
echo "  ${AUTH_URL}"
echo ""

# Open in default browser
if command -v open &>/dev/null; then
  open "${AUTH_URL}"
elif command -v xdg-open &>/dev/null; then
  xdg-open "${AUTH_URL}"
fi

echo "After you approve, you'll be redirected to jameschang.co/whoop/callback/"
echo "with an authorization code displayed on the page."
echo ""
read -rp "Paste the authorization code here: " AUTH_CODE

echo ""
echo "Exchanging code for tokens..."

RESPONSE=$(curl -s -X POST "https://api.prod.whoop.com/oauth/oauth2/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=${AUTH_CODE}" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "redirect_uri=${REDIRECT_URI}")

# Show full response for debugging
echo ""
echo "Token response:"
echo "${RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE}"
echo ""

# Check for error
if echo "${RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); e=d.get('error',''); exit(0 if e else 1)" 2>/dev/null; then
  ERROR=$(echo "${RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error','unknown'))")
  echo "ERROR: ${ERROR}"
  exit 1
fi

ACCESS_TOKEN=$(echo "${RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
REFRESH_TOKEN=$(echo "${RESPONSE}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('refresh_token', 'NONE'))")

echo ""
echo "=== SUCCESS ==="
echo ""
echo "Add these as GitHub Secrets (Settings → Secrets → Actions):"
echo ""
echo "  WHOOP_CLIENT_ID      = ${CLIENT_ID}"
echo "  WHOOP_CLIENT_SECRET  = ${CLIENT_SECRET}"
if [ "${REFRESH_TOKEN}" = "NONE" ]; then
  echo ""
  echo "  NOTE: WHOOP did not return a refresh_token."
  echo "  The access_token below may be long-lived. Store it as:"
  echo "  WHOOP_ACCESS_TOKEN   = ${ACCESS_TOKEN}"
  echo ""
  echo "  If it expires, re-run this script to get a new one."
else
  echo "  WHOOP_REFRESH_TOKEN  = ${REFRESH_TOKEN}"
fi
echo ""
echo "Testing API access..."

PROFILE=$(curl -s -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://api.prod.whoop.com/developer/v1/user/profile/basic")

FIRST_NAME=$(echo "${PROFILE}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('first_name','unknown'))" 2>/dev/null || echo "unknown")
echo "Authenticated as: ${FIRST_NAME}"
echo ""
echo "Done! Now push the repo and the GitHub Action will handle daily updates."
