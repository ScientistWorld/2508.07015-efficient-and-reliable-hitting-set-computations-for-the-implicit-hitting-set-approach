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

## Stop Justification
- Completed at milestone `core_claim`.
