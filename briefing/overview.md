# Overview

The paper proposes more reliable ways to compute hitting sets inside implicit hitting set solvers for pseudo-Boolean optimization. It compares standard IP-based hitting-set optimization with exact PB reasoning, hybrid verification schedules, and stochastic local search.

This reproduction packages a scaled PBO-IHS gym. It implements the actual IHS loop and several hitting-set optimizer variants, then evaluates whether the methods solve nontrivial PBO instances while maintaining independently checkable optimality bounds.
