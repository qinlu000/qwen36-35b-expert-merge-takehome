"""Restore an already completed answer and run only its original native verifier."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import shlex
import traceback

from harbor.environments.factory import EnvironmentFactory
from harbor.models.task.config import NetworkPolicy,NetworkMode
from harbor.models.task.task import Task
from harbor.models.trial.config import TrialConfig
from harbor.models.trial.paths import TrialPaths
from harbor.verifier.verifier import Verifier


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-result',type=Path,required=True)
    parser.add_argument('--restore-manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cpu-offset',type=int,required=True)
    args=parser.parse_args()
    original=json.loads(args.original_result.read_text())
    restoration=json.loads(args.restore_manifest.read_text())
    config=TrialConfig.model_validate(original['config'])
    task=Task(original['task_id']['path'])
    args.output.mkdir(parents=True,exist_ok=False)
    paths=TrialPaths(args.output);paths.mkdir();paths.chmod_dir()
    config.environment.import_path='terminal_verifier_apt_environment:TerminalVerifierAptEnvironment'
    config.environment.kwargs.update(baseline_cpu_offset=args.cpu_offset,baseline_cpu_slots=1)
    config.trials_dir=args.output.parent
    config.trial_name=args.output.name
    mounts=[{'type':'bind','source':str(source),'target':target} for source,target in [
        (paths.agent_dir,'/logs/agent'),(paths.verifier_dir,'/logs/verifier'),(paths.artifacts_dir,'/logs/artifacts')]]
    public=NetworkPolicy(network_mode=NetworkMode.PUBLIC)
    environment=EnvironmentFactory.create_environment_from_config(config.environment,
        task.paths.environment_dir,task.short_name,args.output.name+'__grade',paths,task.config.environment,
        mounts=mounts,network_policy=public,phase_network_policies=[public])
    output={**original,'config':config.model_dump(mode='json'),'trial_name':args.output.name,
        'trial_uri':args.output.as_uri(),'verifier_result':None,'exception_info':None,
        'recovery':{'original_result':str(args.original_result),'restore_manifest':str(args.restore_manifest),
            'new_model_calls':0,**restoration},'finished_at':None}
    try:
        await environment.start(force_build=False)
        await environment.set_network_policy(NetworkPolicy(network_mode=NetworkMode.NO_NETWORK))
        for item in restoration.get('files',[]):
            await environment.exec('mkdir -p '+shlex.quote(str(Path(item['target']).parent)))
            await environment.upload_file(item['source'],item['target'])
        for index,item in enumerate(restoration.get('commands',[])):
            result=await environment.exec(item['command'],timeout_sec=item.get('timeout_sec',600))
            (args.output/f'restore-command-{index}.json').write_text(result.model_dump_json(indent=2)+'\n')
            if result.return_code:raise RuntimeError(f'Original restore command {index} returned {result.return_code}')
        await environment.set_network_policy(public)
        timeout=min(config.verifier.override_timeout_sec or task.config.verifier.timeout_sec,
                    config.verifier.max_timeout_sec or float('inf'))*config.timeout_multiplier
        with environment.with_default_user(task.config.verifier.user):
            result=await asyncio.wait_for(Verifier(task,paths,environment).verify(),timeout=timeout)
        text=paths.test_stdout_path.read_text(errors='replace') if paths.test_stdout_path.exists() else ''
        if any(token in text for token in ('curl: command not found','uvx: command not found','uv: command not found')):
            raise RuntimeError('Native tests did not execute: verifier dependency missing')
        output['verifier_result']=result.model_dump(mode='json')
    except BaseException as exc:
        output['exception_info']={'exception_type':type(exc).__name__,'exception_message':str(exc),
                                  'exception_traceback':traceback.format_exc()}
    finally:
        output['finished_at']=datetime.now(timezone.utc).isoformat()
        (args.output/'result.json').write_text(json.dumps(output,indent=2)+'\n')
        await environment.stop(delete=True)
    print(json.dumps({'result':str(args.output/'result.json'),'verifier_result':output['verifier_result'],
                      'exception_type':(output['exception_info'] or {}).get('exception_type'),'new_model_calls':0}))


if __name__=='__main__':asyncio.run(main())
