"""Evaluate PBO-IHS artifacts without importing method code."""

from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from data.pbo_instances import PBConstraint, benchmark_instances


def brute_force_optimum(inst):
    best_cost = None
    best_assignment = None
    for assignment in product((0, 1), repeat=inst.n_vars):
        if all(c.satisfied(assignment) for c in inst.constraints):
            cost = inst.objective_cost(assignment)
            if best_cost is None or cost < best_cost:
                best_cost = cost
                best_assignment = assignment
    return best_cost, best_assignment


def objective_cost(weights: tuple[int, ...], obj_assignment: tuple[int, ...]) -> int:
    return sum(w * obj_assignment[i] for i, w in enumerate(weights))


def seed_cores(inst) -> list[PBConstraint]:
    return [c for c in inst.constraints if c.objective_only(inst.n_objective)]


def constraint_from_dict(payload: dict) -> PBConstraint:
    terms = []
    for term in payload.get("terms", []):
        terms.append((int(term["var"]), bool(term["positive"]), int(term["coeff"])))
    return PBConstraint(tuple(terms), int(payload["rhs"]))


def hs_feasible(cores: list[PBConstraint], obj_assignment: tuple[int, ...]) -> bool:
    return all(c.satisfied(obj_assignment) for c in cores)


def brute_force_hs_optimum(cores: list[PBConstraint], weights: tuple[int, ...]) -> int | None:
    best = None
    for assignment in product((0, 1), repeat=len(weights)):
        if not hs_feasible(cores, assignment):
            continue
        cost = objective_cost(weights, assignment)
        if best is None or cost < best:
            best = cost
    return best


def implied_by_instance(inst, core: PBConstraint) -> bool:
    for assignment in product((0, 1), repeat=inst.n_vars):
        if all(c.satisfied(assignment) for c in inst.constraints) and not core.satisfied(assignment):
            return False
    return True


def verify_trace(inst, row: dict, optimum: int | None) -> dict:
    trace = row.get("trace")
    if not isinstance(trace, list) or optimum is None:
        return {"ok": False}

    best_assignment = row.get("best_assignment")
    if not isinstance(best_assignment, list) or len(best_assignment) != inst.n_vars:
        return {"ok": False}
    best_tuple = tuple(best_assignment)
    if not all(c.satisfied(best_tuple) for c in inst.constraints):
        return {"ok": False}

    cores = seed_cores(inst)
    lb = -1
    ub = None
    best = None
    exact_hs_calls = 0
    sls_successes = 0
    decision_calls = 1
    learned = 0

    for idx, event in enumerate(trace, start=1):
        if event.get("iteration") != idx:
            return {"ok": False}
        if event.get("core_count_before") != len(cores):
            return {"ok": False}
        if event.get("lb_before") != lb:
            return {"ok": False}
        if ub is not None and event.get("ub_before") != ub:
            return {"ok": False}

        if ub is None:
            ub = event.get("ub_before")
            best = tuple(event.get("best_after", best_tuple))
            if not isinstance(ub, int):
                return {"ok": False}

        hs = event.get("hs", {})
        gamma_raw = hs.get("gamma")
        if not isinstance(gamma_raw, list) or len(gamma_raw) != inst.n_objective:
            return {"ok": False}
        gamma = tuple(int(v) for v in gamma_raw)
        if any(v not in (0, 1) for v in gamma) or not hs_feasible(cores, gamma):
            return {"ok": False}
        gamma_cost = objective_cost(inst.objective_weights, gamma)
        if hs.get("cost") != gamma_cost:
            return {"ok": False}

        if hs.get("exact"):
            exact_cost = brute_force_hs_optimum(cores, inst.objective_weights)
            if exact_cost != gamma_cost:
                return {"ok": False}
            lb = gamma_cost
            exact_hs_calls += 1
        elif hs.get("sls"):
            if not (gamma_cost < ub):
                return {"ok": False}
            sls_successes += 1
        else:
            return {"ok": False}

        if event.get("lb_after_hs") != lb:
            return {"ok": False}
        if ub == lb:
            if not event.get("terminated_after_hs"):
                return {"ok": False}
            if event.get("lb_after") != lb or event.get("ub_after") != ub:
                return {"ok": False}
            continue

        decision = event.get("decision")
        if not isinstance(decision, dict):
            return {"ok": False}
        decision_calls += 1
        if decision.get("sat"):
            alpha_raw = decision.get("alpha")
            if not isinstance(alpha_raw, list) or len(alpha_raw) != inst.n_vars:
                return {"ok": False}
            alpha = tuple(int(v) for v in alpha_raw)
            if alpha[: inst.n_objective] != gamma:
                return {"ok": False}
            if not all(c.satisfied(alpha) for c in inst.constraints):
                return {"ok": False}
            alpha_cost = inst.objective_cost(alpha)
            if decision.get("alpha_cost") != alpha_cost:
                return {"ok": False}
            if alpha_cost < ub:
                ub = alpha_cost
                best = alpha
        else:
            try:
                core = constraint_from_dict(decision["new_core"])
            except (KeyError, TypeError, ValueError):
                return {"ok": False}
            if not core.objective_only(inst.n_objective):
                return {"ok": False}
            if core.satisfied(gamma):
                return {"ok": False}
            if not implied_by_instance(inst, core):
                return {"ok": False}
            cores.append(core)
            learned += 1
            extraction_calls = decision.get("extraction_calls", 0)
            if not isinstance(extraction_calls, int) or extraction_calls < 0:
                return {"ok": False}
            decision_calls += extraction_calls

        if event.get("lb_after") != lb or event.get("ub_after") != ub:
            return {"ok": False}
        best_after = event.get("best_after")
        if best_after is not None and tuple(best_after) != best:
            return {"ok": False}

    certificate = row.get("certificate", {})
    cert_ok = (
        certificate.get("lower_bound") == lb
        and certificate.get("upper_bound") == ub
        and certificate.get("core_count") == len(cores)
        and certificate.get("exact_hs_calls") == exact_hs_calls
        and certificate.get("sls_successes") == sls_successes
        and certificate.get("trace_events") == len(trace)
        and lb == ub == row.get("optimal_cost") == optimum
    )
    return {
        "ok": cert_ok,
        "iterations": len(trace),
        "decision_calls": decision_calls,
        "exact_hs_calls": exact_hs_calls,
        "sls_successes": sls_successes,
        "cores_learned": learned,
    }


