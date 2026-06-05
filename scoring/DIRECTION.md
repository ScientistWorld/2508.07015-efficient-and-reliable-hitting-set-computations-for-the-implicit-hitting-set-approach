# Research Direction

Work within the implicit hitting set approach for pseudo-Boolean optimization.

Allowed directions include better exact PB-style hitting-set optimizers, stronger local-search repair/diversification before exact optimization, improved core extraction heuristics, and hybrid schedules that reduce exact hitting-set calls while preserving exact final optimality.

Do not replace PBO-IHS with a direct end-to-end optimizer that ignores the core extraction and hitting-set loop. Such a solver may solve the small instances, but it does not test the paper's contribution.
