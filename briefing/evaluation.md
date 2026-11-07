# Evaluation

## Commands

| Command | What it does |
|---|---|
| `bash scripts/solver.sh list` | Your solver prints a JSON list of variant names. Every listed variant is scored. |
| `bash scripts/solver.sh run <variant>` | Runs one protocol session (one instance) on stdin/stdout. |
| `bash scripts/evaluate_train.sh` | Scores every listed variant on the 80 public training instances → `scoring/scores_train.json`, per-instance `scoring/details_train.json`. |
| `bash scripts/evaluate_test.sh` | Hidden test, no arguments: scores every listed variant on 80 held-out instances in `eval/test/` → `scoring/scores_test.json`. |

`scripts/solver.sh` is the only interface between a solver and the evaluator. To score a different solver, change what that script executes. `eval/` never imports solver code. The harness starts a fresh solver process per instance, with the workspace as the working directory. Solver logs must go to stderr; the harness keeps them in `logs/`. A wall-clock guard of 120 s per instance stops runaway processes. It is a safety limit, not a metric; the reference solver needs under 20 s per instance.

## Protocol (JSON lines)

1. The harness sends one line:
   `{"type": "instance", "n_objective": n, "weights": [...], "seed_constraints": [C, ...], "budget": 720, "solve_budget": 180, "seed": s}`
   Constraint format `C = {"terms": [[coeff, var, polarity], ...], "rhs": k}` means `sum coeff * lit >= k`, where `lit = x_var` if `polarity == 1`, else `1 - x_var`.
2. The solver sends requests, one JSON object per line. The harness answers each with one line.
   - `{"op": "decide", "assumptions": [[var, value], ...]}` — any subset of objective variables, values 0/1.
     Answer: `{"sat": true, "assignment": [n values], "cost": c, ...}` or `{"sat": false, "core": C, ...}`.
   - `{"op": "hs_improve", "bound": b, "phase": [n values] (optional)}` — `phase` is a preferred value per variable for the oracle's search order.
     Answer: `{"sat": true, "assignment": [...], "cost": c, ...}` (it satisfies the objective-only constraints and every core returned so far, with `c < b`), or `{"sat": false, ...}`, which proves that no such assignment exists.
   - `{"op": "done"}` ends the session.

   Every answer also carries the harness's own `lb`, `ub`, `calls_left` and `certified`.
3. Each `decide` or `hs_improve` costs one call. The session ends when the harness has certified the instance (`lb >= ub`), when the solver sends `done` or exits, when the 720-call cap is reached (`{"error": "budget_exhausted"}`), on any malformed request (`{"error": "protocol_error"}`), or at the wall-clock guard.

The harness keeps its own log. Its upper bound is the cheapest feasible assignment its decision oracle has returned. Its lower bound is the largest `b` for which its exact oracle answered `sat: false`. A solver cannot submit answers, bounds, certificates or counts. Other messages are protocol errors and end the session unsolved.

## Metrics (experiment `certified_ihs_under_budget`)

Every instance is in every denominator; each variant sees the same instances and the same seeds.

- `certified_solve_rate` (primary, coefficient +1.0): fraction of instances certified within 180 oracle calls.
- `mean_call_ratio` (coefficient −0.25, lower is better): mean of (calls answered until certification) / 180. An instance not certified within the 720-call cap counts as 4.
- Diagnostics, not ranked: `mean_decide_calls`, `mean_hs_calls`, `hs_call_share`.

Rank of a submission = Σ coefficient × (its value − reference value). The reference value is the proposed `sis_sls` row of `scoring/scores_test.json`. A run that certifies nothing scores 0 on the solve rate and 4 on the call ratio, which is the worst possible on both.

## Train vs test

Train and test instances come from the same generator and size distribution, 80 each, with the same budgets and the same harness code (two independent copies). The public generator cannot reproduce the test instances: their seed is private to `eval/test/`. Train scores are feedback only. A solver tuned to the identity of training instances gains nothing on test.
