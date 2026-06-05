#!/bin/bash
set -euo pipefail

cd /home/user

RESULTS_ROOT="${1:-checkpoints}"
if [[ -d "${RESULTS_ROOT}" ]]; then
  RESULTS_PATH="${RESULTS_ROOT}/pbo_ihs_results.json"
else
  RESULTS_PATH="${RESULTS_ROOT}"
fi

python -m eval.train.evaluate_pbo_ihs_train \
  --results "${RESULTS_PATH}" \
  --output scoring/scores_train.json
