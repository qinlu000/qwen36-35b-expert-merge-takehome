"""Read-only progress plus accepted grader-only results; no model scheduling."""
from datetime import datetime,timezone
import collections,fcntl,json,os,statistics,time
from pathlib import Path
from terminal_verifier_evidence import verifier_infra_reason

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
OUT=ROOT/'artifacts/results/base-terminal-v2-recovery-20261016'
FOLLOW=ROOT/'artifacts/runs/base-terminal-recovery-v2-20261016/followon'


def save(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)


def main():
    own=(FOLLOW/'observer.lock').open('a')
    fcntl.flock(own,fcntl.LOCK_EX|fcntl.LOCK_NB)
    (FOLLOW/'pid').write_text(str(os.getpid())+'\n')
    while True:
        checkpoint=json.loads((OUT/'checkpoint.json').read_text())
        counts=collections.Counter(s['state'] for s in checkpoint['statuses'].values())
        valid={key:record for key,record in checkpoint['first_valid'].items() if not verifier_infra_reason(json.loads(Path(record['path']).read_text()))}
        # Only independently restored, original-answer grading outputs, never trials.
        scored=[]
        for path in (OUT/'rescoring').glob('*/result.json'):
            try:result=json.loads(path.read_text())
            except (ValueError,OSError):continue
            reward=((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
            if result.get('exception_info') or reward not in (0,1) or not result.get('recovery') or verifier_infra_reason(result):continue
            key=result['task_name']+'/seed'+str(result['config']['agent']['kwargs']['seed'])
            scored.append((result.get('finished_at') or '',key,{'path':str(path),'reward':reward,
                'original_result':result['recovery']['original_result'],
                'reconstructed_from_transcript':result['recovery'].get('reconstructed_from_transcript',False),
                'byte_identical':result['recovery'].get('byte_identical')}))
        for _,key,record in sorted(scored):valid.setdefault(key,record)
        seeds=[]
        for seed in range(5):
            records=[r for key,r in valid.items() if key.endswith('/seed'+str(seed))]
            correct=sum(r['reward'] for r in records)
            seeds.append({'seed':seed,'expected':89,'valid_covered':len(records),'correct_count':correct,
                          'score_percent':100*correct/89 if len(records)==89 else None})
        complete=len(valid)==445 and counts['pending']==0 and counts['admitted']==0
        scores=[s['score_percent'] for s in seeds]
        value={'updated_at_utc':datetime.now(timezone.utc).isoformat(),'expected_trials':445,
            'valid_covered':len(valid),'active_trials':counts['admitted'],'pending_not_admitted':counts['pending'],
            'infrastructure_unscored':445-len(valid)-counts['admitted']-counts['pending'],
            'complete':complete,'per_seed':seeds,'states':dict(counts),'accepted_first_valid':valid,
            'primary_mean_percent':statistics.mean(scores) if complete else None,
            'sample_sd_percent_ddof1':statistics.stdev(scores) if complete else None,
            'invalidated_previous_claims':checkpoint.get('invalidated_previous_claims',{}),
            'queue_summary':{'halted':checkpoint.get('halted',False),'pending_not_admitted':counts['pending']}}
        save(OUT/'final_summary.json',value)
        save(FOLLOW/'status.json',{'pid':os.getpid(),'stage':'observe_single_rolling_queue',**value})
        if complete:
            value['queue_summary']={'halted':False,'pending_not_admitted':0}
            value['first_valid_chronology']=[{'key':key,**record} for key,record in valid.items()]
            save(FOLLOW/'full445.COMPLETE.json',value)
            return
        print(json.dumps({k:value[k] for k in ('updated_at_utc','valid_covered','active_trials','pending_not_admitted','infrastructure_unscored')}),flush=True)
        time.sleep(30)


if __name__=='__main__':main()
