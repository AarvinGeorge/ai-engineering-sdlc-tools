#!/usr/bin/env bash
# Copies the user's draft settings for the live repo into the run's workspace as settings.json (needs --scaffold).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$here/resources/settings.json" settings.json
ls -l settings.json
