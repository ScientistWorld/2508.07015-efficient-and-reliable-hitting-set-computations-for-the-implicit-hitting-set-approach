"""Weaker control: reference sis_sls without weight-aware core extraction.

Extract-Cores stops after the first core instead of relaxing the assumptions
and extracting further cores from the same hitting set.
"""
import sys

from _common import core_sls, ihs_loop, serve
from method.pbo_ihs import sis_optimize


def solve_hs(oracle, n, weights, cores, ub, seed, previous):
    gamma, _ = core_sls(n, weights, cores, ub, seed, previous)
    if gamma is not None:
        return gamma
    gamma, _ = sis_optimize(oracle, ub, previous)
    return gamma


if __name__ == "__main__":
    sys.exit(serve(["sis_sls_single_core"], lambda o, i, v: ihs_loop(o, i, solve_hs, extract="single"), sys.argv))
