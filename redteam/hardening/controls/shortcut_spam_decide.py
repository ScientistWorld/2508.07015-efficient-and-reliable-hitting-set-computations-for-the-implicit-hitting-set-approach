"""Shortcut analogue of the repeated-SLS exploit: repeat a locally valid call.

Calls the decision oracle on the empty assumption set over and over (always
feasible, never informative) and never learns a core.
"""
import sys

from _common import serve


def run(oracle, inst, variant):
    for _ in range(100000):
        oracle.request({"op": "decide", "assumptions": []})


if __name__ == "__main__":
    sys.exit(serve(["sis_sls"], run, sys.argv))
