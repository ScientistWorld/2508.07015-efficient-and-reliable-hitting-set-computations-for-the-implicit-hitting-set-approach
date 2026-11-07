"""Shortcut analogue of public-answer / erased-trace / empty-output submissions.

Does no oracle work and ends the session at once; there is no channel through
which a claimed optimum or certificate could be submitted.
"""
import sys

from _common import serve


def run(oracle, inst, variant):
    return


if __name__ == "__main__":
    sys.exit(serve(["sis_sls"], run, sys.argv))
