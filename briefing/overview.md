# Overview

The paper studies more reliable and efficient ways to compute hitting sets inside implicit hitting set (IHS) solvers for pseudo-Boolean optimisation. It compares IP-based hitting-set optimisation with exact pseudo-Boolean reasoning, local search, hybrid schedules, and certificates of optimality.

This gym poses the problem behind that work at small scale: certify the optimum of held-out pseudo-Boolean instances whose constraints are reachable only through counted oracles, within a budget of oracle calls. The reference solver is the paper's PBO-IHS loop with solution-improving search (`sis`) and with local search integrated into the hitting-set step (`sis_sls`).
