"""Score preserved final files asynchronously, without regenerating solver answers."""
from datetime import datetime,timezone
import fcntl,json,os,subprocess,time
from pathlib import Path

ROOT=Path('/data/caoqinlu/projects/apex-takehome')
RUN=ROOT/'artifacts/runs/base-terminal-recovery-v2-20261016'
OUT=ROOT/'artifacts/results/base-terminal-v2-recovery-20261016'
RECOVERY=ROOT/'artifacts/recovery/terminal-v2/saved-final-states'


def main():
    RECOVERY.mkdir(parents=True,exist_ok=True)
    lock=(RECOVERY/'observer.lock').open('a+')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    env=os.environ.copy()
    env['PYTHONPATH']=':'.join(map(str,[RUN/'runtime8/scripts',RUN/'runtime7/scripts',RUN/'runtime3/scripts',ROOT/'artifacts/runs/base-terminal-724242/runtime2/scripts']))
    env['PATH']=':'.join(str(ROOT/p) for p in ['artifacts/tools/apptainer-1.4.5/rootfs/usr/bin','artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin'])+':'+env['PATH']
    env['APPTAINER_IGNORE_SUBUID']='1'
    while not (RUN/'followon/full445.COMPLETE.json').exists():
        cp=json.loads((OUT/'checkpoint.json').read_text())
        summary=json.loads((OUT/'final_summary.json').read_text())
        found=False
        for key,status in cp['statuses'].items():
            if key in summary['accepted_first_valid'] or status['state'] not in ('verifier_incomplete','valid'):continue
            result_path=Path(status.get('result_path',''))
            if not result_path.is_file():continue
            archive=next(iter(result_path.parent.glob('artifacts/**/final-task-state.tar')),None)
            if not archive:continue
            label=result_path.parent.name+'__savedstate1'
            output=OUT/'rescoring'/label
            if output.exists():continue
            work=RECOVERY/label;work.mkdir(parents=True,exist_ok=True)
            receipt_path=archive.with_suffix('.json')
            receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
            manifest={'files':[{'source':str(archive),'target':'/staging/saved-final-state.tar'}],
                'commands':[{'command':'tar -xf /staging/saved-final-state.tar -C /',
                    'source_evidence':str(archive),'timeout_sec':180}],
                'reconstructed_from_transcript':False,'restored_from_pre_verifier_artifact':True,
                'byte_identical':False,'archived_file_contents_preserved':True,
                'evidence':{'original_result':str(result_path),'snapshot':receipt,
                    'scope':'Archived workdir and verifier-referenced output paths; no claim of entire-rootfs identity'},
                'new_model_calls':0}
            restore=work/'restore.json';restore.write_text(json.dumps(manifest,indent=2)+'\n')
            argv=[str(ROOT/'artifacts/envs/harbor/bin/python'),str(ROOT/'scripts/run_terminal_grader_only_v4.py'),
                '--original-result',str(result_path),'--restore-manifest',str(restore),'--output',str(output),'--cpu-offset','120']
            with (work/'grader.log').open('ab',buffering=0) as log:
                child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                (work/'launch.json').write_text(json.dumps({'at_utc':datetime.now(timezone.utc).isoformat(),
                    'pid':child.pid,'key':key,'argv':argv,'new_model_calls':0},indent=2)+'\n')
                child.wait()
            found=True
            break
        if not found:time.sleep(30)


if __name__=='__main__':main()
