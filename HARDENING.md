# Hardening report (iteration 11)

**Bottom line.** The previous hidden test scored the odd/even halves of a self-written trace on three public instances. It could not be patched: every major shortcut in `REDTEAM.md` came from that design. The test was rebuilt around an evaluator-owned oracle harness and held-out instances. On the rebuilt test:

- A genuinely better variant beats the reference on every seed, by more than twice the reference's own seed spread.
- The no-local-search baseline scores clearly below the reference.
- Every major shortcut from `REDTEAM.md` now scores at or below the reference.
- One major shortcut remains open: private exact hitting-set optimisation inside the solver process (+0.19). The evaluator cannot observe it without timing the solver; it is stated as a rule in `scoring/CONSTRAINTS.md` and left to the grader.

All numbers below are from completed jobs. They come from the final code (job `b65b5596-ec9`, 160 hidden test instances) unless marked v1, which is job `a6a23462-ef2`: first harness version, first 80 test instances. Evidence: `redteam/hardening/results/` (final), `redteam/hardening/results_v1_80inst/` (v1), and the summaries in `results*/summary.json`.

## What the test is now

- **Held-out inputs.** The hidden test runs the solver (`scripts/solver.sh`, discovered via `list`, no method name hard-coded) on 160 generated instances that exist only in `eval/test/`. They come from the same generator and distribution as the 80 public training instances (`data/`), but with a private 128-bit seed, so they cannot be regenerated from public code. Regenerating both instance files reproduces the committed bytes (`results/instances_check.txt`).
- **Counted oracles instead of a trace.** A solver receives the objective and the objective-only constraints. The rest of each instance is reachable only through two oracles that the harness answers and counts:
  - `decide`: a decision oracle over the full instance under assumptions, returning a feasible assignment or a core.
  - `hs_improve`: an exact PB decision procedure over the seed constraints plus every core the harness has returned.

  This mirrors the paper's architecture: PBO-IHS reaches its PB solver (RoundingSat) through both of these calls.
- **The evaluator recomputes everything.** Upper bounds are the harness's own feasible answers; lower bounds are its own unsatisfiability proofs; call counts are its own. A solver has no channel to submit answers, bounds, certificates, counts or files that the evaluator reads. Unknown messages end the session unsolved.
- **The other side of the comparison is fixed by `eval/`.** That covers instances, ground-truth optima (checked against an independent exhaustive search at generation time and asserted at scoring time), budgets (solved means certified within 180 calls; hard cap 720), per-instance seeds, the safety limits, and the test size. The reference row for ranking is fixed in `scoring/scores_test.json`.
- **Failure scores as failure.** An uncertified instance counts as unsolved and is charged the full cap (call ratio 4). A run that certifies nothing scores the worst possible value on both ranked metrics, so efficiency credit cannot survive task failure.
- **Determinism.** The harness is deterministic. Its two safety limits are:
  - a 300 s guard on solver-side time per instance; harness oracle time is excluded;
  - deterministic search-node caps on the exact oracle, 2M per call and 20M per instance, more than 10× the hardest reference session.

  The baseline `sis` gives identical scores on every seed offset.
- **Train and test are independent.** `eval/train/harness.py` and `eval/test/harness.py` are separate copies with no shared imports. `eval/` never imports `method/`.

### Reference method (rerun from the final code)

`method/pbo_ihs.py` re-implements the reproduced algorithm on the new interface: PBO-IHS (Algorithm 1) with Solve-HS from Algorithm 2.

- `sis` (baseline): solution-improving search to optimality in every iteration.
- `sis_sls` (proposed): Core-SLS first, with SIS as the fallback. The SLS keeps the earlier reference's scoring rule and parameters: two phases, (violation change, cost change, random tie) moves, 80·n flips per phase.

Extract-Cores now uses weight-aware core extraction as the paper describes it (Section 2.2). The earlier reference used deletion-based minimisation of a single core, which the paper does not describe. The paper's training method was not changed. The setup was scaled to generated network-activation instances and an oracle-call budget in place of 1786 PB-competition instances and wall-clock time.

## Do better results score higher?

Rank Δ = Σ coefficient × (value − reference value), with the coefficients in `scoring/reference.json` and the reference = the proposed `sis_sls` row of `scoring/scores_test.json`.

| Control | Before (old gym, ΔU on old scale) | After (160 hidden instances, rank Δ) |
|---|---:|---:|
| Reference `sis_sls`, seed offsets 0 / 1 / 2 | 0 / 0 / 0 | **0 / +0.015 / +0.026** (spread 0.026) |
| Better: Algorithm 2 with `opt?` = false (stop at the first improving exact hitting set) | old "better" was single-pass core minimisation: +0.500 | **+0.060 / +0.067 / +0.053** |
| Weaker: remove SLS (`sis` row, every run) | −1.343 | **−0.620** (identical on all seeds) |
| Weaker: Extract-Cores without weight-aware extraction (v1, 80 instances) | — | −0.095 (v1; 3 sessions hit the old 120 s wall guard) |

