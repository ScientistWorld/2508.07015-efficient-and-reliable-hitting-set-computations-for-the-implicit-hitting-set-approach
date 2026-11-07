#!/bin/bash
# Visible evaluation of the current solver (training instances) -> scoring/scores.json
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m eval.train.harness --output scoring/scores.json --details scoring/details_train.json
