#!/bin/bash
# Hardening controls for the rebuilt gym (iteration 11).
#
# Every candidate is staged by swapping in a different solver entry point
# (scripts/solver.sh) or different public data, then scored by the UNCHANGED
# hidden test `bash scripts/evaluate_test.sh` (no arguments).  Seed-noise runs
# call the same test harness with --seed-offset.  Everything staged is
# restored afterwards.  Finished cases are skipped, so the script can resume.
set -uo pipefail
cd "$(dirname "$0")/../.."

H=redteam/hardening
R=$H/results
mkdir -p "$R"

cp scripts/solver.sh "$H/.orig_solver.sh"
cp data/instances_train.json "$H/.orig_instances_train.json"
for f in scores_test.json scores_train.json; do
  [ -f "scoring/$f" ] && cp "scoring/$f" "$H/.orig_$f"
done

restore() {
  cp "$H/.orig_solver.sh" scripts/solver.sh
  cp "$H/.orig_instances_train.json" data/instances_train.json
  for f in scores_test.json scores_train.json; do
    [ -f "$H/.orig_$f" ] && cp "$H/.orig_$f" "scoring/$f"
  done
}
trap restore EXIT

stage_solver() {
  cat > scripts/solver.sh <<EOS
#!/bin/bash
set -euo pipefail
cd "\$(dirname "\$0")/.."
exec python3 $H/controls/$1 "\$@"
EOS
}

# test_case NAME CONTROL_FILE [ENV=VALUE ...]   (CONTROL_FILE "-" = reference solver)
test_case() {
  local name=$1 file=$2
  shift 2
  if [ -f "$R/${name}_test.json" ]; then echo "skip $name (done)"; return; fi
  [ "$file" != "-" ] && stage_solver "$file"
  if env "$@" bash scripts/evaluate_test.sh > "$R/${name}_test.log" 2>&1; then
    cp scoring/scores_test.json "$R/${name}_test.json"
    echo "PASS $name"
  else
    echo "FAIL $name (see $R/${name}_test.log)"
  fi
  restore
}

train_case() {
  local name=$1 file=$2
  shift 2
  if [ -f "$R/${name}_train.json" ]; then echo "skip $name train (done)"; return; fi
  [ "$file" != "-" ] && stage_solver "$file"
  if env "$@" bash scripts/evaluate_train.sh --details "" > "$R/${name}_train.log" 2>&1; then
    cp scoring/scores_train.json "$R/${name}_train.json"
    echo "PASS $name train"
  else
    echo "FAIL $name train"
  fi
  restore
}

# seed_case NAME CONTROL_FILE OFFSET : hidden test harness with shifted solver seeds
seed_case() {
  local name=$1 file=$2 offset=$3
  if [ -f "$R/${name}_test.json" ]; then echo "skip $name (done)"; return; fi
  [ "$file" != "-" ] && stage_solver "$file"
  if python3 -m eval.test.harness --seed-offset "$offset" --output "$R/${name}_test.json" \
      --details "$R/${name}_details.json" > "$R/${name}_test.log" 2>&1; then
    echo "PASS $name"
  else
    rm -f "$R/${name}_test.json"
    echo "FAIL $name"
  fi
  restore
}

# 1. Reference and seed noise (paired: same instances, same seeds per offset)
for k in 0 1 2; do
  seed_case "reference_seed$k" - "$k"
  seed_case "better_opt_first_seed$k" better_opt_first.py "$k"
done

# 2. Weaker control (the `sis` baseline row is scored inside every reference run)
test_case weaker_single_core weaker_single_core.py

# 3. Shortcuts from REDTEAM.md, re-expressed against the new interface
test_case shortcut_immediate_done shortcut_immediate_done.py
test_case shortcut_forged_report shortcut_forged_report.py
test_case shortcut_spam_decide shortcut_spam_decide.py
test_case shortcut_baseline_degrade shortcut_baseline_degrade.py
test_case shortcut_public_train_lookup shortcut_instance_lookup.py IHS_LOOKUP_FILE=data/instances_train.json
train_case shortcut_public_train_lookup shortcut_instance_lookup.py IHS_LOOKUP_FILE=data/instances_train.json

# fixed-data replacement: make every public training instance trivially easy
if [ ! -f "$R/shortcut_data_replace_test.json" ]; then
  python3 - <<'EOF'
import json
p = "data/instances_train.json"
d = json.load(open(p))
for inst in d["instances"]:
    inst["demands"] = [[[0]]]
    inst["seed_constraints"] = []
    inst["optimum"] = inst["weights"][0]
json.dump(d, open(p, "w"))
EOF
  if bash scripts/evaluate_test.sh > "$R/shortcut_data_replace_test.log" 2>&1; then
    cp scoring/scores_test.json "$R/shortcut_data_replace_test.json"; echo "PASS shortcut_data_replace"
  fi
  restore
fi

# 4. Shortcuts left open (measured, documented, left to the grader)
test_case shortcut_private_exact_hs shortcut_private_exact_hs.py
test_case shortcut_read_hidden_file shortcut_instance_lookup.py IHS_LOOKUP_FILE=eval/test/instances_test.json

python3 $H/summarize.py
