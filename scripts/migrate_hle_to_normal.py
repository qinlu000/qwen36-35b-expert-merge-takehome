"""Drain HLE requests, replace emergency replicas on acd_u, then resume untouched ledgers."""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import time

import httpx

from run_direct_formal_pipeline import acceptance, launch, now, save
from run_dedicated_hle_formal import pid_alive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    output = root / 'artifacts/eval/hle_normal_migration_20261017'
    output.mkdir(parents=True, exist_ok=True)
    lock = (output / 'driver.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ssh = ['ssh', '-F', '/dev/null', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
        '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=yes',
        '-o', 'HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn',
        '-o', 'UserKnownHostsFile=' + str(root / 'artifacts/private/baseline_hpc_known_hosts'),
        '-i', '/home/caoqinlu/.ssh/id_ed25519_hpc3_hkustgz', 'qinlucao@10.120.81.30']
    hpc_root = '/data/user/qinlucao/projects/apex-takehome'
    def hpc(command):
        return subprocess.check_output(ssh + [shlex.join(command)], text=True, stderr=subprocess.STDOUT, timeout=45).strip()
    def status(job):
        try:
            text = hpc(['squeue', '-h', '-j', str(job), '-o', '%T|%N|%P|%e'])
        except subprocess.CalledProcessError as error:
            if error.returncode == 1 and 'Invalid job' in error.output:
                return []
            raise
        return text.split('|') if text else []
    def read(path):
        return json.loads(path.read_text())
    state_path = output / 'state.json'
    if state_path.exists():
        state = read(state_path)
        assert not any(p['phase'] == 'submitting' for p in state['profiles'].values()), 'Inspect uncertain submit before resuming'
    else:
        dedicated = read(root / 'configs/eval/hle_dedicated_formal_20261017.json')
        state = {'pid': os.getpid(), 'started_at_utc': now(), 'profiles': {}}
        for profile, old_job, serve, port, bridge, name in [
                ('expert', 727821, 'hle-expert', 18004, 28094, 'hle250_hle2500_20261017'),
                ('merged', 727822, 'hle-merged', 18005, 28095, 'avg64_hle2500_20261017'),
                ('controls', 727831, 'controls', 18006, 28096, 'mixed883_hle2500_20261017')]:
            dest = root / 'artifacts/eval' / name
            if profile == 'controls':
                previous = read(dest / 'task_control_launch.json')
                parent = read(root / 'artifacts/eval/hle_task_controls_20261017/controller.json')['pid']
            else:
                previous = read(dest / 'controller/launch.json')
                parent = read(dest / 'controller/controller.json')['pid']
            old = status(old_job)
            cap = datetime(2026, 10, 18, 2, 20, tzinfo=timezone(timedelta(hours=8)))
            if old:
                cap = min(cap, datetime.fromisoformat(old[3]).replace(tzinfo=timezone(timedelta(hours=8))))
            p = {'old_job': old_job, 'serve_profile': serve, 'port': port, 'bridge': bridge,
                'output': str(dest), 'old_parent_pid': parent, 'old_generator_pid': previous['generation_pid'],
                'grader_pid': previous['scoring_pid'], 'original_launch': previous, 'phase': 'draining',
                'end_cap_utc': cap.astimezone(timezone.utc).isoformat()}
            state['profiles'][profile] = p
            (dest / 'STOP_ADMISSION').write_text('Drain for ordinary acd_u migration; preserve original 300s deadlines.\n')
        save(state_path, state)
    state['pid'] = os.getpid()
    save(output / 'controller.json', {'pid': os.getpid(), 'script': str(Path(__file__).resolve()), 'at_utc': now()})
    key = (root / 'artifacts/private/base_smoke_api_key').read_text().strip()
    def request(port, path):
        with httpx.Client(trust_env=False, headers={'Authorization': 'Bearer ' + key}, timeout=5) as client:
            r = client.get('http://127.0.0.1:' + str(port) + path)
            r.raise_for_status()
            return r.text
    def no_requests(port):
        try:
            lines = request(port, '/metrics').splitlines()
        except httpx.HTTPError:
            return False
        values = [float(s.rsplit(' ', 1)[1]) for s in lines if s.startswith(
            ('vllm:num_requests_running{', 'vllm:num_requests_waiting{'))]
        return len(values) >= 2 and sum(values) == 0
    def update_routes(profile, p):
        node, port = p['node'], str(p['port'])
        assert re.fullmatch(r'ACD1-\d+', node)
        # All agents use this independent lock and reread the current authorized_keys.
        code = """from pathlib import Path
import fcntl,sys
p=Path.home()/'.ssh/authorized_keys'
with (Path.home()/'.ssh/apex-authorized-keys.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 lines=p.read_text().splitlines(); count=0
 for i,line in enumerate(lines):
  if line.endswith('apex-baseline-forward-20261016'):
   count+=1; options,key=line.split(' ssh-ed25519 ',1)
   item='permitopen="'+sys.argv[1]+':'+sys.argv[2]+'"'
   if item not in options:options+=','+item
   lines[i]=options+' ssh-ed25519 '+key
 assert count==1
 q=p.with_name('authorized_keys.hle.tmp');q.write_text('\\n'.join(lines)+'\\n');q.chmod(0o600);q.replace(p)
print('exact permit present')
"""
        hpc(['python3', '-c', code, node, port])
        with (root / 'artifacts/eval/direct_config_update.lock').open('a') as cfg_lock:
            fcntl.flock(cfg_lock, fcntl.LOCK_EX)
            tunnel = root / 'configs/eval' / ('hle_controls_tunnel_20261017.json' if profile == 'controls' else 'hle_dedicated_tunnels_20261017.json')
            cfg = read(tunnel)
            for worker in cfg['workers']:
                if worker['bridge_port'] == p['bridge']:
                    worker.update(job_id=p['new_job'], node=node)
            save(tunnel, cfg)
            if profile != 'controls':
                path = root / 'configs/eval/hle_dedicated_formal_20261017.json';cfg = read(path)
                cfg[profile].update(service_job_id=p['new_job'], service_node=node, partition='acd_u', nice=1000,
                                    service_deadline=p['end_cap_utc'])
                save(path, cfg)
                path = root / 'configs/eval' / ('expert_direct_formal_20261017.json' if profile == 'expert' else 'merged_direct_formal_20261017.json')
                cfg = read(path);cfg['hle'].update(service_job_id=p['new_job'], service_node=node,
                    partition='acd_u', nice=1000, service_deadline=p['end_cap_utc']);save(path,cfg)
    while not all(p['phase'] in ('resumed', 'expired', 'failed') for p in state['profiles'].values()):
        for profile, p in state['profiles'].items():
            dest = Path(p['output'])
            try:
                if p['phase'] == 'draining':
                    c = read(dest / 'checkpoint.json')
                    started = {q.name.removesuffix('.started.json') for q in (dest / 'questions').glob('*.started.json')}
                    terminal = {q.stem for q in (dest / 'questions').glob('*.json') if not q.name.endswith('.started.json')}
                    if (pid_alive(p['old_generator_pid']) or c.get('active', []) or
                            c.get('cancelled_or_unwinding', []) or started - terminal or not no_requests(p['bridge'])):
                        continue
                    p['drain_proof'] = {'at_utc': now(), 'generator_exited': True, 'active': [],
                        'incomplete_started': [], 'model_requests_running_and_waiting': 0,
                        'saved_results': len(terminal), 'original_checkpoint': c}
                    if pid_alive(p['old_parent_pid']):
                        os.kill(p['old_parent_pid'], signal.SIGTERM)  # Only the idle coordinator, never its grader.
                    p['grader_preserved_alive'] = pid_alive(p['grader_pid'])
                    p['phase'] = 'releasing_old';save(state_path,state)
                    hpc(['scancel',str(p['old_job'])])
                elif p['phase'] == 'releasing_old':
                    if status(p['old_job']):continue
                    minutes = int((datetime.fromisoformat(p['end_cap_utc'])-datetime.now(timezone.utc)).total_seconds()//60)
                    if minutes <= 0:p['phase']='expired';continue
                    p['phase']='submitting';save(state_path,state)
                    job=hpc(['sbatch','--parsable','--partition=acd_u','--nice=1000','--time='+str(minutes),
                        '--job-name=apex-hle-normal-'+profile,hpc_root+'/scripts/serve_direct_experts.slurm',p['serve_profile'],str(p['port'])]).split(';')[0]
                    assert job.isdigit();p['new_job']=int(job);p['phase']='waiting_running'
                elif p['phase'] == 'waiting_running':
                    row=status(p['new_job'])
                    if not row:raise RuntimeError('New normal job disappeared before acceptance')
                    if row[0]!='RUNNING':continue
                    assert row[2]=='acd_u';p['node']=row[1]
                    info=dict(s.split('=',1) for s in hpc(['scontrol','show','job','-o',str(p['new_job'])]).split() if '=' in s)
                    start=datetime.fromisoformat(info['StartTime']).replace(tzinfo=timezone(timedelta(hours=8)))
                    minutes=int((datetime.fromisoformat(p['end_cap_utc'])-start).total_seconds()//60)
                    if minutes<=0:hpc(['scancel',str(p['new_job'])]);p['phase']='expired';continue
                    hpc(['scontrol','update','JobId='+str(p['new_job']),'TimeLimit='+str(minutes)])
                    update_routes(profile,p);p['phase']='waiting_service'
                elif p['phase'] == 'waiting_service':
                    try:request(p['bridge'],'/health')
                    except httpx.HTTPError:continue
                    models=({'expert':'apex-hle250','merged':'apex-avg64'} if profile!='controls' else
                            {'mixed883':'apex-mixed883','avg16':'apex-avg16'})
                    if profile!='controls':models={profile:models[profile]}
                    for name,alias in models.items():
                        receipt_dir=output/profile/('acceptance-'+str(p['new_job'])+'-'+name)
                        acceptance(root,'http://127.0.0.1:'+str(p['bridge']),{'hle':alias},receipt_dir)
                        if profile=='controls':
                            cfg=read(root/'configs/eval/hle_task_controls_20261017.json')
                            dest_receipt=root/cfg['models'][name]['output']/'service_acceptance/acceptance.json'
                            if not dest_receipt.exists():
                                save(dest_receipt,dict(read(receipt_dir/'acceptance.json'),migration_source=str(receipt_dir)))
                    p['phase']='accepted';save(state_path,state)
                elif p['phase'] == 'accepted':
                    (dest/'STOP_ADMISSION').unlink(missing_ok=True)
                    command=[str(root/'artifacts/envs/hle/bin/python'),str(root/'scripts'/(
                        'run_hle_task_controls.py' if profile=='controls' else 'run_dedicated_hle_formal.py')),
                        '--project',str(root),'--resume']
                    if profile!='controls':command+=['--profile',profile]
                    child=launch(command,output/(profile+'-resumed-controller.log'),root)
                    launch_path=dest/('task_control_launch.json' if profile=='controls' else 'controller/launch.json')
                    for _ in range(30):
                        info=read(launch_path)
                        if info.get('generation_pid') != p['old_generator_pid']:break
                        time.sleep(.1)
                    p.update(new_controller_pid=child.pid,phase='resumed',resumed_at_utc=now(),
                        generation_summary=str(dest/'summary.json'),
                        generation_launch=str(launch_path),new_generation_pid=info.get('generation_pid'),
                        model_consumer_finished_marker=str(dest/'model-consumer-finished.json'))
                    if profile=='merged':
                        p['next_gpu_consumer']='Root-owned AVG ASI after expert ASI generation_cpu_finished and full AVG HLE2500 generation drain; keep service allocated'
                save(state_path,state)
            except Exception as error:
                p.update(phase='failed',error_type=type(error).__name__,error=str(error)[:400]);save(state_path,state)
        state['updated_at_utc']=now();save(state_path,state)
        print(json.dumps({k:{n:p.get(n) for n in ['phase','old_job','new_job','node','new_controller_pid','error']} for k,p in state['profiles'].items()}),flush=True)
        time.sleep(10)
    state['finished_at_utc']=now();save(state_path,state)


if __name__ == '__main__':
    os.umask(0o077)
    main()