def evaluate(results_path: Path) -> dict:
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    instances = {inst.name: inst for inst in benchmark_instances()}
    optima = {inst.name: brute_force_optimum(inst)[0] for inst in benchmark_instances()}

    grouped: dict[str, list[dict]] = {}
    for row in payload["results"]:
        grouped.setdefault(row["variant"], []).append(row)

    score_results = {}
    for variant, rows in sorted(grouped.items()):
        by_instance = {row["instance"]: row for row in rows if row.get("instance") in instances}
        solved = 0
        exact_matches = 0
        cert_matches = 0
        total_iterations = 0
        total_decisions = 0
        total_exact_hs = 0
        sls_successes = 0
        for instance_name, inst in instances.items():
            row = by_instance.get(instance_name)
            if row is None or not row.get("solved") or row.get("best_assignment") is None:
                continue

            assignment = tuple(row["best_assignment"])
            feasible = len(assignment) == inst.n_vars and all(c.satisfied(assignment) for c in inst.constraints)
            cost = inst.objective_cost(assignment) if feasible else None
            optimal = feasible and cost == optima[instance_name] == row["optimal_cost"]
            trace_check = verify_trace(inst, row, optima[instance_name])
            cert_ok = optimal and trace_check["ok"]
            solved += int(row["solved"] and feasible)
            exact_matches += int(optimal)
            cert_matches += int(cert_ok)
            total_iterations += trace_check.get("iterations", 0)
            total_decisions += trace_check.get("decision_calls", 0)
            total_exact_hs += trace_check.get("exact_hs_calls", 0)
            sls_successes += trace_check.get("sls_successes", 0)

        n = len(instances)
        score_results[variant] = {
            "solved_count": solved,
            "optimality_match_rate": exact_matches / n,
            "certificate_accept_rate": cert_matches / n,
            "avg_iterations": total_iterations / n,
            "avg_decision_calls": total_decisions / n,
            "avg_exact_hs_calls": total_exact_hs / n,
            "sls_successes": sls_successes,
        }

    scores = {"experiments": {"scaled_pbo_ihs_exactness": {"results": score_results}}}
    Path("scoring").mkdir(exist_ok=True)
    Path("scoring/scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="checkpoints/pbo_ihs_results.json")
    args = parser.parse_args()
    print(json.dumps(evaluate(Path(args.results)), indent=2))


if __name__ == "__main__":
    main()
