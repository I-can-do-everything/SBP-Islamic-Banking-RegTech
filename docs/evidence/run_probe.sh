#!/usr/bin/env bash
# Runs probe_prototype.py against a temporary copy of the backend.
# Only BUG-001 is patched in the copy, so the other files can load.
# Needs: python3 with pydantic, pydantic-settings, python-dotenv, openpyxl.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
WORK="$(mktemp -d)"
cp -r "$REPO/backend" "$WORK/backend"
cd "$WORK/backend"
# Patch BUG-001 in the copy: move the __future__ import to the top of each file.
for f in app/schemas/submission.py app/layers/normalisation/mapper.py \
         app/layers/calculations/ratios.py app/models/submission.py; do
  grep -v '^from __future__ import annotations' "$f" > "$f.tmp"
  { echo 'from __future__ import annotations'; cat "$f.tmp"; } > "$f"
  rm "$f.tmp"
done
PYTHONPATH=. python3 -W ignore "$HERE/probe_prototype.py"
rm -rf "$WORK"
