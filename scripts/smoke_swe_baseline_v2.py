#!/usr/bin/env python3
"""Self-authored native mini -> bash -> patch -> fresh official replay fixture."""
import argparse
import asyncio
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import time

from run_swe_baseline_v2 import run_phase, sha256
from swe_baseline_v2 import ROOT, save_json


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.server.requests.append({'path': self.path, 'body': body})
        if self.path == '/tokenize':
            payload = {'count': 123, 'max_model_len': 65536, 'tokens': []}
        else:
            index = len([r for r in self.server.requests if r['path'] == '/v1/chat/completions']) - 1
            commands = ["cat /app/add.py", "printf 'def add(a, b):\\n    return a + b\\n' > /app/add.py; cd /app && python3 -c 'from add import add; assert add(2,3)==5'; python3 /tmp/swe-runtime-probe.py > /logs/agent/runtime-probe.json", 'echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT']
            command = commands[min(index, 2)]
            payload = {'id': f'synthetic-swe-{index}', 'object': 'chat.completion', 'created': int(time.time()),
                'model': 'apex-qwen', 'choices': [{'index': 0, 'finish_reason': 'tool_calls', 'message': {
                    'role': 'assistant', 'content': 'I will inspect, fix and verify the self-authored addition function.',
                    'tool_calls': [{'id': f'call_{index}', 'type': 'function', 'function': {
                        'name': 'bash', 'arguments': json.dumps({'command': command})}}]}}],
                'usage': {'prompt_tokens': 123, 'completion_tokens': 30, 'total_tokens': 153}}
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--endpoint', help='Optional dedicated real SWE Base endpoint; omit for stub')
    parser.add_argument('--key-path', type=Path)
    args = parser.parse_args()
    parent = ROOT / 'artifacts/preflight/swe_v2'
    parent.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='native-', dir=parent))
    task = run / 'instance_synthetic_add'
    files = task / 'environment/files'
    files.mkdir(parents=True)
    tests = task / 'tests'
    tests.mkdir()
    (files / 'runtime_probe.py').write_text('''import errno,json,os,socket,struct
out={'cpus':sorted(os.sched_getaffinity(0))}
try:
    os.sched_setaffinity(0,set(range(os.cpu_count())))
    out['affinity_expansion_blocked']=False
except OSError as e:
    out['affinity_expansion_blocked']=e.errno==errno.EPERM
for label,address in [('public_ip',('1.1.1.1',443)),('dns',('10.0.2.3',53))]:
    s=socket.socket();s.settimeout(1)
    try:
        s.connect(address);out[label+'_blocked']=False
    except OSError:
        out[label+'_blocked']=True
    finally:s.close()
try:
    s=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,0);s.close();out['packet_blocked']=False
except OSError as e:
    out['packet_blocked']=e.errno==errno.EPERM
# Reading routing information is unprivileged. Probe an actual mutation in this
# disposable namespace: RTM_NEWROUTE blackhole of the reserved198.18/24 range.
s=socket.socket(socket.AF_NETLINK,socket.SOCK_RAW,socket.NETLINK_ROUTE);s.settimeout(1)
payload=struct.pack('BBBBBBBBI',socket.AF_INET,24,0,0,254,4,0,6,0)+struct.pack('HH',8,1)+socket.inet_aton('198.18.0.0')
s.sendto(struct.pack('IHHII',16+len(payload),24,0x605,1,0)+payload,(0,0))
response=s.recv(4096);s.close()
out['netlink_route_errno']=struct.unpack('i',response[16:20])[0]
out['netlink_blocked']=out['netlink_route_errno']==-errno.EPERM
print(json.dumps(out))
''')
    (task / 'instruction.md').write_text('This is a self-authored acceptance task. In /app/add.py fix add(a,b) to return a+b for all numbers. Verify with a bash command, then finish with the official completion command.\n')
    (task / 'environment/Dockerfile').write_text('FROM synthetic/local\nWORKDIR /app\n')
    (files / 'setup.sh').write_text('''set -e
if ! command -v git >/dev/null; then apt-get install -y -qq git; fi
cd /
rm -rf /app
mkdir -p /app
cd /app
git init -q
git config user.name 'Synthetic Runtime Test'
git config user.email 'synthetic@example.invalid'
printf 'def add(a, b):\\n    return a - b\\n' > add.py
printf '__pycache__/\\n' > .gitignore
git add add.py .gitignore
git commit -q -m 'Initial self-authored fixture'
cp "$HARBOR_STAGING/runtime_probe.py" /tmp/swe-runtime-probe.py
''')
    (tests / 'test.sh').write_text('''#!/bin/bash
mkdir -p /logs/verifier
cd /app
if python3 -c 'from add import add; assert add(2,3)==5; assert add(-1,4)==3'; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
''')
    (tests / 'test.sh').chmod(0o755)
    (task / 'task.toml').write_text('''schema_version = "1.4"
[task]
name = "synthetic/instance_synthetic_add"
version = "1.0.0"
[agent]
network_mode = "no-network"
timeout_sec = 1800
[verifier]
network_mode = "public"
timeout_sec = 120
[environment]
network_mode = "public"
docker_image = IMAGE
cpus = 1
memory_mb = 4096
storage_mb = 10240
build_timeout_sec = 300
'''.replace('IMAGE', json.dumps(str(args.image.resolve()))))
    server = None
    if args.endpoint:
        endpoint, key = args.endpoint, args.key_path
        assert key is not None
    else:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Stub)
        server.requests = []
        threading.Thread(target=server.serve_forever, daemon=True).start()
        endpoint = f'http://127.0.0.1:{server.server_port}'
        key = run / 'synthetic.key'
        key.write_text('self-authored-fixture-key')
    report = {'benchmark_tasks_executed': 0, 'judge_calls': 0, 'stub_endpoint': server is not None,
              'run_dir': str(run), 'image': str(args.image)}
    started = time.monotonic()
    try:
        generated = await run_phase(task, run, 'generation', 1, endpoint=endpoint, key_path=key, cpu_offset=64)
        report['initial_reward'] = (((generated.verifier_result.rewards if generated and generated.verifier_result else None) or {}).get('reward'))
        patch = run / 'generation/instance_synthetic_add/agent/model.patch'
        report['patch_bytes'] = patch.stat().st_size if patch.exists() else 0
        report['patch_sha256'] = sha256(patch) if patch.exists() else None
        runtime = run / 'generation/instance_synthetic_add/agent/mini-runtime-verified.json'
        report['container_runtime_lock'] = runtime.is_file()
        if runtime.is_file():
            report['runtime'] = json.loads(runtime.read_text())
        replayed = await run_phase(task, run, 'replay', 1, cpu_offset=64) if generated else None
        report['replay_reward'] = (((replayed.verifier_result.rewards if replayed and replayed.verifier_result else None) or {}).get('reward'))
        report['generation_exception'] = generated.exception_info.model_dump(mode='json') if generated and generated.exception_info else None
        report['replay_exception'] = replayed.exception_info.model_dump(mode='json') if replayed and replayed.exception_info else None
        requests = list((run / 'requests/instance_synthetic_add').glob('*.json'))
        report['guarded_requests'] = len(requests)
        report['native_mini'] = (run / 'generation/instance_synthetic_add/agent/mini-swe-agent.trajectory.json').is_file()
        trajectory = json.loads((run / 'generation/instance_synthetic_add/agent/mini-swe-agent.trajectory.json').read_text()) if report['native_mini'] else {}
        usages = [message['extra']['response']['usage']['prompt_tokens'] for message in trajectory.get('messages', [])
                  if isinstance(message.get('extra', {}).get('response'), dict) and message['extra']['response'].get('usage')]
        counts = [json.loads(path.read_text()).get('prompt_tokens_exact') for path in sorted(requests)]
        report['tokenize_prompt_tokens'] = counts
        report['native_response_prompt_tokens'] = usages
        report['tokenize_matches_native_usage'] = bool(counts) and counts == usages
        report['fresh_patch_replay'] = report['patch_bytes'] > 0 and report['replay_reward'] == 1
        probes = run / 'generation/instance_synthetic_add/agent/runtime-probe.json'
        resources = run / 'generation/instance_synthetic_add/agent/swe-runtime-resources.json'
        if probes.exists() and resources.exists():
            report['runtime_probe'] = json.loads(probes.read_text())
            report['resources'] = json.loads(resources.read_text())
            report['cpu_memory_network'] = (len(report['runtime_probe']['cpus']) == 1
                and all(report['runtime_probe'][key] is True for key in ('affinity_expansion_blocked',
                    'public_ip_blocked', 'dns_blocked', 'packet_blocked', 'netlink_blocked'))
                and report['resources']['memory_max'] == 4 * 1024**3
                and report['resources']['memory_swap_max'] == 0)
        else:
            report['cpu_memory_network'] = False
        report['real_endpoint_tokenize'] = args.endpoint is not None and bool(requests) and all(
            json.loads(path.read_text()).get('status') == 'accepted' for path in requests) and report['tokenize_matches_native_usage']
        report['passed'] = (report['initial_reward'] == report['replay_reward'] == 1
            and report['container_runtime_lock'] and report['native_mini'] and report['fresh_patch_replay']
            and not report['generation_exception'] and not report['replay_exception'])
        if args.endpoint:
            report['passed'] = report['passed'] and report['real_endpoint_tokenize']
        if server:
            report['http_generation_requests'] = len([r for r in server.requests if r['path'] == '/v1/chat/completions'])
            report['passed'] = report['passed'] and report['http_generation_requests'] == 3
            report['passed'] = report['passed'] and report['cpu_memory_network']
            save_json(run / 'stub_requests.json', server.requests)
    finally:
        if server:
            server.shutdown()
            server.server_close()
        report['seconds'] = round(time.monotonic() - started, 3)
        save_json(run / 'summary.json', report)
        print(json.dumps(report, indent=2))
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
