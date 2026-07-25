#!/usr/bin/env bash
# Sync the local credential expiry registry (gitignored) up to the
# EXPIRY_REGISTRY GitHub Actions secret, which the expiry-check workflow reads.
# Run after every edit to admin/registry.local.json.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FILE="$ROOT/admin/registry.local.json"

[ -f "$FILE" ] || { echo "error: $FILE not found" >&2; exit 1; }

# Fail before pushing if the JSON is malformed or missing the integrations list.
python3 -c "import json,sys; d=json.load(open('$FILE')); sys.exit(0 if isinstance(d.get('integrations'), list) else 1)" \
  || { echo "error: $FILE is not valid JSON or is missing an 'integrations' list" >&2; exit 1; }

gh secret set EXPIRY_REGISTRY --repo thirstypig/jameschang.co < "$FILE"

count="$(python3 -c "import json; print(len(json.load(open('$FILE'))['integrations']))")"
echo "Pushed ${count} integration(s) to the EXPIRY_REGISTRY secret."
