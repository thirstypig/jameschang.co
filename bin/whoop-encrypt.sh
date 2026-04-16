#!/usr/bin/env bash
# Encrypt a WHOOP refresh token for storage in the repo.
# The encrypted file (.whoop-token.enc) is safe to commit.
# Only someone with WHOOP_TOKEN_KEY can decrypt it.
#
# Usage:
#   ./bin/whoop-encrypt.sh
#
# Then add WHOOP_TOKEN_KEY as a GitHub Secret.

set -euo pipefail

echo "=== Encrypt WHOOP Refresh Token ==="
echo ""
read -rp "Refresh token: " TOKEN
echo ""

# Generate a random passphrase if not provided
read -rp "Encryption passphrase (or press Enter to generate one): " KEY
if [ -z "${KEY}" ]; then
  KEY=$(openssl rand -base64 32)
  echo ""
  echo "Generated passphrase (save as WHOOP_TOKEN_KEY GitHub Secret):"
  echo "  ${KEY}"
fi

echo "${TOKEN}" | openssl enc -aes-256-cbc -pbkdf2 -out .whoop-token.enc -pass "pass:${KEY}"

echo ""
echo "Encrypted token saved to .whoop-token.enc"
echo ""
echo "Add this GitHub Secret (Settings → Secrets → Actions):"
echo "  WHOOP_TOKEN_KEY = ${KEY}"
echo ""
echo "You can delete WHOOP_REFRESH_TOKEN from GitHub Secrets — it's no longer used."
echo "Keep WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET."
echo ""
echo "Then commit and push:"
echo "  git add .whoop-token.enc && git commit -m 'Add encrypted WHOOP token' && git push"
