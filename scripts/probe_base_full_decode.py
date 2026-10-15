"""Finish synthetic cap acceptance with a diagnostic deadline independent of HLE's300s."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time

import httpx
from run_hle_v2 import save


async def main(args):
    prior = json.loads((args.output / 'acceptance.json').read_text())
    cases = {case['case']: case for case in prior['cases']}
    assert cases['authentication']['passed']
    assert cases['native_hle_8_admitted_text_and_image']['result']['passed']
    assert cases['exact57344_input_plus8192_cap']['usage']['prompt_tokens'] == 57344
    assert cases['57345_plus8192_rejected']['http_status'] == 400
    assert len(cases['8_admitted_long_inputs']['results']) == 8
    assert prior['error_type'] == 'ReadTimeout'
    protocol = json.loads((args.project / 'configs/eval/protocol_v2_unified64k8k.json').read_text())
    generation = {k: v for k, v in protocol['generation_default'].items()
                  if k not in {'sampling_seed', 'scope'}}
    request = dict(generation, model='apex-qwen', seed=0, min_tokens=8192,
                   messages=[{'role': 'user', 'content':
                       'Write a very long list of distinct positive integers, one per line. Continue until the token budget is exhausted.'}],
                   chat_template_kwargs={'enable_thinking': False, 'preserve_thinking': False})
    key = args.key_file.read_text().strip()
    report = {'started_at_utc': datetime.now(timezone.utc).isoformat(), 'passed': False,
              'prior_acceptance': 'acceptance.json', 'prior_native_cases_passed': True,
              'synthetic_diagnostic_timeout_seconds': 900,
              'formal_hle_deadline_seconds': 300,
              'note': 'Only this synthetic stress request forces min_tokens8192. Formal requests keep their original cap and300s shared deadline.'}
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(base_url=args.endpoint, trust_env=False,
                                    headers={'Authorization': 'Bearer ' + key}) as client:
            response = await client.post('/v1/chat/completions', json=request, timeout=900)
            response.raise_for_status()
            result = response.json()
        save(args.output / 'full8192_response.json', result)
        assert result['usage']['completion_tokens'] == 8192
        assert result['choices'][0]['finish_reason'] == 'length'
        message = result['choices'][0]['message']
        assert not message.get('reasoning') and not message.get('reasoning_content')
        report.update(passed=True, usage=result['usage'])
    except Exception as exc:
        report.update(error_type=type(exc).__name__, error=str(exc)[:300])
    finally:
        report['elapsed_seconds'] = time.monotonic() - started
        report['full8192_fits_hle300s'] = report['passed'] and report['elapsed_seconds'] <= 300
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        save(args.output / 'full_decode_acceptance.json', report)
        print(json.dumps(report), flush=True)
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--endpoint', default='http://127.0.0.1:18061')
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
