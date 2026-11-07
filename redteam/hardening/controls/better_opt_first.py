"""Better control: Algorithm 2 with opt? = false.

Core-SLS first; when it fails, Optimize stops at the first hitting set cheaper
than ub found by the exact PB oracle instead of running SIS to optimality.
Proving that no cheaper hitting set exists still certifies lb = ub.
"""
import sys

from _common import core_sls, ihs_loop, serve


def solve_hs(oracle, n, weights, cores, ub, seed, previous):
    gamma, _ = core_sls(n, weights, cores, ub, seed, previous)
    if gamma is not None:
        return gamma
    req = {"op": "hs_improve", "bound": ub}
    if previous is not None:
        req["phase"] = previous
    resp = oracle.request(req)
    return resp["assignment"] if resp["sat"] else None


if __name__ == "__main__":
    sys.exit(serve(["sis_sls_optfirst"], lambda o, i, v: ihs_loop(o, i, solve_hs), sys.argv))
