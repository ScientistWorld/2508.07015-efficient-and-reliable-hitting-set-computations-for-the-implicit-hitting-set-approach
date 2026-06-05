# Method

The paper studies the implicit hitting set approach for pseudo-Boolean optimization. PBO-IHS alternates between:

1. Solving a hitting-set problem over the accumulated cores using the objective.
2. Calling a decision oracle under the hitting-set assignment.
3. Adding a new core if that assignment cannot be extended to a full feasible solution.
4. Stopping when the best upper bound equals the hitting-set lower bound.

The implementation in `method/pbo_ihs.py` preserves this computation at small scale. It includes:
- `ip_exact`: an exact hitting-set baseline.
- `sis`: solution-improving search over the current cores, matching the paper's PB-style exact HS optimization family.
- `sis_sls`: the paper's local-search integration idea, trying a two-phase repair/diversification search before falling back to exact SIS.

The full paper also evaluates native PB solvers, IP solvers, hybrids, and VeriPB proof logging at much larger scale. The official solver archive and result table URLs are captured in `scripts/download.sh`.
