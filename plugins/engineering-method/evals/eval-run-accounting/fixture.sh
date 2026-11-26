#!/usr/bin/env bash
# Copies the night's result.json and its kept traces into the run's workspace (needs --scaffold).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -R "$here/resources/eval-out" eval-out
ls -R eval-out
