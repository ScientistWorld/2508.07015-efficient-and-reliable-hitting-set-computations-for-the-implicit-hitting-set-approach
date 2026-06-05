# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-05 08:09] - method_runs
- Implemented a scaled PBO-IHS solver with exact hitting-set optimization, PB-style solution-improving search, and SLS-assisted hitting-set search.
- Added tracked pseudo-Boolean benchmark instances and an independent evaluator.

### [2026-06-05 08:10] - core_claim
- Compute job `e6cc7b5c-f1a` ran `scripts/reproduce.sh` successfully.
- All three variants solved 3/3 tracked instances and matched independently enumerated optima.
- The SLS-assisted variant preserved exact final optimality while reducing exact hitting-set optimizer calls from 5.0 to 1.333 on average.

### [2026-06-05 08:16] - core_claim
- Audited the existing method, evaluator, scripts, scoring, and documentation after milestone reset.
- Confirmed `python validate.py --compare` passes.
- Verified the official Zenodo artifact URLs used by `scripts/download.sh` return HTTP 200 and match the downloaded file sizes.

### [2026-06-05 08:22] - method_runs
- Performed a continuation audit from the reset `method_runs` state.
- Found and fixed weak evaluation of self-reported algorithm metadata by adding method trace output and independent trace validation.
- Reran `bash scripts/reproduce.sh && python validate.py --compare` locally; all scored variants still solve 3/3 instances with independently validated certificates.
- Submitting a CPU validation job before restoring `core_claim` for the hardened evaluator.

### [2026-06-05 08:25] - core_claim
- Compute job `f0c9a696-205` ran `scripts/run.sh` successfully with exit code 0.
- The hardened evaluator accepted the trace-validated certificates for all three variants.
- `sis_sls` preserved 3/3 optimality and certificate acceptance while reducing average exact hitting-set calls from 5.0 to 1.333.

## Stop Justification
- Completed at milestone `core_claim` with compute-node validation of the hardened trace evaluator.
