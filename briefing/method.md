# Method

The paper (Ihalainen, Vandesande, Schidler, Berg, Bogaerts, Järvisalo, AAAI 2026) studies how to compute hitting sets inside the implicit hitting set (IHS) approach to pseudo-Boolean optimisation (PBO-IHS). Algorithm 1 alternates two components:

1. **Solve-HS** — find an assignment to the objective variables that satisfies every core collected so far, either optimally (which yields a lower bound by Proposition 1) or heuristically (cheaper than the current upper bound, no bound change).
2. **Extract-Cores** — call a decision oracle with the hitting set as assumptions. Each conflict yields a core; its literals are dropped from the assumptions (weight-aware core extraction) and the oracle is called again until it returns a feasible assignment, which may improve the upper bound.

The loop stops when the lower bound equals the upper bound.

The paper's contributions concern Solve-HS (Algorithm 2): exact hitting sets by pseudo-Boolean reasoning (solution-improving search, SIS; core-guided; core-boosted) instead of floating-point IP; integrating stochastic local search (Core-SLS) so that cheap heuristic hitting sets replace calls to the expensive exact optimiser; hybrids that delay proof-producing calls; and VeriPB certificates for the whole IHS run.

## Reference implementation (`method/pbo_ihs.py`)

A pure-Python client of the oracle protocol in `briefing/evaluation.md`. The pseudo-Boolean solver the paper calls (RoundingSat) is played by the harness: its `decide` oracle is the decision procedure over the full instance, and its `hs_improve` oracle is the exact PB decision procedure over the cores.

- `sis` (baseline, the paper's single-solver "SIS" row): every Solve-HS runs SIS to optimality — repeated `hs_improve` calls with the bound tightened to each new solution until the oracle proves no cheaper hitting set exists (Algorithm 2 with `opt? = true`, no SLS).
- `sis_sls` (proposed, the paper's "SIS + SLS"): Core-SLS first. It runs two phases, one from the previous hitting set and one from a copy with n/2 variables flipped. Each flip minimises (change in total core violation, change in cost) with random tie-breaking, for 80·n flips per phase. The cheapest violation-free assignment below the upper bound is kept, with ties going to the second phase. If SLS finds one, it is the hitting set (no lower-bound change); otherwise SIS runs as in `sis`.

Both variants use the same Extract-Cores (weight-aware core extraction) and the same seeds.

## Scale-down

The paper runs 1786 PB-competition instances with Gurobi, SCIP, RoundingSat and VeriPB under a 1-hour limit. Here, solvers run on generated network-activation instances, 24–52 objective variables each, under a fixed oracle-call budget per instance; solved means certified optimal by the harness. The paper itself uses oracle-call counts to explain its results (OptLB "requires the fewest RoundingSat calls and performs best"). The official solver archive and result tables are fetched by `scripts/download.sh` for reference.
