This audit stages only method/data/result artifacts, then calls the original
`bash scripts/evaluate_test.sh` with no arguments in a separate Python process.
The evaluator, interpreter, imports and environment are not modified by a case.
The train scorer is also run. A `finally` block restores the prior method, data,
checkpoint, and score files after each case. No candidate reads the paper, hidden
test module, hidden scoring anchors, or pre-existing checkpoints.

Run the complete suite with `bash redteam/run_all.sh` inside the gym container.
Each candidate has its own `redteam/<name>/run.sh`, persistent `artifact.json`,
and `scores_{train,test}.json`. For cheap artifact-only cases, a reference run
generated from the visible method is reused. Missing reference results are
regenerated automatically. `harness.py` contains their explicit transformations.
The public-answer shortcut has an independent solver under its own directory.

`reference_source.py` is the original visible implementation. Scoring anchors
in this directory are used only by the audit reporter, never by candidates.
Rank deltas use the signed coefficients from `scoring/reference.json` and the
initial hidden-test results as the reference point. Both the proposed `sis_sls`
delta and the sum across all three matching variant names are saved, to make
the handling of fixed baseline rows explicit.

The baseline-degradation shortcut changes only its comparison row. The fixed-data
replacement shortcut changes only the concrete benchmark instances, not verifier
classes or their behavior. The failing-repeated-SLS shortcut returns infeasible
all-zero assignments and never needs the optimum, but supplies repeated locally
valid, non-improving events for the all-one assignment.
