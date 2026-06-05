#!/bin/bash
set -euo pipefail

cd /home/user

python -m method.pbo_ihs --variant ip_exact --output checkpoints/ip_exact_results.json
bash scripts/evaluate.sh checkpoints/ip_exact_results.json
