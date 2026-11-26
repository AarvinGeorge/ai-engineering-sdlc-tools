#!/usr/bin/env bash
# Copies the two exports of the failing turn into the run's workspace (needs --scaffold).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p resources
cp "$here/resources/session_local.jsonl" "$here/resources/trace_export.json" resources/
ls -l resources
