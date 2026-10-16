"""Generate gold-matched High teacher answers with one shared budget ledger."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import requests

from expand_hle_sft_2k import MODEL_REV, lengths
from transformers import AutoTokenizer

SYSTEM = ('Solve the multiple-choice problem independently. Your final response must be a JSON object '
          'with fields "solution" (a worked explanation for the reader) and "answer" (one uppercase '
          'option letter). Do not include think tags or text outside the final JSON object. '
          'If uncertain, choose the best-supported option; do not invent missing information.')
INPUT_RATE, OUTPUT_RATE, CNY_FACTOR = 1.32, 3.96, 8.0
MAX_OUTPUT = 65536


def rows(path):
    return [json.loads(l) for l in path.open() if l.strip()] if path.exists() else []


def append(path, value):
    with path.open('a') as f:
        f.write(json.dumps(value, ensure_ascii=False)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--credentials',type=Path,required=True)
    p.add_argument('--max-attempts',type=int,default=2200)
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--budget-cny',type=float,default=80)
    a=p.parse_args()
    root=a.repo/'artifacts/data/candidates/night_hle_20261016/expanded_2k'
    cfg=json.loads((root/'selection_summary.json').read_text())
    target=cfg['new_teacher_target']
    creds={}
    for line in a.credentials.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            k,v=line.split('=',1)
            if k in {'DEEPSEEK_API_KEY','DEEPSEEK_BASE_URL'}:
                creds[k]=v.strip().strip('\"\'')
    base=creds.get('DEEPSEEK_BASE_URL','https://api.deepseek.com').rstrip('/')
    assert base in {'https://api.deepseek.com','https://api.deepseek.com/v1'}
    headers={'Authorization':'Bearer '+creds['DEEPSEEK_API_KEY']}
    balance=requests.get('https://api.deepseek.com/user/balance',headers=headers,timeout=30)
    balance.raise_for_status()
    balances=balance.json()
    (root/'balance_before_generation.json').write_text(json.dumps(balances,indent=2)+'\n')
    print(json.dumps({'balance_available':balances.get('is_available'),
                      'balance_infos':balances.get('balance_infos')}),flush=True)
    assert balances.get('is_available')
    tokenizer=AutoTokenizer.from_pretrained(a.repo/'artifacts/models/base_metadata'/MODEL_REV,
        local_files_only=True,trust_remote_code=False)
    old=a.repo/'artifacts/data/candidates/night_hle_20261016'
    prior=sum(r['conservative_cost_usd'] for name in ['teacher_api_ledger.jsonl','science_quality_review.jsonl']
              for r in rows(old/name))
    prior+=sum(r.get('conservative_cost_usd',0) for r in rows(
        a.repo/'artifacts/data/candidates/night_scicode_20261016/teacher_api_ledger.jsonl'))
    prior=max(prior,2.62661616/CNY_FACTOR)  # Existing academic branch receipt, including SciCode.
    ledger=rows(root/'teacher_api_ledger.jsonl')
    accepted=rows(root/'new_teacher_accepted.jsonl')
    attempted={r['family_key'] for r in ledger}
    success=Counter(r['hle_category'] for r in accepted)
    spent=prior+sum(r['conservative_cost_usd'] for r in ledger)
    grouped=defaultdict(list)
    for r in rows(root/'teacher_reservoir.jsonl'):
        if r['family_key'] not in attempted:
            grouped[r['hle_category']].append(r)
    positions=Counter()
    pending=Counter()
    active={}
    budget=a.budget_cny/CNY_FACTOR
    stop='reservoir_exhausted'
    started=time.time()

    def generate(row,reserve):
        t=time.time()
        receipt={'family_key':row['family_key'],'hle_category':row['hle_category'],
            'source_question_id':row['question_id'],'requested_model':'deepseek-v4-pro',
            'thinking':'enabled','reasoning_effort':'high','max_tokens':MAX_OUTPUT,
            'requested_at':datetime.now(timezone.utc).isoformat(), 'gold_was_sent_to_teacher':False,
            'reserved_maximum_cost_usd':reserve, 'historical_500_question':row['historical_500_question']}
        record=None
        try:
            response=requests.post(base+'/chat/completions',headers=headers,json={
                'model':'deepseek-v4-pro','messages':[{'role':'system','content':SYSTEM},
                    {'role':'user','content':row['prompt']}], 'thinking':{'type':'enabled'},
                'reasoning_effort':'high','max_tokens':MAX_OUTPUT,
                'response_format':{'type':'json_object'},'stream':False},timeout=900)
            receipt['http_status']=response.status_code
            response.raise_for_status()
            data=response.json()
            usage=data['usage']
            receipt.update({'usage':usage,'returned_model':data.get('model'),'response_id':data.get('id'),
                'conservative_cost_usd':(usage['prompt_tokens']*INPUT_RATE+usage['completion_tokens']*OUTPUT_RATE)/1e6})
            choice=data['choices'][0]
            msg=choice['message']
            receipt['finish_reason']=choice['finish_reason']
            receipt['reasoning_content_present']=bool(msg.get('reasoning_content'))
            receipt['reasoning_content_characters']=len(msg.get('reasoning_content') or '')
            assert choice['finish_reason']=='stop','incomplete_response'
            result=json.loads(msg['content'])
            answer=result['answer'].strip()
            solution=result['solution'].strip()
            assert solution and len(answer)==1 and 'A'<=answer<chr(65+len(row['options'])),'invalid_final_json'
            assert '<think>' not in solution and '</think>' not in solution,'think_tags_in_final'
            receipt['teacher_answer']=answer
            receipt['gold_match']=answer==row['gold_answer']
            receipt['status']='accepted' if receipt['gold_match'] else 'gold_mismatch'
            messages=[{'role':'user','content':row['prompt']},
                      {'role':'assistant','content':solution+'\n\nAnswer: '+answer+'. '+row['gold_option']}]
            full,body=lengths(tokenizer,messages)
            receipt.update({'complete_sequence_tokens':full,'assistant_content_tokens':body})
            if full>65536 or body>8192:
                receipt['status']='complete_64k_or_assistant_8k_limit'
            if receipt['status']=='accepted':
                record=dict(row,messages=messages,teacher_model=data.get('model'),
                    teacher_requested_model='deepseek-v4-pro',teacher_mode='high',
                    teacher_thinking=True,reasoning_effort='high', hidden_reasoning_removed=True,
                    answer_evidence='High_teacher_choice_matches_publisher_gold',teacher_usage=usage)
        except (requests.RequestException,ValueError,KeyError,TypeError,AssertionError) as e:
            receipt.update({'status':'request_or_protocol_error','error_class':type(e).__name__})
            if isinstance(e,AssertionError): receipt['protocol_failure']=str(e)
            receipt.setdefault('conservative_cost_usd',reserve)
        receipt['elapsed_seconds']=round(time.time()-t,3)
        return receipt,record

    with ThreadPoolExecutor(max_workers=a.workers) as executor:
        while True:
            if all(success[k]>=v for k,v in target.items()) and not active:
                stop='quotas_satisfied'
                break
            submitted=False
            for cat in target:
                if (root/'STOP_ADMISSION').exists():
                    stop='manual_stop_admission'
                    break
                if len(active)>=a.workers or len(ledger)+len(active)>=a.max_attempts:
                    break
                if success[cat]+pending[cat]>=target[cat] or positions[cat]>=len(grouped[cat]):
                    continue
                row=grouped[cat][positions[cat]]
                reserve=((len((SYSTEM+row['prompt']).encode())+1024)*INPUT_RATE+MAX_OUTPUT*OUTPUT_RATE)/1e6
                if spent+sum(v[1] for v in active.values())+reserve>budget:
                    stop='budget_guard'
                    continue
                positions[cat]+=1
                pending[cat]+=1
                active[executor.submit(generate,row,reserve)]=(row,reserve)
                submitted=True
            if not active:
                if len(ledger)>=a.max_attempts: stop='attempt_cap'
                break
            done,_=wait(active,return_when=FIRST_COMPLETED,timeout=5)
            for future in done:
                row,reserve=active.pop(future)
                pending[row['hle_category']]-=1
                receipt,record=future.result()
                spent+=receipt['conservative_cost_usd']
                receipt['cumulative_branch_cny']=spent*CNY_FACTOR
                append(root/'teacher_api_ledger.jsonl',receipt)
                ledger.append(receipt)
                if record:
                    append(root/'new_teacher_accepted.jsonl',record)
                    success[row['hle_category']]+=1
                if len(ledger)<=4 or len(ledger)%10==0:
                    print(json.dumps({'attempts':len(ledger),'accepted':dict(success),
                        'last_status':receipt['status'],'budget_cny':round(spent*CNY_FACTOR,5),
                        'elapsed_seconds':round(time.time()-started,1)}),flush=True)
    summary={'requested_model':'deepseek-v4-pro','thinking':'enabled','reasoning_effort':'high',
        'max_tokens_including_reasoning':MAX_OUTPUT,'target':target,'accepted':dict(success),
        'attempts':len(ledger),'status_counts':dict(Counter(r['status'] for r in ledger)),
        'stop_reason':stop,'prior_branch_cost_usd':prior,'conservative_branch_cny':spent*CNY_FACTOR,
        'this_generation_cost_cny':(spent-prior)*CNY_FACTOR,'budget_cny_guard':a.budget_cny,
        'prompt_tokens':sum(r.get('usage',{}).get('prompt_tokens',0) for r in ledger),
        'completion_tokens_including_reasoning':sum(r.get('usage',{}).get('completion_tokens',0) for r in ledger),
        'reasoning_tokens':sum(r.get('usage',{}).get('completion_tokens_details',{}).get('reasoning_tokens',0) for r in ledger),
        'reasoning_content_stored_in_training':False,'gold_sent_to_teacher':False,
        'validation_teacher_calls':0,'elapsed_this_run_seconds':round(time.time()-started,2)}
    (root/'teacher_generation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    main()
