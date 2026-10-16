"""Serialize only the final values and counts printed in the original trajectory."""
from pathlib import Path
import json,struct
ROOT=Path('/data/caoqinlu/projects/apex-takehome')
out=ROOT/'artifacts/recovery/terminal-v2/distribution-search__seed0'
out.mkdir(parents=True,exist_ok=True)
header="{'descr': '<f8', 'fortran_order': False, 'shape': (150000,), }"
header=header+' '*((64-(10+len(header)+1)%64)%64)+'\n'
values=[('1.555092395593655e-01',6),('6.689920705251225e-02',1),('3.023847199198183e-10',149993)]
with (out/'dist.npy').open('wb') as stream:
    stream.write(b'\x93NUMPY\x01\x00'+struct.pack('<H',len(header))+header.encode())
    for text,count in values:stream.write(struct.pack('<d',float(text))*count)
manifest={'files':[{'source':str(out/'dist.npy'),'target':'/app/dist.npy'}],
    'commands':[],'reconstructed_from_transcript':True,
    'reconstructed_from_original_transcript':True,'byte_identical':False,
    'evidence':{'pane':'distribution-search__seed0__manual1/agent/terminus_2.pane:992,1043-1046',
        'original_write':'arr=np.full(V,q); arr[:6]=p1; arr[6:7]=p2; np.save',
        'printed_values_counts':values,'shape':[150000],'dtype':'float64',
        'numerical_equivalence':'Original tests depend only on shape, finite positive values, sum and aggregate KL, not ordering. Printed16sig rounding changes the sum by less than1e-14 versus1e-5 tolerance and KL far below1e-3 tolerance.',
        'new_search_or_model_calls':0}}
(out/'restore.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(out/'restore.json')
