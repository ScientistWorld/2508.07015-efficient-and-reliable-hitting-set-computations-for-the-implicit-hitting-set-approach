# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-06-05 07:57] - none
- Started reproduction work.
- Read the paper and identified PBO-IHS hitting-set optimization as the core method.

### [2026-06-05 08:05] - none
- Verified the official Zenodo and Bitbucket artifact locations.
- Implemented a scaled PBO-IHS environment; awaiting compute-node execution before claiming `method_runs`.

### [2026-06-05 08:07] - method_runs
- Ran the scaled PBO-IHS implementation locally on all tracked instances.
- `ip_exact`, `sis`, and `sis_sls` all executed end-to-end and wrote method artifacts.
- Independent evaluation and `python validate.py --compare` passed locally.

### [2026-06-05 08:09] - core_claim
- Compute job `e6cc7b5c-f1a` completed with exit code 0.
- The container run reproduced the scaled PBO-IHS experiment and passed `python validate.py --compare`.
- Exact SIS matched the exact hitting-set baseline on all tracked instances, and the SLS-integrated variant preserved exactness while reducing average exact HS calls from 5.0 to 1.333.
