"""Shared helpers for hardening control solvers (not part of the gym)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from method.pbo_ihs import OracleClient, Stop, core_sls, parse_constraint  # noqa: E402,F401


def serve(variants, run_fn, argv):
    """Minimal `list` / `run <variant>` entry point for a control solver."""
    if len(argv) >= 2 and argv[1] == "list":
        print(json.dumps(variants))
        return 0
    if len(argv) >= 3 and argv[1] == "run" and argv[2] in variants:
        oracle = OracleClient(sys.stdin, sys.stdout)
        try:
            inst = oracle.read()
            run_fn(oracle, inst, argv[2])
        except Stop:
            return 0
        oracle.done()
        return 0
    return 2


def ihs_loop(oracle, inst, solve_hs, extract="wce"):
    """PBO-IHS loop (Algorithm 1) with a pluggable Solve-HS."""
    n = int(inst["n_objective"])
    weights = [int(w) for w in inst["weights"]]
    seed = int(inst.get("seed", 1))
    cores = [parse_constraint(c) for c in inst["seed_constraints"]]
    resp = oracle.request({"op": "decide", "assumptions": []})
    if not resp["sat"]:
        return
    ub = resp["ub"]
    previous = None
    iteration = 0
    while True:
        iteration += 1
        gamma = solve_hs(oracle, n, weights, cores, ub, seed + iteration, previous)
        if gamma is None:
            return
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
            if extract == "single":
                break
            for _, v, _ in core[0]:
                assumptions.pop(v, None)
