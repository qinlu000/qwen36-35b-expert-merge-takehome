"""Judge-only DeepSeek transport. Native ASI prompts, repeats and scoring stay upstream."""
import fcntl
import hashlib
import json
from pathlib import Path
import time
import uuid

import httpx
import litellm


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def input_token_bound(messages):
    """UTF-8 byte ceiling for text plus official 1024-token ceiling per image.

    https://api-docs.deepseek.com/guides/vision/ (retrieved 2026-10-16).
    The 256-token allowance covers chat framing; image base64 is not text input.
    """
    bound = 256
    for message in messages:
        content = message['content']
        if isinstance(content, str):
            bound += len(content.encode())
        else:
            for part in content:
                bound += len(part['text'].encode()) if part['type'] == 'text' else 1024
    return bound


class DeepSeekJudgeTransport:
    def __init__(self, settings, condition):
        self.settings = settings
        self.root = Path(settings["output"])
        self.condition = condition
        self.occurrences = {}
        self.directory = self.root / "judge_calls" / condition
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if settings["mode"] == "stub":
            self.key = "synthetic-only"
        else:
            credentials = dict(line.split("=", 1) for line in Path(settings["credentials"]).read_text().splitlines()
                               if line and not line.startswith("#") and "=" in line)
            self.key = credentials["DEEPSEEK_API_KEY"].strip().strip("\"'")

    def journal(self, event, *, reserve=False):
        path = self.root / "judge_calls.jsonl"
        with path.open("a+") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            if reserve:
                stream.seek(0)
                starts = [json.loads(line) for line in stream if line.strip()]
                starts = [row for row in starts if row.get("event") == "started"]
                used = len(starts)
                if used >= self.settings["max_generation_calls"]:
                    write_json(self.root / 'budget_exhausted.json', {'kind': 'generation_calls', 'used': used})
                    raise RuntimeError("Judge generation-call budget exhausted")
                if self.settings.get("max_cny") is not None:
                    charged = sum(row.get("reserved_cny", 0) for row in starts)
                    if charged + event["reserved_cny"] > self.settings["max_cny"]:
                        write_json(self.root / 'budget_exhausted.json', {'kind': 'CNY', 'reserved': charged})
                        raise RuntimeError("Judge CNY budget exhausted")
            stream.seek(0, 2)
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
            stream.flush()

    def __call__(self, **kwargs):
        if (self.root / "judge_identity_drift.json").exists() or (self.root / 'token_bound_exceeded.json').exists():
            raise RuntimeError("Judge identity drift was detected; batch stopped")
        body = {"model": "deepseek-flash", "messages": kwargs["messages"],
                "max_tokens": kwargs["max_tokens"], "temperature": 0,
                "thinking": {"type": "disabled"}, "stream": False}
        input_bound = kwargs.pop("input_token_bound", self.settings.get("input_token_bound"))
        if self.settings.get('input_bound_mode') == 'utf8_plus_image_ceiling':
            input_bound = input_token_bound(body['messages'])
        reserved_cny = ((input_bound * .3 + body["max_tokens"] * 1.2) / 1e6 * 8
                        if input_bound is not None else 0)
        request_hash = digest(body)
        occurrence = self.occurrences.get(request_hash, 0)
        self.occurrences[request_hash] = occurrence + 1
        key = f"{request_hash}.{occurrence}"
        response_path = self.directory / (key + ".response.json")
        if response_path.exists():
            payload = json.loads(response_path.read_text())
            self.journal({"event": "cache_reused", "condition": self.condition,
                          "request_sha256": request_hash, "occurrence": occurrence})
            return litellm.ModelResponse(**payload)
        write_json(self.directory / (key + ".request.json"), body)
        call_id = uuid.uuid4().hex
        base = {"id": call_id, "condition": self.condition,
                "request_sha256": request_hash, "occurrence": occurrence}
        self.journal({**base, "event": "started", "max_tokens": body["max_tokens"],
                      "input_token_bound": input_bound, "reserved_cny": reserved_cny,
                      "at_unix": time.time()}, reserve=True)
        started = time.monotonic()
        try:
            with httpx.Client(transport=httpx.HTTPTransport(retries=0), trust_env=False,
                              follow_redirects=False, timeout=self.settings["http_timeout"]) as client:
                response = client.post(self.settings["endpoint"] + "/chat/completions", json=body,
                    headers={"Authorization": "Bearer " + self.key})
                response.raise_for_status()
                payload = response.json()
            identity = {"requested_model": "deepseek-flash", "reported_model": payload.get("model"),
                        "system_fingerprint": payload.get("system_fingerprint"),
                        "provider_revision_pinned": False}
            identity_path = self.root / "judge_identity.json"
            expected_model = self.settings.get("expected_reported_model", "deepseek-flash")
            if ((expected_model is not None and identity["reported_model"] != expected_model) or
                    (identity_path.exists() and json.loads(identity_path.read_text()) != identity)):
                rejected = self.directory / (key + ".unaccepted.response.json")
                write_json(rejected, payload)
                write_json(self.root / "judge_identity_drift.json", {"observed": identity,
                    "call_id": call_id, "response_file": str(rejected), "usage": payload.get("usage")})
                raise RuntimeError("Judge response identity changed")
            if not identity_path.exists():
                write_json(identity_path, identity)
            write_json(response_path, payload)
            usage = payload.get("usage") or {}
            observed_cny = ((usage.get("prompt_tokens", 0) * .3 +
                             usage.get("completion_tokens", 0) * 1.2) / 1e6 * 8)
            self.journal({**base, "event": "completed", "elapsed_seconds": time.monotonic() - started,
                "response_id": payload.get("id"), "created": payload.get("created"),
                "identity": identity, "usage": payload.get("usage"),
                "observed_ceiling_cny": observed_cny,
                "finish_reason": payload["choices"][0].get("finish_reason")})
            if input_bound is not None and usage.get("prompt_tokens", 0) > input_bound:
                write_json(self.root / 'token_bound_exceeded.json', {'call_id':call_id,
                    'bound':input_bound, 'observed':usage.get('prompt_tokens')})
                raise RuntimeError("Judge input token bound exceeded; stop batch")
            return litellm.ModelResponse(**payload)
        except Exception as error:
            self.journal({**base, "event": "failed", "error_class": type(error).__name__,
                          "elapsed_seconds": time.monotonic() - started})
            raise RuntimeError("Judge transport failed: " + type(error).__name__) from None
