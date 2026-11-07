"""Compute signed-coefficient rank deltas without changing gym scores."""
import json
from pathlib import Path

from redteam.harness import AUDIT, CASES


def main():
    spec = json.loads((AUDIT / 'rank_spec.json').read_text())['experiments']
    anchors = json.loads((AUDIT / 'original_scores_test.json').read_text())['experiments']
    records = {}
    for case in CASES:
        path = AUDIT / case / 'scores_test.json'
        if not path.exists():
            records[case] = {'error': 'missing completed hidden-test run'}
            continue
        score = json.loads(path.read_text())['experiments']
        deltas = {}
        utilities = {}
        contributions = {}
        for experiment, exp_spec in spec.items():
            for variant, metrics in score[experiment]['results'].items():
                ref = anchors[experiment]['results'][variant]
                weight = exp_spec['weight']
                parts = {m: weight * details['coefficient'] * (metrics[m] - ref[m])
                         for m, details in exp_spec['metrics'].items()}
                deltas[variant] = sum(parts.values())
                utilities[variant] = sum(weight * details['coefficient'] * metrics[m]
                                         for m, details in exp_spec['metrics'].items())
                contributions[variant] = parts
        records[case] = {'rank_delta_by_variant': deltas,
                         'rank_delta_sum_variants': sum(deltas.values()),
                         'utility_by_variant': utilities,
                         'contributions': contributions,
                         'metrics': score}
        print(case, 'sis_sls delta:', round(deltas['sis_sls'], 9),
              'sum:', round(sum(deltas.values()), 9))
    (AUDIT / 'summary.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
