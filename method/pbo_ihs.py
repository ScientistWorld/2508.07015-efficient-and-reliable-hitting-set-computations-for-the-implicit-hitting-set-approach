"""Reference PBO-IHS solver (scaled reproduction of Ihalainen et al., AAAI 2026).

The solver speaks the JSON-lines oracle protocol documented in
``briefing/evaluation.md``: it reads one ``instance`` message on stdin, then
alternates requests (``decide`` / ``hs_improve``) and responses until the
harness reports the instance certified, the budget is exhausted, or the solver
sends ``done``.  Logs go to stderr only.

Implemented procedure (paper, Section 2.2 and Algorithm 2):

* Algorithm 1 (PBO-IHS): an initial decision call gives the first upper bound;
  the hitting-set problem is seeded with the objective-only constraints; the
  loop alternates Solve-HS and Extract-Cores until lb = ub.
* Extract-Cores: decision calls under the hitting set as assumptions; each core
  is added and its literals are dropped from the assumptions (weight-aware core
  extraction) until the oracle returns a feasible assignment, which may improve
  the upper bound.
* Solve-HS (Algorithm 2) for variant ``sis``: Optimize by solution-improving
  search (SIS) -- repeated exact PB decision calls ``K and O < ub_c`` until the
  harness proves none exists, which certifies the lower bound (opt? = true).
* Solve-HS for variant ``sis_sls``: Core-SLS first (two phases: start from the
  previous hitting set, then from a heavily perturbed copy; prefer lower cost,
  ties to the second phase).  If Core-SLS finds a hitting set cheaper than the
  upper bound it is returned without changing the lower bound; otherwise SIS
  runs as above.

Usage:
    python -m method.pbo_ihs list           # prints the variant names (JSON)
    python -m method.pbo_ihs run sis_sls    # protocol session on stdin/stdout
"""

from __future__ import annotations

import json
import random
import sys

VARIANTS = ["sis", "sis_sls"]
SLS_FLIPS_PER_VAR = 80


class Stop(Exception):
    """Raised when the harness ends the session (certified, budget, error)."""


class OracleClient:
    def __init__(self, inp, out):
        self.inp = inp
        self.out = out

    def read(self) -> dict:
        line = self.inp.readline()
        if not line:
            raise Stop("eof")
        return json.loads(line)

    def request(self, payload: dict) -> dict:
        self.out.write(json.dumps(payload) + "\n")
        self.out.flush()
        resp = self.read()
        if "error" in resp:
            raise Stop(resp["error"])
        return resp

    def done(self) -> None:
        try:
            self.out.write(json.dumps({"op": "done"}) + "\n")
            self.out.flush()
        except (BrokenPipeError, OSError):
            pass


# ---------------------------------------------------------------------------
# Constraint helpers (general PB constraints: sum coeff * lit >= rhs)
# ---------------------------------------------------------------------------


def parse_constraint(payload: dict) -> tuple[list[tuple[int, int, int]], int]:
    terms = [(int(a), int(v), int(p)) for a, v, p in payload["terms"]]
    return terms, int(payload["rhs"])


def cost_of(weights: list[int], x: list[int]) -> int:
    return sum(w for w, xi in zip(weights, x) if xi)


# ---------------------------------------------------------------------------
# Core-SLS (incremental implementation of the reference scoring rule)
# ---------------------------------------------------------------------------


