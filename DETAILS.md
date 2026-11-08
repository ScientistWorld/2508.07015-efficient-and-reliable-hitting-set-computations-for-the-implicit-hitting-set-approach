# Overview

The paper studies more reliable and efficient ways to compute hitting sets inside implicit hitting set (IHS) solvers for pseudo-Boolean optimisation. It compares IP-based hitting-set optimisation with exact pseudo-Boolean reasoning, local search, hybrid schedules, and certificates of optimality.

This gym poses the problem behind that work at small scale: certify the optimum of held-out pseudo-Boolean instances whose constraints are reachable only through counted oracles, within a budget of oracle calls. The reference solver is the paper's PBO-IHS loop with solution-improving search (`sis`) and with local search integrated into the hitting-set step (`sis_sls`).

---

# Problem

Certified pseudo-Boolean optimisation when the constraints can only be queried, not read.

Each instance is a 0–1 linear minimisation problem: minimise `sum_i w_i x_i` (all `w_i > 0`) over objective variables `x_0 … x_{n-1}`, subject to pseudo-Boolean constraints. Most constraints also involve auxiliary variables. A solver receives:

- the objective weights,
- the constraints that mention objective variables only (unit-coefficient coverage rules `sum_{i in S} x_i >= k`),
- a seed, the per-instance call budget and the solve budget.

Everything else about the instance is reachable only through two oracles answered and counted by the evaluation harness:

- `decide(assumptions)` — a decision procedure over the full instance under fixed values for some objective variables. It returns either a feasible assignment of the objective variables with its cost, or a **core**: a constraint over objective variables that every feasible assignment satisfies and that the assumptions violate.
- `hs_improve(bound)` — an exact pseudo-Boolean decision procedure over the **hitting-set problem**, i.e. the objective-only constraints plus every core the harness has returned so far. It returns an assignment that satisfies all of them with cost `< bound`, or a proof that none exists. Such a proof makes `bound` a lower bound on the optimum.

An instance is **solved** when the harness itself holds a feasible assignment of cost `U` and a proof that the hitting-set problem has no assignment cheaper than `U`, i.e. a certificate of optimality, within the solve budget of oracle calls. Nothing a solver claims is taken on trust.

The task is to certify as many instances as possible and to use as few oracle calls as possible doing it.

## Instances

Instances come from a network-activation family. Each objective variable activates a component with a cost. Each demand must be served by at least one of its alternative routes, and a route is usable only when all of its components are active. Every constraint is monotone in the objective variables. Sizes range over 24–52 objective variables and 8–25 demands. The public training instances and their generator are in `data/` (`data/instances_train.json`, `data/make_train_instances.py`). The held-out test instances come from the same distribution with a private seed; they live only in `eval/test/` and are never shown to solvers.

---

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

---

# Evaluation

## Commands

| Command | What it does |
|---|---|
| `bash scripts/solver.sh list` | Your solver prints a JSON list of variant names. Every listed variant is scored. |
| `bash scripts/solver.sh run <variant>` | Runs one protocol session (one instance) on stdin/stdout. |
| `bash scripts/evaluate_train.sh` | Scores every listed variant on the 80 public training instances → `scoring/scores_train.json`, per-instance `scoring/details_train.json`. |
| `bash scripts/evaluate_test.sh` | Hidden test, no arguments: scores every listed variant on 160 held-out instances in `eval/test/` → `scoring/scores_test.json`. |

`scripts/solver.sh` is the only interface between a solver and the evaluator. To score a different solver, change what that script executes. `eval/` never imports solver code. The harness starts a fresh solver process per instance, with the workspace as the working directory. Solver logs must go to stderr; the harness keeps them in `logs/`. Two safety limits stop runaway sessions; neither is a metric. First, a guard of 300 s per instance on time spent waiting for the solver; the harness's own oracle time is excluded, and the reference solver needs under 60 s. Second, deterministic search-node caps on the exact oracle, 2M nodes per call and 20M per instance, more than 10× what any reference session uses. A session that hits either limit ends unsolved.

## Protocol (JSON lines)

1. The harness sends one line:
   `{"type": "instance", "n_objective": n, "weights": [...], "seed_constraints": [C, ...], "budget": 560, "solve_budget": 140, "seed": s}`
   Constraint format `C = {"terms": [[coeff, var, polarity], ...], "rhs": k}` means `sum coeff * lit >= k`, where `lit = x_var` if `polarity == 1`, else `1 - x_var`.
