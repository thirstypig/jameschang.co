#!/usr/bin/env bash
# Encrypt a Trakt refresh token to .trakt-token.enc.
# Same pattern as bin/whoop-encrypt.sh — see docs/solutions/integration-issues/
# oauth2-refresh-token-rotation-encrypted-committed-file.md.
#
# Usage:
#   export TRAKT_TOKEN_KEY="your-passphrase"
#   echo "your-refresh-token" | bash bin/trakt-encrypt.sh
#
# Or interactively:
#   bash bin/trakt-encrypt.sh
#   (paste token, press Enter, then Ctrl-D)

set -euo pipefail

: "${TRAKT_TOKEN_KEY:?Set TRAKT_TOKEN_KEY first}"

if [ -t 0 ]; then
  echo "Paste the Trakt refresh token, then press Enter + Ctrl-D:"
fi

openssl enc -aes-256-cbc -pbkdf2 -iter 600000 \
  -out .trakt-token.enc -pass "pass:${TRAKT_TOKEN_KEY}"

echo "Encrypted to .trakt-token.enc ($(wc -c < .trakt-token.enc | tr -d ' ') bytes)."
echo "Commit this file. The passphrase stays in TRAKT_TOKEN_KEY GitHub Secret."
