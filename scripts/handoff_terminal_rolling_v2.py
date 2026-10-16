"""One natural drain: merge historical incomplete attempts into the rolling queue."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,json,os,shutil,subprocess,time

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
RUN=ROOT/'artifacts/runs/base-terminal-recovery-v2-20261016'
OUT=ROOT/'artifacts/results/base-terminal-v2-recovery-20261016'
LEAF=RUN/'runtime8';(LEAF/'scripts').mkdir(parents=True,exist_ok=True)
cp=json.loads((OUT/'checkpoint.json').read_text())
manifest=json.loads((RUN/'runtime3/manifest.json').read_text())
entries={e['key']:e for e in manifest['entries']}
retry=[]
for key,status in cp['statuses'].items():
    if status['state'] not in ('cancelled','failed_attempt'):continue
    path=Path(status['result_path'])
    result=json.loads(path.read_text())
    end=((result.get('agent_result') or {}).get('metadata') or {}).get('v2_end_reason')
    previous=status['manual_attempt']
    if previous>=2 or end=='native_return':continue
    entry=entries[key]
    evidence={'result_path':str(path),'exception_type':(result.get('exception_info') or {}).get('exception_type'),
              'v2_end_reason':end,'retained_agent_usage':{k:(result.get('agent_result') or {}).get(k) for k in ('n_input_tokens','n_output_tokens')},
              'classification':'observed_queue_peer_cancellation_or_fixed_harness_bootstrap_failure'}
    if previous==0:
        entry.update(original_result=str(path),prior_manual_attempts=[])
    else:entry['prior_manual_attempts']=[*entry.get('prior_manual_attempts',[]),evidence]
    entry['manual_attempt']=previous+1
    entry['manual_retry_authorization']='user authorized infrastructure repair; max2; incomplete solver only'
    retry.append({'key':key,'manual_attempt':previous+1,**evidence})
# Mix historical work with never-started work, rather than a cohort barrier.
old=[entries[x['key']] for x in retry]
fresh=[e for e in manifest['entries'] if e['key'] not in {x['key'] for x in retry}]
mixed=[]
while old or fresh:
    if old:mixed.append(old.pop(0))
    if fresh:mixed.append(fresh.pop(0))
manifest.update(entries=mixed,rolling_recovery_plan=retry,
    policy='fixed445; rolling FIRST_COMPLETED; no cohort barrier; completed answers grading only')
(LEAF/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
for name in ('run_terminal_native7.py','terminal_admission_v2.py'):
    shutil.copy2(RUN/'runtime7/scripts'/name,LEAF/'scripts'/name)
prepared={'prepared_at_utc':datetime.now(timezone.utc).isoformat(),'historical_incomplete_retries':len(retry),
    'fixed445':True,'manual_retry_max':2,'existing_solver_answers_regenerated':0,'items':retry}
(LEAF/'handoff.json').write_text(json.dumps(prepared,indent=2)+'\n')
# All assets are now prepared; existing tasks continue naturally.
(RUN/'runtime7/STOP_ADMISSION').touch()
while True:
    lock=(ROOT/'artifacts/runs/base-terminal-724242.lock').open('a+')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close();time.sleep(5);continue
    cp=json.loads((OUT/'checkpoint.json').read_text())
    if any(s['state']=='admitted' for s in cp['statuses'].values()):
        lock.close();raise SystemExit('unexpected admitted tasks after prior controller exited; retain for audit')
    break
shutil.copy2(OUT/'checkpoint.json',LEAF/'checkpoint-before-handoff.json')
for item in retry:
    if item['key'] not in cp['first_valid']:
        cp['statuses'][item['key']].update(state='pending',manual_attempt=item['manual_attempt'],
            retained_prior_result=item['result_path'],infrastructure_retry_reason=item['classification'])
temporary=(OUT/'checkpoint.json').with_suffix('.tmp')
temporary.write_text(json.dumps(cp,indent=2)+'\n');temporary.replace(OUT/'checkpoint.json')
env=os.environ.copy()
env['PATH']=':'.join(str(ROOT/p) for p in ['artifacts/tools/apptainer-1.4.5/rootfs/usr/bin','artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin'])+':'+env['PATH']
env['PYTHONPATH']=':'.join(map(str,[LEAF/'scripts',RUN/'runtime7/scripts',RUN/'runtime3/scripts',ROOT/'artifacts/runs/base-terminal-724242/runtime2/scripts']))
env.update(APPTAINER_IGNORE_SUBUID='1',PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
argv=[str(ROOT/'artifacts/envs/harbor/bin/python'),str(LEAF/'scripts/run_terminal_native7.py'),
    '--manifest',str(LEAF/'manifest.json'),'--output',str(OUT),'--endpoint','http://127.0.0.1:28082',
    '--api-key-path',str(ROOT/'artifacts/private/base_smoke_api_key'),'--concurrency','16',
    '--resume-after-bridge-approval','--stop-admission-file',str(LEAF/'STOP_ADMISSION')]
with (RUN/'runner-native8.log').open('ab',buffering=0) as stream:
    child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(lock.fileno(),))
prepared.update(launched_at_utc=datetime.now(timezone.utc).isoformat(),pid=child.pid,argv=argv,
    pending_admissions=sum(s['state']=='pending' for s in cp['statuses'].values()),
    max_solver_futures=16,max_model_sequences=8,model_job=726129)
(RUN/'launch-native8.json').write_text(json.dumps(prepared,indent=2)+'\n')
(RUN/'pid-native8').write_text(str(child.pid)+'\n')
print(json.dumps({'pid':child.pid,'pending_admissions':prepared['pending_admissions'],'historical_retries':len(retry)}))
