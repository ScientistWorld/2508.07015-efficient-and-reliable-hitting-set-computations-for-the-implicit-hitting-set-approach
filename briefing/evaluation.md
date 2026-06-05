# Evaluation

Run `scripts/evaluate.sh` on a JSON artifact produced by a method run. The evaluator imports only `data/`, recomputes the true optimum of each tracked instance by exhaustive enumeration, and writes `scoring/scores.json`.

For each submitted variant, every tracked benchmark instance is counted in the denominator. Missing, malformed, infeasible, or non-optimal rows count as failures.

Metrics:
- `solved_count`: number of feasible reported solutions.
- `optimality_match_rate`: fraction of instances matching the independent optimum.
- `certificate_accept_rate`: fraction of runs whose final lower and upper bounds both equal the checked optimum.
- `avg_exact_hs_calls`: average number of exact hitting-set optimizer calls used by the run.
- `avg_iterations`, `avg_decision_calls`, and `sls_successes`: diagnostic metrics.
