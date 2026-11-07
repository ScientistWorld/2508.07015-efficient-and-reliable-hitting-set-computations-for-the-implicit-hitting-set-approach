"""Shortcut: degrade the comparison row while leaving the proposed row unchanged."""
import sys

from _common import serve
from method import pbo_ihs


def run(oracle, inst, variant):
    if variant == "sis":
        return  # baseline row gives up immediately
    pbo_ihs.pbo_ihs(oracle, inst, variant)


if __name__ == "__main__":
    sys.exit(serve(["sis", "sis_sls"], run, sys.argv))