2. The solver sends requests, one JSON object per line. The harness answers each with one line.
   - `{"op": "decide", "assumptions": [[var, value], ...]}` — any subset of objective variables, values 0/1.
     Answer: `{"sat": true, "assignment": [n values], "cost": c, ...}` or `{"sat": false, "core": C, ...}`.
   - `{"op": "hs_improve", "bound": b, "phase": [n values] (optional)}` — `phase` is a preferred value per variable for the oracle's search order.
     Answer: `{"sat": true, "assignment": [...], "cost": c, ...}` (it satisfies the objective-only constraints and every core returned so far, with `c < b`), or `{"sat": false, ...}`, which proves that no such assignment exists.
   - `{"op": "done"}` ends the session.

   Every answer also carries the harness's own `lb`, `ub`, `calls_left` and `certified`.
3. Each `decide` or `hs_improve` costs one call. The session ends when the harness has certified the instance (`lb >= ub`), when the solver sends `done` or exits, when the 560-call cap is reached (`{"error": "budget_exhausted"}`), on any malformed request (`{"error": "protocol_error"}`), or at a safety limit.

The harness keeps its own log. Its upper bound is the cheapest feasible assignment its decision oracle has returned. Its lower bound is the largest `b` for which its exact oracle answered `sat: false`. A solver cannot submit answers, bounds, certificates or counts. Other messages are protocol errors and end the session unsolved.

## Metrics (experiment `certified_ihs_under_budget`)

Every instance is in every denominator; each variant sees the same instances and the same seeds.

- `certified_solve_rate` (primary, coefficient +1.0): fraction of instances certified within 140 oracle calls. The solve budget of 140 is the reference solver's median calls-to-certify on the training instances, where the rate is most sensitive to efficiency gains.
- `mean_call_ratio` (coefficient −0.25, lower is better): mean of (calls answered until certification) / 140. An instance not certified within the 560-call cap counts as 4.
- Diagnostics, not ranked: `mean_decide_calls`, `mean_hs_calls`, `hs_call_share`.

Rank of a submission = Σ coefficient × (its value − reference value). The reference value is the proposed `sis_sls` row of `scoring/scores_test.json`. A run that certifies nothing scores 0 on the solve rate and 4 on the call ratio, which is the worst possible on both.

## Train vs test

Train and test instances come from the same generator and size distribution (80 training, 160 held-out), with the same budgets and the same harness code (two independent copies). The public generator cannot reproduce the test instances: their seed is private to `eval/test/`. Train scores are feedback only. A solver tuned to the identity of training instances gains nothing on test.

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 11m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 07:57] - none
- Started reproduction work.
- Read the paper and identified PBO-IHS hitting-set optimization as the core method.

### [2026-06-05 08:05] - none
- Verified the official Zenodo and Bitbucket artifact locations.
- Implemented a scaled PBO-IHS environment; awaiting compute-node execution before claiming `method_runs`.

### [2026-06-05 08:07] - method_runs
- Ran the scaled PBO-IHS implementation locally on all tracked instances.
- `ip_exact`, `sis`, and `sis_sls` all executed end-to-end and wrote method artifacts.
- Independent evaluation and `python validate.py --compare` passed locally.

### [2026-06-05 08:09] - core_claim
- Compute job `e6cc7b5c-f1a` completed with exit code 0.
- The container run reproduced the scaled PBO-IHS experiment and passed `python validate.py --compare`.
- Exact SIS matched the exact hitting-set baseline on all tracked instances, and the SLS-integrated variant preserved exactness while reducing average exact HS calls from 5.0 to 1.333.

</details>

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 3m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Fixed evaluator coverage so missing benchmark rows are counted as unsolved rather than omitted.
- Reran `scripts/reproduce.sh` and `python validate.py --compare`; all checks passed with the same core-claim metrics.

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 11m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Confirmed `python validate.py --compare` passes.
- Verified the official Zenodo artifact URLs used by `scripts/download.sh` return HTTP 200 and match the downloaded file sizes.

### [2026-06-05 08:22] - method_runs
- Performed a continuation audit from the reset `method_runs` state.
- Found and fixed weak evaluation of self-reported algorithm metadata by adding method trace output and independent trace validation.
- Reran `bash scripts/reproduce.sh && python validate.py --compare` locally; all scored variants still solve 3/3 instances with independently validated certificates.
- Submitting a CPU validation job before restoring `core_claim` for the hardened evaluator.

### [2026-06-05 08:25] - core_claim
- Compute job `f0c9a696-205` ran `scripts/run.sh` successfully with exit code 0.
- The hardened evaluator accepted the trace-validated certificates for all three variants.
- `sis_sls` preserved 3/3 optimality and certificate acceptance while reducing average exact hitting-set calls from 5.0 to 1.333.

