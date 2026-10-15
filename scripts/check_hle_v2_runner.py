"""Local fake-HTTP checks for HLE persistence,guards and ambiguous failure handling."""
import asyncio
import base64
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import shutil
import tempfile
import threading
from types import SimpleNamespace

from PIL import Image
import run_hle_v2 as runner


state = {'mode': 'normal', 'requests': 0, 'generations': 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        state['requests'] += 1
        assert self.headers['Authorization'] == 'Bearer synthetic-private-key'
        if self.path == '/tokenize':
            result = {'count': 57345 if state['mode'] == 'overflow' else 100,
                      'max_model_len': 65536}
        else:
            state['generations'] += 1
            assert data['max_tokens'] == 8192 and data['seed'] == 0 and data['top_k'] == 20
            assert data['chat_template_kwargs'] == {'enable_thinking': False, 'preserve_thinking': False}
            if state['mode'] == 'server_error':
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'{}')
                return
            content = data['messages'][1]['content']
            answer = '42'
            if len(content) > 1:
                image = Image.open(io.BytesIO(base64.b64decode(content[1]['image_url']['url'].split(',', 1)[1])))
                answer = 'red' if image.getpixel((0, 0))[0] else 'blue'
            result = {'choices': [{'message': {'content': answer}, 'finish_reason': 'stop'}],
                      'usage': {'prompt_tokens': 101 if state['mode'] == 'mismatch' else 100,
                                'completion_tokens': 2}}
        body = json.dumps(result).encode()
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    project = Path(__file__).resolve().parents[1]
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    checks = {}
    with tempfile.TemporaryDirectory(prefix='apex-hle-fixture-') as temporary:
        root = Path(temporary)
        files = ['configs/eval/protocol_v2_unified64k8k.json',
                 'analysis/source_snapshots/protocol/hle_task_ids.json',
                 'configs/eval/prompts/hle_system.txt']
        for name in files:
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project / name, root / name)
        source = root / 'artifacts/benchmarks/hle/source/hle_eval/run_model_predictions.py'
        source.parent.mkdir(parents=True)
        source.write_text('SYSTEM_PROMPT=' + repr((project / files[-1]).read_text().rstrip('\n')))
        key = root / 'key'
        key.write_text('synthetic-private-key')
        for mode in ['normal', 'overflow', 'mismatch', 'server_error']:
            state.update(mode=mode, requests=0, generations=0)
            args = SimpleNamespace(project=root, mode='calibration',
                                   endpoint=f'http://127.0.0.1:{server.server_port}',
                                   key_file=key, output=root / mode, prepare_only=False)
            with contextlib.redirect_stdout(io.StringIO()):
                asyncio.run(runner.run(args))
            summary = json.loads((root / mode / 'summary.json').read_text())
            checks[mode] = {'counts': summary['status_counts'], 'generations': state['generations']}
            if mode == 'normal':
                assert summary['passed'] and state['generations'] == 8
                before = state['requests']
                with contextlib.redirect_stdout(io.StringIO()):
                    asyncio.run(runner.run(args))
                assert state['requests'] == before
                checks['resume'] = {'extra_requests': 0}
            elif mode == 'overflow':
                assert state['generations'] == 0 and summary['status_counts'] == {'context_overflow': 8}
            else:
                assert state['generations'] == 8 and summary['status_counts'] == {'failed': 8}
    server.shutdown()
    print(json.dumps({'fixture_passed': True, 'checks': checks,
                      'network': 'local fake HTTP only; no model,API or GPU'}))


if __name__ == '__main__':
    main()
