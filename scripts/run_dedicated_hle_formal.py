"""One dedicated HLE service consumer: synthetic acceptance, fixed generation and judge."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time

from run_direct_formal_pipeline import acceptance, launch, now, save


def pid_alive(pid):
    path = Path('/proc') / str(pid)
    return path.exists() and (path / 'stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--profile', choices=['expert', 'merged'], required=True)
    parser.add_argument('--accept-only', action='store_true')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = args.project.resolve()
    config = json.loads((root / 'configs/eval/hle_dedicated_formal_20261017.json').read_text())[args.profile]
    hle = root / config['output']
    output = hle / 'controller'
    output.mkdir(parents=True, exist_ok=True)
    claim = (hle / 'formal_consumer.lock').open('a')
    fcntl.flock(claim, fcntl.LOCK_EX | fcntl.LOCK_NB)
    save(output / 'controller.json', {'pid': os.getpid(), 'profile': args.profile,
        **config, 'started_at_utc': now(), 'consumer_claim': str(hle / 'formal_consumer.lock')})
    save(output / 'state.json', {'state': 'synthetic_acceptance', 'at_utc': now()})
    acceptance(root, config['endpoint'], {'text': config['model'], 'hle': config['model']}, output)
    if args.accept_only:
        save(output / 'state.json', {'state': 'acceptance_passed', 'at_utc': now()})
        return
    protocol = json.loads((root / 'configs/eval/protocol_v2_unified64k8k.json').read_text())
    order = json.loads((root / protocol['benchmarks']['hle']['task_manifest']).read_text())['task_ids']
    manifest = {'selection_rule': 'One frozen terminal result per ID; no retries or score selection',
        'retained': [{'id': i, 'manual_retry_index': 0, 'original_result': str(hle / 'questions' / (i + '.json'))} for i in order],
        'selected': [], 'expected_questions': 2500, 'formal_model': config['model']}
    path = hle / 'manual_retry_manifest.json'
    if path.exists():
        assert json.loads(path.read_text()) == manifest
    else:
        save(path, manifest)
    py = str(root / 'artifacts/envs/hle/bin/python')
    generation = [py, str(root / 'scripts/run_direct_hle_formal.py'), '--project', str(root),
        '--mode', 'formal', '--model', config['model'], '--endpoint', config['endpoint'],
        '--key-file', str(root / 'artifacts/private/base_smoke_api_key'), '--output', str(hle)]
    scoring = [py, str(root / 'scripts/score_direct_hle_formal.py'), '--project', str(root),
        '--retry', str(hle), '--output', str(hle / 'scoring'),
        '--max-cny', '20', '--max-calls', '5000', '--workers', '2']
    previous = json.loads((output / 'launch.json').read_text()) if args.resume else {}
    grader_pid = previous.get('scoring_pid')
    hg = launch(generation, output / 'generation.log', root)
    hs = None if grader_pid and pid_alive(grader_pid) else launch(scoring, output / 'scoring.log', root)
    grader_pid = hs.pid if hs is not None else grader_pid
    save(output / 'launch.json', {'generation': generation, 'generation_pid': hg.pid,
        'scoring': scoring, 'scoring_pid': grader_pid, 'scorer_reattached': hs is None, 'at_utc': now()})
    save(output / 'state.json', {'state': 'generation_and_scoring', 'generation_pid': hg.pid,
        'scoring_pid': grader_pid, 'at_utc': now()})
    grc = hg.wait()
    summary = json.loads((hle / 'summary.json').read_text())
    if grc == 0 and summary.get('saved_results') == 2500:
        save(hle / 'model-consumer-finished.json', {'model_consumer_finished': True,
            'generation_process_finished': True, 'generation_pid': hg.pid, 'saved_results': 2500,
            'model': config['model'], 'at_utc': now(), 'scoring_uses_external_judge_only': True})
    if hs is None:
        while pid_alive(grader_pid):
            time.sleep(10)
        src = None  # A non-child process has no waitpid exit status here.
    else:
        src = hs.wait()
    save(output / 'state.json', {'state': 'finished', 'generation_exitcode': grc,
        'scoring_exitcode': src, 'at_utc': now()})


if __name__ == '__main__':
    os.umask(0o077)
    main()
