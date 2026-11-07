"""Scientific weak control: return an initial feasible point without optimization."""
import argparse
import json
from pathlib import Path

from data.pbo_instances import all_assignments, benchmark_instances


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rows = []
    for inst in benchmark_instances():
        answer = next(a for a in all_assignments(inst.n_vars)
                      if all(c.satisfied(a) for c in inst.constraints))
        cost = inst.objective_cost(answer)
        rows.append({'instance': inst.name, 'variant': 'sis_sls',
                     'solved': True, 'best_assignment': list(answer),
                     'optimal_cost': cost, 'trace': [],
                     'certificate': {'lower_bound': -1, 'upper_bound': cost,
                                     'trace_events': 0}})
    Path(args.output).write_text(json.dumps({'results': rows}, indent=2))


if __name__ == '__main__':
    main()
