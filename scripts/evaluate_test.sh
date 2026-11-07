#!/bin/bash
# Hidden test: score every variant listed by `bash scripts/solver.sh list` on
# the held-out instances in eval/test/ through the oracle harness.
# Takes no arguments; writes scoring/scores_test.json.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m eval.test.harness
