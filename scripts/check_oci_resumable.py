#!/usr/bin/env python3
"""Reproduce a truncated OCI layer using synthetic bytes and private caches only."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gzip
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from urllib.parse import urlsplit


CHUNK = 64 * 1024


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fixture():
    payload = random.Random(31415).randbytes(9 * 1024 * 1024)
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as archive:
        member = tarfile.TarInfo("synthetic-payload.bin")
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))
    layer = gzip.compress(raw.getvalue(), mtime=0)
    config = json.dumps({"architecture": "amd64", "os": "linux", "config": {},
        "rootfs": {"type": "layers", "diff_ids": [digest(raw.getvalue())]},
        "history": [{"created_by": "self-authored EOF fixture"}]}).encode()
    manifest = json.dumps({"schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {"mediaType": "application/vnd.oci.image.config.v1+json",
                   "digest": digest(config), "size": len(config)},
        "layers": [{"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                    "digest": digest(layer), "size": len(layer)}]}).encode()
    return layer, config, manifest


@contextmanager
def registry(layer, config, manifest):
    requests = []
    first_range = True
    blobs = {digest(layer): layer, digest(config): config}

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_HEAD(self):
            self.serve(head=True)

        def do_GET(self):
            self.serve(head=False)

        def serve(self, head):
            nonlocal first_range
            path = urlsplit(self.path).path
            if path.rstrip("/") == "/v2":
                data, content_type = b"{}", "application/json"
            elif path.startswith("/v2/synthetic/manifests/"):
                data = manifest
                content_type = "application/vnd.oci.image.manifest.v1+json"
            elif path.startswith("/v2/synthetic/blobs/") and path.rsplit("/", 1)[1] in blobs:
                data = blobs[path.rsplit("/", 1)[1]]
                content_type = "application/octet-stream"
            else:
                self.send_error(404)
                return
            start, end, status = 0, len(data) - 1, 200
            range_header = self.headers.get("Range")
            if range_header:
                match = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header)
                if not match:
                    self.send_error(400)
                    return
                start = int(match[1])
                end = min(int(match[2]), end) if match[2] else end
                if start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{len(data)}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                status = 206
            body = data[start:end + 1]
            truncate = False
            if not head and data is layer:
                truncate = range_header is None or first_range
                if range_header:
                    first_range = False
            sent = min(CHUNK, len(body)) if truncate else len(body)
            requests.append({"method": "HEAD" if head else "GET", "path": path,
                "range": range_header, "status": status, "start": start,
                "declared_bytes": len(body), "sent_bytes": 0 if head else sent,
                "truncated": truncate})
            self.send_response(status)
            self.send_header("Docker-Distribution-Api-Version", "registry/2.0")
            self.send_header("Docker-Content-Digest", digest(data))
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            if range_header:
                self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
            self.send_header("Connection", "close")
            self.end_headers()
            if not head:
                self.wfile.write(body[:sent])
                self.wfile.flush()
            self.close_connection = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def check_helper(path, base, layer, cache, requests_log):
    import requests

    started = time.monotonic()
    spec = importlib.util.spec_from_file_location("oci_resume_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    start = len(requests_log)
    with requests.Session() as session:
        session.trust_env = False
        blob = module.download_blob(session, base + "/v2/synthetic/blobs/" + digest(layer),
                                    digest(layer), len(layer), cache)
        assert blob.read_bytes() == layer
        calls = list(requests_log[start:])
        assert calls[0]["truncated"] and calls[0]["range"]
        assert any(call["status"] == 206 and call["start"] == module.CHUNK_SIZE for call in calls)
        before_cache_hit = len(requests_log)
        again = module.download_blob(session, base + "/v2/synthetic/blobs/" + digest(layer),
                                     digest(layer), len(layer), cache)
        assert again == blob and len(requests_log) == before_cache_hit
        # An unverified migrated prefix can be corrupt. Reject it at whole-blob
        # SHA, keep the evidence, then let the next attempt start at byte zero.
        bad_cache = cache.parent / "corrupt-prefix-cache"
        part = bad_cache / "parts" / (digest(layer).split(":")[1] + ".part")
        part.parent.mkdir(parents=True)
        bad_prefix = bytearray(layer[:CHUNK])
        bad_prefix[0] ^= 1
        part.write_bytes(bad_prefix)
        corrupt_start = len(requests_log)
        try:
            module.download_blob(session, base + "/v2/synthetic/blobs/" + digest(layer),
                                 digest(layer), len(layer), bad_cache)
        except ValueError:
            pass
        else:
            raise AssertionError("Corrupt prefix unexpectedly passed whole-layer SHA")
        invalid = part.with_suffix(".invalid")
        assert not part.exists() and invalid.stat().st_size == len(layer)
        assert digest(invalid.read_bytes()) != digest(layer)
        assert requests_log[corrupt_start]["start"] == CHUNK
        restart_start = len(requests_log)
        recovered = module.download_blob(session, base + "/v2/synthetic/blobs/" + digest(layer),
                                         digest(layer), len(layer), bad_cache)
        assert requests_log[restart_start]["start"] == 0
        assert recovered.read_bytes() == layer
    return {"passed": True, "seconds": round(time.monotonic() - started, 3),
        "helper_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "blob_bytes": blob.stat().st_size,
        "blob_digest": digest(blob.read_bytes()), "range_requests": calls,
        "verified_cache_hit_without_get": True,
        "corrupt_prefix": {"seed_bytes": CHUNK, "first_range_start": CHUNK,
            "sha_rejected": True, "invalid_bytes_preserved": invalid.stat().st_size,
            "next_attempt_range_start": 0, "recovered_full_sha": True}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apptainer", type=Path, required=True)
    parser.add_argument("--helper", type=Path, help="Module exporting download_blob; optional for the native red-only check")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or root / "artifacts/preflight/swe_tb" / ("oci-eof-" + stamp)
    output.mkdir(parents=True, exist_ok=True)
    layer, config, manifest = fixture()
    summary = {"self_authored_only": True, "image_contents_executed": False,
        "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "layer_bytes": len(layer), "layer_digest": digest(layer), "baseline_red": False}
    with tempfile.TemporaryDirectory(prefix="apex-oci-eof-") as temporary:
        work = Path(temporary)
        with registry(layer, config, manifest) as (base, requests):
            env = dict(os.environ, APPTAINER_CACHEDIR=str(work / "cache"),
                APPTAINER_TMPDIR=str(work / "tmp"), NO_PROXY="127.0.0.1,localhost",
                no_proxy="127.0.0.1,localhost", GOMAXPROCS="2")
            (work / "tmp").mkdir()
            command = [str(args.apptainer.resolve()), "pull", "--no-https",
                str(work / "synthetic.sif"), "docker://" + base.removeprefix("http://") + "/synthetic:latest"]
            started = time.monotonic()
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=30)
            (output / "apptainer.log").write_text(result.stdout + result.stderr)
            errors = [line for line in (result.stdout + result.stderr).splitlines() if "FATAL" in line or "EOF" in line]
            summary.update(baseline_returncode=result.returncode,
                baseline_red=result.returncode != 0 and "unexpected EOF" in result.stdout + result.stderr,
                baseline_errors=errors, baseline_command=command,
                baseline_seconds=round(time.monotonic() - started, 3))
            if args.helper:
                assert summary["baseline_red"], "Native pull must reach the EOF before testing the helper"
                summary["resumable"] = check_helper(args.helper.resolve(), base, layer,
                                                      work / "resumable-cache", requests)
            summary["requests"] = requests
    summary["temporary_directory_removed"] = not work.exists()
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"output": str(output), **summary}, indent=2))
    assert summary["baseline_red"], "Expected native Apptainer to reproduce unexpected EOF"


if __name__ == "__main__":
    main()
