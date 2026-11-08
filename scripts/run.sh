#!/bin/bash
# Job: final reference scores under budget 140 / cap 560, then the controls
# without saved per-instance details (resumable; restored to the plain
# end-to-end reproduction afterwards).
set -euo pipefail
cd /home/user
R=redteam/hardening/results
mkdir -p "$R"

before=$(sha256sum data/instances_train.json eval/test/instances_test.json)
python3 -m data.make_train_instances
python3 -m eval.test.make_test_instances
after=$(sha256sum data/instances_train.json eval/test/instances_test.json)
if [ "$before" = "$after" ]; then echo "instances reproducible" > "$R/instances_check.txt"; else echo "INSTANCE MISMATCH" > "$R/instances_check.txt"; fi

if [ ! -f "$R/.train_done" ]; then
  bash scripts/method.sh
  bash scripts/evaluate_train.sh > "$R/reference_train.log" 2>&1
  cp scoring/scores_train.json scoring/scores.json
  touch "$R/.train_done"
fi
if [ ! -f "$R/.reference_done" ]; then
  bash scripts/evaluate_test.sh > "$R/reference_test.log" 2>&1
  cp scoring/scores_test.json "$R/reference_seed0_test.json"
  touch "$R/.reference_done"
fi

bash redteam/hardening/run_controls.sh
python3 validate.py --post-design > "$R/validate_post_design.log" 2>&1 || true
