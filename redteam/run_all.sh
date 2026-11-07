#!/bin/bash
set -euo pipefail
cd /home/user
python -m redteam.prepare
failed=0
for case in reference_seed1 reference_seed2 reference_seed3 \
  better_single_pass_core weaker_no_sls weaker_initial_solution \
  shortcut_public_answers shortcut_erased_trace \
  shortcut_extraction_underreport shortcut_summary_forgery \
  shortcut_empty_output shortcut_constant_ones \
  shortcut_repeated_sls shortcut_failing_repeated_sls \
  shortcut_fixed_data_replace shortcut_baseline_degrade; do
  if ! bash "redteam/${case}/run.sh"; then
    failed=1
  fi
done
python -m redteam.summarize
exit "$failed"
