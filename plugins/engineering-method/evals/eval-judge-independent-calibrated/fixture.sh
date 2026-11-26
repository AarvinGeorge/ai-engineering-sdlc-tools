#!/usr/bin/env bash
# Copies the owner's rulings, beside the judge's verdicts, into the run's workspace as labels.csv (needs --scaffold).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$here/resources/labels.csv" labels.csv
ls -l labels.csv
