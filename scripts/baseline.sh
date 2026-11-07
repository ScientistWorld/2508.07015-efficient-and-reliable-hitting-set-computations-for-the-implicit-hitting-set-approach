#!/bin/bash
# The baseline (`sis`: exact hitting sets by solution-improving search, no
# local search) is one of the variants the reference solver lists, so the
# standard evaluation scores it alongside the proposed `sis_sls` variant.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/evaluate_train.sh
