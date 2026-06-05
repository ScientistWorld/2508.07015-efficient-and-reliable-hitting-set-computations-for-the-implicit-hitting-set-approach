# Progress

## What Works

- Read the paper and identified the central algorithm: PBO-IHS with alternative hitting-set optimizers.
- Verified the official Zenodo artifact URLs and downloaded `Results.zip` and `Solver.zip` into `data/downloads/`.
- Implemented a scaled, pure-Python PBO-IHS reproduction with exact IP-style HS, PB-style SIS HS, and SLS+SIS variants.
- Added independent evaluation that does not import `method/`.

## Results Achieved

Local smoke-test results:

- `ip_exact`: solved 3/3, optimality match 1.0, certificate accept 1.0.
- `sis`: solved 3/3, optimality match 1.0, certificate accept 1.0.
- `sis_sls`: solved 3/3, optimality match 1.0, certificate accept 1.0, with fewer exact HS calls than the exact-only variants.

No compute-node job has completed yet in this turn. The next submitted CPU job runs `scripts/reproduce.sh` and `python validate.py --compare`.

## Deviations From Paper

The paper evaluates 1786 public PBO benchmark instances using native PB/IP solvers, Gurobi, SCIP, Roundingsat, and VeriPB. This first reproduction uses small tracked PBO instances and pure-Python exact decision procedures so the environment is runnable without commercial solvers or large native builds.

The method is scaled down, not replaced: it still alternates between hitting-set optimization, decision-oracle calls under assumptions, core extraction over objective literals, and lower/upper-bound termination.

## What Remains

- Run the packaged job and inspect `scoring/scores.json`.
- If the scaled benchmark passes, consider adding a native PBHS build path from `data/downloads/Solver.zip`.
- Add more generated or public `.opb` instances if budget remains after the first job.

## Issues Encountered

- The official solver stack depends on several native and optional commercial components. A pure-Python scaled implementation was used for the first reusable gym milestone.
