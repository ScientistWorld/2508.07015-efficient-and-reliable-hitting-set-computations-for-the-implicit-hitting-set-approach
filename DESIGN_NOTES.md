# Train/Test Evaluation Design Notes

## Checks Performed

- Read both split evaluators side-by-side and confirmed the train slice verifies odd IHS trace events while the test slice verifies the complementary even events.
- Checked that both split evaluators read submitted result artifacts and do not import from `method/`.
- Checked for train/test cross-imports and paper-agreement metric names.
- Checked that `scripts/evaluate_test.sh` references `eval/test/` and writes `scoring/scores_test.json`.
- Ran `bash -n` on `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh`.
- Confirmed no `scoring/scores_train.json` or `scoring/scores_test.json` stubs exist.
- Confirmed active metrics in `scoring/reference.json` are emitted by both split evaluators.

## Changes Made

- Added `selected_trace_accept_rate` to both split evaluators. This gives a granular signal for metric-gaming: a method that fabricates or overfits only visible trace events should fail held-out events partially rather than only through the all-or-nothing certificate metric.
- Added `exact_hs_call_fraction` after the first real run showed exactness and trace validity saturating at 1.0 for every valid method. The new metric keeps the split focused on the paper's efficiency claim by measuring the share of selected iterations that still require exact hitting-set optimization.
- Removed the test evaluator's dependency on `scoring/scores_train.json`. The held-out run now scores the submitted artifact directly and discovers variants from that artifact, matching the train-side interface.
- Updated `scripts/evaluate_test.sh` to stop passing `--train-scores`.
- Updated every active metric in `scoring/reference.json` with the required `higher_is_better`, `coefficient`, and `description` fields, and added the new trace metric.

## Real-Run Results

- Job `2024c07b-8ed` completed successfully and produced all original train/test metrics for `ip_exact`, `sis`, and `sis_sls`.
- Job `ac5b4a95-67e` completed successfully after adding `exact_hs_call_fraction`; both `scoring/scores_train.json` and `scoring/scores_test.json` now include every active metric from `scoring/reference.json`.
- Exactness-style metrics are saturated for the current valid methods: `solved_count = 3`, `optimality_match_rate = 1.0`, `certificate_accept_rate = 1.0`, and `selected_trace_accept_rate = 1.0` on both slices. These remain useful as constraints against broken shortcut methods.
- `avg_exact_hs_calls` is the primary ranking metric because it is present in the original reference results, differentiates methods on the visible train slice, and differs between train and test while measuring the paper's exact-solver-reduction claim. `exact_hs_call_fraction` remains as a normalized supporting metric; `sis_sls` reduces it from `1.0` to `0.3` on train and to `0.14285714285714285` on test, while preserving exactness and certificate validity.

## Runtime Concerns For Next Iteration

- The split is trace-event based rather than instance based because the benchmark has only three deterministic PBO instances. This is appropriate for the paper's algorithmic trace/certificate claim, but the runner should watch for saturation: exact methods may score 1.0 on both optimality and certificate metrics.
- `selected_trace_accept_rate` is intentionally paired with `certificate_accept_rate`; if future result artifacts contain very short traces, the event-level denominator may be small even though the final certificate metric still catches invalid or missing traces.
- `exact_hs_call_fraction`, `avg_exact_hs_calls`, `avg_iterations`, `avg_decision_calls`, and `sls_successes` should be interpreted only together with the exactness and certificate constraints; a low-work method that fails exactness is not a valid improvement.
- The evaluators depend on the JSON artifact containing complete per-instance IHS traces. A future method that outputs only final assignments will still get feasibility/optimality credit but should fail certificate and selected-trace metrics.
- The original paper markdown path supplied for this iteration was not present at `/home/user/scratch/AgentWorkspaces/papers/arxiv_mds/2508.07015/2508.07015.md`, so paper-context review was limited to the existing workspace docs and implementation.
