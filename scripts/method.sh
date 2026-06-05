#!/bin/bash
set -euo pipefail

cd /home/user

python -m method.pbo_ihs \
  --variant ip_exact \
  --variant sis \
  --variant sis_sls \
  --output checkpoints/pbo_ihs_results.json
