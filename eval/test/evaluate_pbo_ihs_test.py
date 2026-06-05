"""Held-out test-slice evaluator for PBO-IHS artifacts.

This scorer reads the same method artifact as the train scorer, but verifies
the complementary half of each IHS trace. It also preserves every method key
already scored by scores_train.json so test cannot silently drop a variant.
"""

from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from data.pbo_instances import PBConstraint, benchmark_instances


EXPERIMENT = "scaled_pbo_ihs_exactness"
SLICE = "test"
SELECT_ODD_EVENTS = False


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


def selected_event(index: int) -> bool:
    return index % 2 == (1 if SELECT_ODD_EVENTS else 0)


def validate_selected_event(inst, event: dict, index: int, cores: list[PBConstraint]) -> tuple[bool, dict]:
    metrics = {
        "iterations": 1,
        "decision_calls": 0,
        "exact_hs_calls": 0,
        "sls_successes": 0,
        "cores_learned": 0,
    }
    if event.get("iteration") != index:
        return False, metrics
    if event.get("core_count_before") != len(cores):
        return False, metrics

    lb_before = event.get("lb_before")
    ub_before = event.get("ub_before")
    if not isinstance(lb_before, int) or not isinstance(ub_before, int):
        return False, metrics

    hs = event.get("hs", {})
    gamma_raw = hs.get("gamma")
    if not isinstance(gamma_raw, list) or len(gamma_raw) != inst.n_objective:
        return False, metrics
    gamma = tuple(int(v) for v in gamma_raw)
    if any(v not in (0, 1) for v in gamma) or not hs_feasible(cores, gamma):
        return False, metrics
    gamma_cost = objective_cost(inst.objective_weights, gamma)
    if hs.get("cost") != gamma_cost:
        return False, metrics

    if hs.get("exact"):
        metrics["exact_hs_calls"] = 1
        if brute_force_hs_optimum(cores, inst.objective_weights) != gamma_cost:
            return False, metrics
        expected_lb_after_hs = gamma_cost
    elif hs.get("sls"):
        metrics["sls_successes"] = 1
        if not (gamma_cost < ub_before):
            return False, metrics
        expected_lb_after_hs = lb_before
    else:
        return False, metrics

    if event.get("lb_after_hs") != expected_lb_after_hs:
        return False, metrics

    if event.get("terminated_after_hs"):
        return (
            event.get("lb_after") == expected_lb_after_hs
            and event.get("ub_after") == ub_before
            and expected_lb_after_hs == ub_before,
            metrics,
        )

    decision = event.get("decision")
    if not isinstance(decision, dict):
        return False, metrics
    metrics["decision_calls"] = 1

    if decision.get("sat"):
        alpha_raw = decision.get("alpha")
        if not isinstance(alpha_raw, list) or len(alpha_raw) != inst.n_vars:
            return False, metrics
        alpha = tuple(int(v) for v in alpha_raw)
        if alpha[: inst.n_objective] != gamma:
            return False, metrics
        if any(v not in (0, 1) for v in alpha) or not all(c.satisfied(alpha) for c in inst.constraints):
            return False, metrics
        alpha_cost = inst.objective_cost(alpha)
        if decision.get("alpha_cost") != alpha_cost:
            return False, metrics
        expected_ub_after = min(ub_before, alpha_cost)
    else:
        try:
            core = constraint_from_dict(decision["new_core"])
        except (KeyError, TypeError, ValueError):
            return False, metrics
        if not core.objective_only(inst.n_objective):
            return False, metrics
        if core.satisfied(gamma):
            return False, metrics
        if not implied_by_instance(inst, core):
            return False, metrics
        extraction_calls = decision.get("extraction_calls", 0)
        if not isinstance(extraction_calls, int) or extraction_calls < 0:
            return False, metrics
        metrics["decision_calls"] += extraction_calls
        metrics["cores_learned"] = 1
        expected_ub_after = ub_before

    return (
        event.get("lb_after") == expected_lb_after_hs
        and event.get("ub_after") == expected_ub_after,
        metrics,
    )


def append_trace_core_if_present(inst, event: dict, cores: list[PBConstraint]) -> None:
    decision = event.get("decision")
    if not isinstance(decision, dict) or decision.get("sat", True):
        return
    try:
        core = constraint_from_dict(decision["new_core"])
    except (KeyError, TypeError, ValueError):
        return
    if core.objective_only(inst.n_objective):
        cores.append(core)


def verify_trace_slice(inst, row: dict, optimum: int | None) -> dict:
    trace = row.get("trace")
    if not isinstance(trace, list) or optimum is None:
        return {"ok": False}

    certificate = row.get("certificate", {})
    final_certificate_ok = (
        certificate.get("lower_bound") == optimum
        and certificate.get("upper_bound") == optimum
        and certificate.get("trace_events") == len(trace)
        and row.get("optimal_cost") == optimum
    )

    cores = seed_cores(inst)
    ok = final_certificate_ok
    totals = {
        "iterations": 0,
        "decision_calls": 0,
        "exact_hs_calls": 0,
        "sls_successes": 0,
        "cores_learned": 0,
    }

    for index, event in enumerate(trace, start=1):
        if selected_event(index):
            event_ok, event_metrics = validate_selected_event(inst, event, index, cores)
            ok = ok and event_ok
            for key in totals:
                totals[key] += event_metrics.get(key, 0)
        append_trace_core_if_present(inst, event, cores)

    totals["ok"] = ok
    return totals


def variants_from_train_scores(train_scores_path: Path) -> set[str]:
    if not train_scores_path.is_file():
        return set()
    try:
        payload = json.loads(train_scores_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    experiments = payload.get("experiments", payload)
    exp = experiments.get(EXPERIMENT, {}) if isinstance(experiments, dict) else {}
    results = exp.get("results", exp) if isinstance(exp, dict) else {}
    if not isinstance(results, dict):
        return set()
    return {str(name) for name in results if not str(name).startswith("_")}


def zero_metrics() -> dict:
    return {
        "solved_count": 0,
        "optimality_match_rate": 0.0,
        "certificate_accept_rate": 0.0,
        "avg_iterations": 0.0,
        "avg_decision_calls": 0.0,
        "avg_exact_hs_calls": 0.0,
        "sls_successes": 0,
    }


def evaluate(results_path: Path, output_path: Path, train_scores_path: Path) -> dict:
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    instances = {inst.name: inst for inst in benchmark_instances()}
    optima = {inst.name: brute_force_optimum(inst)[0] for inst in benchmark_instances()}

    grouped: dict[str, list[dict]] = {}
    for row in payload.get("results", []):
        if isinstance(row, dict) and "variant" in row:
            grouped.setdefault(str(row["variant"]), []).append(row)

    variants = sorted(set(grouped) | variants_from_train_scores(train_scores_path))
    score_results = {}
    for variant in variants:
        rows = grouped.get(variant, [])
        if not rows:
            score_results[variant] = zero_metrics()
            continue

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
            optimal = feasible and cost == optima[instance_name] == row.get("optimal_cost")
            trace_check = verify_trace_slice(inst, row, optima[instance_name])
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

    scores = {"slice": SLICE, "experiments": {EXPERIMENT: {"results": score_results}}}
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(json.dumps(scores, indent=2), encoding="utf-8")
    return scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="checkpoints/pbo_ihs_results.json")
    parser.add_argument("--output", default="scoring/scores_test.json")
    parser.add_argument("--train-scores", default="scoring/scores_train.json")
    args = parser.parse_args()
    print(json.dumps(evaluate(Path(args.results), Path(args.output), Path(args.train_scores)), indent=2))


if __name__ == "__main__":
    main()
