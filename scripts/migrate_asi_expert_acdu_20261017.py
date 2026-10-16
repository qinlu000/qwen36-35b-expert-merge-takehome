#!/usr/bin/env python3
"""Pause only the existing ASI parent, drain its workers, replace its TP2 service.

Run on host80. No trial is cancelled or resubmitted; the same parent is resumed.
The already-written pause.json pins its PID/starttime and admission/audit ledger.
"""
import argparse
from datetime import datetime, timezone, timedelta
import fcntl
import json
import math
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time
import urllib.request


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def read(path):
    return json.loads(path.read_text())


def parent_state(pid, starttime):
    fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
    assert fields[19] == str(starttime), 'Parent PID identity changed'
    return fields[0]


def terminal_conditions(output, expected):
    terminal = []
    for condition in expected:
        task = condition.split('__seed31415__')[0]
        path = output / task / (condition + '.json')
        if path.exists():
            try:
                result = read(path)
            except json.JSONDecodeError:
                continue  # Native _save_result may still be writing this file.
            assert result['task_id'] == task
            terminal.append(condition)
    return terminal


def active_scopes(cpus, owned):
    listing = subprocess.check_output(['systemctl', '--user', 'list-units', '--type=scope',
        '--state=running', '--no-legend', '--plain'], text=True)
    rows = []
    for line in listing.splitlines():
        scope = line.split()[0]
        if scope not in owned and not scope.startswith('apex-asi-'):
            continue
        group = subprocess.check_output(['systemctl', '--user', 'show', scope,
            '--property=ControlGroup', '--value'], text=True).strip()
        directory = Path('/sys/fs/cgroup') / group.lstrip('/')
        actual, count, examples = set(), 0, []
        for path in directory.rglob('cgroup.procs'):
            for text in path.read_text().split():
                try:
                    actual.update(os.sched_getaffinity(int(text)))
                    count += 1
                    if len(examples) < 3:
                        examples.append(int(text))
                except ProcessLookupError:
                    pass
        if count and (scope in owned or actual.intersection(cpus)):
            rows.append({'scope': scope, 'process_count': count,
                         'actual_cpu_union': sorted(actual), 'pid_examples': examples})
    return rows


def idle_metrics(text):
    values = {}
    for name in ('num_requests_running', 'num_requests_waiting'):
        matches = re.findall(r'^vllm:' + name + r'(?:\{[^\n]*\})?\s+([0-9.eE+-]+)', text, re.M)
        assert matches, 'Missing vLLM metric ' + name
        values[name] = sum(float(value) for value in matches)
    return values


def drained(snapshot):
    return (not snapshot['admitted_without_terminal'] and not snapshot['started_without_terminal']
            and not snapshot['active_scopes']
            and snapshot['metrics']['num_requests_running'] == 0
            and snapshot['metrics']['num_requests_waiting'] == 0)


