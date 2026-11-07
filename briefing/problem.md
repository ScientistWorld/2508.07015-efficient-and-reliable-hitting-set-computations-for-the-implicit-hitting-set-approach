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
