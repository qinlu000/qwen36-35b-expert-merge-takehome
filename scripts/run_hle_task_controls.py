"""Run two fixed task controls serially on their own TP2 replica; no training."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path

from run_direct_formal_pipeline import acceptance, launch, save
from run_dedicated_hle_formal import pid_alive


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=Path('configs/eval/hle_task_controls_20261017.json'))
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    root = args.project.resolve()
    config = json.loads((root / args.config).read_text())
    output = root / config['controller_output']
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / 'controller.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert config['execution_order'] == ['mixed883', 'avg16']
    protocol = json.loads((root / 'configs/eval/protocol_v2_unified64k8k.json').read_text())
    manifest = json.loads((root / protocol['benchmarks']['hle']['task_manifest']).read_text())
    ids = manifest['task_ids']
    assert len(ids) == len(set(ids)) == 2500
    python = str(root / 'artifacts/envs/hle/bin/python')
    completed = []
    save(output / 'controller.json', {'pid': os.getpid(), 'at_utc': now(),
        'config': str(root / args.config), 'endpoint': config['endpoint'],
        'order': config['execution_order'], 'actual_benchmark_control': True,
        'independent_validation_set': False, 'loss_selection': False})
    for name in config['execution_order']:
        model = config['models'][name]
        destination = root / model['output']
        destination.mkdir(parents=True, exist_ok=True)
        claim = destination / 'task_control_launch.json'
        previous = json.loads(claim.read_text()) if claim.exists() else {}
        assert args.resume or not previous, 'Existing control launch is retained; use explicit resume'
        summary_path = destination / 'summary.json'
        if args.resume and summary_path.exists() and json.loads(summary_path.read_text()).get('saved_results') == 2500:
            completed.append({'model': model['alias'], 'saved_results': 2500,
                              'generation_exit_code': 0, 'grader_pid': previous.get('scoring_pid')})
            continue
        receipt = destination / 'service_acceptance'
        receipt.mkdir(exist_ok=True)
        acceptance(root, config['endpoint'], {'hle': model['alias']}, receipt)
        save(destination / 'manual_retry_manifest.json', {
            'selection_rule': 'One fixed terminal result per task ID; no score selection or retries',
            'retained': [{'id': task, 'manual_retry_index': 0,
                          'original_result': str(destination / 'questions' / (task + '.json'))} for task in ids],
            'selected': [], 'expected_questions': 2500, 'formal_model': model['alias']})
        generation = [python, str(root / 'scripts/run_direct_hle_formal.py'),
            '--project', str(root), '--mode', 'formal', '--model', model['alias'],
            '--endpoint', config['endpoint'], '--key-file', str(root / config['key_file']),
            '--output', str(destination)]
        scoring = [python, str(root / 'scripts/score_direct_hle_formal.py'),
            '--project', str(root), '--retry', str(destination),
            '--output', str(destination / 'scoring'), '--max-cny', str(config['judge_max_cny_per_model']),
            '--max-calls', str(config['judge_max_calls_per_model']), '--workers', str(config['judge_workers'])]
        generator = launch(generation, output / (name + '_generation.log'), root)
        grader_pid = previous.get('scoring_pid')
        grader = None if grader_pid and pid_alive(grader_pid) else launch(scoring, output / (name + '_scoring.log'), root)
        grader_pid = grader.pid if grader is not None else grader_pid
        save(claim, {'state': 'running', 'at_utc': now(), 'controller_pid': os.getpid(),
            'model': model['alias'], 'artifact': model['artifact'],
            'generation_pid': generator.pid, 'scoring_pid': grader_pid, 'scorer_reattached': grader is None,
            'generation': generation, 'scoring': scoring})
        generation_rc = generator.wait()
        generation_summary = json.loads((destination / 'summary.json').read_text())
        assert generation_rc == 0
        if generation_summary['saved_results'] != 2500:
            assert (destination / 'STOP_ADMISSION').exists(), 'Partial generation requires explicit migration stop'
            save(output / 'progress.json', {'at_utc': now(), 'state': 'paused_migration',
                'model': model['alias'], 'saved_results': generation_summary['saved_results'],
                'grader_pid': grader_pid})
            return
        completed.append({'model': model['alias'], 'saved_results': 2500,
                          'generation_exit_code': generation_rc, 'grader_pid': grader_pid})
        save(destination / 'model-consumer-finished.json', {
            'model_consumer_finished': True, 'at_utc': now(), 'model': model['alias'],
            'expected': 2500, 'generation_process_finished': True, 'saved_results': 2500,
            'scoring_uses_external_judge_only': True})
        save(output / 'progress.json', {'at_utc': now(), 'completed_generation': completed,
            'next_model': 'avg16' if name == 'mixed883' else None})
        # The next alias starts only after the previous model's HTTP requests drained.
        # Its external grader can finish independently of the GPU.
    save(output / 'model-consumer-finished.json', {
        'model_consumer_finished': True, 'at_utc': now(), 'models': completed,
        'total_saved_results': 5000, 'generation_processes_finished': True,
        'scoring_uses_external_judge_only': True})


if __name__ == '__main__':
    os.umask(0o077)
    main()
