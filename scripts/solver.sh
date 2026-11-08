#!/bin/bash
# Solver entry point used by both evaluation harnesses.
#   bash scripts/solver.sh list            -> JSON list of variant names to score
#   bash scripts/solver.sh run <variant>   -> one oracle-protocol session on stdin/stdout
# Replace the module below to score a different solver; logs must go to stderr.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m method.pbo_ihs "$@"
