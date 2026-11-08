# Progress

## Current state (iteration 11)

- **Gym.** Certified PBO-IHS under an oracle-call budget. Solvers talk to evaluator-owned oracles over a JSON-lines protocol (`briefing/evaluation.md`). The hidden test is 160 held-out generated instances in `eval/test/`; training is 80 public instances in `data/`.
- **Reference.** `method/pbo_ihs.py` implements PBO-IHS (paper Algorithm 1) with weight-aware core extraction and Solve-HS from Algorithm 2. Variant `sis` runs SIS to optimality; variant `sis_sls` runs Core-SLS with SIS fallback.
- **Reference scores.** On the hidden test (`scoring/scores_test.json`): `sis_sls` 0.6813 certified within 180 calls, mean call ratio 0.8592; `sis` 0.2500 / 1.6138. On train (`scoring/scores_train.json`): 0.6875 / 0.8105 and 0.2625 / 1.5047.
- **Hardening evidence.** `HARDENING.md` and `redteam/hardening/`.

## Deviations from the paper

- The paper uses 1786 PB-competition instances with Gurobi, SCIP, RoundingSat and VeriPB under a 1 h limit. The gym uses generated network-activation instances (24–52 objective variables), a pure-Python harness standing in for the PB solver, and an oracle-call budget in place of time.
- IP-based hitting sets, core-guided and core-boosted optimisers, and proof logging overhead are not modelled. The reproduced claim is SIS vs SIS+SLS inside certified PBO-IHS.

## Open issues

- **Private exact hitting-set optimisation** inside a solver cannot be observed by the evaluator (+0.19 when used). It is forbidden by `scoring/CONSTRAINTS.md` and left to the shortcut grader.
- **`validate.py --post-design`** flags train `sis_sls` (0.6875) against the paper's fraction of competition instances (0.3835). These numbers are not comparable; see `HARDENING.md`.
