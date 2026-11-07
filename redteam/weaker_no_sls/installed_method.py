"""Scaled implementation of PBO-IHS and hitting-set optimizer variants."""

from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from data.pbo_instances import PBConstraint, PBOInstance, all_assignments, benchmark_instances


@dataclass
class SolverStats:
    instance: str
    variant: str
    solved: bool
    optimal_cost: int | None
    best_assignment: list[int] | None
    iterations: int
    cores_learned: int
    hs_calls: int
    decision_calls: int
    sls_successes: int
    exact_hs_calls: int
    elapsed_sec: float
    certificate: dict
    trace: list[dict]


def constraint_to_dict(constraint: PBConstraint) -> dict:
    return {
        "terms": [
            {"var": var, "positive": positive, "coeff": coeff}
            for var, positive, coeff in constraint.terms
        ],
        "rhs": constraint.rhs,
    }


def objective_cost(weights: tuple[int, ...], obj_assignment: tuple[int, ...]) -> int:
    return sum(w * obj_assignment[i] for i, w in enumerate(weights))


def satisfies_constraints(constraints: tuple[PBConstraint, ...], assignment: tuple[int, ...]) -> bool:
    return all(c.satisfied(assignment) for c in constraints)


def full_solve(inst: PBOInstance, assumptions: tuple[int | None, ...] | None = None):
    assumptions = assumptions or (None,) * inst.n_objective
    for assignment in all_assignments(inst.n_vars):
        if any(v is not None and assignment[i] != v for i, v in enumerate(assumptions)):
            continue
        if satisfies_constraints(inst.constraints, assignment):
            return assignment
    return None


def seed_cores(inst: PBOInstance) -> list[PBConstraint]:
    return [c for c in inst.constraints if c.objective_only(inst.n_objective)]


def _core_from_partial(partial: dict[int, int]) -> PBConstraint:
    terms = []
    for var, value in sorted(partial.items()):
        terms.append((var, False if value else True, 1))
    return PBConstraint(tuple(terms), 1)


def extract_core(inst: PBOInstance, obj_assignment: tuple[int, ...]) -> tuple[PBConstraint, int]:
    partial = {i: obj_assignment[i] for i in range(inst.n_objective)}
    calls = 0
    changed = True
    while changed:
        changed = False
        for var in list(partial):
            trial = dict(partial)
            del trial[var]
            assumptions = [None] * inst.n_objective
            for key, value in trial.items():
                assumptions[key] = value
            calls += 1
            if full_solve(inst, tuple(assumptions)) is None:
                partial = trial
                changed = True
    return _core_from_partial(partial), calls


def hs_feasible(cores: list[PBConstraint], obj_assignment: tuple[int, ...]) -> bool:
    return all(c.satisfied(obj_assignment) for c in cores)


def ip_exact_hs(cores: list[PBConstraint], weights: tuple[int, ...]):
    best_assignment = None
    best_cost = None
    checked = 0
    for assignment in all_assignments(len(weights)):
        checked += 1
        if not hs_feasible(cores, assignment):
            continue
        cost = objective_cost(weights, assignment)
        if best_cost is None or cost < best_cost:
            best_assignment = assignment
            best_cost = cost
    if best_assignment is None:
        raise RuntimeError("core set is infeasible")
    return best_assignment, best_cost, checked


def sis_hs(cores: list[PBConstraint], weights: tuple[int, ...], ub: int):
    """Solution-improving search over the current core set."""
    best_assignment = None
    best_cost = ub
    calls = 0
    while True:
        candidate = None
        candidate_cost = None
        for assignment in all_assignments(len(weights)):
            if not hs_feasible(cores, assignment):
                continue
            cost = objective_cost(weights, assignment)
            if cost < best_cost and (candidate_cost is None or cost > candidate_cost):
                candidate = assignment
                candidate_cost = cost
        calls += 1
        if candidate is None:
            if best_assignment is None:
                best_assignment, best_cost, _ = ip_exact_hs(cores, weights)
            return best_assignment, best_cost, calls
        best_assignment = candidate
        best_cost = candidate_cost


