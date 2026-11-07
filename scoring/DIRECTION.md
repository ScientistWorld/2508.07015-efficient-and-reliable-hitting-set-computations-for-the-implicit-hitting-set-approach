# Research Direction

Work within the implicit hitting set approach: alternate between computing hitting sets over the collected cores and extracting new cores or solutions with the decision oracle, and finish with an exact proof that no cheaper hitting set exists.

Directions the paper points to:

- Better hitting-set heuristics, so that fewer exact calls are needed. The paper notes that local search "can get stuck in local optima" and that improving SLS heuristics for the IHS setting "has potential for even further improvements".
- When to demand optimal hitting sets: the `opt?` heuristic of Algorithm 2, and hybrid schedules that delay exact calls (OptLB/ForceLB/AllLB).
- Exact optimisation strategies built from `hs_improve` calls: solution-improving search, bound probing, phase hints.
- Core extraction strategies: weight-aware core extraction, core minimisation, multiple cores per iteration. Each one trades decision calls against stronger cores.

Out of scope: replacing the IHS loop with a solver that bypasses the oracles, private complete search over the cores, or anything that reads the held-out instances (see `CONSTRAINTS.md`).
