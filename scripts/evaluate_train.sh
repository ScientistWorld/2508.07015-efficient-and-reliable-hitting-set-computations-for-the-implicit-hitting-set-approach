#!/bin/bash
# Score every variant listed by `bash scripts/solver.sh list` on the public
# training instances (data/instances_train.json) through the oracle harness.
# Writes scoring/scores_train.json and per-instance scoring/details_train.json.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m eval.train.harness "$@"
