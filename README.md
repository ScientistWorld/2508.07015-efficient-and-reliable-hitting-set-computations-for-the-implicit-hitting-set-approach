# Overview

The paper proposes more reliable ways to compute hitting sets inside implicit hitting set solvers for pseudo-Boolean optimization. It compares standard IP-based hitting-set optimization with exact PB reasoning, hybrid verification schedules, and stochastic local search.

This reproduction packages a scaled PBO-IHS gym. It implements the actual IHS loop and several hitting-set optimizer variants, then evaluates whether the methods solve nontrivial PBO instances while maintaining independently checkable optimality bounds.

---

# Problem

The task is pseudo-Boolean optimization: find a Boolean assignment satisfying a set of pseudo-Boolean linear constraints while minimizing a positive weighted sum over objective variables.

The benchmark instances in this environment are small tracked PBO instances with objective variables, auxiliary variables, and feasibility constraints. A solver must output a feasible full assignment and its objective value.

Success is measured by independently checking feasibility and objective optimality against exhaustive search over the tracked instances.

---

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

---

# Evaluation

Run `scripts/evaluate.sh` on a JSON artifact produced by a method run. The evaluator imports only `data/`, recomputes the true optimum of each tracked instance by exhaustive enumeration, and writes `scoring/scores.json`.

For each submitted variant, every tracked benchmark instance is counted in the denominator. Missing, malformed, infeasible, or non-optimal rows count as failures.

Metrics:
- `solved_count`: number of feasible reported solutions.
- `optimality_match_rate`: fraction of instances matching the independent optimum.
- `certificate_accept_rate`: fraction of runs whose final lower and upper bounds both equal the checked optimum.
- `avg_exact_hs_calls`: average number of exact hitting-set optimizer calls used by the run.
- `avg_iterations`, `avg_decision_calls`, and `sls_successes`: diagnostic metrics.

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


---

# Reproduction Milestones

**Current: method_runs**

## Stop Justification
- Completed at milestone `method_runs`.
