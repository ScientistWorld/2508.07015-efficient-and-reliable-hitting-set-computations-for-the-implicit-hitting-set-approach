# Scoring Targets

## scaled_pbo_ihs_exactness

This benchmark evaluates whether a solver implements the PBO-IHS problem-solving loop on the tracked pseudo-Boolean instances.

Every tracked instance is scored for each submitted variant. Omitting an instance is treated as an unsolved instance, not as a smaller benchmark.

Primary benefit metric:
- `optimality_match_rate`: fraction of instances where the reported solution matches the independently computed optimum.

Constraint metrics:
- `certificate_accept_rate`: fraction of runs whose reported lower and upper bounds agree with the independently checked optimum.
- `avg_exact_hs_calls`: lower is better when exactness is maintained, because the paper studies reducing expensive exact hitting-set calls.

Coverage metric:
- `solved_count`: number of tracked instances for which the method reports a feasible solution.
