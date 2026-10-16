#!/opt/harbor-server/bin/python3
"""Exact GET URL cache; every uncached curl invocation uses the original curl."""
import json,os,shutil,sys
from pathlib import Path

base=Path('/staging/verifier_assets')
args=sys.argv[1:]
mapping=base/'url-cache/url_map.json'
urls=[a for a in args if a.startswith(('https://','http://'))]
cache=json.loads(mapping.read_text()) if mapping.exists() else {}
source=cache.get(urls[0]) if len(urls)==1 else None
if isinstance(source,dict):source=source.get('file') or source.get('path')
if source:
    source=base/'url-cache'/Path(source).name
if source and source.is_file() and not any(a in args for a in ('-I','--head','-X','--request','--data','-d')):
    output=None
    for index,arg in enumerate(args):
        if arg in ('-o','--output'):output=args[index+1]
        elif arg.startswith('--output='):output=arg.split('=',1)[1]
        elif arg.startswith('-o') and len(arg)>2:output=arg[2:]
    if output and output!='-':shutil.copyfile(source,output)
    else:
        with source.open('rb') as stream:shutil.copyfileobj(stream,sys.stdout.buffer)
    raise SystemExit(0)
os.execv(str(base/'native/ld-linux-x86-64.so.2'),[str(base/'native/ld-linux-x86-64.so.2'),
    '--library-path',str(base/'native'),str(base/'native/curl'),*args])
