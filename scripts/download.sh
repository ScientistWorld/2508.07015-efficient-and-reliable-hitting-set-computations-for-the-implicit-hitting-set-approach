#!/bin/bash
# Download all external artifacts used for documentation and optional native runs.
#
# Estimated total download size: 224 MB
# Estimated disk usage after extraction: 650 MB

set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p data/downloads

if [ ! -e data/downloads/Results.zip ]; then
  curl -L --fail --retry 3 \
    -o data/downloads/Results.zip \
    https://zenodo.org/api/records/17600095/files/Results.zip/content
fi

if [ ! -e data/downloads/Solver.zip ]; then
  curl -L --fail --retry 3 \
    -o data/downloads/Solver.zip \
    https://zenodo.org/api/records/17600095/files/Solver.zip/content
fi
