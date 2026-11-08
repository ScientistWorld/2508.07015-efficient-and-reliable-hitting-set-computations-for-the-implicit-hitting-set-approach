#!/bin/bash
# Reproduce the reference end to end (CPU only, ~45 min on one core):
#   1. regenerate the instance files and check they match the committed ones,
#   2. score the reference solver's variants (sis, sis_sls) on the public
#      training instances and on the hidden test.
# The hardening controls and shortcuts are rerun by redteam/hardening/run_controls.sh.
set -euo pipefail
cd /home/user

before=$(sha256sum data/instances_train.json eval/test/instances_test.json)
python3 -m data.make_train_instances
python3 -m eval.test.make_test_instances
after=$(sha256sum data/instances_train.json eval/test/instances_test.json)
if [ "$before" != "$after" ]; then
  echo "regenerated instance files differ from the committed ones" >&2
  exit 1
fi

bash scripts/reproduce.sh
python3 validate.py
