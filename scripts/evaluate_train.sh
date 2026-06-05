#!/bin/bash
set -euo pipefail

cd /home/user

RESULTS_PATH="${1:-checkpoints/pbo_ihs_results.json}"
python -m eval.train.evaluate_pbo_ihs_train \
  --results "${RESULTS_PATH}" \
  --output scoring/scores_train.json
