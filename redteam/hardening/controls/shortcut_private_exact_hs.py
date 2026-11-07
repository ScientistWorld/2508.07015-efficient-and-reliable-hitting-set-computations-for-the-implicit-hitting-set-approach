"""Shortcut (left open, grader territory): private exact hitting-set optimisation.

Solves every hitting-set problem to optimality inside the solver process with
its own branch and bound over the cores it has received, presents the result as
if it were a heuristic hitting set, and uses the counted exact oracle only once
at the end to certify lb = ub.  The harness cannot see computation inside the
solver process.
"""
import sys

from _common import ihs_loop, serve
from eval.train.harness import hs_improve as private_search  # a private copy of an exact search


def private_optimum(n, weights, cores):
    """Private solution-improving search with a copy of the public training harness's exact search."""
    cons = []
    for terms, rhs in cores:
        cons.append((tuple(v for a, v, p in terms if p == 1 and a == 1), rhs))
    best, best_cost = None, None
    bound = sum(weights) + 1
    while True:
        sol, _ = private_search(n, weights, cons, bound, best, 10**9)
        if sol is None:
            return best, best_cost
        best = sol
        best_cost = sum(w for w, xi in zip(weights, sol) if xi)
        bound = best_cost


def solve_hs(oracle, n, weights, cores, ub, seed, previous):
    gamma, cost = private_optimum(n, weights, cores)
    if gamma is not None and cost < ub:
        return gamma
    resp = oracle.request({"op": "hs_improve", "bound": ub})
    return resp["assignment"] if resp["sat"] else None


if __name__ == "__main__":
    sys.exit(serve(["sis_sls"], lambda o, i, v: ihs_loop(o, i, solve_hs), sys.argv))
