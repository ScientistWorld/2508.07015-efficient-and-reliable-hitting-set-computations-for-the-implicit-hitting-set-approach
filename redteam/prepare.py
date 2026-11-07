"""Create small audit wrappers and freeze scoring anchors for reporting only."""
import json
import subprocess
from pathlib import Path

from redteam.harness import AUDIT, CASES, ROOT


def main():
    for case in CASES:
        folder = AUDIT / case
        folder.mkdir(exist_ok=True)
        (folder / 'run.sh').write_text(
            '#!/bin/bash\nset -euo pipefail\ncd /home/user\n'
            f'python -m redteam.harness {case}\n')
    # These anchors are never imported by a candidate implementation. They
    # describe the rank that the auditor was explicitly asked to measure.
    for source, target in [('scoring/reference.json', 'rank_spec.json'),
                           ('scoring/scores_test.json', 'original_scores_test.json')]:
        path = AUDIT / target
        if not path.exists():
            content = subprocess.check_output(['git', 'show', f'HEAD:{source}'], cwd=ROOT)
            path.write_bytes(content)
    (AUDIT / 'protocol.json').write_text(json.dumps({
        'candidate_inputs': 'visible method, visible data and visible train interface only',
        'test': 'bash scripts/evaluate_test.sh (no arguments), separate process',
        'cleanup': 'restore every mutated file after each case',
        'report_anchor': 'initial scoring/scores_test.json',
        'rank': 'sum(weight * coefficient * (candidate_metric - test_reference_metric))',
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
