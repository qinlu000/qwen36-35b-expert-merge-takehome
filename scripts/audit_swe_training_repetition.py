#!/usr/bin/env python3
"""Read-only action/observation audit of the frozen SWE SFT JSONL; no tokenization."""
import argparse
from collections import Counter, deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex

DATA = 'artifacts/data/candidates/new_swe_20261016/expanded_2k/swift_ready64k'
FILTERED = {223, 239, 279, 1256, 1462, 1530, 1972}
REV = '1db674173119d71df45c22007af99e214600711a'
SUBMIT = 'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT'
OLD_FINALS = {SUBMIT+' && cat patch.txt', 'cd /testbed && '+SUBMIT+' && cat patch.txt', SUBMIT+' && cat /testbed/patch.txt'}
encode = lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
digest = lambda x: hashlib.sha256(encode(x)).hexdigest()
read_lines = lambda p: [json.loads(line) for line in p.open() if line.strip()]


def args(call):
    value = call['function']['arguments']
    return json.loads(value) if isinstance(value, str) else value


def actions(message):
    return [(call['function']['name'], args(call)) for call in message.get('tool_calls', [])]


def canonical(message):
    row = {'role': message['role'], 'content': message.get('content') or ''}
    if message.get('tool_calls'):
        row['actions'] = actions(message)
    if row['role'] == 'tool':
        try: row['content'] = json.loads(row['content'])
        except ValueError: pass
    return row


def read_only(command):
    """Conservative syntax heuristic, not proof that a shell command cannot write."""
    if any(x in command for x in ('\n', '$(', '`', '<(', '>(')):
        return False
    text = re.sub(r'\s*(?:2>\s*/dev/null|2>\s*&1|>\s*/dev/null)', '', command)
    if '<' in text or '>' in text:
        return False
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=';&|'); lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        return False
    segments = []; current = []
    for token in tokens:
        if token in (';', '&&', '||', '|'):
            if current: segments.append(current); current = []
        else: current.append(token)
    if current: segments.append(current)
    if not segments:
        return False
    for segment in segments:
        while segment and re.match(r'^[A-Za-z_][A-Za-z_0-9]*=', segment[0]): segment = segment[1:]
        if not segment: return False
        name = Path(segment[0]).name; a = segment[1:]
        if name in ('cd', 'pwd', 'ls', 'cat', 'head', 'tail', 'wc', 'stat', 'file', 'readlink', 'realpath', 'which', 'type', 'printf', 'echo', 'true'):
            continue
        if name in ('grep', 'rg') and not any(x.startswith('--pre') for x in a): continue
        if name == 'find' and not any(x in ('-delete', '-exec', '-execdir', '-ok', '-okdir', '-fprint', '-fprint0', '-fprintf', '-fls') for x in a): continue
        if name == 'sed' and len(a)>=2 and a[0]=='-n' and re.fullmatch(r'(?:\d+|\$)(?:,(?:\d+|\$))?p', a[1]): continue
        if name == 'git':
            if any(x.startswith(('--output', '--ext-diff', '--textconv')) for x in a): return False
            while a and a[0] in ('-C', '-c'): a = a[2:]
            if a and a[0] in ('status', 'diff', 'show', 'log', 'grep', 'ls-files', 'rev-parse', 'blame', 'ls-tree', 'cat-file', 'describe'): continue
        return False
    return True


