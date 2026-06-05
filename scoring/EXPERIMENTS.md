# Experiments

## scaled_pbo_ihs_exactness

This experiment checks whether each submitted method solves the same pseudo-Boolean optimization instances and returns solutions that agree with an independent exhaustive verifier.

The comparison includes a direct exact hitting-set baseline, an exact pseudo-Boolean solution-improving hitting-set optimizer, and a variant that tries local-search repair before falling back to exact optimization.

The experiment is intended to establish both benefit and reliability: methods should solve all instances, match the independent optimum, and expose bound information sufficient for the evaluator to accept the final optimality claim.
