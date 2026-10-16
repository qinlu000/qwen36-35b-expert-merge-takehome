"""At most two independently generated V4-Pro scientific programs; no gold in prompts."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

import requests

MODEL = 'deepseek-v4-pro'
PRIOR_BUDGET_CNY = 2.58201072


def append(path, record):
    with path.open('a') as stream:
        stream.write(json.dumps(record) + '\n')
        stream.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--credentials', type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (args.root/'two_task_candidates.jsonl').read_text().splitlines()]
    assert len(rows) == 2 and {r['problem_id'] for r in rows} == {'5', '8'}
    ledger_path = args.root/'scicode_api_ledger.jsonl'
    ledger = [json.loads(line) for line in ledger_path.read_text().splitlines()] if ledger_path.exists() else []
    attempted = {r['problem_id'] for r in ledger}
    spent = PRIOR_BUDGET_CNY + sum(r['budget_cny'] for r in ledger)
    env = {}
    for line in args.credentials.read_text().splitlines():
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            env[key] = value.strip().strip('\"\'')
    base = env.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')
    assert base in {'https://api.deepseek.com', 'https://api.deepseek.com/v1'}
    session = requests.Session()
    session.headers['Authorization'] = 'Bearer ' + env['DEEPSEEK_API_KEY']
    for row in rows:
        if row['problem_id'] in attempted:
            continue
        reserve = ((row['prompt_utf8_bytes_with_system']+1024)*1.32 + 8192*3.96)/1e6*8
        assert spent+reserve < 20
        receipt = {'problem_id': row['problem_id'], 'main_family': row['main_family'],
            'requested_model': MODEL, 'thinking': False, 'max_tokens': 8192,
            'requested_at': datetime.now(timezone.utc).isoformat(),
            'prompt_sha256': row['prompt_sha256'], 'references_sent': False,
            'pricing_url': 'https://api-docs.deepseek.com/quick_start/pricing/',
            'peak_usd_per_million': {'input_cache_miss': 1.32, 'output': 3.96},
            'budget_factor': 8, 'budget_cny': reserve, 'usage_unknown_reserve_cny': reserve}
        # Durable start marker prevents an interrupted call being regenerated for free.
        started = args.root/('api_started_'+row['problem_id']+'.json')
        assert not started.exists(), 'Previously started request must be audited before resuming'
        started.write_text(json.dumps(receipt, indent=2)+'\n')
        begin = time.time()
        raw = None
        try:
            response = session.post(base+'/chat/completions', json={
                'model': MODEL, 'thinking': {'type': 'disabled'}, 'max_tokens': 8192,
                'temperature': 0, 'stream': False,
                'messages': [{'role': 'system', 'content': row['system']},
                             {'role': 'user', 'content': row['prompt']}]}, timeout=180)
            receipt['http_status'] = response.status_code
            response.raise_for_status()
            raw = response.json()
            usage = raw['usage']
            receipt.update({'usage': usage, 'returned_model': raw.get('model'), 'response_id': raw.get('id'),
                'conservative_cost_usd': (usage['prompt_tokens']*1.32+usage['completion_tokens']*3.96)/1e6})
            receipt['budget_cny'] = receipt['conservative_cost_usd']*8
            receipt.pop('usage_unknown_reserve_cny')
            choice = raw['choices'][0]
            message = choice['message']
            receipt['finish_reason'] = choice['finish_reason']
            assert choice['finish_reason'] == 'stop'
            assert not message.get('reasoning_content')
            text = message['content']
            assert not re.search(r'</?think>|<\|(?:im_start|im_end)\|>', text)
            blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', text, re.S)
            assert len(blocks) == 1
            code = blocks[0].strip()+'\n'
            ast.parse(code)
            (args.root/('teacher_'+row['problem_id']+'.py')).write_text(code)
            receipt.update({'status': 'generated_ungraded', 'code_sha256': hashlib.sha256(code.encode()).hexdigest()})
        except (requests.RequestException, ValueError, KeyError, TypeError, AssertionError, SyntaxError) as error:
            receipt.update({'status': 'request_or_protocol_error', 'error_class': type(error).__name__})
        if raw is not None:
            (args.root/('raw_response_'+row['problem_id']+'.json')).write_text(json.dumps(raw, indent=2)+'\n')
        receipt['elapsed_seconds'] = round(time.time()-begin, 3)
        spent += receipt['budget_cny']
        receipt['branch_total_budget_cny'] = spent
        append(ledger_path, receipt)
        print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
