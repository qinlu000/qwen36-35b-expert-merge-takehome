"""CPU11-only DNS/HTTP phase differential using the frozen Terminal runtime.

No Trial, agent, setup command, verifier or model request is created.
"""
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from harbor.environments.factory import EnvironmentFactory
from harbor.models.task.config import NetworkMode, NetworkPolicy
from harbor.models.task.task import Task
from harbor.models.trial.config import TrialConfig
from harbor.models.trial.paths import TrialPaths


ROOT = Path('/data/caoqinlu/projects/apex-takehome')
OUTPUT = ROOT / 'artifacts/eval/terminal-network-probe-20261017'
DOMAINS = ['pypi.org', 'archive.ubuntu.com']
SINGLE = r'''
import http.client,json,socket,sys,time
host=sys.argv[1];start=time.monotonic()
try:
 addresses=sorted({x[4][0] for x in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)})
 print(json.dumps({'stage':'dns','host':host,'ok':True,'addresses':addresses,'seconds':time.monotonic()-start}),flush=True)
except OSError as e:
 print(json.dumps({'stage':'dns','host':host,'ok':False,'error':str(e),'seconds':time.monotonic()-start}),flush=True);sys.exit(0)
try:
 conn=http.client.HTTPSConnection(host,timeout=max(.1,4.5-(time.monotonic()-start)))
 conn.request('HEAD','/',headers={'User-Agent':'apex-network-metadata-probe'})
 response=conn.getresponse()
 print(json.dumps({'stage':'https_head','host':host,'ok':True,'status':response.status,'seconds':time.monotonic()-start}),flush=True)
 conn.close()
except Exception as e:
 print(json.dumps({'stage':'https_head','host':host,'ok':False,'error':type(e).__name__+': '+str(e),'seconds':time.monotonic()-start}),flush=True)
'''


def wrapper(python):
    return """import json,subprocess,os
from pathlib import Path
rows=[]
for host in DOMAINS:
 try:
  p=subprocess.run([PYTHON,'-c',SINGLE,host],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5)
  rows.append({'host':host,'timeout':False,'return_code':p.returncode,'events':[json.loads(x) for x in p.stdout.splitlines() if x.startswith('{')],'stderr':p.stderr[-300:]})
 except subprocess.TimeoutExpired as e:
  text=e.stdout or b''
  if isinstance(text,bytes):text=text.decode(errors='replace')
  rows.append({'host':host,'timeout':True,'events':[json.loads(x) for x in text.splitlines() if x.startswith('{')]})
print(json.dumps({'cpu_affinity':sorted(os.sched_getaffinity(0)),'resolv_conf':Path('/etc/resolv.conf').read_text(),'proxy_variable_names':[key for key in os.environ if key.lower() in ('http_proxy','https_proxy','all_proxy','no_proxy')],'domains':rows}))
""".replace('DOMAINS', repr(DOMAINS)).replace('PYTHON', repr(python)).replace('SINGLE', repr(SINGLE))


def check_captured(result):
    phases = {row['phase']: row for row in result['phases']}
    for row in [result['host'], phases['public_before'], phases['public_after']]:
        assert row['cpu_affinity'] == [11]
        for domain in row['domains']:
            assert not domain['timeout']
            events = {event['stage']: event for event in domain['events']}
            assert events['dns']['ok'] and events['https_head']['ok']
    for domain in phases['solver_no_network']['domains']:
        assert not domain['timeout']
        dns = domain['events'][0]
        assert dns['stage'] == 'dns' and not dns['ok']
        assert 'Temporary failure in name resolution' in dns['error']
    assert all(row['resolv_conf'] == 'nameserver 10.0.2.3\n' for row in phases.values())
    assert not any(row['proxy_variable_names'] for row in [result['host'], *phases.values()])
    assert result['own_environment_stopped']
    print('PASS: host/public DNS+HTTPS green, solver DNS red, restored-public green; resolver unchanged')


async def main():
    assert os.sched_getaffinity(0) == {11}, 'Probe must be launched with taskset -c 11'
    OUTPUT.mkdir(parents=True, exist_ok=False)
    result = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'kind': 'network_metadata_only', 'domains': DOMAINS, 'maximum_seconds_per_domain': 5,
        'task_setup_agent_verifier_model_calls': 0,
        'runtime': 'artifacts/eval/avg64_terminal_full445_20261017/runtime/scripts',
        'probe_cpus': [11], 'formal_cpu_memory_protocol_modified': False}
    host = subprocess.run([sys.executable, '-c', wrapper(sys.executable)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=12)
    assert host.returncode == 0, host.stderr[-300:]
    result['host'] = json.loads(host.stdout)
    source = ROOT / 'artifacts/eval/avg64_terminal_full445_20261017/trials/bn-fit-modify__seed0/config.json'
    config = TrialConfig.model_validate_json(source.read_text())
    task = Task(config.task.path)
    # A diagnostic allocation only: one CPU11, same immutable SIF/runtime, 8GiB.
    config.environment.override_cpus = 1
    config.environment.kwargs.update(baseline_cpu_offset=0, baseline_cpu_slots=1)
    paths = TrialPaths(OUTPUT / 'sandbox'); paths.mkdir(); paths.chmod_dir()
    public = NetworkPolicy(network_mode=NetworkMode.PUBLIC)
    denied = NetworkPolicy(network_mode=NetworkMode.NO_NETWORK)
    mounts = [{'type': 'bind', 'source': str(path), 'target': target} for path, target in
        [(paths.agent_dir, '/logs/agent'), (paths.verifier_dir, '/logs/verifier'),
         (paths.artifacts_dir, '/logs/artifacts')]]
    environment = EnvironmentFactory.create_environment_from_config(config.environment,
        task.paths.environment_dir, task.short_name, 'apex-dns-differential-20261017',
        paths, task.config.environment, mounts=mounts, network_policy=public,
        phase_network_policies=[public, denied])
    result['source_trial_config'] = str(source)
    result['task_environment'] = str(task.paths.environment_dir)
    try:
        await environment.start(force_build=False)
        result['scope'] = environment._scope_unit + '.scope'
        result['sif'] = str(environment._sif_path)
        result['phases'] = []
        for name, policy in [('public_before', public), ('solver_no_network', denied),
                             ('public_after', public)]:
            await environment.set_network_policy(policy)
            value = await environment.exec('/opt/harbor-server/bin/python3 -c ' +
                shlex.quote(wrapper('/opt/harbor-server/bin/python3')), timeout_sec=15)
            assert value.return_code == 0, value.stderr[-500:]
            result['phases'].append({'phase': name, **json.loads(value.stdout)})
            (OUTPUT / 'probe.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        await environment.stop(delete=True)
        result['own_environment_stopped'] = True
        result['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        (OUTPUT / 'probe.json').write_text(json.dumps(result, indent=2) + '\n')
    check_captured(result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--check-captured':
        check_captured(json.loads(Path(sys.argv[2]).read_text()))
    else:
        asyncio.run(main())