def distribution(values):
    v = sorted(values)
    return {'n':len(v), 'mean':sum(v)/len(v) if v else None,
        'median':v[(len(v)-1)//2] if v else None,
        'p90':v[min(len(v)-1,int(len(v)*.9))] if v else None,
        'p95':v[min(len(v)-1,int(len(v)*.95))] if v else None,
        'max':max(v,default=None)}


def add_context(table, context, target, row):
    v = table.setdefault(context, {'count':0,'targets':Counter(),'rows':0,'last_row':None})
    v['count'] += 1; v['targets'][target] += 1
    if v['last_row'] != row: v['rows'] += 1; v['last_row'] = row


def context_summary(table):
    repeated = [v for v in table.values() if v['count']>1]
    return {'unique_contexts':len(table),'repeated_contexts':len(repeated),
        'events_in_repeated_contexts':sum(v['count'] for v in repeated),
        'same_action_only_repeated_contexts':sum(len(v['targets'])==1 for v in repeated),
        'same_context_action_duplicate_excess':sum(sum(n-1 for n in v['targets'].values()) for v in repeated),
        'cross_row_repeated_contexts':sum(v['rows']>1 for v in repeated),
        'largest_context_count':max((v['count'] for v in repeated),default=1)}


def row_analysis(row, meta, line, split, tables):
    commands=[]; readonly=[]; observations=[]; pending=deque(); pairing=Counter(); history=[]
    prompt = digest([m.get('content') for m in row['messages'] if m['role']=='user'])
    running = hashlib.sha256(encode(row.get('tools')))
    for turn,m in enumerate(row['messages']):
        if m['role']=='assistant' and m.get('tool_calls'):
            aa=actions(m); target=digest(aa)
            add_context(tables['full_prefix'],running.hexdigest(),target,line)
            for size in (2,4):
                if len(history)>=size:
                    add_context(tables['local'+str(size)],digest([prompt,history[-size:]]),target,line)
            if pending: pairing['pending_before_new_assistant'] += len(pending); pending.clear()
            for call in m['tool_calls']:
                a=args(call);command=a.get('command')
                if call['function']['name']=='bash' and isinstance(command,str):
                    commands.append(command); readonly.append(read_only(command)); observations.append(None)
                    pending.append((call.get('id'),len(commands)-1))
                else: pairing['non_bash_or_missing_command'] += 1
        elif m['role']=='tool':
            if not pending: pairing['orphan_tool'] += 1
            else:
                expected,index=pending.popleft()
                if m.get('tool_call_id')!=expected: pairing['tool_id_mismatch'] += 1
                try: ob=json.loads(m.get('content') or '')
                except ValueError: ob={'unparsed':m.get('content')};pairing['unparsed_observation']+=1
                observations[index]=digest(ob)
        cm=canonical(m);history.append(cm);running.update(encode(cm)+b'\0')
    if pending and not (len(pending)==1 and commands and commands[-1]==SUBMIT):pairing['unanswered_nonfinal_call']+=len(pending)
    runs=[];start=0
    for index in range(1,len(commands)+1):
        if index==len(commands) or commands[index]!=commands[start]:
            runs.append((index-start,start));start=index
    longest,position=max(runs,default=(0,0));counts=Counter(commands)
    repeats=sum(n-1 for n,_ in runs if n>1);inruns=sum(n for n,_ in runs if n>1)
    nonfinal=[i for i,c in enumerate(commands) if c!=SUBMIT]
    best_ob=[observations[i] for i in range(position,position+longest)]
    return {'split':split,'line_1based':line,'family_key':meta.get('family_key'),'repo':meta.get('repo'),
        'source':meta.get('source'),'source_file':meta.get('file'),'source_row':meta.get('row'),'resolved':meta.get('resolved'),
        'instance_id':meta.get('instance_id'),'trajectory_id':meta.get('trajectory_id'),
        'native_loader_retained':split!='train' or line not in FILTERED,
        'bash_calls':len(commands),'longest_exact_consecutive_run':longest,'adjacent_repeat_excess':repeats,
        'calls_in_runs_ge2':inruns,'max_same_command_total':max(counts.values(),default=0),
        'readonly_heuristic_calls':sum(readonly),'nonfinal_calls':len(nonfinal),
        'readonly_nonfinal_calls':sum(readonly[i] for i in nonfinal),
        'readonly_nonfinal_fraction':sum(readonly[i] for i in nonfinal)/len(nonfinal) if nonfinal else None,
        'all_nonfinal_syntax_readonly':bool(nonfinal) and all(readonly[i] for i in nonfinal),
        'longest_command_sha256':hashlib.sha256(commands[position].encode()).hexdigest() if commands else None,
        'longest_command_preview':commands[position][:160] if commands else None,
        'longest_run_readonly_heuristic':readonly[position] if commands else None,
        'longest_run_same_observation':len(set(best_ob))==1 and None not in best_ob,
        'pairing_issues':dict(pairing),'observation_count':sum(o is not None for o in observations),
        'trajectory_canonical_sha256':running.hexdigest(),'user_messages_sha256':prompt}


def aggregate(rows):
    calls=sum(r['bash_calls'] for r in rows)
    return {'rows':len(rows),'bash_calls':calls,'resolved_labels':dict(Counter(str(r['resolved']) for r in rows)),
        'run_distribution':distribution([r['longest_exact_consecutive_run'] for r in rows]),
        'rows_run_at_least':{str(n):sum(r['longest_exact_consecutive_run']>=n for r in rows) for n in [2,5,10,20,50,100,106,162,205]},
        'adjacent_repeat_excess':sum(r['adjacent_repeat_excess'] for r in rows),
        'adjacent_repeat_excess_fraction':sum(r['adjacent_repeat_excess'] for r in rows)/calls if calls else None,
        'calls_in_runs_ge2':sum(r['calls_in_runs_ge2'] for r in rows),
        'readonly_heuristic_fraction':sum(r['readonly_heuristic_calls'] for r in rows)/calls if calls else None,
        'rows_readonly_nonfinal_at_least':{str(n):sum((r['readonly_nonfinal_fraction'] or 0)>=n for r in rows) for n in [.5,.8,.9,.95,1.]},
        'all_nonfinal_syntax_readonly_rows':sum(r['all_nonfinal_syntax_readonly'] for r in rows),
        'pairing_issues':dict(sum((Counter(r['pairing_issues']) for r in rows),Counter())),
        'whole_trajectory_duplicate_excess':len(rows)-len({r['trajectory_canonical_sha256'] for r in rows}),
        'user_messages_duplicate_excess':len(rows)-len({r['user_messages_sha256'] for r in rows}),
        'top_runs':sorted(rows,key=lambda r:(-r['longest_exact_consecutive_run'],r['line_1based']))[:12]}


def observation(text):
    if text.startswith(('<exception>', '<returncode>')):
        prefix = r'\A(?:<exception>(?P<exception>.*?)</exception>\n)?<returncode>(?P<rc>-?\d+)</returncode>\n'
        m = re.fullmatch(prefix+r'<output>\n(?P<output>.*)</output>\Z', text, re.S)
        if m:
            return {'returncode':int(m['rc']),'exception_info':m['exception'] or None,'output':m['output']}
        m = re.fullmatch(prefix+r'<warning>.*?</warning><output_head>\n(?P<head>.{5000})\n</output_head>\n<elided_chars>\n(?P<elided>\d+) characters elided\n</elided_chars>\n<output_tail>\n(?P<tail>.{5000})\n</output_tail>\Z',text,re.S)
        if not m: raise ValueError('unrecognized_source_XML')
        return {'returncode':int(m['rc']),'exception_info':m['exception'] or None,'output_head':m['head'],'output_tail':m['tail'],'elided_chars':int(m['elided'])}
    ob=json.loads(text)
    assert isinstance(ob,dict) and set(ob)<= {'returncode','exception_info','output','output_head','output_tail','elided_chars','warning'}
    # Target template omits null exception_info and rewrites warning boilerplate.
    visible={'returncode':ob['returncode'],'exception_info':ob.get('exception_info') or None}
    visible.update({k:ob[k] for k in ('output','output_head','output_tail','elided_chars') if k in ob})
    return visible


def source_fingerprint(row, source=False):
    # Replay only published deterministic text transformations, not tokenization.
    old = ('Step 3: Submit (EXACT command required)\nYou MUST use this EXACT command to submit:\n\n'
        '```bash\necho COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT && cat patch.txt\n```\n\n'
        'If the command fails (nonzero exit status), it will not submit.\n')
    new = ('Step 3: Submit (EXACT command required)\nSubmit your changes and finish your work by issuing this command:\n\n'
        '```bash\necho COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n```\n\n'
        'Do not combine it with any other command. After this command, you cannot continue working on this task.\n')
    normalized=[]; visible=[]; aa=[]; obs=[]; roles=[]; counts=Counter(); source_ids=deque()
    for turn,m in enumerate(row['messages']):
        role=m['role'];content=m.get('content') or ''; roles.append(role)
        if role=='system':
            if source: counts['source_system_contract_matches'] += content=='You are a helpful assistant that can interact with a computer shell to solve programming tasks.'
            # Actual target system is independently checked as one shared constant.
            content='TARGET_SYSTEM'
        elif role=='user' and source:
            counts['source_submit_wrapper_replacements'] += content.count(old);content=content.replace(old,new)
        elif role=='assistant':
            if source:
                counts['removed_reasoning_content_messages'] += bool((m.get('reasoning_content') or '').strip())
                if '<think>' in content or '</think>' in content:
                    match=re.match(r'\A\s*<think>.*?</think>\s*',content,re.S)
                    assert match and '<think>' not in content[match.end():] and '</think>' not in content[match.end():]
                    content=content[match.end():];counts['removed_leading_think_messages']+=1
            visible.append(content);calls=[]
            for call in m.get('tool_calls',[]):
                arguments=dict(args(call))
                if source and turn==len(row['messages'])-1 and arguments.get('command') in OLD_FINALS:
                    arguments['command']=SUBMIT;counts['source_submit_command_replacements']+=1
                calls.append([call['function']['name'],arguments]);aa.append(calls[-1])
                source_ids.append(call.get('id'))
            normalized.append({'role':role,'content':content,'actions':calls});continue
        elif role=='tool':
            content=observation(content);obs.append(content)
            expected=source_ids.popleft() if source_ids else None
            actual=m.get('tool_call_id')
            counts['tool_id_present'] += actual is not None
            counts['source_id_unavailable'] += expected is None or actual is None
            counts['source_id_mismatch_when_both_present'] += expected is not None and actual is not None and expected!=actual
        normalized.append({'role':role,'content':content})
    tools=[json.loads(t) if isinstance(t,str) else t for t in row['tools']]
    return {'roles_sha256':digest(roles),'assistant_visible_sha256':digest(visible),'actions_sha256':digest(aa),
        'observations_sha256':digest(obs),'message_sequence_sha256':digest(normalized),'tools_sha256':digest(tools),
        'messages':len(roles),'actions':len(aa),'observations':len(obs),'counts':dict(counts)}


def raw_fingerprints(root,output):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from collections import defaultdict
    pa.set_cpu_count(1);pa.set_io_thread_count(1)
    train=read_lines(root/DATA/'train.manifest.jsonl');val=read_lines(root/DATA/'val.manifest.jsonl')
    provenance={r['family_key']:r for r in read_lines(root/'artifacts/data/candidates/new_swe_20261016/night_v2/val.manifest.jsonl')}
    selected=[]
    for split,rows in [('train',train),('val',val)]:
        for line,meta in enumerate(rows,1):
            m=meta if split=='train' else provenance[meta['family_key']]
            selected.append((split,line,m))
    sample_keys={('train',122),('train',998),('val',1)}
    selected=[x for x in selected if (x[0],x[1]) in sample_keys]
    assert len(selected)==3
    wanted=defaultdict(dict)
    for split,line,m in selected:wanted[m['file']][m['row']]=(split,line,m['family_key'])
    count=0
    with output.open('w') as stream:
        for name,rows in sorted(wanted.items()):
            path=root/'artifacts/data/raw/open_swe'/REV/name;offset=0
            for batch in pq.ParquetFile(path).iter_batches(batch_size=32,columns=['messages','tools'],use_threads=False):
                for index in sorted(i for i in rows if offset<=i<offset+len(batch)):
                    split,line,family=rows[index];raw=batch.slice(index-offset,1).to_pylist()[0]
                    fp=source_fingerprint(raw,True)
                    stream.write(json.dumps({'split':split,'line_1based':line,'family_key':family,'file':name,'row':index,'fingerprint':fp})+'\n');count+=1
                offset+=len(batch)
                if offset>max(rows):break
            stream.flush()
    assert count==3
    print(json.dumps({'mode':'raw_visible_fingerprints_only','rows':count,'parquet_files':len(wanted),'output':str(output),'raw_dataset_modified':False,'no_tokenization_environment_model':True}))


def hidden_reasoning_scan(root):
    result={}
    for split in ('train','val'):
        counts=Counter();roles=Counter();fields=Counter();hidden=Counter()
        for text in (root/DATA/(split+'.messages.jsonl')).open():
            counts['rows']+=1
            for message in json.loads(text)['messages']:
                roles[message['role']]+=1;fields.update(message.keys())
                for key,value in message.items():
                    if re.search(r'reason|think|analysis',key,re.I):
                        hidden[key]+=1;counts['hidden_fields_present']+=1
                        counts['hidden_fields_nonempty']+=not (value is None or value=='' or value==[] or value=={} or (isinstance(value,str) and not value.strip()))
                content=message.get('content') or ''
                if not isinstance(content,str):counts['nonstring_content']+=1;continue
                opens=len(re.findall(r'<think>',content,re.I));closes=len(re.findall(r'</think>',content,re.I))
                blocks=re.findall(r'<think>(.*?)</think>',content,re.S|re.I)
                counts['think_open_tags']+=opens;counts['think_close_tags']+=closes
                counts['complete_think_blocks']+=len(blocks);counts['empty_think_blocks']+=sum(not b.strip() for b in blocks)
                counts['nonempty_think_blocks']+=sum(bool(b.strip()) for b in blocks)
                counts['unpaired_open_tags']+=max(opens-len(blocks),0);counts['unpaired_close_tags']+=max(closes-len(blocks),0)
        for key in ('hidden_fields_present','hidden_fields_nonempty','nonstring_content'):counts.setdefault(key,0)
        result[split]={'path':str(root/DATA/(split+'.messages.jsonl')),'counts':dict(counts),'roles':dict(roles),
            'message_fields':dict(fields),'hidden_field_names':dict(hidden)}
    return {'captured_at_utc':datetime.now(timezone.utc).isoformat(),'mode':'stdlib_all_messages_text_only_no_render_encoding_or_raw_parquet',
        'splits':result,'existing_export_does_not_contain_hidden_reasoning_to_revive':all(not d['counts']['hidden_fields_present'] and not d['counts']['think_open_tags'] and not d['counts']['think_close_tags'] for d in result.values()),
        'rendered_empty_think_shells_are_not_stored_export_content':True,'new_model_calls':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,default=Path('analysis/source_snapshots/swe_training_repetition_audit_20261017.json'));p.add_argument('--raw-source-fingerprints',action='store_true');p.add_argument('--compare-fingerprints',type=Path);p.add_argument('--hidden-field-scan',action='store_true');a=p.parse_args();root=a.root
    if a.hidden_field_scan:
        report=json.loads((root/a.output).read_text());report['hidden_reasoning_field_audit']=hidden_reasoning_scan(root);report['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        (root/a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['hidden_reasoning_field_audit'],indent=2));return
    if a.raw_source_fingerprints:
        raw_fingerprints(root,root/a.output);return
    if a.compare_fingerprints:
        report=json.loads((root/a.output).read_text());expected={(r['split'],r['line_1based']):r for r in read_lines(a.compare_fingerprints)}
        checks=Counter();mismatches=[];source_counts=Counter();systems=Counter()
        for split in ('train','val'):
            for line,text in enumerate((root/DATA/(split+'.messages.jsonl')).open(),1):
                if (split,line) not in expected:continue
                row=json.loads(text);actual=source_fingerprint(row);source=expected[(split,line)];fp=source['fingerprint'];source_counts.update(fp['counts'])
                for m in row['messages']:
                    if m['role']=='system':systems[hashlib.sha256(m['content'].encode()).hexdigest()]+=1
                bad=[k for k in actual if k!='counts' and actual[k]!=fp[k]]
                checks['rows']+=1;checks['matched_rows']+=not bad
                if bad:mismatches.append({'split':split,'line_1based':line,'family_key':source['family_key'],'mismatched_fields':bad})
        report['source_raw_comparison']={'checks':dict(checks),'mismatches':mismatches,'source_counts':dict(source_counts),'target_system_unique':len(systems),'source_fingerprints_file':str(a.compare_fingerprints),'scope':'Only3fixed representatives train122(longest run3), train998(Scale-SWE multicall), val1; raw pinned parquet selected rows; XML/JSON observation visible fields, roles, visible assistant, commands, ordered messages andtools; only documented think/wrapper/finalsubmit changes normalized.'}
        (root/a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['source_raw_comparison'],indent=2));return
    allrows={};contexts={};stats={}
    trainmeta=read_lines(root/DATA/'train.manifest.jsonl');valmeta=read_lines(root/DATA/'val.manifest.jsonl')
    for split,metas in [('train',trainmeta),('val',valmeta)]:
        tables={name:{} for name in ('full_prefix','local2','local4')};rows=[]
        with (root/DATA/(split+'.messages.jsonl')).open() as stream:
            for line,text in enumerate(stream,1):rows.append(row_analysis(json.loads(text),metas[line-1],line,split,tables))
        assert len(rows)==len(metas)
        allrows[split]=rows;stats[split]=aggregate(rows);contexts[split]={name:context_summary(t) for name,t in tables.items()}
    stats['native_loaded_train_1993']=aggregate([r for r in allrows['train'] if r['native_loader_retained']])
    report={'captured_at_utc':datetime.now(timezone.utc).isoformat(),'mode':'local_JSON_read_only_no_environment_model_tokenization','dataset':str(root/DATA),'data_stats':{f:{'bytes':(root/DATA/f).stat().st_size,'mtime_ns':str((root/DATA/f).stat().st_mtime_ns)} for f in ['train.messages.jsonl','val.messages.jsonl','train.manifest.jsonl','val.manifest.jsonl']},'definitions':{'consecutive_run':'Exact full bash command string across consecutive tool actions, with tool observations between actions; no command whitespace normalization.','adjacent_repeat_excess':'sum(run_length-1)/all bash actions; distinct from all calls belonging to a repeated run.','local_context':'Same task user-message hash and exact previous2 or4 canonical messages; tool IDs removed and JSON object key order normalized. No semantic embedding/near-duplicate approximation.','full_prefix':'All previous canonical messages+tools, not merely a suffix.','readonly':'Conservative syntax heuristic only; all other commands unknown, not necessarily writes.','source_success':'Publisher resolved label, not independently rerun or verified here.','native_filtered_lines':sorted(FILTERED),'native_filtered_source':'analysis/source_snapshots/sft_actual_loaded_rows_20261016.json'},'splits':stats,'contexts':contexts,'train_val_overlap':{'canonical_trajectory':len({r['trajectory_canonical_sha256'] for r in allrows['train']}&{r['trajectory_canonical_sha256'] for r in allrows['val']}),'user_messages':len({r['user_messages_sha256'] for r in allrows['train']}&{r['user_messages_sha256'] for r in allrows['val']})},'source_raw_comparison':'pending independent raw-parquet visible-field check','new_model_or_environment_calls':0}
    (root/a.output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(root/a.output),'train':{k:v for k,v in stats['train'].items() if k not in ['top_runs']},'val':{k:v for k,v in stats['val'].items() if k not in ['top_runs']},'contexts':contexts},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
