"""Keep official LockedMiniSwe/mini behavior, pin installation and v2 request settings."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shlex
import socket
import sys
import threading
import time

import httpx
import yaml

from asi_fixed_relay import FixedModelRelay


ROOT = Path(__file__).resolve().parents[1]
TOOLING = ROOT / 'artifacts/benchmarks/swe-bench-pro/v2/tooling'
sys.path.insert(0, str(TOOLING))
from locked_mini_swe import LockedMiniSwe

BRIDGES = {}
TEMPLATE = {'enable_thinking': False, 'preserve_thinking': False}


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


class SweModelBridge:
    """Fixed upstream auth and exact native chat/tool budget at the host boundary."""
    def __init__(self, socket_path, endpoint, key_path, logs_dir, model='apex-qwen'):
        self.identifier = str(socket_path)
        self.endpoint = endpoint.rstrip('/').removesuffix('/v1')
        self.key = Path(key_path).read_text().strip()
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.deadline = None
        self.counter = 0
        self.lock = threading.Lock()
        self.relay = FixedModelRelay(Path(socket_path), base_url=self.endpoint + '/v1',
            model=model, api_key=self.key, timeout=1800, request_validator=self.validate)

    def __enter__(self):
        self.relay.__enter__()
        BRIDGES[self.identifier] = self
        return self

    def remaining(self):
        if self.deadline is None or self.deadline <= time.monotonic():
            raise TimeoutError('SWE model access is outside the shared1800s solver phase')
        return self.deadline - time.monotonic()

    def begin(self):
        self.deadline = time.monotonic() + 1800
        self.relay.deadline = self.deadline

    def end(self):
        self.relay.deadline = time.monotonic()
        with self.relay.lock:
            active = list(self.relay.active_sockets)
        for connection in active:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()

    def __exit__(self, *args):
        BRIDGES.pop(self.identifier, None)
        self.relay.__exit__(*args)

    def validate(self, body):
        with self.lock:
            self.counter += 1
            path = self.logs_dir / f'{self.counter:05d}.json'
        # Preserve native messages/tools, and reconstruct the fixed generation
        # contract. This also prevents shell curl requests selecting n>1,
        # prompt truncation, a second output cap, or a different template.
        body = {key: body[key] for key in ('messages', 'tools', 'tool_choice', 'parallel_tool_calls') if key in body}
        body.update(model=self.model, max_tokens=8192, temperature=.7, top_p=.8,
            top_k=20, min_p=0, presence_penalty=0, repetition_penalty=1, seed=0,
            n=1, stream=False, chat_template_kwargs=TEMPLATE)
        record = {'request': body, 'status': 'tokenizing',
                  'request_sha256': hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()}
        save_json(path, record)
        try:
            remaining = self.remaining()
            with httpx.Client(transport=httpx.HTTPTransport(retries=0), trust_env=False,
                    headers={'Authorization': 'Bearer ' + self.key}) as client:
                payload = {'model': self.model, 'messages': body['messages'],
                           'tools': body.get('tools'), 'add_generation_prompt': True,
                           'chat_template_kwargs': TEMPLATE}
                response = client.post(self.endpoint + '/tokenize', json=payload, timeout=remaining)
                response.raise_for_status()
                counted = response.json()
            record['prompt_tokens_exact'] = counted['count']
            if counted['max_model_len'] != 65536:
                raise ValueError('SWE endpoint context differs from frozen65536')
            if counted['count'] + 8192 > 65536:
                raise ValueError('context_budget_exceeded')
            self.remaining()
            record['status'] = 'accepted'
            return body
        except (httpx.HTTPError, KeyError) as error:
            record.update(status='rejected', error_type=type(error).__name__, error=str(error))
            raise ValueError('SWE exact tokenizer guard failed') from error
        except (ValueError, TimeoutError) as error:
            record.update(status='rejected', error_type=type(error).__name__, error=str(error))
            raise
        finally:
            save_json(path, record)


class DeadlineEnvironment:
    """Clamp native execs, including its final patch capture, to the solver clock."""
    def __init__(self, environment, bridge):
        self.environment, self.bridge = environment, bridge

    def __getattr__(self, name):
        return getattr(self.environment, name)

    async def exec(self, *args, **kwargs):
        remaining = self.bridge.remaining()
        if remaining < 1:
            raise TimeoutError('SWE solver has less than one whole exec second left')
        # Harbor's server wire schema requires an integer timeout; a fractional
        # monotonic remainder is rejected with HTTP422 before running the exec.
        kwargs['timeout_sec'] = int(min(kwargs.get('timeout_sec') or remaining, remaining))
        return await self.environment.exec(*args, **kwargs)


def mini_config(root=ROOT):
    source = Path(root) / 'artifacts/benchmarks/swe-bench-pro/v2/tooling/configs/mini_toolcall.yaml'
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '7275afa9920a6fb1b9ec66ab74cee44121db9b0276bb9fa90f5ec0597e523a45'
    config = yaml.safe_load(raw)
    config['agent'].update(cost_limit=0, step_limit=0)
    model = config['model']
    model['model_kwargs'].pop('reasoning_effort')
    model['model_kwargs'].update(temperature=0.7, top_p=0.8, seed=0, max_tokens=8192,
        num_retries=0, timeout=1800, presence_penalty=0, repetition_penalty=1,
        extra_body={'top_k': 20, 'min_p': 0,
                    'chat_template_kwargs': {'enable_thinking': False, 'preserve_thinking': False}})
    return config


class SweBaselineV2(LockedMiniSwe):
    def __init__(self, *args, **kwargs):
        self.v2_bridge_id = kwargs.pop('v2_bridge_id', None)
        if kwargs.get('version', '2.4.6') != '2.4.6':
            raise ValueError('This baseline pins mini-swe-agent 2.4.6')
        kwargs.update(version='2.4.6', config=mini_config(), max_tokens=8192,
                      cost_limit='0', reasoning_effort=None)
        super().__init__(*args, **kwargs)
        # Harbor's external timeout does not populate the official wrapper's
        # private field; set it so its native budget-minus60 path yields1740s.
        self._timeout_sec = 1800

    async def install(self, environment):
        install_user = None if os.environ.get('APEX_HPC_NO_FAKEROOT') == '1' else 'root'
        await environment.exec(command='mkdir -p /tmp/apex-mini-lock', user=install_user)
        await environment.upload_file(ROOT / 'configs/envs/mini-swe-py312.txt',
                                      '/tmp/apex-mini-lock/constraints.txt')
        if os.environ.get('APEX_HPC_NO_FAKEROOT') == '1':
            await self.exec_as_agent(environment, command=(
                'set -euo pipefail; export PATH="/opt/apex-swe-tools:$HOME/.local/bin:$PATH"; '
                'uv tool install --python 3.12 mini-swe-agent==2.4.6 '
                '--with litellm --with orjson --with fastapi && mini-swe-agent --help'))
            await self._verify_mini_runtime(environment)
            return
        await super().install(environment)
        await self._verify_mini_runtime(environment)

    async def _verify_mini_runtime(self, environment):
        # Freeze actual installed versions as well as the requested constraints.
        code = ('import importlib.metadata as m,json; '
                'print(json.dumps({d.metadata["Name"]:d.version for d in m.distributions()},sort_keys=True))')
        await self.exec_as_agent(environment, command=(
            'mkdir -p /logs/agent; '
            'p="$HOME/.local/share/uv/tools/mini-swe-agent/bin/python"; '
            '"$p" -c ' + shlex.quote(code) + ' '
            '> /logs/agent/mini-runtime.json'))
        result = await environment.exec(command='cat /logs/agent/mini-runtime.json', timeout_sec=30)
        installed = json.loads(result.stdout)
        pinned = dict(line.split('==', 1) for line in
                      (ROOT / 'configs/envs/mini-swe-py312.txt').read_text().splitlines() if '==' in line)
        normalize = lambda name: name.lower().replace('_', '-').replace('.', '-')
        pinned = {normalize(k): v for k, v in pinned.items()}
        mismatches = {k: v for k, v in installed.items() if pinned.get(normalize(k)) != v}
        if installed.get('mini-swe-agent') != '2.4.6' or mismatches:
            raise ValueError('Container mini runtime differs from fixed constraints: ' + str(mismatches))
        save_json(self.logs_dir / 'mini-runtime-verified.json', {
            'versions': installed, 'constraint_sha256': hashlib.sha256(
                (ROOT / 'configs/envs/mini-swe-py312.txt').read_bytes()).hexdigest(),
            'offline_runtime_manifest_sha256': hashlib.sha256(
                (ROOT / 'artifacts/cache/swe-v2-runtime/manifest.json').read_bytes()).hexdigest(),
            'native_yaml_sha256': '7275afa9920a6fb1b9ec66ab74cee44121db9b0276bb9fa90f5ec0597e523a45'})

    async def run(self, instruction, environment, context):
        bridge = BRIDGES[self.v2_bridge_id]
        bridge.begin()
        try:
            async with asyncio.timeout_at(bridge.deadline):
                await super().run(instruction, DeadlineEnvironment(environment, bridge), context)
        except BaseException as error:
            receipt = await environment.terminate_solver_processes(reason=f'{type(error).__name__}: {error}')
            context.metadata = context.metadata or {}
            context.metadata['v2_solver_error_cleanup'] = receipt
            raise
        finally:
            bridge.end()
            save_json(self.logs_dir / 'v2-relay.json', {'calls': bridge.counter,
                'events': bridge.relay.events, 'transport_attempt_limit_per_request': 1})

    async def exec_as_agent(self, environment, command, **kwargs):
        if 'uv tool install --python 3.12 mini-swe-agent' in command:
            command = command.replace('uv tool install --python 3.12 mini-swe-agent',
                'uv tool install --constraints /tmp/apex-mini-lock/constraints.txt '
                '--python 3.12 mini-swe-agent', 1)
            kwargs['env'] = {**(kwargs.get('env') or {}), 'UV_OFFLINE': '1',
                'UV_FIND_LINKS': '/opt/apex-swe-wheels', 'UV_PYTHON_DOWNLOADS': 'never',
                'UV_LINK_MODE': 'copy'}
        if 'mini-swe-agent --yolo' in command:
            kwargs['env'] = {**(kwargs.get('env') or {}),
                            'OPENAI_API_KEY': BRIDGES[self.v2_bridge_id].relay.agent_token,
                            'MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT': '1',
                            'OPENAI_MAX_RETRIES': '0', 'LITELLM_LOCAL_MODEL_COST_MAP': 'True'}
        return await super().exec_as_agent(environment, command, **kwargs)
