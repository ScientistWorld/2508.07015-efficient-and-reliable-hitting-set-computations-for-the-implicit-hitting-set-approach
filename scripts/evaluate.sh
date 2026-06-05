#!/bin/bash
set -euo pipefail

cd /home/user

RESULTS_PATH="${1:-checkpoints/pbo_ihs_results.json}"
python -m eval.evaluate_pbo_ihs --results "${RESULTS_PATH}"
