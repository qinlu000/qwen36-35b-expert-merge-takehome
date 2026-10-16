"""One-shot CPU follow-up: finish data, sync it, then release only HLE job726344."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import time

HPC = '/data/user/qinlucao/projects/apex-takehome'
HLE = 'artifacts/data/candidates/night_hle_20261016/expanded_2k'
MIXED = 'artifacts/data/candidates/mixed_expanded_20261016'
JOB = '726344'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    a=p.parse_args()
    root=a.repo
    out=root/HLE
    state_path=out/'followup_state.json'
    ssh=['ssh','-i','/home/caoqinlu/.ssh/id_ed25519_hpc3_hkustgz',
         '-o','BatchMode=yes','-o','ConnectTimeout=8','-o','StrictHostKeyChecking=yes']
    host='qinlucao@hpc3login.hpc.hkust-gz.edu.cn'
    state={'job_authorized_for_release':JOB,'phase':'starting','data_ready':False,'released':False}

    def save(phase,**values):
        state.update(phase=phase,updated_at=datetime.now(timezone.utc).isoformat(),**values)
        state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(state,ensure_ascii=False),flush=True)

    def run(command,**kw):
        return subprocess.run(command,check=True,text=True,**kw)

    if state_path.exists() and json.loads(state_path.read_text()).get('released'):
        print('Already completed; no repeat release',flush=True)
        return
    try:
        pid=int((out/'generation.pid').read_text())
        save('waiting_for_high_generation',generation_pid=pid)
        while True:
            proc=Path('/proc')/str(pid)
            if not proc.exists():
                break
            status=(proc/'status').read_text()
            if 'State:\tZ' in status:
                break
            assert b'generate_hle_2k_high.py' in (proc/'cmdline').read_bytes(),'generation_pid_reused'
            time.sleep(15)
        generation=json.loads((out/'teacher_generation_summary.json').read_text())
        assert generation['stop_reason']=='quotas_satisfied',generation['stop_reason']
        assert generation['thinking']=='enabled' and generation['reasoning_effort']=='high'
        assert generation['accepted']==generation['target']
        assert sum(generation['accepted'].values())==1183
        save('exporting_hle',generation=generation)
        run(['/data/caoqinlu/envs/datamind-sft/bin/python',str(root/'scripts/expand_hle_sft_2k.py'),
             '--repo',str(root),'--phase','export'])
        ready=json.loads((out/'ready_summary.json').read_text())
        assert ready['data_ready'] and ready['train_rows']==2000 and ready['validation_rows']==100
        save('building_mixed',hle_full_max=ready['full_sequence_tokens']['max'],
             hle_suggested_max_length=ready['suggested_max_length'])
        sources=[out,root/'artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k',
                 root/'artifacts/data/candidates/terminal_sft_2k_20261016',
                 root/'artifacts/data/candidates/asi_sft_expanded_20261016']
        run(['python3',str(root/'scripts/prepare_mixed_sft.py'),
             '--train',*[str(p/'train.messages.jsonl') for p in sources],
             '--val',*[str(p/'val.messages.jsonl') for p in sources],
             '--output-dir',str(root/MIXED)])
        mixed=json.loads((root/MIXED/'summary.json').read_text())
        assert mixed['train_rows']==7073 and mixed['val_rows']==249
        assert [r['rows'] for r in mixed['train_sources']]==[2000,2000,2000,1073]
        save('syncing_hpc',data_ready=True,mixed_train_rows=7073,mixed_val_rows=249)
        for rel in [HLE,MIXED]:
            run(ssh+[host,shlex.join(['mkdir','-p',HPC+'/'+rel])])
            run(['rsync','-a','-e',shlex.join(ssh),str(root/rel)+'/',host+':'+HPC+'/'+rel+'/'])
        remote_code=f'''
from pathlib import Path
import json
r=Path({HPC!r})
result={{}}
for rel,train,val in [({HLE!r},2000,100),({MIXED!r},7073,249)]:
 p=r/rel
 actual={{name:sum(1 for l in (p/name).open() if l.strip()) for name in ['train.messages.jsonl','val.messages.jsonl']}}
 assert actual=={{'train.messages.jsonl':train,'val.messages.jsonl':val}},actual
 result[rel]=actual
h=json.loads((r/{HLE!r}/'ready_summary.json').read_text())
m=json.loads((r/{MIXED!r}/'summary.json').read_text())
assert h['data_ready'] and h['train_rows']==2000 and m['train_rows']==7073 and m['val_rows']==249
for name in ['val.messages.jsonl','val.tasks.jsonl','val.provenance.jsonl']:
 assert (r/{HLE!r}/name).read_bytes()==(r/'artifacts/data/candidates/night_hle_20261016/swift_ready'/name).read_bytes()
result['frozen_val_bytes_equal']=True
result['hle_full_max']=h['full_sequence_tokens']['max']
print(json.dumps(result))
'''
        verified=run(ssh+[host,'python3 -'],input=remote_code,capture_output=True)
        verification=json.loads(verified.stdout)
        save('hpc_verified',remote_verification=verification)
        job=run(ssh+[host,'scontrol show job '+JOB+' -o'],capture_output=True).stdout
        assert 'JobName=apex-hle2k-sft' in job and 'Reason=JobHeldUser' in job,job
        save('releasing_authorized_hle_job')
        run(ssh+[host,'scontrol release '+JOB])
        job_after=run(ssh+[host,'scontrol show job '+JOB+' -o'],capture_output=True).stdout
        assert 'Reason=JobHeldUser' not in job_after
        save('complete',released=True,hpc_job_after=job_after.strip())
    except Exception as error:
        save('failed',error_class=type(error).__name__,error=str(error))
        raise


if __name__=='__main__':
    main()
