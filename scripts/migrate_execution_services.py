"""Drain two owned execution services, replace in acd_u, resume only unadmitted IDs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time

import httpx


def now():
    return datetime.now(timezone.utc)


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    tmp.replace(path)


def process(pid, ticks=None):
    try:
        p = Path('/proc') / str(pid)
        stat = (p / 'stat').read_text().rsplit(')', 1)[1].split()
        return stat[0] != 'Z' and (ticks is None or stat[19] == ticks)
    except (FileNotFoundError, ProcessLookupError):
        return False


def busy_scopes(cpus):
    busy = set()
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            group = (p / 'cgroup').read_text()
            if (any(prefix in group for prefix in ('apex-baseline-', 'apex-asi-', 'ai4sci-submission-'))
                    and set(cpus).intersection(os.sched_getaffinity(int(p.name)))):
                busy.add(group.strip().split('/')[-1])
        except (OSError, ProcessLookupError):
            pass
    return sorted(busy)


class Migration:
    def __init__(self, config):
        self.config = config
        self.root = Path(config['project'])
        self.output = self.root / config['state_output']
        self.context = {x['output']: x for x in load(self.root / config['launch_context'])['queues']}
        self.ssh = ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
            '-o', 'ControlMaster=auto', '-o', 'ControlPersist=600',
            '-o', 'ControlPath=/tmp/apex-execution-migration-hpc-ctl',
            '-o', 'HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn',
            '-o', 'UserKnownHostsFile=' + config['known_hosts'], '-i', config['identity_file'],
            config['hpc_user'] + '@' + config['hpc_host']]

    def hpc(self, args, check=True):
        result = subprocess.run(self.ssh + [shlex.join([str(x) for x in args])],
                                capture_output=True, text=True, timeout=45)
        if check and result.returncode:
            raise RuntimeError('HPC CLI failed: ' + result.stderr[-300:])
        return result

    def remote_json(self, path):
        result = self.hpc(['cat', path], check=False)
        if result.returncode and 'No such file' in result.stderr:
            return None
        if result.returncode:
            raise RuntimeError('HPC metadata unavailable: ' + result.stderr[-200:])
        return json.loads(result.stdout)

    def job(self, job_id):
        result = self.hpc(['squeue', '-h', '-j', job_id, '-o', '%i|%T|%P|%N|%S|%e'], check=False)
        if result.returncode and 'Invalid job id' not in result.stderr:
            raise RuntimeError('Cannot verify allocation state: ' + result.stderr[-200:])
        lines = result.stdout.strip().splitlines()
        if not lines:
            return None
        fields = lines[0].split('|')
        return dict(zip(('job', 'state', 'partition', 'node', 'start', 'end'), fields))

    def metrics(self, group):
        key = (self.root / 'artifacts/private/base_smoke_api_key').read_text().strip()
        with httpx.Client(trust_env=False, timeout=10, headers={'Authorization': 'Bearer ' + key}) as client:
            r = client.get(group['endpoint'] + '/metrics')
            r.raise_for_status()
        counts = {}
        for name in ('num_requests_running', 'num_requests_waiting'):
            prefix = 'vllm:' + name
            values = [float(line.rsplit(' ', 1)[-1]) for line in r.text.splitlines()
                      if line.startswith((prefix + '{', prefix + ' '))]
            if not values:
                raise RuntimeError('Native request counter missing: ' + name)
            counts[name] = sum(values)
        return counts

    def queue_drain(self, queue):
        out = self.root / queue['output']
        cp = load(out / 'checkpoint.json')
        context = self.context[queue['output']]
        cpus = cp.get('leased_cpu_ids', [])
        if queue['kind'] == 'terminal':
            cpus = [cpu + i for cpu in cp['leased_cpu_offsets'] for i in range(4)]
        alive = process(context['parent_pid'], context['parent_start_ticks'])
        normal = cp['state'] in ('stopped_admission', 'all445_attempts_finished',
                                 'all51_attempts_finished', 'service_expiring')
        ready = not alive and not cp['active'] and normal
        return {'ready': ready, 'parent_alive': alive, 'checkpoint_state': cp['state'],
                'active': len(cp['active']), 'pending': len(cp['pending']),
                'terminal': len(cp['terminal']), 'cpu_ids': cpus}

    def retarget(self, group, state, folder):
        config_path = self.root / group['tunnel_config']
        tunnel = load(config_path)
        for worker in tunnel['workers']:
            if worker['benchmark'] == group['tunnel_worker']:
                worker.update(job_id=int(state['new_job']), node=state['new_node'])
        save(config_path, tunnel)
        pid = state.get('tunnel_supervisor_pid') or group['old_tunnel_supervisor_pid']
        if not pid or not process(pid):
            old = group['old_forward_pid']
            if process(old):
                command = (Path('/proc') / str(old) / 'cmdline').read_bytes().decode()
                assert f"127.0.0.1:{group['bridge_port']}:" in command and 'ssh' in command
                os.kill(old, signal.SIGTERM)
                while process(old):
                    time.sleep(1)
            with (folder / 'tunnel-supervisor.log').open('ab') as log:
                child = subprocess.Popen([sys.executable, str(self.root / 'scripts/supervise_hpc_tunnels.py'),
                    '--config', str(config_path), '--state-dir', str(self.root / group['tunnel_state'])],
                    cwd=self.root, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
            state['tunnel_supervisor_pid'] = child.pid
        else:
            state['tunnel_supervisor_pid'] = pid

    def acceptance(self, group, folder):
        path = folder / 'service-acceptance.json'
        if path.exists():
            assert load(path)['ready']
            return
        key = (self.root / 'artifacts/private/base_smoke_api_key').read_text().strip()
        template = {'enable_thinking': False, 'preserve_thinking': False}
        messages = [{'role': 'user', 'content': 'Return exactly MIGRATION_READY.'}]
        with httpx.Client(trust_env=False, headers={'Authorization': 'Bearer ' + key}, timeout=120) as client:
            models = client.get(group['endpoint'] + '/v1/models')
            models.raise_for_status()
            ids = {row['id'] for row in models.json()['data']}
            assert {group['model'], group['base_alias']} <= ids
            count = client.post(group['endpoint'] + '/tokenize', json={'model': group['model'],
                'messages': messages, 'add_generation_prompt': True, 'chat_template_kwargs': template})
            count.raise_for_status()
            assert count.json()['max_model_len'] == 65536
            started = folder / 'synthetic-request-started.json'
            assert not started.exists(), 'Ambiguous prior synthetic request; retain rather than repeat'
            save(started, {'at': now().isoformat(), 'model': group['model'], 'formal_questions': 0})
            response = client.post(group['endpoint'] + '/v1/chat/completions', json={
                'model': group['model'], 'messages': messages, 'max_tokens': 32, 'temperature': 0,
                'seed': 0, 'chat_template_kwargs': template})
            response.raise_for_status()
            data = response.json()
            save(folder / 'synthetic-response.json', data)
            message = data['choices'][0]['message']
            assert 'MIGRATION_READY' in message['content']
            assert not message.get('reasoning') and not message.get('reasoning_content')
            assert data['usage']['prompt_tokens'] == count.json()['count']
            assert data['usage']['completion_tokens'] <= 32
        save(path, {'ready': True, 'at': now().isoformat(), 'model': group['model'],
            'model_ids': sorted(ids), 'context_tokens': 65536, 'synthetic_output_cap': 32,
            'formal_output_cap_unchanged': 8192, 'synthetic_generation_requests': 1,
            'formal_or_validation_questions': 0, 'usage': data['usage']})

    def resume(self, group, queue, state, folder):
        out = self.root / queue['output']
        context = self.context[queue['output']]
        name = out.name
        receipt = folder / (name + '-resume.json')
        if receipt.exists():
            saved = load(receipt)
            if saved.get('pid') and process(saved['pid']):
                return saved
            raise RuntimeError('Existing resume intent/process requires audit; no duplicate controller')
        checkpoint = load(out / 'checkpoint.json')
        assert not checkpoint['active']
        assert len(checkpoint['terminal']) + len(checkpoint['pending']) == queue['expected']
        terminal = checkpoint['terminal']
        if not checkpoint['pending']:
            return {'already_finished': True, 'terminal': len(terminal)}
        before = folder / 'before-resume' / name
        before.mkdir(parents=True, exist_ok=True)
        for filename in ('checkpoint.json', 'summary.json', 'config.json', 'experiment.json',
                         'controller.json', 'admission-opened.json', 'initial-admission-opened.json',
                         'cpu-handoffs.json', 'source-expert-consumers-finished.json'):
            if (out / filename).exists() and not (before / filename).exists():
                shutil.copy2(out / filename, before / filename)
        config_path = self.root / queue['config']
        config = load(config_path)
        config.update(service_job=str(state['new_job']), service_node=state['new_node'],
            service_ends=state['service_ends'], service_partition='acd_u', service_nice=1000,
            service_migration_receipt=str(folder.relative_to(self.root) / 'state.json'))
        if queue['kind'] == 'swe':
            config['native_service_log_hpc'] = (self.config['hpc_project'] + '/artifacts/eval/' +
                group['service_launch_prefix'] + str(state['new_job']) + '.log')
            config['stop_new_tasks_after'] = (datetime.fromisoformat(state['service_ends']) - timedelta(seconds=2100)).isoformat()
        save(config_path, config)
        if queue['kind'] == 'terminal':
            save(out / 'config.json', config)
        if queue['kind'] == 'swe':
            staged = self.output / 'staged/run_swe_merged_benchmark.py'
            shutil.copy2(staged, self.root / 'scripts/run_swe_merged_benchmark.py')
        marker = out / 'STOP_ADMISSION'
        assert load(marker)['owner'] == self.config['migration_id'], 'Do not clear a foreign STOP reason'
        save(receipt, {'state': 'launch_intent', 'at': now().isoformat(),
            'terminal_before': len(terminal), 'pending_before': len(checkpoint['pending']),
            'original_parent': context['parent_pid'], 'argv': context['argv']})
        marker.unlink()
        env = dict(os.environ)
        env.update(context['environment'])
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        with (folder / (name + '-resume.log')).open('ab') as log:
            child = subprocess.Popen(context['argv'], cwd=self.root, env=env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=log, start_new_session=True)
        value = {'state': 'launched', 'at': now().isoformat(), 'pid': child.pid,
            'terminal_before': len(terminal), 'pending_before': len(checkpoint['pending']),
            'original_parent': context['parent_pid'], 'argv': context['argv'],
            'retained_terminal_ledger': str((before / 'checkpoint.json').relative_to(self.root))}
        save(receipt, value)
        time.sleep(3)
        assert child.poll() is None, 'Resumed parent exited; retain STOP/ledger for audit'
        current = load(out / 'checkpoint.json')
        assert all(current['terminal'].get(key) == row for key, row in terminal.items())
        return value

    def run_group(self, group):
        folder = self.output / group['name']
        folder.mkdir(parents=True, exist_ok=True)
        state_path = folder / 'state.json'
        state = load(state_path) if state_path.exists() else {'group': group['name'], 'old_job': group['old_job']}
        if state.get('stage') in ('resumed', 'finished_no_remaining_work'):
            return

        def status(stage, **extra):
            state.update(stage=stage, at_utc=now().isoformat(), **extra)
            save(state_path, state)

        hard_end = min(datetime.fromisoformat(group['hard_end']), datetime.fromisoformat(self.config['hard_cap']))
        old_launch_path = (self.config['hpc_project'] + '/artifacts/eval/' +
                          group['service_launch_prefix'] + str(group['old_job']) + '/launch.json')
        old_launch_file = folder / 'old-service-launch.json'
        if not old_launch_file.exists():
            save(old_launch_file, self.remote_json(old_launch_path))
        old_launch = load(old_launch_file)
        if not state.get('drain_proof'):
            idle_samples = 0
            while True:
                drains = {q['output']: self.queue_drain(q) for q in group['queues']}
                cpus = sorted({cpu for item in drains.values() for cpu in item['cpu_ids']})
                busy = busy_scopes(cpus)
                metric = None
                if all(item['ready'] for item in drains.values()) and not busy:
                    try:
                        metric = self.metrics(group)
                    except (httpx.HTTPError, RuntimeError):
                        metric = None
                idle_samples = idle_samples + 1 if metric is not None and all(v == 0 for v in metric.values()) else 0
                status('waiting_original_consumers', queue_drains=drains, remaining_cpu_scopes=busy,
                       native_requests=metric, consecutive_idle_samples=idle_samples)
                if idle_samples >= 2:
                    state['drain_proof'] = {'at': now().isoformat(), 'queue_drains': drains,
                        'cpu_ids': cpus, 'remaining_cpu_scopes': [], 'native_requests': metric,
                        'original_parents_exited': True, 'two_idle_samples': True}
                    status('drained')
                    break
                time.sleep(self.config['poll_seconds'])
        if not state.get('old_gpus_released'):
            status('cancelling_old_service')
            if self.job(group['old_job']):
                self.hpc(['scancel', group['old_job']])
            while self.job(group['old_job']):
                time.sleep(self.config['poll_seconds'])
            state['old_gpus_released'] = {'at': now().isoformat(), 'job_absent_from_squeue': True}
            status('old_service_released')
        if not any(load(self.root / q['output'] / 'checkpoint.json')['pending'] for q in group['queues']):
            status('finished_no_remaining_work')
            return
        if not state.get('new_job'):
            minutes = int((hard_end - now()).total_seconds() // 60)
            assert minutes >= self.config['minimum_job_minutes'], 'Original experiment window too short; no replacement'
            intent = folder / 'submission-intent.json'
            if intent.exists():
                result = self.hpc(['squeue', '-h', '-u', self.config['hpc_user'], '-n', group['job_name'], '-o', '%i'])
                matches = result.stdout.strip().splitlines()
                assert len(matches) == 1, 'Ambiguous previous submit; never allocate a duplicate service'
                state['new_job'] = int(matches[0])
            else:
                command = ['sbatch', '--parsable', '--partition=acd_u', '--nice=1000',
                    '--job-name=' + group['job_name'], '--time=' + str(minutes),
                    '--deadline=' + hard_end.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S'),
                    self.config['hpc_project'] + '/' + group['slurm_script']]
                save(intent, {'at': now().isoformat(), 'command': command,
                    'old_job_released_before_submission': state['old_gpus_released'], 'hard_end': hard_end.isoformat()})
                result = self.hpc(command)
                state['new_job'] = int(result.stdout.strip().split(';')[0])
            status('replacement_submitted')
        while True:
            if now() >= hard_end:
                self.hpc(['scancel', state['new_job']], check=False)
                raise RuntimeError('Original experiment deadline reached; no extension or emergency fallback')
            job = self.job(state['new_job'])
            status('waiting_ordinary_allocation', replacement_job=job)
            if job and job['state'] == 'RUNNING':
                assert job['partition'] == 'acd_u'
                state['new_node'] = job['node']
                end = datetime.fromisoformat(job['end']).replace(tzinfo=timezone(timedelta(hours=8)))
                if end > hard_end:
                    self.hpc(['scontrol', 'update', 'JobId=' + str(state['new_job']),
                              'EndTime=' + hard_end.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%dT%H:%M:%S')])
                    job = self.job(state['new_job'])
                    end = datetime.fromisoformat(job['end']).replace(tzinfo=timezone(timedelta(hours=8)))
                assert end <= hard_end
                state['service_ends'] = end.isoformat()
                break
            if job is None:
                raise RuntimeError('Replacement ended before acceptance; retain all existing attempts')
            time.sleep(self.config['poll_seconds'])
        meta = self.hpc(['scontrol', 'show', 'job', state['new_job'], '-o']).stdout
        assert 'Partition=acd_u' in meta and re.search(r'\bNice=1000(?: |$)', meta)
        assert 'NumCPUs=16' in meta and 'NumNodes=1' in meta and 'QOS=formal-user' in meta
        allocated = re.search(r'\bAllocTRES=([^ ]+)', meta).group(1).split(',')
        assert 'gres/gpu=2' in allocated and 'mem=128G' in allocated
        save(folder / 'replacement-slurm.json', {'at': now().isoformat(), 'scontrol': meta,
             'hard_end': hard_end.isoformat(), 'actual_service_ends': state['service_ends']})
        launch_path = (self.config['hpc_project'] + '/artifacts/eval/' +
                       group['service_launch_prefix'] + str(state['new_job']) + '/launch.json')
        self.retarget(group, state, folder)
        status('waiting_replacement_health')
        while True:
            assert now() < hard_end, 'Original hard deadline reached during model load'
            assert self.job(state['new_job']) is not None, 'Replacement ended during model load'
            fresh = self.remote_json(launch_path)
            if fresh:
                for key in ('model_revision', 'context_tokens', 'output_cap_per_request', 'adapter',
                            'port', 'max_num_seqs', 'thinking', 'preserve_thinking', 'command'):
                    assert fresh[key] == old_launch[key], 'Frozen deployment mismatch: ' + key
                save(folder / 'replacement-service-launch.json', fresh)
                try:
                    with httpx.Client(trust_env=False, timeout=5) as client:
                        healthy = client.get(group['endpoint'] + '/health').status_code == 200
                    tunnel = load(self.root / group['tunnel_state'] / 'state.json')['workers'][group['tunnel_worker']]
                    if healthy and tunnel['node'] == state['new_node'] and int(tunnel['job_id']) == state['new_job']:
                        break
                except (httpx.HTTPError, FileNotFoundError, KeyError):
                    pass
            time.sleep(self.config['poll_seconds'])
        self.acceptance(group, folder)
        status('accepted_same_frozen_deployment')
        resumes = {}
        for queue in group['queues']:
            resumes[queue['output']] = self.resume(group, queue, state, folder)
        status('resumed', resumed_queues=resumes, unadmitted_only=True,
               original_answers_unchanged=True, old_cancelled_before_new_submission=True)

    def guarded_group(self, group):
        try:
            self.run_group(group)
        except Exception as error:
            path = self.output / group['name'] / 'state.json'
            state = load(path) if path.exists() else {'group': group['name']}
            state.update(stage='needs_attention', at_utc=now().isoformat(), error_type=type(error).__name__, error=str(error))
            save(path, state)
            print(group['name'] + ': ' + type(error).__name__ + ': ' + str(error), flush=True)

    def run(self):
        self.output.mkdir(parents=True, exist_ok=True)
        lock = (self.output / 'driver.lock').open('a')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.guarded_group, group) for group in self.config['groups']]
            while True:
                groups = {g['name']: load(self.output / g['name'] / 'state.json')
                          for g in self.config['groups'] if (self.output / g['name'] / 'state.json').exists()}
                save(self.output / 'state.json', {'at_utc': now().isoformat(), 'pid': os.getpid(),
                    'partition': 'acd_u', 'nice': 1000, 'groups': groups,
                    'all_driver_workers_finished': all(f.done() for f in futures)})
                if all(f.done() for f in futures):
                    break
                time.sleep(self.config['poll_seconds'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    Migration(load(args.config.resolve())).run()
