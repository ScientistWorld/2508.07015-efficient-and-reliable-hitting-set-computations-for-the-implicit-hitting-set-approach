# Constraints

The evaluator enforces these mechanically:

- Instances are visible to a solver only through the protocol in `briefing/evaluation.md`. The constraints that involve auxiliary variables are never sent. Lower bounds exist only as `hs_improve` proofs inside the harness; upper bounds exist only as `decide` answers.
- Every `decide` and `hs_improve` call is counted by the harness. Solver-written numbers, flags, logs or files are never read. Malformed or unknown requests end the session unsolved.
- Uncertified instances count as unsolved and are charged the 560-call cap in `mean_call_ratio`.
- Ground truth, test instances, budgets, seeds and the reference row are fixed by `eval/test/` and `scoring/`. Editing `data/` changes only training feedback.

Rules a submission must follow, which the evaluator cannot observe (checked by the shortcut grader):

1. Do not read anything under `eval/test/` (instances, generator, seed) from solver code, and do not try to recover held-out instances by other means.
2. Every **exact** or otherwise **complete** optimisation over the hitting-set problem (branch and bound, exhaustive enumeration, an ILP/MaxSAT/PB/CP solver, etc. run on the cores) must go through `hs_improve`, so that it is counted. Incomplete heuristics run privately (local search, greedy, repair, diversification) are the intended place to innovate and are free. Running a private exact optimiser and presenting its results as heuristic hitting sets is a shortcut.
3. Use the `seed` from the instance message for all randomness, so that runs are reproducible.
4. Solve each instance from the protocol alone. Do not hard-code instance identities, weights or answers taken from the training set.
5. Keep each instance well under the 300 s solver-time guard, and list only the variants you want scored. The hidden test runs every listed variant on all 160 instances in one job, about 15 minutes per reference-like variant.
