# Progress

## What Works

- Read the paper and identified the central algorithm: PBO-IHS with alternative hitting-set optimizers.
- Verified the official Zenodo artifact URLs and downloaded `Results.zip` and `Solver.zip` into `data/downloads/`.
- Implemented a scaled, pure-Python PBO-IHS reproduction with exact IP-style HS, PB-style SIS HS, and SLS+SIS variants.
- Added independent evaluation that does not import `method/`.
- Audited the evaluator and tightened it so every tracked instance is scored for each variant; missing artifacts now count as failures.

## Results Achieved

Local smoke-test results:

- `ip_exact`: solved 3/3, optimality match 1.0, certificate accept 1.0.
- `sis`: solved 3/3, optimality match 1.0, certificate accept 1.0.
- `sis_sls`: solved 3/3, optimality match 1.0, certificate accept 1.0, with fewer exact HS calls than the exact-only variants.

Compute job `e6cc7b5c-f1a` completed successfully after 25.1 seconds with exit code 0.

Compute-node results:

- `ip_exact`: solved 3/3, optimality match 1.0, certificate accept 1.0, average exact HS calls 5.0.
- `sis`: solved 3/3, optimality match 1.0, certificate accept 1.0, average exact HS calls 5.0.
- `sis_sls`: solved 3/3, optimality match 1.0, certificate accept 1.0, average exact HS calls 1.333.

This supports the scaled core claim: exact PB-style hitting-set optimization inside PBO-IHS produces the same optimal answers as the exact baseline, and local-search integration can reduce expensive exact HS calls without losing independently checked exactness.

Iteration 3 audit: `python validate.py --compare` still passes, and the official Zenodo downloads in `scripts/download.sh` were rechecked with HTTP 200 responses on 2026-06-05.

Continuation audit fix: the method artifact now includes per-iteration IHS traces. The evaluator no longer trusts summary counters alone; it independently verifies exact hitting-set optima for lower-bound updates, learned-core implication/falsification, SLS shortcut validity, and final certificate fields from the trace. `bash scripts/reproduce.sh && python validate.py --compare` passes after this hardening.

Compute job `f0c9a696-205` completed successfully with exit code 0 after the trace hardening. It ran `scripts/run.sh`, regenerated `checkpoints/pbo_ihs_results.json`, wrote `scoring/scores.json`, and passed `python validate.py --compare` inside the managed Apptainer environment.

Trace-validated compute-node results:

- `ip_exact`: solved 3/3, optimality match 1.0, certificate accept 1.0, average exact HS calls 5.0.
- `sis`: solved 3/3, optimality match 1.0, certificate accept 1.0, average exact HS calls 5.0.
- `sis_sls`: solved 3/3, optimality match 1.0, certificate accept 1.0, average exact HS calls 1.333, SLS successes 13.

## Deviations From Paper

The paper evaluates 1786 public PBO benchmark instances using native PB/IP solvers, Gurobi, SCIP, Roundingsat, and VeriPB. This first reproduction uses small tracked PBO instances and pure-Python exact decision procedures so the environment is runnable without commercial solvers or large native builds.

The method is scaled down, not replaced: it still alternates between hitting-set optimization, decision-oracle calls under assumptions, core extraction over objective literals, and lower/upper-bound termination.

`scoring/reference.json` defines the scaled gym target used by the reusable evaluator. The full paper reported results are documented from the paper as: Gurobi 951 solved, SCIP 913, Exact SCIP 762, Core Guided 687, SIS Reified 651, SIS 672, SIS+CB 716 in Table 1; with SLS, the solved-instance gains in Table 2 are +17, +4, +44, +41, +10, +13, and +19 respectively.

## What Remains For Higher Milestones

- Add a native PBHS build path from `data/downloads/Solver.zip`.
- Add more generated or public `.opb` instances if budget remains after the first job.

## Issues Encountered

- The official solver stack depends on several native and optional commercial components. A pure-Python scaled implementation was used for the first reusable gym milestone.
- Audit found that the first evaluator averaged only over rows present in an artifact. This has been fixed so partial submissions are penalized.
- Continuation audit found that exact-HS call counts and certificate fields were self-reported. This has been fixed by trace validation in `eval/evaluate_pbo_ihs.py`.
