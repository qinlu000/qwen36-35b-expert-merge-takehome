"""Accept only the dedicated validation endpoint, never a running Base replica."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.request


ALIASES = ['apex-val-base', 'apex-val-swe249', 'apex-val-asi128', 'apex-val-hle16', 'apex-val-hle250']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--job-id', required=True)
    args = parser.parse_args()
    output = args.project / 'artifacts/validation' / ('lora-service-' + args.job_id)
    launch = json.loads((output / 'launch.json').read_text())
    url = 'http://{}:{}'.format(launch['hostname'], launch['port'])
    key = (args.project / 'artifacts/private/base_smoke_api_key').read_text().strip()

    def request(path, payload=None):
        req = urllib.request.Request(url + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=180) as response:
            body = response.read()
            return json.loads(body) if body else {'http_status': response.status}

    health = request('/health')
    models = request('/v1/models')
    assert {row['id'] for row in models['data']} == set(ALIASES)
    log = (args.project / 'artifacts/validation' / ('lora-service-' + args.job_id + '.log')).read_text()
    assert not any(text in log for text in [
        'These parameters will be ignored', 'no matching PunicaWrapper',
        'While loading ', 'does not support LoRA', 'not supported for LoRA',
        'not in the deployment-time target_modules',
    ])
    results = []
    for alias in ALIASES:
        response = request('/v1/chat/completions', {
            'model': alias,
            'messages': [{'role': 'user', 'content': 'What is 17*19? Give only the integer.'}],
            'max_tokens': 32, 'temperature': 0, 'seed': 1729,
            'logprobs': True, 'top_logprobs': 5,
            'chat_template_kwargs': {'enable_thinking': False, 'preserve_thinking': False},
        })
        choice = response['choices'][0]
        assert response['model'] == alias
        assert choice['message'].get('content')
        assert not choice['message'].get('reasoning') and not choice['message'].get('reasoning_content')
        results.append({'alias': alias, 'response': response})

    tool_response = request('/v1/chat/completions', {
        'model': 'apex-val-swe249',
        'messages': [
            {'role': 'system', 'content': 'Use the bash tool to execute the requested command. Do not write a final answer.'},
            {'role': 'user', 'content': 'Execute echo validation-ready'},
        ],
        'tools': [{'type': 'function', 'function': {'name': 'bash', 'description': 'Execute a shell command.',
            'parameters': {'type': 'object', 'properties': {'command': {'type': 'string'}}, 'required': ['command']}}}],
        'tool_choice': 'auto', 'max_tokens': 128, 'temperature': 0, 'seed': 1729,
        'chat_template_kwargs': {'enable_thinking': False, 'preserve_thinking': False},
    })
    assert tool_response['choices'][0]['message'].get('tool_calls')
    result = {
        'accepted_at_utc': datetime.now(timezone.utc).isoformat(),
        'job_id': args.job_id, 'hostname': launch['hostname'], 'port': launch['port'],
        'health': health, 'aliases': ALIASES, 'models': models,
        'startup_ignored_adapter_warning': False, 'adapter_inventory': launch['adapters'],
        'probes': results, 'swe_tool_probe': tool_response,
        'smoke_caps_only': {'plain_request': 32, 'tool_request': 128},
        'formal_context_tokens': 65536, 'formal_output_tokens': 8192,
        'ready': True,
    }
    (output / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'ready': True, 'job_id': args.job_id, 'hostname': launch['hostname'],
        'port': launch['port'], 'aliases': ALIASES, 'acceptance': str(output / 'acceptance.json')}))


if __name__ == '__main__':
    main()
