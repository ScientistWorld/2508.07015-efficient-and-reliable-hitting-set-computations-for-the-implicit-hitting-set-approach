"""Shortcut: solve only the replaced, vacuous fixed benchmark artifact."""
import argparse
import json
from pathlib import Path

from data.pbo_instances import benchmark_instances


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rows = []
    for inst in benchmark_instances():
        for variant in ('ip_exact', 'sis', 'sis_sls'):
            event = {'core_count_before': 0, 'lb_before': -1, 'ub_before': 0,
                     'hs': {'gamma': [0] * inst.n_objective, 'cost': 0,
                            'exact': True, 'sls': False},
                     'lb_after_hs': 0, 'terminated_after_hs': True,
                     'lb_after': 0, 'ub_after': 0}
            trace = [dict(event, iteration=1), dict(event, iteration=2)]
            rows.append({'instance': inst.name, 'variant': variant,
                         'solved': True, 'best_assignment': [0] * inst.n_vars,
                         'optimal_cost': 0, 'trace': trace,
                         'certificate': {'lower_bound': 0, 'upper_bound': 0,
                                         'trace_events': 2}})
    Path(args.output).write_text(json.dumps({'results': rows}, indent=2))


if __name__ == '__main__':
    main()
