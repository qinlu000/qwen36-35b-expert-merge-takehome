"""Preseed verified module downloads before the official script resets GOPROXY."""
import json
import shlex


async def preseed_go_score_cache(environment):
    location=await environment.exec('go env GOMODCACHE',timeout_sec=30)
    if location.return_code:
        raise RuntimeError('Cannot locate native Go module cache: '+str(location.stdout))
    target=location.stdout.strip().splitlines()[-1].rstrip('/')+'/cache/download'
    code='''import json,os,pathlib,shutil
source=pathlib.Path('/opt/apex-swe-score-go/gopath/pkg/mod/cache/download')
target=pathlib.Path(TARGET)
copied=kept=0
for directory,_,files in os.walk(source):
 destination=target/pathlib.Path(directory).relative_to(source)
 destination.mkdir(parents=True,exist_ok=True)
 for name in files:
  current=pathlib.Path(directory)/name
  output=destination/name
  if output.exists():kept+=1
  else:shutil.copy2(current,output);copied+=1
print(json.dumps({'copied_files':copied,'kept_existing_files':kept,'target':str(target)}))
'''.replace('TARGET',repr(target),1)
    result=await environment.exec('/opt/harbor-server/bin/python3 -c '+shlex.quote(code),timeout_sec=60)
    if result.return_code:
        raise RuntimeError('Cannot preseed native Go module cache: '+str(result.stdout))
    return json.loads(result.stdout)
