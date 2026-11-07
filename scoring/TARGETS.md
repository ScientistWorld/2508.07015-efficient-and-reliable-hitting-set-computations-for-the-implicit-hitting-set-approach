# Scoring Targets

## certified_ihs_under_budget

Scored by `scripts/evaluate_test.sh` (hidden test, 80 held-out instances) and mirrored on the 80 public training instances by `scripts/evaluate_train.sh`. Every variant listed by `bash scripts/solver.sh list` is scored. Every instance counts in every denominator.

Ranked metrics (coefficients in `scoring/reference.json`):

- `certified_solve_rate` (benefit and constraint, primary, +1.0): fraction of instances the harness certifies optimal within 180 oracle calls. Certification is computed by the harness from its own oracle log; a solver cannot claim it.
- `mean_call_ratio` (benefit, −0.25, lower is better): mean oracle calls until certification divided by 180. An instance uncertified within the 720-call cap counts as 4, so a run that fails cannot gain efficiency credit.

Diagnostics (coefficient 0): `mean_decide_calls`, `mean_hs_calls`, `hs_call_share`.

Reference point for ranking: the `sis_sls` row of `scoring/scores_test.json`. The baseline row `sis` must stay clearly below it, which it does on both ranked metrics.
