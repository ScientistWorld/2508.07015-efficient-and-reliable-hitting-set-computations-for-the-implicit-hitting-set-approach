# Experiments

## certified_ihs_under_budget (weight 1.0)

**What it establishes.** Can a solver prove optimality, not just find good solutions, on unseen pseudo-Boolean instances while spending few calls to the expensive reasoning components? The paper's claim has two sides, and the experiment measures both:

- **Benefit:** more instances solved within a resource limit, with fewer oracle calls per certified answer (`certified_solve_rate`, `mean_call_ratio`).
- **Constraint (reliability):** an answer counts only if it is certified. The evaluator holds the instances and builds the certificate itself, from its own decision-oracle answers (the upper bound) and its own exact proofs over the collected cores (the lower bound). An uncertified or wrong claim earns nothing and is charged the full call cap.

**Inputs.** 160 held-out generated instances in `eval/test/`, from the same distribution as the 80 public training instances. Every variant a solver lists sees the same instances and the same seeds (paired comparison).

**Reference behaviour.** The reference method's proposed variant certifies about two thirds of the instances within the solve budget. The baseline variant without local search certifies far fewer and needs about twice the oracle calls. There is headroom above the reference on both ranked metrics. The exact values are in `scoring/scores_test.json`, and `HARDENING.md` shows a variant that beats them.

**Diagnostics (not ranked).** Mean decision-oracle calls, mean exact hitting-set oracle calls, and the exact-call share show where a solver spends its budget.
