#!/bin/bash
set -euo pipefail

cd /home/user

bash scripts/method.sh
bash scripts/evaluate.sh checkpoints/pbo_ihs_results.json
