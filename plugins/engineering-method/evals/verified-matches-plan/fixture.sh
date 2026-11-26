#!/usr/bin/env bash
# Copies the plan, diff-stat and diff the prompt shows into the run's workspace as review-input.md (needs --scaffold).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$here/resources/review-input.md" review-input.md
ls -l review-input.md
