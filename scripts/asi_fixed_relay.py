#!/usr/bin/env python3
"""One fixed model endpoint over a Unix socket; no HTTP proxy interface.

The controller owns FixedModelRelay. Its real key never enters the sandbox.
The --inside entry point only bridges namespace-local TCP to that Unix socket.
"""

from __future__ import annotations

import http.client
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import secrets
import select
import socket
import socketserver
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit


class _UnixHTTPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


class FixedModelRelay:
    """Allow only POST <base>/chat/completions for one configured model.

    No redirects, environment proxy, arbitrary host/path, or CONNECT support.
    Multimodal content supports only text and inline data images; the model
    server must not become an outbound URL fetcher on the agent's behalf.
    Only method/status metadata is recorded; request bodies and keys are not.
    """

    def __init__(self, socket_path: Path, *, base_url: str, model: str,
                 api_key: str, timeout: int = 10800, request_validator=None,
                 deadline: float | None = None):
        target = urlsplit(base_url)
        if (target.scheme not in ("http", "https") or not target.hostname
                or target.username or target.password or target.query or target.fragment):
            raise ValueError("Expected a fixed HTTP(S) model base URL")
        self.socket_path = Path(socket_path)
        self.target = target
        self.path = target.path.rstrip("/") + "/chat/completions"
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.request_validator = request_validator
        self.deadline = deadline
        self.agent_token = "asi-local-" + secrets.token_urlsafe(24)
        self.events: list[dict] = []
        self.active_sockets = set()
        self.lock = threading.Lock()
        self.closing = False

    def _track(self, connection):
        with self.lock:
            if self.closing:
                connection.close()
                return False
            self.active_sockets.add(connection)
            return True

    def _untrack(self, connection):
        with self.lock:
            self.active_sockets.discard(connection)

    def __enter__(self):
        relay = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def setup(self):
                super().setup()
                self.connection.settimeout(30)
                if not relay._track(self.connection):
                    self.connection.shutdown(socket.SHUT_RDWR)

            def finish(self):
                try:
                    super().finish()
                finally:
                    relay._untrack(self.connection)

            def log_message(self, *_args):
                pass

            def reject(self, status):
                relay.events.append({"method": self.command, "status": status})
                self.send_response(status)
                self.send_header("Content-Length", "0")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True

            def do_POST(self):
                if relay.deadline is not None and time.monotonic() >= relay.deadline:
                    return self.reject(408)
                if self.path != relay.path:
                    return self.reject(403)
                if self.headers.get("Authorization") != "Bearer " + relay.agent_token:
                    return self.reject(401)
                if self.headers.get("Transfer-Encoding"):
                    return self.reject(400)
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 64 * 1024 * 1024:
                        return self.reject(413)
                    raw = self.rfile.read(length)
                    body = json.loads(raw)
                    if body.get("model") != relay.model:
                        return self.reject(403)
                    for message in body.get("messages", []):
                        content = message.get("content")
                        if isinstance(content, list):
                            for part in content:
                                if part.get("type") == "text":
                                    continue
                                image = part.get("image_url", {})
                                url = image.get("url", "") if isinstance(image, dict) else ""
                                if (part.get("type") != "image_url" or not isinstance(url, str)
                                        or not url.startswith("data:image/") or ";base64," not in url):
                                    return self.reject(403)
                    if relay.request_validator is not None:
                        body = relay.request_validator(body)
                    # Send the parsed object, eliminating duplicate-key ambiguity
                    # between the controller and the fixed upstream parser.
                    raw = json.dumps(body).encode()
                except (ValueError, AttributeError, TimeoutError):
                    return self.reject(400)
                target = relay.target
                connection_class = (http.client.HTTPSConnection if target.scheme == "https"
                                    else http.client.HTTPConnection)
                remaining = relay.timeout
                if relay.deadline is not None:
                    remaining = min(remaining, relay.deadline - time.monotonic())
                if remaining <= 0:
                    return self.reject(408)
                upstream = connection_class(target.hostname, target.port, timeout=min(30, remaining))
                upstream_socket = None
                started = False
                try:
                    upstream.connect()
                    upstream_socket = upstream.sock
                    if not relay._track(upstream_socket):
                        return
                    if relay.deadline is not None:
                        remaining = min(remaining, relay.deadline - time.monotonic())
                    if remaining <= 0:
                        raise TimeoutError("Model relay deadline exhausted")
                    upstream_socket.settimeout(remaining)
                    # Construct fresh headers: the agent cannot choose upstream auth,
                    # Host, forwarding headers, proxy targets, or another URL.
                    upstream.request("POST", relay.path, body=raw, headers={
                        "Authorization": "Bearer " + relay.api_key,
                        "Content-Type": "application/json", "Accept": "text/event-stream, application/json",
                    })
                    response = upstream.getresponse()
                    relay.events.append({"method": "POST", "status": response.status})
                    self.send_response(response.status)
                    self.send_header("Content-Type", response.getheader("Content-Type", "application/json"))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    started = True
                    while True:
                        if relay.deadline is not None:
                            left = relay.deadline - time.monotonic()
                            if left <= 0:
                                raise TimeoutError("Model relay deadline exhausted")
                            upstream_socket.settimeout(left)
                            self.connection.settimeout(min(30, left))
                        chunk = response.read1(65536)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
                except (OSError, http.client.HTTPException):
                    if not started:
                        self.reject(502)
                finally:
                    self.close_connection = True
                    upstream.close()
                    if upstream_socket is not None:
                        relay._untrack(upstream_socket)

            def do_CONNECT(self):
                self.reject(403)

            do_GET = do_CONNECT
            do_PUT = do_CONNECT
            do_DELETE = do_CONNECT
            do_PATCH = do_CONNECT

        self.socket_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.server = _UnixHTTPServer(str(self.socket_path), Handler)
        self.socket_path.chmod(0o600)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_args):
        with self.lock:
            self.closing = True
            active = list(self.active_sockets)
        for connection in active:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.socket_path.unlink(missing_ok=True)


def run_inside(socket_path: str, port: int, command: list[str]) -> int:
    """Keep the local bridge alive while the unchanged native CLI runs."""
    class Bridge(socketserver.BaseRequestHandler):
        def handle(self):
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as upstream:
                upstream.connect(socket_path)
                peers = (self.request, upstream)
                while True:
                    ready, _, _ = select.select(peers, [], [])
                    for source in ready:
                        data = source.recv(65536)
                        if not data:
                            return
                        (upstream if source is self.request else self.request).sendall(data)

    class TCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        daemon_threads = True

    with TCPServer(("127.0.0.1", port), Bridge) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            # Inherit native stdin/stdout/stderr; no wrapper JSONL parser.
            return subprocess.call(command)
        finally:
            server.shutdown()


if __name__ == "__main__":
    if len(sys.argv) < 6 or sys.argv[1] != "--inside" or sys.argv[4] != "--":
        raise SystemExit("usage: asi_fixed_relay.py --inside SOCKET PORT -- COMMAND...")
    raise SystemExit(run_inside(sys.argv[2], int(sys.argv[3]), sys.argv[5:]))
