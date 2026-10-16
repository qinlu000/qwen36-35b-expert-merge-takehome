"""Persistent expert/AVG64 ASI -> HLE formal blocks with independent frozen graders."""
import argparse
import base64
from datetime import datetime, timezone
import fcntl
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import httpx
from PIL import Image


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def now():
    return datetime.now(timezone.utc).isoformat()


def wait_marker(path, field, expected):
    while not (path.is_file() and json.loads(path.read_text()).get(field) == expected):
        time.sleep(10)


def launch(command, log, root, env=None):
    handle = log.open('a')
    process = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                               stdout=handle, stderr=handle, start_new_session=True)
    handle.close()
    return process


def acceptance(root, endpoint, aliases, output):
    receipt = output / 'acceptance.json'
    if receipt.exists():
        assert json.loads(receipt.read_text())['ready']
        return
    key = (root / 'artifacts/private/base_smoke_api_key').read_text().strip()
    template = {'enable_thinking': False, 'preserve_thinking': False}
    rows = []
    with httpx.Client(trust_env=False, headers={'Authorization': 'Bearer ' + key}) as client:
        while True:
            try:
                if client.get(endpoint + '/health', timeout=3).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(10)
        models = client.get(endpoint + '/v1/models', timeout=10).json()
        assert set(aliases.values()) <= {row['id'] for row in models['data']}
        for task, alias in aliases.items():
            image = task == 'hle'
            content = [{'type': 'text', 'text': 'Name the dominant color in this image.' if image else 'What is 17 + 25?'}]
            if image:
                stream = io.BytesIO()
                Image.new('RGB', (32, 32), 'red').save(stream, format='PNG')
                content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode()}})
            messages = [{'role': 'user', 'content': content}]
            count = client.post(endpoint + '/tokenize', json={'model': alias, 'messages': messages,
                'chat_template_kwargs': template, 'add_generation_prompt': True}, timeout=60)
            count.raise_for_status()
            tokenized = count.json()
            response = client.post(endpoint + '/v1/chat/completions', json={'model': alias,
                'messages': messages, 'max_tokens': 32, 'temperature': 0, 'seed': 0,
                'chat_template_kwargs': template}, timeout=120)
            response.raise_for_status()
            payload = response.json()
            save(output / ('acceptance_' + task + '.response.json'), payload)
            message = payload['choices'][0]['message']
            assert payload['usage']['prompt_tokens'] == tokenized['count']
            assert tokenized['max_model_len'] == 65536
            assert not message.get('reasoning') and not message.get('reasoning_content')
            assert ('red' if image else '42') in message['content'].lower()
            rows.append({'task': task, 'model': alias, 'vision': image,
                         'prompt_tokens': tokenized['count'], 'usage': payload['usage']})
    save(receipt, {'ready': True, 'at_utc': now(), 'model_requests': len(rows),
                   'synthetic_only': True, 'formal_or_validation_questions': 0, 'checks': rows})