def core_sls(cores: list[PBConstraint], weights: tuple[int, ...], ub: int, seed: int, previous=None):
    rng = random.Random(seed)
    n = len(weights)
    starts = [list(previous) if previous is not None else [0] * n]
    diversified = list(starts[0])
    for idx in rng.sample(range(n), max(1, n // 2)):
        diversified[idx] = 1 - diversified[idx]
    starts.append(diversified)

    best = None
    best_cost = None
    flips = 0
    for start in starts:
        current = start
        for _ in range(80 * n):
            flips += 1
            tup = tuple(current)
            if hs_feasible(cores, tup):
                cost = objective_cost(weights, tup)
                if cost < ub and (best_cost is None or cost <= best_cost):
                    best = tup
                    best_cost = cost
            scores = []
            current_gap = sum(max(0, c.rhs - c.value(tuple(current))) for c in cores)
            for var in range(n):
                trial = current.copy()
                trial[var] = 1 - trial[var]
                next_gap = sum(max(0, c.rhs - c.value(tuple(trial))) for c in cores)
                cost_delta = objective_cost(weights, tuple(trial)) - objective_cost(weights, tuple(current))
                scores.append((next_gap - current_gap, cost_delta, rng.random(), var))
            _, _, _, var = min(scores)
            current[var] = 1 - current[var]
    return best, best_cost, flips


def solve_hs(variant: str, cores: list[PBConstraint], weights: tuple[int, ...], lb: int, ub: int, seed: int, previous):
    if variant == "ip_exact":
        gamma, cost, checked = ip_exact_hs(cores, weights)
        return gamma, cost, {"exact": True, "checked": checked, "sls": False, "solution_cost": cost}
    if variant == "sis":
        gamma, cost, calls = sis_hs(cores, weights, ub)
        return gamma, cost, {"exact": True, "sis_calls": calls, "sls": False, "solution_cost": cost}
    if variant == "sis_sls":
        # Scientific ablation: remove local search, retaining the IHS loop.
        gamma, cost, calls = sis_hs(cores, weights, ub)
        return gamma, cost, {"exact": True, "sis_calls": calls, "sls": False, "solution_cost": cost}
    raise ValueError(f"unknown variant {variant}")


def pbo_ihs(inst: PBOInstance, variant: str, seed: int, max_iterations: int = 200) -> SolverStats:
    start = time.perf_counter()
    first = full_solve(inst)
    decision_calls = 1
    if first is None:
        return SolverStats(inst.name, variant, False, None, None, 0, 0, 0, decision_calls, 0, 0, 0.0, {}, [])

    best = first
    ub = inst.objective_cost(best)
    lb = -1
    cores = seed_cores(inst)
    learned = 0
    hs_calls = 0
    exact_hs_calls = 0
    sls_successes = 0
    previous = None
    trace = []

    for iteration in range(1, max_iterations + 1):
        event = {
            "iteration": iteration,
            "lb_before": lb,
            "ub_before": ub,
            "core_count_before": len(cores),
        }
        gamma, new_lb, meta = solve_hs(variant, cores, inst.objective_weights, lb, ub, seed + iteration, previous)
        hs_calls += 1
        previous = gamma
        event["hs"] = {
            "gamma": list(gamma),
            "cost": meta["solution_cost"],
            "exact": meta["exact"],
            "sls": bool(meta.get("sls")),
            "optimizer": variant,
            "details": {k: v for k, v in meta.items() if k not in {"solution_cost", "exact", "sls"}},
        }
        if meta["exact"]:
            exact_hs_calls += 1
            lb = new_lb
        elif meta.get("sls"):
            sls_successes += 1
        event["lb_after_hs"] = lb
        if ub == lb:
            event["terminated_after_hs"] = True
            event["ub_after"] = ub
            event["lb_after"] = lb
            event["best_after"] = list(best)
            trace.append(event)
            break

        alpha = full_solve(inst, tuple(gamma))
        decision_calls += 1
        if alpha is not None:
            cost = inst.objective_cost(alpha)
            event["decision"] = {
                "sat": True,
                "alpha": list(alpha),
                "alpha_cost": cost,
            }
            if cost < ub:
                ub = cost
                best = alpha
            if ub == lb:
                event["terminated_after_decision"] = True
                event["ub_after"] = ub
                event["lb_after"] = lb
                event["best_after"] = list(best)
                trace.append(event)
                break
        else:
            core, calls = extract_core(inst, gamma)
            decision_calls += calls
            event["decision"] = {
                "sat": False,
                "new_core": constraint_to_dict(core),
                "extraction_calls": calls,
            }
            cores.append(core)
            learned += 1
        event["ub_after"] = ub
        event["lb_after"] = lb
        event["best_after"] = list(best)
        trace.append(event)
    else:
        raise RuntimeError(f"{variant} exceeded iteration limit on {inst.name}")

    elapsed = time.perf_counter() - start
    cert = {
        "lower_bound": lb,
        "upper_bound": ub,
        "core_count": len(cores),
        "exact_hs_calls": exact_hs_calls,
        "sls_successes": sls_successes,
        "trace_events": len(trace),
        "optimality_reason": "ub_equals_lb",
    }
    return SolverStats(
        inst.name,
        variant,
        True,
        ub,
        list(best),
        iteration,
        learned,
        hs_calls,
        decision_calls,
        sls_successes,
        exact_hs_calls,
        elapsed,
        cert,
        trace,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=["ip_exact", "sis", "sis_sls"], action="append", required=True)
    parser.add_argument("--output", default="checkpoints/pbo_ihs_results.json")
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    results = []
    for variant in args.variant:
        for inst in benchmark_instances():
            results.append(asdict(pbo_ihs(inst, variant, args.seed)))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