</details>

### Iteration 4: gpt-5.5 (designer_stage_1)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Confirmed `python validate.py --compare` passes.
- Verified the official Zenodo artifact URLs used by `scripts/download.sh` return HTTP 200 and match the downloaded file sizes.

### [2026-06-05 08:22] - method_runs
- Performed a continuation audit from the reset `method_runs` state.
- Found and fixed weak evaluation of self-reported algorithm metadata by adding method trace output and independent trace validation.
- Reran `bash scripts/reproduce.sh && python validate.py --compare` locally; all scored variants still solve 3/3 instances with independently validated certificates.
- Submitting a CPU validation job before restoring `core_claim` for the hardened evaluator.

### [2026-06-05 08:25] - core_claim
- Compute job `f0c9a696-205` ran `scripts/run.sh` successfully with exit code 0.
- The hardened evaluator accepted the trace-validated certificates for all three variants.
- `sis_sls` preserved 3/3 optimality and certificate acceptance while reducing average exact hitting-set calls from 5.0 to 1.333.

</details>

### Iteration 5: gpt-5.5 (designer_stage_2)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 5m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Confirmed `python validate.py --compare` passes.
- Verified the official Zenodo artifact URLs used by `scripts/download.sh` return HTTP 200 and match the downloaded file sizes.

### [2026-06-05 08:22] - method_runs
- Performed a continuation audit from the reset `method_runs` state.
- Found and fixed weak evaluation of self-reported algorithm metadata by adding method trace output and independent trace validation.
- Reran `bash scripts/reproduce.sh && python validate.py --compare` locally; all scored variants still solve 3/3 instances with independently validated certificates.
- Submitting a CPU validation job before restoring `core_claim` for the hardened evaluator.

### [2026-06-05 08:25] - core_claim
- Compute job `f0c9a696-205` ran `scripts/run.sh` successfully with exit code 0.
- The hardened evaluator accepted the trace-validated certificates for all three variants.
- `sis_sls` preserved 3/3 optimality and certificate acceptance while reducing average exact hitting-set calls from 5.0 to 1.333.

</details>

### Iteration 6: gpt-5.5 (designer_stage_3)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Confirmed `python validate.py --compare` passes.
- Verified the official Zenodo artifact URLs used by `scripts/download.sh` return HTTP 200 and match the downloaded file sizes.

### [2026-06-05 08:22] - method_runs
- Performed a continuation audit from the reset `method_runs` state.
- Found and fixed weak evaluation of self-reported algorithm metadata by adding method trace output and independent trace validation.
- Reran `bash scripts/reproduce.sh && python validate.py --compare` locally; all scored variants still solve 3/3 instances with independently validated certificates.
- Submitting a CPU validation job before restoring `core_claim` for the hardened evaluator.

### [2026-06-05 08:25] - core_claim
- Compute job `f0c9a696-205` ran `scripts/run.sh` successfully with exit code 0.
- The hardened evaluator accepted the trace-validated certificates for all three variants.
- `sis_sls` preserved 3/3 optimality and certificate acceptance while reducing average exact hitting-set calls from 5.0 to 1.333.

</details>

### Iteration 7: gpt-5.5 (packager)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 15m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Confirmed `python validate.py --compare` passes.
- Verified the official Zenodo artifact URLs used by `scripts/download.sh` return HTTP 200 and match the downloaded file sizes.

### [2026-06-05 08:22] - method_runs
- Performed a continuation audit from the reset `method_runs` state.
- Found and fixed weak evaluation of self-reported algorithm metadata by adding method trace output and independent trace validation.
- Reran `bash scripts/reproduce.sh && python validate.py --compare` locally; all scored variants still solve 3/3 instances with independently validated certificates.
- Submitting a CPU validation job before restoring `core_claim` for the hardened evaluator.

### [2026-06-05 08:25] - core_claim
- Compute job `f0c9a696-205` ran `scripts/run.sh` successfully with exit code 0.
- The hardened evaluator accepted the trace-validated certificates for all three variants.
- `sis_sls` preserved 3/3 optimality and certificate acceptance while reducing average exact hitting-set calls from 5.0 to 1.333.

</details>

### Iteration 8: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 30m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Confirmed `python validate.py --compare` passes.
- Verified the official Zenodo artifact URLs used by `scripts/download.sh` return HTTP 200 and match the downloaded file sizes.

