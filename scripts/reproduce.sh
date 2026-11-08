#!/bin/bash
# Reproduce the reference scores end to end (CPU only, roughly 45 minutes on one core).
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/method.sh
bash scripts/evaluate_train.sh
cp scoring/scores_train.json scoring/scores.json
bash scripts/evaluate_test.sh
