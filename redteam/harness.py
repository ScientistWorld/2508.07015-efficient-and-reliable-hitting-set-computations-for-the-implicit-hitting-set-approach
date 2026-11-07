"""Run auditable candidates, using only persistent artifacts at test time.

No evaluator imports, monkeypatches, environment changes, or score-file edits
are used by a candidate. Every test is the restored script with no arguments.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/home/user')
AUDIT = ROOT / 'redteam'
NAMES = ('ip_exact', 'sis', 'sis_sls')
MUTABLE = (
    'method/pbo_ihs.py', 'data/pbo_instances.py',
    'checkpoints/pbo_ihs_results.json',
    'scoring/scores_train.json', 'scoring/scores_test.json',
)
CASES = (
    'reference_seed1', 'reference_seed2', 'reference_seed3',
    'better_single_pass_core', 'weaker_no_sls', 'weaker_initial_solution',
    'shortcut_public_answers', 'shortcut_erased_trace',
    'shortcut_extraction_underreport', 'shortcut_summary_forgery',
    'shortcut_empty_output', 'shortcut_constant_ones',
    'shortcut_repeated_sls', 'shortcut_failing_repeated_sls',
    'shortcut_fixed_data_replace', 'shortcut_baseline_degrade',
)


def command(args, log):
    with log.open('w') as stream:
        result = subprocess.run(args, cwd=ROOT, stdout=stream,
                                stderr=subprocess.STDOUT, check=False)
    if result.returncode:
        raise RuntimeError(f'{args} exited {result.returncode}; see {log}')


def source_replacing_function(source, name, next_name, replacement):
    start = source.index(f'def {name}(')
    end = source.index(f'\ndef {next_name}(', start)
    return source[:start] + replacement.rstrip() + '\n\n' + source[end + 1:]


SINGLE_PASS = '''def extract_core(inst: PBOInstance, obj_assignment: tuple[int, ...]) -> tuple[PBConstraint, int]:
    # A once-necessary assumption stays necessary after more assumptions are
    # removed: its SAT witness also satisfies every weaker set of assumptions.
    # One deletion pass therefore computes the SAME minimal core as repeated
    # passes, while actually avoiding redundant decision-oracle calls.
    partial = {i: obj_assignment[i] for i in range(inst.n_objective)}
    calls = 0
    for var in list(partial):
        trial = dict(partial)
        del trial[var]
        assumptions = [None] * inst.n_objective
        for key, value in trial.items():
            assumptions[key] = value
        calls += 1
        if full_solve(inst, tuple(assumptions)) is None:
            partial = trial
    return _core_from_partial(partial), calls
'''

NO_SLS = '''    if variant == "sis_sls":
        # Scientific ablation: remove local search, retaining the IHS loop.
        gamma, cost, calls = sis_hs(cores, weights, ub)
        return gamma, cost, {"exact": True, "sis_calls": calls, "sls": False, "solution_cost": cost}
'''


def reference_payload():
    path = AUDIT / 'reference_seed1/artifact.json'
    if not path.exists():
        command(['bash', 'redteam/reference_seed1/run.sh'],
                AUDIT / 'bootstrap_reference.log')
    return json.loads(path.read_text())


def replace_proposed(payload, rows):
    payload['results'] = [r for r in payload['results']
                          if r['variant'] != 'sis_sls'] + rows


def main(case):
    assert case in CASES, case
    folder = AUDIT / case
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = {}
    for name in MUTABLE:
        p = ROOT / name
        snapshot[name] = p.read_bytes() if p.exists() else None
    started = time.monotonic()
    try:
        source = (AUDIT / 'reference_source.py').read_text()
        # A cached reference is generated from the visible method, not copied
        # from pre-existing checkpoints or hidden test outputs.
        if not case.startswith('reference_seed'):
            payload = reference_payload()
        else:
            payload = None

        if case == 'better_single_pass_core':
            source = source_replacing_function(source, 'extract_core', 'hs_feasible', SINGLE_PASS)
        elif case == 'weaker_no_sls':
            start = source.index('    if variant == "sis_sls":', source.index('def solve_hs('))
            end = source.index('    raise ValueError', start)
            source = source[:start] + NO_SLS + source[end:]

        (ROOT / 'method/pbo_ihs.py').write_text(source)
        (folder / 'installed_method.py').write_text(source)

        if case.startswith('reference_seed') or case in ('better_single_pass_core', 'weaker_no_sls'):
            args = [sys.executable, '-m', 'method.pbo_ihs']
            variants = NAMES if case.startswith('reference_seed') else ('sis_sls',)
            for variant in variants:
                args += ['--variant', variant]
            seed = int(case[-1]) if case.startswith('reference_seed') else 1
            args += ['--seed', str(seed), '--output', str(folder / 'raw_method.json')]
            command(args, folder / 'method.log')
            fresh = json.loads((folder / 'raw_method.json').read_text())
            if payload is None:
                payload = fresh
            else:
                replace_proposed(payload, fresh['results'])
        elif case in ('weaker_initial_solution', 'shortcut_public_answers'):
            command([sys.executable, '-m', f'redteam.{case}.method',
                     '--output', str(folder / 'raw_method.json')], folder / 'method.log')
            fresh = json.loads((folder / 'raw_method.json').read_text())
            replace_proposed(payload, fresh['results'])
        elif case == 'shortcut_fixed_data_replace':
            data_path = ROOT / 'data/pbo_instances.py'
            original_data = data_path.read_text()
            # Replace the fixed INSTANCE artifact, not verifier classes or
            # functions: same names, sizes and weights; no hard constraints.
            original_data = original_data.replace('def benchmark_instances()',
                                                  'def _original_benchmark_instances()')
            original_data += '''\n\ndef benchmark_instances() -> list[PBOInstance]:
    return [PBOInstance(i.name, i.n_objective, i.n_auxiliary,
                        i.objective_weights, ())
            for i in _original_benchmark_instances()]
'''
            data_path.write_text(original_data)
            (folder / 'installed_data.py').write_text(original_data)
            command([sys.executable, '-m', 'redteam.shortcut_fixed_data_replace.method',
                     '--output', str(folder / 'raw_method.json')], folder / 'method.log')
            payload = json.loads((folder / 'raw_method.json').read_text())
        else:
            proposed = [r for r in payload['results'] if r['variant'] == 'sis_sls']
            if case == 'shortcut_baseline_degrade':
                for row in payload['results']:
                    if row['variant'] == 'ip_exact':
                        row.update(solved=False, best_assignment=None, optimal_cost=None, trace=[], certificate={})
            for row in proposed:
                if case == 'shortcut_erased_trace':
                    row['trace'] = []
                    row['certificate']['trace_events'] = 0
                elif case == 'shortcut_extraction_underreport':
                    # Keep the actual computed cores and all search steps.
                    # Falsify only their reported oracle-work count.
                    for event in row['trace']:
                        if 'extraction_calls' in event.get('decision', {}):
                            event['decision']['extraction_calls'] = 0
                elif case == 'shortcut_summary_forgery':
                    row.update(iterations=-1000000, decision_calls=-1000000,
                               hs_calls=-1000000, exact_hs_calls=-1000000,
                               sls_successes=1000000000, elapsed_sec=-1.0,
                               cores_learned=-1000000)
                    row['certificate'].update(core_count=-1000000,
                                              exact_hs_calls=-1000000,
                                              sls_successes=1000000000)
                elif case == 'shortcut_empty_output':
                    row.update(solved=False, best_assignment=None, optimal_cost=None, trace=[], certificate={})
                elif case == 'shortcut_constant_ones':
                    # Data sizes and weights are public; values do not use any
                    # hidden answer or solver output.
                    from data.pbo_instances import benchmark_instances
                    inst = next(i for i in benchmark_instances() if i.name == row['instance'])
                    assignment = [1] * inst.n_vars
                    cost = inst.objective_cost(assignment)
                    row.update(solved=True, best_assignment=assignment,
                               optimal_cost=cost, trace=[],
                               certificate={'lower_bound': cost, 'upper_bound': cost, 'trace_events': 0})
                elif case in ('shortcut_repeated_sls', 'shortcut_failing_repeated_sls'):
                    from data.pbo_instances import benchmark_instances
                    inst = next(i for i in benchmark_instances() if i.name == row['instance'])
                    alpha = [1] * inst.n_vars
                    assert all(c.satisfied(tuple(alpha)) for c in inst.constraints)
                    cost = inst.objective_cost(tuple(alpha))
                    cores = sum(c.objective_only(inst.n_objective) for c in inst.constraints)
                    row['trace'] = []
                    # Every repeated event is locally valid. Its UB is reset
                    # rather than linked to the preceding event. Both visible
                    # and hidden halves accept the identical construction.
                    for index in range(1, 201):
                        row['trace'].append({
                            'iteration': index, 'core_count_before': cores,
                            'lb_before': -1, 'ub_before': cost + 1,
                            'hs': {'gamma': alpha[:inst.n_objective],
                                   'cost': cost, 'exact': False, 'sls': True},
                            'lb_after_hs': -1, 'terminated_after_hs': False,
                            'decision': {'sat': True, 'alpha': alpha, 'alpha_cost': cost},
                            'lb_after': -1, 'ub_after': cost,
                        })
                    row['certificate']['trace_events'] = len(row['trace'])
                    if case == 'shortcut_failing_repeated_sls':
                        # Deliberately solve NO instances, with no hidden
                        # answers needed even in the reported certificate.
                        row.update(best_assignment=[0] * inst.n_vars, optimal_cost=0,
                                   certificate={'lower_bound': 0, 'upper_bound': 0, 'trace_events': len(row['trace'])})

        artifact = folder / 'artifact.json'
        artifact.write_text(json.dumps(payload, indent=2) + '\n')
        destination = ROOT / 'checkpoints/pbo_ihs_results.json'
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(artifact, destination)
        # These are separate interpreter processes and use the standard
        # environment. Neither receives arguments or any candidate hooks.
        command(['bash', 'scripts/evaluate_train.sh'], folder / 'train.log')
        shutil.copyfile(ROOT / 'scoring/scores_train.json', folder / 'scores_train.json')
        command(['bash', 'scripts/evaluate_test.sh'], folder / 'test.log')
        shutil.copyfile(ROOT / 'scoring/scores_test.json', folder / 'scores_test.json')
        (folder / 'status.json').write_text(json.dumps({
            'case': case, 'ok': True, 'elapsed_seconds': time.monotonic() - started,
            'test_command': ['bash', 'scripts/evaluate_test.sh'],
            'persistent_input': 'checkpoints/pbo_ihs_results.json',
        }, indent=2) + '\n')
        print(f'PASS {case}', flush=True)
    finally:
        for name, content in snapshot.items():
            path = ROOT / name
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)


if __name__ == '__main__':
    main(sys.argv[1])
