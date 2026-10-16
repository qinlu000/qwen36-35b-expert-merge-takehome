#!/usr/bin/env python3
"""One persistent dense-TIES service/HLE consumer; default prints the plan only.

Root must approve --execute. No allocation or model request precedes completed
export validation. A durable submit intent is never automatically submitted again.
"""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import fcntl
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time

import httpx
from PIL import Image

from run_direct_formal_pipeline import launch, now, save


def read(path):
    return json.loads(path.read_text())


def fields(text):
    return dict(re.findall(r'(\w+)=([^ ]*)', text))


def gpu_count(jobs, project):
    """Count requested project GPUs, including pending allocations."""
    total = 0
    for job in jobs:
        if job.get('WorkDir') == project:
            matches = re.findall(r'(?:^|,)gres/gpu=(\d+)(?:,|$)', job['ReqTRES'])
            assert len(matches) == 1
            total += int(matches[0])
    return total


def native_requests(client, endpoint):
    response = client.get(endpoint + '/metrics', timeout=5)
    response.raise_for_status()
    values = re.findall(r'^vllm:num_requests_(?:running|waiting)(?:\{[^\n]*\})?\s+([0-9.eE+-]+)', response.text, re.M)
    assert len(values) >= 2
    return [float(v) for v in values]


def acceptance(client, endpoint, model, output, deadline):
    """Two synthetic requests only; bounded health wait, no benchmark material."""
    while datetime.now(timezone.utc) < deadline:
        try:
            if client.get(endpoint + '/health', timeout=3).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(5)
    else:
        raise TimeoutError('Dense service did not become healthy before bounded admission deadline')
    listed = client.get(endpoint + '/v1/models', timeout=10).json()
    assert model in {row['id'] for row in listed['data']}
    # Persistent intent before either synthetic request; uncertain acceptance is not repeated.
    with (output / 'acceptance-intent.json').open('x') as handle:
        json.dump({'at_utc': now(), 'model': model, 'max_synthetic_requests': 2}, handle)
    checks = []
    for image in (False, True):
        assert datetime.now(timezone.utc) + timedelta(seconds=180) < deadline
        content = [{'type': 'text', 'text': 'Name the dominant color in this image.' if image else 'What is 17 + 25?'}]
        if image:
            stream = io.BytesIO(); Image.new('RGB', (32, 32), 'red').save(stream, format='PNG')
            content.append({'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode()}})
        messages = [{'role': 'user', 'content': content}]
        template = {'enable_thinking': False, 'preserve_thinking': False}
        count = client.post(endpoint + '/tokenize', json={'model': model, 'messages': messages,
            'chat_template_kwargs': template, 'add_generation_prompt': True}, timeout=60)
        count.raise_for_status(); counted = count.json()
        response = client.post(endpoint + '/v1/chat/completions', json={'model': model,
            'messages': messages, 'max_tokens': 32, 'temperature': 0, 'seed': 0,
            'chat_template_kwargs': template}, timeout=120)
        response.raise_for_status(); raw = response.json()
        save(output / ('acceptance-image.response.json' if image else 'acceptance-text.response.json'), raw)
        message = raw['choices'][0]['message']
        assert raw['model'] == model and counted['max_model_len'] == 65536
        assert raw['usage']['prompt_tokens'] == counted['count']
        assert type(raw['usage']['completion_tokens']) is int and 0 <= raw['usage']['completion_tokens'] <= 32
        assert not message.get('reasoning') and not message.get('reasoning_content')
        assert message.get('role') == 'assistant' and isinstance(message.get('content'), str) and message['content'].strip()
        checks.append({'vision': image, 'usage': raw['usage'], 'token_guard_passed': True})
    save(output / 'acceptance.json', {'ready': True, 'at_utc': now(), 'model': model,
        'synthetic_only': True, 'model_requests': 2, 'formal_or_validation_questions': 0,
        'semantic_correctness_used_for_admission': False, 'checks': checks})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=Path('configs/eval/ties_dense_hle_control_20261017.json'))
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    root = args.project.resolve(); config = read(root / args.config)
    service = config['service']
    assert service['partition'] == 'acd_u' and service['nice'] == 1000 and service['gpus'] == 2
    assert service['bridge_port'] == 28097 and service['port'] == 18006 and service['profile'] == 'ties-dense'
    assert config['model'] == 'apex-ties-dense' and config['judge']['max_calls_combined'] == 5000
    assert config['judge']['max_cny_combined'] == 20 and config['judge']['workers'] == 2
    assert config['generation'] == {'questions':2500,'images':342,'concurrency':50,'context_tokens':65536,
        'max_tokens':8192,'question_walltime_seconds':300,'thinking':False,'preserve_thinking':False}
    if not args.execute:
        print(json.dumps({'mode':'prepare_only','network_calls':0,'new_gpu_allocations':0,
            'config':str(root/args.config),'requires_completed_export':True,
            'model':config['model'],'profile':service['profile'],'endpoint':'http://127.0.0.1:28097'}))
        return
    os.umask(0o077)
    output = root / config['controller_output']; output.mkdir(parents=True, exist_ok=True)
    lock = (output / 'controller.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # This version is one-shot. A prior claim requires human inspection, never resubmission.
    with (output / 'controller-claim.json').open('x') as handle:
        json.dump({'pid':os.getpid(),'at_utc':now(),'config':config}, handle, indent=2)
    state = {'pid':os.getpid(),'model':config['model'],'phase':'verifying_export','new_gpu_allocations':0}
    def phase(name, **values):
        state.update(phase=name,at_utc=now(),**values); save(output/'state.json',state)
    ssh = ['ssh','-F','/dev/null','-o','BatchMode=yes','-o','IdentitiesOnly=yes','-o','ConnectTimeout=10',
        '-o','StrictHostKeyChecking=yes','-o','HostKeyAlias=hpc3login.hpc.hkust-gz.edu.cn',
        '-o','UserKnownHostsFile='+str(root/'artifacts/private/baseline_hpc_known_hosts'),
        '-i','/home/caoqinlu/.ssh/id_ed25519_hpc3_hkustgz','qinlucao@10.120.81.30']
    hroot = config['hpc_project']
    def hpc(command):
        return subprocess.check_output(ssh+[shlex.join(command)],text=True,stderr=subprocess.STDOUT,timeout=45).strip()
    def job_info(job):
        return fields(hpc(['scontrol','show','job','-o',str(job)]))
    def job_present(job):
        try:
            return bool(hpc(['squeue','-h','-j',str(job),'-o','%i']))
        except subprocess.CalledProcessError as error:
            if error.returncode == 1 and 'Invalid job' in error.output:
                return False
            raise
    def owned_job(job):
        info = job_info(job)
        assert info['WorkDir'] == hroot and info['UserId'].startswith('qinlucao(')
        assert info['JobName'] == service['job_name'] and info['Partition'] == 'acd_u'
        return info
    admitted_formal = False
    tunnel = None
    try:
        assert not any((root/config['output']/'questions').glob('*.json')), 'Existing attempts require audit; never relaunch blindly'
        # The exact same light guard is also executed inside the allocated service.
        proof = json.loads(hpc(['python3',hroot+'/scripts/serve_direct_experts.py','--project',hroot,
            '--profile','ties-dense','--check-dense-export']))
        save(output/'export-admission.json',proof)
        assert proof['lora_enabled'] is False
        assert not hpc(['squeue','-h','-u','qinlucao','-n',service['job_name'],'-o','%i'])
        ids = hpc(['squeue','-h','-u','qinlucao','-o','%i']).splitlines()
        current = gpu_count([job_info(job) for job in ids],hroot)
        assert current+2 <= service['max_project_gpus']
        cap = datetime.fromisoformat(service['core_cap']).astimezone(timezone.utc)
        minutes = min(service['requested_minutes'],int((cap-datetime.now(timezone.utc)).total_seconds()//60))
        assert minutes*60 >= service['minimum_runway_seconds']
        # The old controls may run concurrently on port18006; avoid its node rather than changing its routes.
        controls_route = read(root/'configs/eval/hle_controls_tunnel_20261017.json')
        excluded = {'ACD1-59'} | {w['node'] for w in controls_route['workers'] if w['service_port']==18006}
        assert all(re.fullmatch(r'ACD1-\d+',node) for node in excluded)
        command = ['sbatch','--parsable','--partition=acd_u','--nice=1000','--time='+str(minutes),
            '--exclude='+','.join(sorted(excluded)),
            '--job-name='+service['job_name'],hroot+'/scripts/serve_direct_experts.slurm','ties-dense','18006']
        with (output/'submit-intent.json').open('x') as handle:
            json.dump({'at_utc':now(),'command':command,'existing_project_gpus':current,'projected_gpus':current+2},handle,indent=2)
        phase('submitting',project_gpu_count_before=current)
        raw = hpc(command); job = raw.split(';')[0]; assert job.isdigit()
        job = int(job); phase('waiting_running',job_id=job,new_gpu_allocations=2)
        while True:
            assert datetime.now(timezone.utc)+timedelta(seconds=service['minimum_runway_seconds']) < cap
            info = owned_job(job)
            if info['JobState']=='RUNNING': break
            assert info['JobState']=='PENDING'
            time.sleep(10)
        node = info['NodeList']; assert re.fullmatch(r'ACD1-\d+',node)
        tz = timezone(timedelta(hours=8))
        end = min(cap,datetime.fromisoformat(info['EndTime']).replace(tzinfo=tz).astimezone(timezone.utc))
        start = datetime.fromisoformat(info['StartTime']).replace(tzinfo=tz).astimezone(timezone.utc)
        time_limit = int((end-start).total_seconds()//60)
        hpc(['scontrol','update','JobId='+str(job),'TimeLimit='+str(time_limit)])
        stop_at = end-timedelta(seconds=service['drain_seconds'])
        phase('routing',node=node,service_end_utc=end.isoformat(),stop_admission_at_utc=stop_at.isoformat())
        code = """from pathlib import Path
import fcntl,sys
p=Path.home()/'.ssh/authorized_keys'
with (Path.home()/'.ssh/apex-authorized-keys.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 lines=p.read_text().splitlines();count=0
 for i,line in enumerate(lines):
  if line.endswith('apex-baseline-forward-20261016'):
   count+=1;options,key=line.split(' ssh-ed25519 ',1);item='permitopen="'+sys.argv[1]+':18006"'
   if item not in options:options+=','+item
   lines[i]=options+' ssh-ed25519 '+key
 assert count==1
 q=p.with_name('authorized_keys.ties-dense.tmp');q.write_text('\\n'.join(lines)+'\\n');q.chmod(0o600);q.replace(p)
print('exact permit present')
"""
        hpc(['python3','-c',code,node])
        routing = read(root/'configs/eval/hle_controls_tunnel_20261017.json')
        routing['workers']=[{'benchmark':'ties_dense_hle','job_id':job,'node':node,'service_port':18006,'bridge_port':28097}]
        save(output/'tunnel.json',routing)
        tunnel=launch([str(root/'artifacts/envs/hle/bin/python'),str(root/'scripts/supervise_hpc_tunnels.py'),
            '--config',str(output/'tunnel.json'),'--state-dir',str(output/'tunnel')],output/'tunnel-supervisor.log',root)
        phase('waiting_acceptance',tunnel_supervisor_pid=tunnel.pid)
        key=(root/'artifacts/private/base_smoke_api_key').read_text().strip()
        endpoint='http://127.0.0.1:28097'
        with httpx.Client(trust_env=False,headers={'Authorization':'Bearer '+key}) as client:
            acceptance(client,endpoint,config['model'],output,
                min(stop_at,datetime.now(timezone.utc)+timedelta(seconds=service['health_wait_seconds'])))
            assert (stop_at-datetime.now(timezone.utc)).total_seconds() >= service['minimum_runway_seconds']
            protocol=read(root/config['protocol'])
            ids=read(root/protocol['benchmarks']['hle']['task_manifest'])['task_ids']
            assert len(ids)==len(set(ids))==2500
            destination=root/config['output'];destination.mkdir(exist_ok=True)
            assert not any((destination/'questions').glob('*.json')), 'Existing attempts require audit; never relaunch blindly'
            save(destination/'manual_retry_manifest.json',{'selection_rule':'One fixed terminal result per task ID; no score selection or retries',
                'retained':[{'id':task,'manual_retry_index':0,'original_result':str(destination/'questions'/(task+'.json'))} for task in ids],
                'selected':[],'expected_questions':2500,'formal_model':config['model']})
            python=str(root/'artifacts/envs/hle/bin/python')
            generation=[python,str(root/'scripts/run_direct_hle_formal.py'),'--project',str(root),'--mode','formal',
                '--model',config['model'],'--endpoint',endpoint,'--key-file',str(root/'artifacts/private/base_smoke_api_key'),'--output',str(destination)]
            scoring=[python,str(root/'scripts/score_direct_hle_formal.py'),'--project',str(root),'--retry',str(destination),
                '--output',str(destination/'scoring'),'--max-cny','20','--max-calls','5000','--workers','2']
            save(output/'formal-launch-intent.json',{'at_utc':now(),'generation':generation,'scoring':scoring})
            admitted_formal=True
            generator=launch(generation,output/'generation.log',root)
            grader=launch(scoring,output/'scoring.log',root)
            phase('generating',generation_pid=generator.pid,scoring_pid=grader.pid,endpoint=endpoint)
            while generator.poll() is None:
                if datetime.now(timezone.utc)>=stop_at and not (destination/'STOP_ADMISSION').exists():
                    (destination/'STOP_ADMISSION').write_text('Fixed service deadline: stop new admission; retain full original300s in-flight budgets.\n')
                assert datetime.now(timezone.utc)<end+timedelta(seconds=360), 'Generator did not drain; retain ledgers for audit'
                time.sleep(5)
            rows=[read(p) for p in (destination/'questions').glob('*.json') if not p.name.endswith('.started.json')]
            assert all(r.get('finished_at_utc') for r in rows)
            final_ids={r['id'] for r in rows}
            started={p.name[:-len('.started.json')] for p in (destination/'questions').glob('*.started.json')}
            assert not started-final_ids
            phase('draining_native',generation_exit_code=generator.returncode,saved_results=len(rows))
            while job_present(job):
                try:
                    if not any(native_requests(client,endpoint)): break
                except httpx.HTTPError:
                    pass
                assert datetime.now(timezone.utc)<end+timedelta(seconds=60), 'Native drain unknown; do not cancel or retry answers'
                time.sleep(5)
            present=job_present(job)
            if present:
                assert not any(native_requests(client,endpoint))
                owned_job(job);hpc(['scancel',str(job)])
            while job_present(job): time.sleep(5)
            save(destination/'model-consumer-finished.json',{'model_consumer_finished':True,'at_utc':now(),
                'generation_process_finished':True,'generation_pid':generator.pid,'saved_results':len(rows),
                'expected':2500,'job_id':job,'job_absent_from_squeue':True,'native_metrics_zero_before_release':present,
                'service_expired_before_release':not present,'scoring_uses_external_judge_only':True})
            phase('generation_released_scoring_external',job_absent_from_squeue=True,
                saved_results=len(rows),full_generation=len(rows)==2500,
                scoring_summary=str(destination/'scoring/summary.json'),compact_rule=config['judge']['compact_recovery_rule'])
    except Exception as error:
        phase('needs_attention',error_type=type(error).__name__,error=str(error)[:500],
            unknown_submit_must_not_be_retried=(state.get('phase')=='submitting'))
        # Before formal admission, this new owned job has no benchmark answers to preserve.
        if state.get('job_id') and not admitted_formal:
            owned_job(state['job_id']);hpc(['scancel',str(state['job_id'])])
            state['preformal_release_requested']=True;save(output/'state.json',state)
        raise
    finally:
        if tunnel and state.get('phase')=='generation_released_scoring_external':
            tunnel.terminate();tunnel.wait(timeout=15)


if __name__=='__main__':
    main()
