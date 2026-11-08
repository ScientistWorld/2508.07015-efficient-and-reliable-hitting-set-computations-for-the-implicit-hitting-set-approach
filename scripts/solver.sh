#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 redteam/hardening/controls/shortcut_baseline_degrade.py "$@"