def core_sls(n: int, weights: list[int], cores: list, ub: int, seed: int, previous: list[int] | None,
             flips_per_var: int = SLS_FLIPS_PER_VAR):
    """Two-phase local search for a cheap assignment satisfying every core.

    Each flip minimises (change in total constraint violation, change in cost,
    random tie-break) over all variables.  The cheapest violation-free
    assignment with cost < ub seen in either phase is returned; ties go to the
    second (diversified) phase.  Returns (assignment, cost) or (None, None).
    """
    rng = random.Random(seed)
    start = list(previous) if previous is not None else [0] * n
    diversified = list(start)
    for idx in rng.sample(range(n), max(1, n // 2)):
        diversified[idx] = 1 - diversified[idx]

    occ: list[list[tuple[int, int, int]]] = [[] for _ in range(n)]  # (constraint, coeff, polarity)
    for ci, (terms, _) in enumerate(cores):
        for a, v, p in terms:
            occ[v].append((ci, a, p))
    rhs = [r for _, r in cores]

    def run(init: list[int]):
        x = list(init)
        val = [0] * len(cores)
        for ci, (terms, _) in enumerate(cores):
            val[ci] = sum(a * (x[v] if p else 1 - x[v]) for a, v, p in terms)
        score = [0] * n

        def contrib(v: int, ci: int, a: int, p: int) -> int:
            lit = x[v] if p else 1 - x[v]
            d = a * (1 - 2 * lit)
            return max(0, rhs[ci] - val[ci] - d) - max(0, rhs[ci] - val[ci])

        for v in range(n):
            score[v] = sum(contrib(v, ci, a, p) for ci, a, p in occ[v])
        gap = sum(max(0, rhs[ci] - val[ci]) for ci in range(len(cores)))
        cost = cost_of(weights, x)
        best = None
        best_cost = None
        for _ in range(flips_per_var * n):
            if gap == 0 and cost < ub and (best_cost is None or cost <= best_cost):
                best, best_cost = list(x), cost
            # argmin of (violation change, cost change), uniform among ties
            best_s = None
            best_dc = 0
            ties: list[int] = []
            for u in range(n):
                s = score[u]
                if best_s is not None and s > best_s:
                    continue
                dc = -weights[u] if x[u] else weights[u]
                if best_s is None or s < best_s or dc < best_dc:
                    best_s, best_dc, ties = s, dc, [u]
                elif dc == best_dc:
                    ties.append(u)
            v = ties[0] if len(ties) == 1 else ties[rng.randrange(len(ties))]
            gap += score[v]
            pairs = neighbours[v]
            for u, ci, a, p in pairs:
                score[u] -= contrib(u, ci, a, p)
            d = 1 - 2 * x[v]
            for ci, a, p in occ[v]:
                val[ci] += a * d * (1 if p else -1)
            x[v] += d
            cost += weights[v] * d
            for u, ci, a, p in pairs:
                score[u] += contrib(u, ci, a, p)
        return best, best_cost

    # (u, constraint, coeff, polarity) for every u sharing a constraint with v
    neighbours: list[list[tuple[int, int, int, int]]] = [[] for _ in range(n)]
    for v in range(n):
        seen = set()
        for ci, _, _ in occ[v]:
            if ci in seen:
                continue
            seen.add(ci)
            for a, u, p in cores[ci][0]:
                neighbours[v].append((u, ci, a, p))

    best, best_cost = None, None
    for init in (start, diversified):
        found, found_cost = run(init)
        if found is not None and (best_cost is None or found_cost <= best_cost):
            best, best_cost = found, found_cost
    return best, best_cost


# ---------------------------------------------------------------------------
# Solve-HS and PBO-IHS
# ---------------------------------------------------------------------------


def sis_optimize(oracle: OracleClient, ub: int, phase: list[int] | None):
    """Solution-improving search over the cores held by the harness.

    Returns (gamma, cost) of an optimal hitting set, or (None, ub) when no
    hitting set is cheaper than ub (the harness then has lb = ub).
    """
    bound = ub
    best = None
    while True:
        req = {"op": "hs_improve", "bound": bound}
        if phase is not None:
            req["phase"] = phase
        resp = oracle.request(req)
        if not resp["sat"]:
            return best, bound
        best = resp["assignment"]
        bound = resp["cost"]
        phase = best
        if resp.get("certified"):
            raise Stop("certified")


def solve_hs(variant: str, oracle: OracleClient, n: int, weights: list[int], cores: list, ub: int, seed: int,
             previous: list[int] | None):
    if variant == "sis_sls":
        gamma, cost = core_sls(n, weights, cores, ub, seed, previous)
        if gamma is not None:
            return gamma
    elif variant != "sis":
        raise ValueError(f"unknown variant {variant}")
    gamma, _ = sis_optimize(oracle, ub, previous)
    return gamma


def pbo_ihs(oracle: OracleClient, inst: dict, variant: str) -> None:
    n = int(inst["n_objective"])
    weights = [int(w) for w in inst["weights"]]
    seed = int(inst.get("seed", 1))
    cores = [parse_constraint(c) for c in inst["seed_constraints"]]

    resp = oracle.request({"op": "decide", "assumptions": []})
    if not resp["sat"]:
        return  # no feasible solutions
    ub = resp["ub"]
    previous = None
    iteration = 0
    while True:
        iteration += 1
        gamma = solve_hs(variant, oracle, n, weights, cores, ub, seed + iteration, previous)
        if gamma is None:
            return  # SIS proved lb = ub; the harness has certified the instance
        previous = list(gamma)
        assumptions = {v: gamma[v] for v in range(n)}
        while True:
            resp = oracle.request({"op": "decide", "assumptions": [[v, val] for v, val in assumptions.items()]})
            if resp.get("certified"):
                return
            if resp["sat"]:
                ub = resp["ub"]
                break
            core = parse_constraint(resp["core"])
            cores.append(core)
            for _, v, _ in core[0]:
                assumptions.pop(v, None)


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "list":
        print(json.dumps(VARIANTS))
        return 0
    if len(argv) >= 3 and argv[1] == "run":
        variant = argv[2]
        if variant not in VARIANTS:
            print(f"unknown variant {variant}", file=sys.stderr)
            return 2
        oracle = OracleClient(sys.stdin, sys.stdout)
        try:
            inst = oracle.read()
            pbo_ihs(oracle, inst, variant)
        except Stop:
            return 0
        oracle.done()
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
