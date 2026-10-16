"""Restore the final CSV printed verbatim in the original terminal pane."""
from pathlib import Path
import json,re
ROOT=Path('/data/caoqinlu/projects/apex-takehome')
old=ROOT/'artifacts/results/base-terminal-v2-recovery-20261016/trials/log-summary-date-ranges__seed0__first'
out=ROOT/'artifacts/recovery/terminal-v2/log-summary-date-ranges__seed0';out.mkdir(parents=True,exist_ok=True)
pane=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',(old/'agent/terminus_2.pane').read_text())
lines=[s.strip('\r') for s in pane.splitlines() if s.strip('\r')]
index=lines.index('period,severity,count')
rows=lines[index:index+16]
if len(rows)!=16 or not all(re.fullmatch(r'[a-z0-9_]+,(ERROR|WARNING|INFO),[0-9]+',s) for s in rows[1:]):
    raise ValueError('Final printed CSV block is incomplete; do not infer missing rows')
(out/'summary.csv').write_bytes(('\r\n'.join(rows)+'\r\n').encode())
manifest={'files':[{'source':str(out/'summary.csv'),'target':'/app/summary.csv'}],'commands':[],
    'reconstructed_from_transcript':True,'byte_identical':False,
    'evidence':{'source':str(old/'agent/terminus_2.pane')+':352-368',
        'content':'Exact final cat output header+15 rows, no recomputation or new model',
        'serialization':'CRLF chosen from recorded csv.writer(newline="") script; original file bytes unavailable',
        'official_verifier_reads':'/app/summary.csv only'}}
(out/'restore.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(out/'restore.json')
