#!/bin/bash
# The method has no training stage: it is an online solver that the harness
# runs per instance through scripts/solver.sh.  This prints its variants.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/solver.sh list
