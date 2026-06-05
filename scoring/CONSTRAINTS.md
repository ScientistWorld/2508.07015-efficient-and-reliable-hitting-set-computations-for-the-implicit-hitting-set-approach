# Constraints

Future methods must use the tracked PBO instances from `data/pbo_instances.py` and write artifacts in the same JSON format as `method/pbo_ihs.py`, including per-instance IHS trace events.

Evaluation code must remain independent of `method/`. It may import `data/` but must not import solver internals.

A valid improvement cannot change the benchmark instances, objective weights, or feasibility constraints. It may change the hitting-set optimizer strategy inside the IHS loop.

The reported certificate fields must correspond to the actual run: lower bound, upper bound, core count, exact hitting-set call count, SLS successes, and trace length. The evaluator recomputes these from trace events, so copying reference values into artifacts is invalid.
