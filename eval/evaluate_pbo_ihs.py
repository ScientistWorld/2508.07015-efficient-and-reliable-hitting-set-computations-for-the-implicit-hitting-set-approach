"""Evaluate PBO-IHS artifacts without importing method code."""

from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

from data.pbo_instances import benchmark_instances


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
            cert = row.get("certificate", {})
            cert_ok = cert.get("lower_bound") == cert.get("upper_bound") == row.get("optimal_cost")
            solved += int(row["solved"] and feasible)
            exact_matches += int(optimal)
            cert_matches += int(optimal and cert_ok)
            total_iterations += row.get("iterations", 0)
            total_decisions += row.get("decision_calls", 0)
            total_exact_hs += row.get("exact_hs_calls", 0)
            sls_successes += row.get("sls_successes", 0)

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