def request(endpoint, path, key, payload=None, timeout=15):
    headers = {'Authorization': 'Bearer ' + key}
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    call = urllib.request.Request(endpoint + path,
        data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(call, timeout=timeout) as response:
        body = response.read().decode()
    return body if path == '/metrics' else (json.loads(body) if body else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    config = read(args.config)
    state = root / config['state_dir']
    state.mkdir(parents=True, exist_ok=True)
    lock = (state / 'driver.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    pause = read(state / 'pause.json')
    pid, starttime = pause['pid'], pause['starttime_ticks']
    assert pid == config['parent_pid'] and starttime == config['parent_starttime_ticks']
    assert parent_state(pid, starttime) == 'T'
    output = root / config['formal_output']
    expected = pause['expected_conditions']
    assert len(expected) == len(set(expected)) == 240
    admitted = set(pause['started_conditions']) | set(pause['progress_at_pause']['active'])
    assert admitted <= set(expected)
    key = (root / 'artifacts/private/base_smoke_api_key').read_text().strip()
    endpoint = config['endpoint']
    ssh = ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
        '-o', 'ConnectTimeout=8', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn',
        '-o', 'UserKnownHostsFile=' + str(root / 'artifacts/private/baseline_hpc_known_hosts'),
        '-i', config['ssh_identity'], config['hpc_user'] + '@' + config['hpc_host']]
    remote_root = config['hpc_project']
    status = {'state': 'draining', 'at_utc': now(), 'driver_pid': os.getpid(),
              'parent_pid': pid, 'parent_starttime_ticks': starttime,
              'old_job': config['old_job'], 'formal_output': config['formal_output']}

    def remote(code):
        call = subprocess.run(ssh + ['python3 -c ' + shlex.quote(code)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=50)
        if call.returncode:
            raise RuntimeError('HPC CLI failed: ' + call.stderr[-1500:])
        return json.loads(call.stdout)

    def update(**values):
        status.update(values, at_utc=now())
        save(state / 'state.json', status)
        print(json.dumps({k: status[k] for k in ('state', 'at_utc', 'driver_pid')}), flush=True)

    def job(job_id):
        return remote("import json,subprocess\np=subprocess.run(['scontrol','show','job','-o'," + repr(str(job_id)) +
            "],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)\n"
            "x=dict(t.split('=',1) for t in p.stdout.split() if '=' in t) if p.returncode==0 else {'JobState':'ABSENT'}\n"
            "x['queue_state']=subprocess.check_output(['squeue','-h','-j'," + repr(str(job_id)) + ",'-o','%t'],universal_newlines=True).strip()\nprint(json.dumps(x))")

    try:
        update()
        stable = 0
        while stable < 2:
            assert parent_state(pid, starttime) == 'T'
            started = {p.name[:-13] for p in (output / 'audit').glob('*.started.json')}
            assert started <= set(expected)
            admitted.update(started)
            terminal = set(terminal_conditions(output, expected))
            owned = {Path(read(p)['cgroup']).name for p in (output / 'audit').glob('*.limits.json')}
            snapshot = {'at_utc': now(), 'parent_state': 'T', 'started_count': len(started),
                'terminal_count': len(terminal), 'admitted_count': len(admitted),
                'admitted_without_terminal': sorted(admitted - terminal),
                'started_without_terminal': sorted(started - terminal),
                'active_scopes': active_scopes(set(config['cpu_ids']), owned),
                'metrics': idle_metrics(request(endpoint, '/metrics', key)),
                'progress_active_is_stale_and_not_a_gate': True}
            save(state / 'drain-latest.json', snapshot)
            stable = stable + 1 if drained(snapshot) else 0
            update(drain=snapshot, consecutive_drained_checks=stable)
            if stable < 2:
                time.sleep(config['poll_seconds'])
        save(state / 'drain-confirmed.json', snapshot)
        old = job(config['old_job'])
        assert old['JobState'] in ('RUNNING', 'COMPLETING', 'CANCELLED', 'COMPLETED', 'ABSENT')
        if old['JobState'] == 'RUNNING':
            remote("import json,subprocess\nsubprocess.check_call(['scancel'," + repr(str(config['old_job'])) + "])\nprint(json.dumps({'cancelled':" + str(config['old_job']) + "}))")
        update(state='old_job_releasing', old_job_at_release=old, old_release_requested_at_utc=now())
        while job(config['old_job'])['queue_state']:
            time.sleep(config['poll_seconds'])
        old_deadline = datetime.fromisoformat(pause['old_service']['EndTime']).replace(
            tzinfo=timezone(timedelta(hours=8)))
        cap = datetime.fromisoformat(config['absolute_cap'])
        deadline = min(old_deadline, cap)
        remaining_minutes = math.floor((deadline - datetime.now(timezone.utc)).total_seconds() / 60)
        assert remaining_minutes >= 10, 'Original service deadline too close to migrate'
        submit_code = """import json,subprocess,fcntl
from pathlib import Path
root=Path(ROOT)
state=root/STATE
state.mkdir(parents=True,exist_ok=True)
lock=(state/'submission.lock').open('a')
fcntl.flock(lock,fcntl.LOCK_EX)
receipt=state/'submitted.json'
if receipt.exists():
 print(receipt.read_text())
else:
 existing=subprocess.check_output(['squeue','-h','-u','qinlucao','-n',NAME,'-o','%i'],universal_newlines=True).split()
 assert len(existing)<=1
 if existing: jid=existing[0]
 else:
  jid=subprocess.check_output(['sbatch','--parsable','--partition=acd_u','--nice=1000','--time='+str(MINUTES),'--job-name='+NAME,str(root/'scripts/serve_direct_experts.slurm'),'experts','18002'],cwd=str(root),universal_newlines=True).strip().split(';')[0]
 value={'job_id':int(jid),'partition':'acd_u','nice':1000,'time_limit_minutes_at_submit':MINUTES,'absolute_deadline':DEADLINE}
 tmp=receipt.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\\n');tmp.replace(receipt)
 print(json.dumps(value))
"""
        for token, value in [('ROOT', remote_root), ('STATE', config['state_dir']),
                             ('NAME', config['job_name']), ('DEADLINE', deadline.isoformat()),
                             ('MINUTES', remaining_minutes)]:
            submit_code = re.sub(r'\b' + token + r'\b', lambda match, value=value: repr(value), submit_code)
        submission = remote(submit_code)
        new_job = submission['job_id']
        update(state='new_job_pending', submission=submission)
        while True:
            current = job(new_job)
            assert datetime.now(timezone.utc) < deadline, 'Original deadline elapsed'
            if current['JobState'] == 'RUNNING':
                break
            assert current['JobState'] in ('PENDING', 'CONFIGURING')
            time.sleep(config['poll_seconds'])
        node = current['NodeList']
        assert re.fullmatch(r'ACD1-[0-9]+', node)
        # TimeLimit is measured from actual job start. Tighten after queue delay.
        start = datetime.fromisoformat(current['StartTime']).replace(tzinfo=timezone(timedelta(hours=8)))
        limit = math.floor((deadline - start).total_seconds() / 60)
        assert limit >= 10
        remote("import json,subprocess\nsubprocess.check_call(['scontrol','update','JobId=" + str(new_job) + "','TimeLimit=" + str(limit) + "'])\nprint(json.dumps({'time_limit_minutes':" + str(limit) + "}))")
        key_code = """import json,fcntl,os
from pathlib import Path
directory=Path('/data/user/qinlucao/.ssh')
lock=(directory/'apex-authorized-keys.lock').open('a')
fcntl.flock(lock,fcntl.LOCK_EX)
path=directory/'authorized_keys'
lines=path.read_text().splitlines()
indices=[i for i,line in enumerate(lines) if 'apex-baseline-forward-20261016' in line]
assert len(indices)==1
index=indices[0]
permit='permitopen="'+NODE+':18002"'
if permit not in lines[index].split(' ssh-ed25519 ',1)[0]:
 lines[index]=permit+','+lines[index]
 temporary=path.with_name('authorized_keys.asi-migration.tmp')
 temporary.write_text('\\n'.join(lines)+'\\n');os.chmod(str(temporary),0o600);temporary.replace(path)
print(json.dumps({'permit':permit,'lock':str(directory/'apex-authorized-keys.lock')}))
""".replace('NODE', repr(node))
        permit = remote(key_code)
        config_lock = (root / 'artifacts/eval/direct_config_update.lock').open('a')
        with config_lock:
            fcntl.flock(config_lock, fcntl.LOCK_EX)
            formal_path = root / config['formal_config']
            formal = read(formal_path)
            formal.update(service_job_id=new_job, node=node, partition='acd_u', nice=1000,
                          service_deadline=deadline.isoformat())
            save(formal_path, formal)
            tunnel_path = root / config['tunnel_config']
            tunnel = read(tunnel_path)
            worker = next(w for w in tunnel['workers'] if w['benchmark'] == 'expert_direct')
            worker.update(job_id=new_job, node=node)
            save(tunnel_path, tunnel)
        update(state='new_service_loading', new_job=new_job, node=node, permit=permit,
               service_deadline=deadline.isoformat(), time_limit_minutes=limit)
        while True:
            current = job(new_job)
            assert current['JobState'] == 'RUNNING'
            try:
                request(endpoint, '/health', key)
                models = request(endpoint, '/v1/models', key)
                assert {'apex-asi128', 'apex-hle250'} <= {row['id'] for row in models['data']}
                break
            except (OSError, ValueError, AssertionError):
                time.sleep(config['poll_seconds'])
        launch = remote("import json,re\nfrom pathlib import Path\nroot=Path(" + repr(remote_root) + ")\np=root/'artifacts/eval/direct-expert-service-" + str(new_job) + "'/'launch.json'\nx=json.loads(p.read_text())\nlog=(root/'artifacts/eval/direct-expert-service-" + str(new_job) + ".log').read_text(errors='replace')[-300000:]\nprint(json.dumps({'launch':x,'ignored_adapter_warning_lines':[line for line in log.splitlines() if re.search(r'(ignored.*lora|lora.*ignored|unsupported.*lora|skipping.*lora|unexpected.*lora|lora.*unexpected)',line,re.I)]}))")
        metadata = launch['launch']
        assert metadata['profile'] == 'experts' and metadata['context_tokens'] == 65536
        assert metadata['max_num_seqs'] == 50 and metadata['max_lora_rank'] == 16
        assert metadata['adapters']['apex-asi128']['path'].endswith('/checkpoint-128')
        assert not launch['ignored_adapter_warning_lines']
        save(state / 'service-launch-verification.json', launch)
        # Exactly one small deployment check, identical text to original acceptance.
        messages = [{'role': 'user', 'content': [{'type': 'text', 'text': 'What is 17 + 25?'}]}]
        template = {'enable_thinking': False, 'preserve_thinking': False}
        tokenized = request(endpoint, '/tokenize', key, {'model': 'apex-asi128',
            'messages': messages, 'add_generation_prompt': True, 'chat_template_kwargs': template}, 60)
        payload = request(endpoint, '/v1/chat/completions', key, {'model': 'apex-asi128',
            'messages': messages, 'max_tokens': 32, 'temperature': 0, 'seed': 0,
            'chat_template_kwargs': template}, 120)
        save(state / 'acceptance.response.json', payload)
        message = payload['choices'][0]['message']
        assert payload['usage']['prompt_tokens'] == tokenized['count']
        assert tokenized['max_model_len'] == 65536
        assert not message.get('reasoning') and not message.get('reasoning_content')
        assert '42' in message['content']
        save(state / 'acceptance.json', {'ready': True, 'at_utc': now(), 'new_job': new_job,
            'node': node, 'model': 'apex-asi128', 'model_requests': 1,
            'synthetic_only': True, 'formal_or_validation_questions': 0,
            'prompt_tokens': tokenized['count'], 'usage': payload['usage']})
        while any(idle_metrics(request(endpoint, '/metrics', key)).values()):
            time.sleep(2)
        assert parent_state(pid, starttime) == 'T'
        os.kill(pid, signal.SIGCONT)
        update(state='parent_resumed', resumed_at_utc=now(), acceptance_ready=True)
        time.sleep(3)
        update(state='finished', parent_state=parent_state(pid, starttime),
               progress_after_resume={k: v for k, v in read(output / 'progress.json').items()
                                      if k not in ('admitted_this_session', 'completed_this_session')})
    except BaseException as error:
        update(state='failed_parent_remains_paused_unless_already_resumed',
               error_class=type(error).__name__, error=str(error))
        raise


if __name__ == '__main__':
    main()
