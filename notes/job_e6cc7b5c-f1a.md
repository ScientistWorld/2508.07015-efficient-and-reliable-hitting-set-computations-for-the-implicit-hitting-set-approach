# Job e6cc7b5c-f1a

Status: completed successfully, exit code 0.

The job ran `scripts/run.sh` inside the compute container with 0 GPUs and 1 CPU. It executed `scripts/reproduce.sh`, wrote `scoring/scores.json`, and then passed `python validate.py --compare`.

Key reproduced metrics:

- `ip_exact`: solved 3/3, optimality match 1.0, certificate accept 1.0, average exact HS calls 5.0.
- `sis`: solved 3/3, optimality match 1.0, certificate accept 1.0, average exact HS calls 5.0.
- `sis_sls`: solved 3/3, optimality match 1.0, certificate accept 1.0, average exact HS calls 1.333.

Conclusion: the packaged scaled PBO-IHS environment reaches `core_claim`.