def active_program_scopes(cpus):
    listing = subprocess.check_output(['systemctl', '--user', 'list-units', '--type=scope',
        '--state=running', '--no-legend', '--plain'], text=True)
    active = []
    for line in listing.splitlines():
        scope = line.split()[0]
        if not scope.startswith(('apex-', 'asi-', 'ai4sci-')):
            continue
        group = subprocess.check_output(['systemctl', '--user', 'show', scope,
            '--property=ControlGroup', '--value'], text=True).strip()
        path = Path('/sys/fs/cgroup') / group.lstrip('/') / 'cgroup.procs'
        if not path.exists():
            continue
        pids = []
        for pid in path.read_text().split():
            try:
                affinity = os.sched_getaffinity(int(pid))
            except ProcessLookupError:
                continue
            if affinity and affinity <= set(cpus):
                pids.append(int(pid))
        if pids:
            active.append({'scope': scope, 'pids': pids})
    return active


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--profile', choices=['expert', 'merged'], required=True)
    parser.add_argument('--resume-after-asi-pid', type=int)
    args = parser.parse_args()
    root = args.project.resolve()
    merged = args.profile == 'merged'
    prefix = 'avg64' if merged else 'asi128'
    asi = root / f'artifacts/eval/{prefix}_asi240_20261017'
    hle = root / f'artifacts/eval/{"avg64" if merged else "hle250"}_hle2500_20261017'
    output = root / f'artifacts/eval/{args.profile}_direct_pipeline_20261017'
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / 'controller.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    endpoint = 'http://127.0.0.1:' + ('28093' if merged else '28090')
    aliases = {'asi': 'apex-avg64' if merged else 'apex-asi128',
               'hle': 'apex-avg64' if merged else 'apex-hle250'}
    save(output / 'controller.json', {'pid': os.getpid(), 'profile': args.profile,
        'endpoint': endpoint, 'aliases': aliases, 'at_utc': now(), 'state': 'waiting_service'})
    acceptance(root, endpoint, aliases, output)
    gate = (root / 'artifacts/eval/asi128_asi240_20261017/generation_cpu_finished.json' if merged else
            root / 'artifacts/eval/terminal250_full445_20261017/acceptance/acceptance.json')
    save(output / 'state.json', {'state': 'waiting_cpu_gate', 'gate': str(gate), 'at_utc': now()})
    wait_marker(gate, 'state' if merged else 'ready', 'finished' if merged else True)
    key = str(root / 'artifacts/private/base_smoke_api_key')
    pyasi = str(root / 'artifacts/envs/asi-py312/bin/python')
    pyhle = str(root / 'artifacts/envs/hle/bin/python')
    command = [pyasi, str(root / 'scripts/run_direct_asi_formal.py'), '--project', str(root),
        '--model', aliases['asi'], '--endpoint', endpoint, '--key-file', key,
        '--output', str(asi), '--parallel', '8', '--cpu-offset', '96']
    if args.resume_after_asi_pid:
        save(output / 'state.json', {'state': 'asi_generation', 'pid': args.resume_after_asi_pid,
            'coordinator_reattached': True, 'at_utc': now()})
        while Path(f'/proc/{args.resume_after_asi_pid}').exists():
            time.sleep(10)
    else:
        save(output / 'asi_launch.json', {'command': command, 'at_utc': now()})
        p = launch(command, output / 'asi_generation.log', root)
        save(output / 'state.json', {'state': 'asi_generation', 'pid': p.pid, 'at_utc': now()})
        if p.wait():
            raise RuntimeError('ASI generation failed; retain all attempts and stop pipeline')
    if not (asi / 'generation_cpu_finished.json').exists():
        raise RuntimeError('ASI generation did not fully drain; retain all attempts and stop pipeline')
    protocol = json.loads((root / 'configs/eval/protocol_v2_unified64k8k.json').read_text())
    order = json.loads((root / protocol['benchmarks']['hle']['task_manifest']).read_text())['task_ids']
    hle.mkdir(parents=True, exist_ok=True)
    save(hle / 'manual_retry_manifest.json', {'selection_rule': 'One frozen terminal result per ID; no retries or score selection',
        'retained': [{'id': i, 'manual_retry_index': 0, 'original_result': str(hle / 'questions' / (i + '.json'))} for i in order],
        'selected': [], 'expected_questions': 2500, 'formal_model': aliases['hle']})
    hlegen = [pyhle, str(root / 'scripts/run_direct_hle_formal.py'), '--project', str(root),
        '--mode', 'formal', '--model', aliases['hle'], '--endpoint', endpoint,
        '--key-file', key, '--output', str(hle)]
    hlescore = [pyhle, str(root / 'scripts/score_direct_hle_formal.py'), '--project', str(root),
        '--retry', str(hle), '--output', str(hle / 'scoring'), '--max-cny', '20', '--max-calls', '5000', '--workers', '2']
    hg = launch(hlegen, output / 'hle_generation.log', root)
    hs = launch(hlescore, output / 'hle_scoring.log', root)
    save(output / 'hle_launch.json', {'generation': hlegen, 'generation_pid': hg.pid,
        'scoring': hlescore, 'scoring_pid': hs.pid, 'at_utc': now()})
    # All ASI graders share this four-core lease; native grader timeouts stay unchanged.
    grade_lock = (root / 'artifacts/eval/direct_asi_grader_cpu92_95.lock').open('a')
    if merged:
        wait_marker(root / 'artifacts/eval/asi128_asi240_20261017/all_cpu_consumers_finished.json', 'state', 'finished')
    fcntl.flock(grade_lock, fcntl.LOCK_EX)
    runtime = asi / 'scoring/runtime'
    if not runtime.exists():
        shutil.copytree(root / 'artifacts/asi/scoring_v2_formal_params_20261016/runtime', runtime)
    env = dict(os.environ, PYTHONPATH=str(runtime), PYTHONDONTWRITEBYTECODE='1')
    score = ['taskset', '-c', '92-95', pyasi, str(runtime / 'scripts/score_asi_baseline_v2.py'),
        '--project', str(root), '--results', str(asi),
        '--instances', str(root / 'artifacts/asi/scoring_seed31415/instances'),
        '--output', str(asi / 'scoring'),
        '--judge-identity', str(root / 'artifacts/preflight/asi-real-calibration-20261016/judge_identity.json'),
        '--ngspice-runtime', str(root / 'artifacts/asi/scoring_ngspice_20261016/rootfs'),
        '--credentials', str(root / 'artifacts/private/deepseek.env'),
        '--max-generation-calls', '396', '--max-cny', '20', '--allow-paid-api',
        '--skip-hashes', '--workers', '1', '--condition-timeout', '7200']
    sp = launch(score, output / 'asi_scoring.log', root, env)
    save(output / 'asi_score_launch.json', {'command': score, 'pid': sp.pid, 'at_utc': now(),
        'source_runtime': 'artifacts/asi/scoring_v2_formal_params_20261016/runtime', 'cpu_lease': '92–95'})
    rc = sp.wait()
    report_path = asi / 'scoring/local_score_seed31415.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    remaining_scopes = active_program_scopes(range(92, 96))
    if remaining_scopes:
        save(output / 'state.json', {'state': 'paused_cpu_scope_drain', 'active_scopes': remaining_scopes, 'at_utc': now()})
        raise RuntimeError('Owned CPU programs have not fully drained; no release marker')
    save(asi / 'all_cpu_consumers_finished.json', {'state': 'finished', 'at_utc': now(),
        'generation_conditions': 240, 'generation_cpu_sets': [list(range(i, i + 4)) for i in range(96, 128, 4)],
        'grader_cpus': list(range(92, 96)), 'grader_process_exitcode': rc,
        'grader_complete': report.get('complete', False), 'scorer_error_count': report.get('scorer_error_count'),
        'generation_worker_pool_shutdown': True, 'grader_process_finished': True, 'active_program_scopes': remaining_scopes})
    fcntl.flock(grade_lock, fcntl.LOCK_UN)
    save(output / 'state.json', {'state': 'hle_generation_and_scoring', 'at_utc': now(),
        'hle_generation_pid': hg.pid, 'hle_scoring_pid': hs.pid})
    grc, src = hg.wait(), hs.wait()
    save(output / 'state.json', {'state': 'finished', 'at_utc': now(),
        'asi_scoring_exitcode': rc, 'hle_generation_exitcode': grc, 'hle_scoring_exitcode': src})


if __name__ == '__main__':
    os.umask(0o077)
    main()