### [2026-06-05 08:22] - method_runs
- Performed a continuation audit from the reset `method_runs` state.
- Found and fixed weak evaluation of self-reported algorithm metadata by adding method trace output and independent trace validation.
- Reran `bash scripts/reproduce.sh && python validate.py --compare` locally; all scored variants still solve 3/3 instances with independently validated certificates.
- Submitting a CPU validation job before restoring `core_claim` for the hardened evaluator.

### [2026-06-05 08:25] - core_claim
- Compute job `f0c9a696-205` ran `scripts/run.sh` successfully with exit code 0.
- The hardened evaluator accepted the trace-validated certificates for all three variants.
- `sis_sls` preserved 3/3 optimality and certificate acceptance while reducing average exact hitting-set calls from 5.0 to 1.333.

</details>

### Iteration 9: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 30m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Confirmed `python validate.py --compare` passes.
- Verified the official Zenodo artifact URLs used by `scripts/download.sh` return HTTP 200 and match the downloaded file sizes.

### [2026-06-05 08:22] - method_runs
- Performed a continuation audit from the reset `method_runs` state.
- Found and fixed weak evaluation of self-reported algorithm metadata by adding method trace output and independent trace validation.
- Reran `bash scripts/reproduce.sh && python validate.py --compare` locally; all scored variants still solve 3/3 instances with independently validated certificates.
- Submitting a CPU validation job before restoring `core_claim` for the hardened evaluator.

### [2026-06-05 08:25] - core_claim
- Compute job `f0c9a696-205` ran `scripts/run.sh` successfully with exit code 0.
- The hardened evaluator accepted the trace-validated certificates for all three variants.
- `sis_sls` preserved 3/3 optimality and certificate acceptance while reducing average exact hitting-set calls from 5.0 to 1.333.

</details>

### Iteration 10: gpt-6.1-sol (redteam)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 4 total (4 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Confirmed `python validate.py --compare` passes.
- Verified the official Zenodo artifact URLs used by `scripts/download.sh` return HTTP 200 and match the downloaded file sizes.

### [2026-06-05 08:22] - method_runs
- Performed a continuation audit from the reset `method_runs` state.
- Found and fixed weak evaluation of self-reported algorithm metadata by adding method trace output and independent trace validation.
- Reran `bash scripts/reproduce.sh && python validate.py --compare` locally; all scored variants still solve 3/3 instances with independently validated certificates.
- Submitting a CPU validation job before restoring `core_claim` for the hardened evaluator.

### [2026-06-05 08:25] - core_claim
- Compute job `f0c9a696-205` ran `scripts/run.sh` successfully with exit code 0.
- The hardened evaluator accepted the trace-validated certificates for all three variants.
- `sis_sls` preserved 3/3 optimality and certificate acceptance while reducing average exact hitting-set calls from 5.0 to 1.333.

</details>

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 1.1h | **GPU**: 0.0h
- **Jobs**: 7 total (5 completed, 1 failed)

<details>
<summary>Progress Log</summary>

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Confirmed `python validate.py --compare` passes.
- Verified the official Zenodo artifact URLs used by `scripts/download.sh` return HTTP 200 and match the downloaded file sizes.

### [2026-06-05 08:22] - method_runs
- Performed a continuation audit from the reset `method_runs` state.
- Found and fixed weak evaluation of self-reported algorithm metadata by adding method trace output and independent trace validation.
- Reran `bash scripts/reproduce.sh && python validate.py --compare` locally; all scored variants still solve 3/3 instances with independently validated certificates.
- Submitting a CPU validation job before restoring `core_claim` for the hardened evaluator.

### [2026-06-05 08:25] - core_claim
- Compute job `f0c9a696-205` ran `scripts/run.sh` successfully with exit code 0.
- The hardened evaluator accepted the trace-validated certificates for all three variants.
- `sis_sls` preserved 3/3 optimality and certificate acceptance while reducing average exact hitting-set calls from 5.0 to 1.333.

### [2026-11-08] - core_claim (iteration 11, hardening)
- Rebuilt the hidden test: the solver runs on 160 held-out instances in `eval/test/` through evaluator-owned, counted oracles, and certification comes from the harness's own log.
- Reran the reference from the final code: `sis_sls` certified_solve_rate 0.681, mean_call_ratio 0.859; `sis` 0.250 / 1.614. This is the paper's direction: SLS integration solves more instances and replaces exact hitting-set calls.
- A better variant beats the reference by 0.053–0.067 on every seed (reference seed spread 0.026). All major REDTEAM shortcuts now score at or below the reference. The private exact hitting-set shortcut is left open for the grader (see `HARDENING.md`).

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