- **The better variant clears seed noise.** Its worst seed (+0.053) is twice the reference's whole seed spread (0.026).
- **Paired per instance**, it saves about 6 calls on average and is cheaper on 114 and 110 of the 160 instances (seed offsets 1 and 2).
- **Sensitivity was a real problem at 80 instances.** In v1 the reference spread was 0.066 against a mean gain of +0.076. Doubling the test to 160 instances (the first 80 unchanged) fixed it.

The old "better" control, single-pass deletion minimisation, has no counterpart: the reference no longer minimises cores.

| Final metrics (hidden test) | certified_solve_rate | mean_call_ratio | mean decide calls | mean exact HS calls |
|---|---:|---:|---:|---:|
| `sis` (baseline) | 0.2500 | 1.6138 | 126.3 | 164.2 |
| `sis_sls` (reference) | **0.6813** | **0.8592** | 137.6 | 17.1 |
| better `opt?` = false, offset 0 | 0.7312 | 0.8207 | — | — |

## Major shortcuts: fix and score before/after

"Before" is the proposed-variant ΔU from `REDTEAM.md` (old scale). "After" is the rank Δ on the final hidden test.

| Shortcut (REDTEAM.md) | Fix | Before | After |
|---|---|---:|---:|
| Public answers (enumerate public instances, assert final bounds) | Test instances are held out and their constraints are never sent. There is no answer or bound channel; only the harness's own oracle log certifies. Re-expressed as `shortcut_immediate_done` (no oracle work) and `shortcut_public_train_lookup` (identifies public training instances and exploits them). | +1.224 | −1.466 (immediate done). Train lookup: 0.000 on test (v1), +0.025 solve rate on train only. |
| Erased trace (keep answers, delete events) | No trace exists; certification needs the harness's own feasible answer and exact proof. `shortcut_immediate_done`. | +1.224 | −1.466 |
| Extraction under-report (self-reported `extraction_calls`) | Every call is counted by the harness; solver numbers are never read. `shortcut_forged_report` sends a self-reported certificate with zero work. | +1.833 | −1.466 |
| Summary forgery (impossible summary values) | Solver-written values are never read. Forged `scores_*.json` written by the solver are overwritten by the evaluator; unknown messages are protocol errors. | 0 (tie) | −1.466 |
| Repeated SLS events (unbounded SLS-success reward) | No SLS or work reward exists; repeating locally valid calls only burns budget. `shortcut_spam_decide`. | +11.824 | −1.466 |
| Failing repeated SLS (efficiency credit despite failure) | An uncertified instance is unsolved and charged the full cap. `shortcut_spam_decide`. | +8.324 | −1.466 |
| Fixed-data replacement (ground truth follows `data/`) | The test reads only `eval/test/`; `data/` affects training feedback only. `shortcut_data_replace` replaces every training instance with a trivial one. | +1.124 (sum +6.057) | 0.000 |
| Baseline degradation | The rank compares each row with the fixed reference row; degrading a comparison row cannot raise the proposed row. | 0 / −0.933 (sum) | 0.000 (`sis` row −1.466) |
| Empty output / constant ones (failed before) | — | −2.276 / −0.776 | −1.466 (immediate done) |

The re-expressed shortcuts were run through the unchanged `bash scripts/evaluate_test.sh` with no arguments (`redteam/hardening/run_controls.sh`). One staging artifact affected these runs: a node preemption during the baseline-degradation case left its solver staged, so the final data-replacement run used it. As a result that run's `sis` row is zeroed. Its ranked `sis_sls` row is the reference code and matches the reference exactly. In v1, without the artifact, both rows matched exactly. The runner now keeps the originals across restarts.

## Shortcuts left open

| Shortcut | Score (final hidden test) | Why left |
|---|---:|---|
| **Private exact hitting-set optimisation**: solve each hitting-set problem to optimality inside the solver with a private exact search, present the result as a heuristic hitting set, and call `hs_improve` only once to certify (`controls/shortcut_private_exact_hs.py`) | **+0.191** (solve 0.838, call ratio 0.719, exact-call share 0.008) | The harness sees only the oracle calls, not computation inside the solver process. Measuring that computation would require timing the solver, which is forbidden for scored metrics. Hiding the cores would remove the local-search research direction the paper points to. `scoring/CONSTRAINTS.md` rule 2 forbids private complete search over the cores. A grader can detect it by code inspection: branch and bound, enumeration, or an ILP/MaxSAT/PB/CP solver applied to the cores. |
| Reading `eval/test/` from solver code (`shortcut_instance_lookup.py` with the hidden file) | +0.008 for the naive version that only fixes the upper bound early. A smarter version could do much more. | The solver runs in the same container as the evaluator, and file access cannot be prevented without a sandbox. CONSTRAINTS rule 1; left to the grader. |
| Exploiting the instance family (monotone constraints, ring locality of routes) through the protocol | not measured | This is legitimate use of the public training distribution; the protocol still bounds what can be learned per call. |

