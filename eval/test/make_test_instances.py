"""Generate the hidden test instances (``eval/test/instances_test.json``).

Same instance family and parameter distribution as the public training
generator, drawn from a private 128-bit seed that exists only in this file.
The test instances and their optima must never be copied outside eval/test/.

Instance family: monotone network activation.  Each objective variable x_i
activates component i at cost w_i.  Each demand j must be served by at least
one of its alternative routes; a route is usable only when every component on
it is active.  As a pseudo-Boolean formula this uses one auxiliary variable
y_{j,r} per route:

    sum_r y_{j,r} >= 1                      for every demand j
    x_i + (1 - y_{j,r}) >= 1                for every component i on route r
    sum_{i in S} x_i >= k                   a few objective-only coverage rules

and the objective is  min sum_i w_i x_i.  Only the objective-only rules are
visible to a solver; the demand/route structure is reachable only through the
decision oracle of the evaluation harness.

The optimum stored with each instance is computed here by an exhaustive
branch-and-bound over route choices that is independent of the harness.

Usage:  python3 -m eval.test.make_test_instances
"""

from __future__ import annotations

import json
import random
from pathlib import Path

TEST_SEED = 16270665939503735278329640736036430645
N_INSTANCES = 160
OUT = Path(__file__).resolve().parent / "instances_test.json"


def generate(rng: random.Random, name: str) -> dict:
    n = rng.randint(24, 52)
    weights = [rng.randint(1, 20) for _ in range(n)]
    m = max(8, round(n * rng.uniform(0.32, 0.48)))
    demands = []
    for _ in range(m):
        center = rng.randrange(n)
        n_routes = rng.randint(2, 4)
        routes: set[tuple[int, ...]] = set()
        guard = 0
        while len(routes) < n_routes and guard < 200:
            guard += 1
            size = rng.choice([1, 2, 2, 3, 3, 3])
            comps: set[int] = set()
            while len(comps) < size:
                comps.add((center + int(round(rng.gauss(0.0, 3.0)))) % n)
            routes.add(tuple(sorted(comps)))
        demands.append([list(r) for r in sorted(routes)])
    seeds = []
    start = rng.randrange(n)
    for _ in range(rng.randint(2, 3)):
        size = rng.randint(4, 6)
        group = sorted({(start + d) % n for d in range(size)})
        start = (start + size + rng.randint(1, 4)) % n
        seeds.append({"vars": group, "k": rng.choice([1, 1, 2])})
    return {"name": name, "n_objective": n, "weights": weights, "demands": demands, "seed_constraints": seeds}


def optimum(inst: dict) -> int:
    """Exact optimum by depth-first search over one route per demand."""
    n = inst["n_objective"]
    w = inst["weights"]
    demands = [[tuple(r) for r in d] for d in inst["demands"]]
    seeds = [(tuple(s["vars"]), s["k"]) for s in inst["seed_constraints"]]
    ones = [0] * n
    best = [None]
    order = sorted(range(len(demands)), key=lambda j: len(demands[j]))

    def served(j: int) -> bool:
        return any(all(ones[v] for v in r) for r in demands[j])

    def seed_completion() -> int:
        add = 0
        for vs, k in seeds:  # seed groups are disjoint, so greedy per group is optimal
            have = sum(ones[v] for v in vs)
            if have < k:
                add += sum(sorted(w[v] for v in vs if not ones[v])[: k - have])
        return add

    def bound(idx: int) -> int:
        used: set[int] = set()
        total = 0
        for j in order[idx:]:
            if served(j):
                continue
            cand = {v for r in demands[j] for v in r if not ones[v]}
            if cand & used:
                continue
            used |= cand
            total += min(sum(w[v] for v in r if not ones[v]) for r in demands[j])
        return total

    def dfs(idx: int, cost: int) -> None:
        if best[0] is not None and cost + bound(idx) >= best[0]:
            return
        while idx < len(order) and served(order[idx]):
            idx += 1
        if idx == len(order):
            total = cost + seed_completion()
            if best[0] is None or total < best[0]:
                best[0] = total
            return
        j = order[idx]
        for r in sorted(demands[j], key=lambda r: sum(w[v] for v in r if not ones[v])):
            newly = [v for v in r if not ones[v]]
            for v in newly:
                ones[v] = 1
            dfs(idx + 1, cost + sum(w[v] for v in newly))
            for v in newly:
                ones[v] = 0

    dfs(0, 0)
    return int(best[0])


def main() -> None:
    rng = random.Random(TEST_SEED)
    instances = []
    for i in range(N_INSTANCES):
        inst = generate(rng, f"test_{i:03d}")
        inst["optimum"] = optimum(inst)
        instances.append(inst)
    OUT.write_text(json.dumps({"slice": "test", "instances": instances}) + "\n", encoding="utf-8")
    print(f"wrote {len(instances)} instances to {OUT}")


if __name__ == "__main__":
    main()
