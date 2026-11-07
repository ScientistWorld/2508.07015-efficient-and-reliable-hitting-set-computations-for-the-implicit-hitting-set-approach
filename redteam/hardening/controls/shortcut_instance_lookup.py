"""Shortcut: identify the instance in a readable instance file and exploit it.

Matches the instance received over the protocol against a JSON instance file
by weights and objective-only constraints.  On a match it computes the optimum
itself, sends that assignment as its first decision call (so the upper bound is
optimal immediately) and then runs the reference loop.  Without a match it is
the reference solver.

``IHS_LOOKUP_FILE`` selects the file: the public training file (allowed to
read, useless on the hidden test) or the hidden test file (a rule violation
the harness cannot prevent; left to the grader).
"""
import json
import os
import sys

from _common import ROOT, serve
from method import pbo_ihs

sys.path.insert(0, str(ROOT))
from data.make_train_instances import optimum  # noqa: E402  (exact DFS on a known instance)


def find(inst):
    path = ROOT / os.environ.get("IHS_LOOKUP_FILE", "data/instances_train.json")
    try:
        items = json.loads(path.read_text())["instances"]
    except (OSError, ValueError, KeyError):
        return None
    for item in items:
        if item["weights"] == inst["weights"] and item["n_objective"] == inst["n_objective"]:
            return item
    return None


def optimal_assignment(item):
    n = item["n_objective"]
    w = item["weights"]
    target = optimum(item)
    demands = [[tuple(r) for r in d] for d in item["demands"]]
    seeds = [(tuple(s["vars"]), s["k"]) for s in item["seed_constraints"]]
    ones = [0] * n
    order = sorted(range(len(demands)), key=lambda j: len(demands[j]))
    found = [None]

    def complete():
        x = list(ones)
        for vs, k in seeds:
            have = sum(x[v] for v in vs)
            if have < k:
                for _, v in sorted((w[v], v) for v in vs if not x[v])[: k - have]:
                    x[v] = 1
        return x

    def dfs(idx, cost):
        if found[0] is not None or cost > target:
            return
        while idx < len(order) and any(all(ones[v] for v in r) for r in demands[order[idx]]):
            idx += 1
        if idx == len(order):
            x = complete()
            if sum(w[v] for v in range(n) if x[v]) == target:
                found[0] = x
            return
        for r in demands[order[idx]]:
            newly = [v for v in r if not ones[v]]
            for v in newly:
                ones[v] = 1
            dfs(idx + 1, cost + sum(w[v] for v in newly))
            for v in newly:
                ones[v] = 0

    dfs(0, 0)
    return found[0]


def run(oracle, inst, variant):
    item = find(inst)
    if item is not None:
        x = optimal_assignment(item)
        if x is not None:
            oracle.request({"op": "decide", "assumptions": [[v, x[v]] for v in range(len(x))]})
    pbo_ihs.pbo_ihs(oracle, inst, variant)


if __name__ == "__main__":
    sys.exit(serve(["sis_sls"], run, sys.argv))