## Reference score before/after

- **Before:** U = 2.276 (old metric set, three public instances). Every correctness metric sat at its bound.
- **After:** `sis_sls` certified_solve_rate 0.6813 and mean_call_ratio 0.8592 on 160 hidden instances; `sis` 0.2500 and 1.6138. On train the same solver gets 0.6875 / 0.8105 (`sis` 0.2625 / 1.5047), so the honest method scores alike on train and test.
- **Paper's direction:** SLS-integrated SIS certifies far more instances than plain SIS (paper, Table 2: SIS +13 solved with SLS). It cuts exact hitting-set calls from 164 to 17 per instance and uses only 9% more decision calls.

## Headroom check

- **No ranked metric is at its bound for the reference.** The solve rate is 0.68 (bound 1) and the call ratio 0.86 (bound 0).
- **The old saturated metrics were removed.** These were solved_count, optimality_match_rate, certificate_accept_rate and selected_trace_accept_rate, all 1 for every method. Correctness is now the constraint inside the solve rate (certification) rather than a separate saturated metric.
- **A variant scores above the reference.** The `opt?` = false variant beats it on every seed. The private-exact shortcut shows how much an information-equivalent but better hitting-set strategy is worth (0.84 solve rate).
- **Remaining headroom is large.** Any solver needs at least one exact call per instance plus the decision calls that produce the needed cores, against the reference's ~155 calls per instance.
- **No extra experiment was needed.** The reference does not sit at the bound of any ranked metric.

## Weights and coefficients

There is one experiment, weight 1.0.

- `certified_solve_rate`: coefficient +1.0. This is the paper's main quantity: instances solved within the resource limit, where solved must mean certified.
- `mean_call_ratio`: coefficient −0.25. This is the paper's explanatory efficiency measure: its hybrids "require the fewest RoundingSat calls". It is continuous and its seed spread is small (0.009 on the reference), so it sharpens comparisons. Its small coefficient keeps the solve rate dominant: halving the reference's calls on every instance is worth about 0.11, i.e. 17 instances' worth of solve rate.
- `mean_decide_calls`, `mean_hs_calls`, `hs_call_share`: coefficient 0, diagnostics only.

`scoring/reference.json` `results` now hold the paper's reported fractions (SIS 672/1786 = 0.376; SIS+SLS 685/1786 = 0.384), with a scaling note and the paper's other Table 1/2 numbers. The previous file held gym values under the old metric names, none of which exist any more.

## Could not fix / caveats

- **Private exact hitting-set optimisation stays open** (+0.19, above). It is the largest remaining exploit and pays more than the legitimate improvement found.
- **`python validate.py` passes; `python validate.py --post-design` does not.** It flags train `sis_sls` 0.6875 against the paper's 0.3835 (absolute gap 0.304, threshold 0.30; the test value 0.681 is just inside). The paper's value is a fraction of 1786 competition instances solved in 1 h; the gym's is a fraction of generated instances certified within 180 calls. They are not comparable, and moving the budget to match the paper would be calibrating to the paper's number. Left as is.
- **Not modelled at this scale:** IP-based hitting sets (Gurobi/SCIP, floating-point errors), proof logging overhead, and the core-guided / core-boosted optimisers. The reproduced claim is the SIS vs SIS+SLS comparison inside certified PBO-IHS.
- **Instance family.** It is a single synthetic family (monotone network activation, 24–52 objective variables). Within that family, monotonicity makes the decision oracle exact and cheap in pure Python.
- **Weaker control evidence.** The weight-aware-extraction ablation was only run under v1 (80 instances, old wall guard hit on 3 sessions). The "initial solution only" control has no direct analogue, because no answer can be submitted without certification.
- **Old audit scripts.** The old `redteam/*` audit scripts target the removed trace evaluator and no longer run. They are kept as the record behind `REDTEAM.md`.

## Reproduce

- `bash scripts/run.sh`: regenerates and checks the instance files, scores the reference on train and hidden test, and validates (~45 min, one CPU).
- `bash redteam/hardening/run_controls.sh`: reruns every control and shortcut through the unchanged hidden test (resumable, ~3.5 h), then `python3 redteam/hardening/summarize.py results`.
