# Problem

The task is pseudo-Boolean optimization: find a Boolean assignment satisfying a set of pseudo-Boolean linear constraints while minimizing a positive weighted sum over objective variables.

The benchmark instances in this environment are small tracked PBO instances with objective variables, auxiliary variables, and feasibility constraints. A solver must output a feasible full assignment and its objective value.

Success is measured by independently checking feasibility and objective optimality against exhaustive search over the tracked instances.
