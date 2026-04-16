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
read -rsp "Refresh token: " TOKEN
echo ""

# Generate a random passphrase if not provided
read -rsp "Encryption passphrase (or press Enter to generate one): " KEY
echo ""
GENERATED_KEY_FILE=""
if [ -z "${KEY}" ]; then
  KEY=$(openssl rand -base64 32)
  umask 077
  GENERATED_KEY_FILE=$(mktemp)
  printf "%s\n" "${KEY}" > "${GENERATED_KEY_FILE}"
  echo ""
  echo "Generated passphrase saved to: ${GENERATED_KEY_FILE}"
  echo "View it with:   cat ${GENERATED_KEY_FILE}"
  echo "Save it as WHOOP_TOKEN_KEY GitHub Secret, then run:"
  echo "    shred -u ${GENERATED_KEY_FILE}    # or rm"
fi

echo "${TOKEN}" | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -out .whoop-token.enc -pass "pass:${KEY}"

echo ""
echo "Encrypted token saved to .whoop-token.enc"
echo ""
echo "Add WHOOP_TOKEN_KEY as a GitHub Secret (Settings → Secrets → Actions)."
if [ -n "${GENERATED_KEY_FILE}" ]; then
  echo "(Passphrase is in ${GENERATED_KEY_FILE} — shred it after copying.)"
fi
echo ""
echo "You can delete WHOOP_REFRESH_TOKEN from GitHub Secrets — it's no longer used."
echo "Keep WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET."
echo ""
echo "Then commit and push:"
echo "  git add .whoop-token.enc && git commit -m 'Add encrypted WHOOP token' && git push"
