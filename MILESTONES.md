# Reproduction Milestones

**Current: method_runs**

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
