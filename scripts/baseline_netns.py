#!/usr/bin/env python3
"""Per-container rootless network namespace; host control and model-only Unix bridges."""
import argparse
import asyncio
import os
from pathlib import Path
import select
import subprocess
import sys


async def bridge(reader, writer, *, tcp=None, unix=None):
    """Forward bytes to one fixed destination, never a client-selected host."""
    other = None
    try:
        upstream, other = (await asyncio.open_unix_connection(unix) if unix else
                           await asyncio.open_connection(*tcp))

        async def copy(source, target):
            while data := await source.read(65536):
                target.write(data)
                await target.drain()
            if target.can_write_eof():
                target.write_eof()

        tasks = [asyncio.create_task(copy(reader, other)),
                 asyncio.create_task(copy(upstream, writer))]
        _, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()
        if other:
            other.close()


class NetworkNamespace:
    def __init__(self, root, directory):
        self.root = Path(root)
        self.directory = Path(directory)
        self.owner = None
        self.slirp = None
        self.relay = None
        self.model_server = None
        self.log = None

    def command(self, *command):
        return ["nsenter", "-t", str(self.owner.pid), "--user", "--net",
                "--preserve-credentials", *map(str, command)]

    def run(self, *command, **kwargs):
        return subprocess.run(self.command(*command), check=True, capture_output=True,
                              text=True, timeout=15, **kwargs)

    async def start(self, control_port, model_host_port=None, model_socket=None):
        self.owner = subprocess.Popen(
            ["unshare", "-Urn", "sh", "-c", "echo READY; exec sleep infinity"],
            stdout=subprocess.PIPE, text=True)
        if self.owner.stdout.readline().strip() != "READY":
            raise RuntimeError("Network namespace did not start")
        self.owner.stdout.close()
        tools = self.root / "artifacts/tools/slirp4netns/rootfs/usr"
        compat = self.root / "artifacts/tools/slirp4netns/compat_glibc235"
        if all((compat / name).exists() for name in
               ("ld-linux-x86-64.so.2", "slirp4netns")):
            slirp_command = [
                str(compat / "ld-linux-x86-64.so.2"),
                "--library-path",
                ":".join((str(compat), str(tools / "lib/x86_64-linux-gnu"),
                           "/lib64", "/lib/x86_64-linux-gnu")),
                str(compat / "slirp4netns"),
            ]
        else:
            slirp_command = [str(tools / "bin/slirp4netns")]
        read_fd, write_fd = os.pipe()
        self.log = (self.directory / "network.log").open("w")
        self.slirp = subprocess.Popen(
            [*slirp_command, "--configure", "--disable-host-loopback",
             "--enable-seccomp", "--ready-fd", str(write_fd), "--userns-path",
             f"/proc/{self.owner.pid}/ns/user", str(self.owner.pid), "tap0"],
            env=dict(os.environ, LD_LIBRARY_PATH=str(tools / "lib/x86_64-linux-gnu")),
            pass_fds=(write_fd,), stdout=self.log, stderr=self.log)
        os.close(write_fd)
        ready = await asyncio.to_thread(select.select, [read_fd], [], [], 10)
        success = bool(ready[0]) and os.read(read_fd, 1) == b"1"
        os.close(read_fd)
        if not success:
            raise RuntimeError("slirp4netns did not become ready")
        self.resolver = self.directory / "resolv.conf"
        self.resolver.write_text("nameserver 10.0.2.3\n")
        self.control_socket = self.directory / "control.sock"
        self.model_socket = Path(model_socket) if model_socket else self.directory / "model.sock"
        if model_socket is None and model_host_port is not None:
            self.model_server = await asyncio.start_unix_server(
                lambda r, w: bridge(r, w, tcp=("127.0.0.1", model_host_port)),
                str(self.model_socket))
            self.model_socket.chmod(0o600)
        model_args = ["--model-socket", self.model_socket] if model_socket or model_host_port else []
        self.relay = subprocess.Popen(self.command(
            sys.executable, str(Path(__file__).resolve()), "--namespace-relays",
            "--control-socket", self.control_socket, "--control-port", control_port,
            *model_args), stdout=self.log, stderr=self.log)
        for _ in range(100):
            if self.control_socket.exists():
                break
            if self.relay.poll() is not None:
                raise RuntimeError("Namespace relay exited")
            await asyncio.sleep(0.05)
        else:
            raise RuntimeError("Namespace relay did not start")
        self.set_public(True)

    def set_public(self, public):
        # No established-connection exception in solver mode: old public streams
        # lose both directions when the phase changes. IPv6 egress stays disabled.
        output = "ACCEPT" if public else "DROP"
        rules = ["*filter", ":INPUT DROP [0:0]", ":FORWARD DROP [0:0]",
                 f":OUTPUT {output} [0:0]", "-A INPUT -i lo -j ACCEPT",
                 "-A OUTPUT -o lo -j ACCEPT"]
        if public:
            rules += ["-A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT",
                      "-A OUTPUT -d 10.0.2.3 -p udp --dport 53 -j ACCEPT",
                      "-A OUTPUT -d 10.0.2.3 -p tcp --dport 53 -j ACCEPT"]
            for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
                            "169.254.0.0/16", "100.64.0.0/10"):
                rules.append(f"-A OUTPUT -d {network} -j REJECT")
        self.run("iptables-restore", input="\n".join(rules + ["COMMIT", ""]))
        self.run("ip6tables-restore", input="*filter\n:INPUT DROP [0:0]\n"
                 ":FORWARD DROP [0:0]\n:OUTPUT DROP [0:0]\n"
                 "-A INPUT -i lo -j ACCEPT\n-A OUTPUT -o lo -j ACCEPT\nCOMMIT\n")

    async def close(self):
        if self.model_server:
            self.model_server.close()
            await self.model_server.wait_closed()
        for process in (self.relay, self.slirp, self.owner):
            if process and process.poll() is None:
                process.terminate()
                try:
                    await asyncio.to_thread(process.wait, 3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    await asyncio.to_thread(process.wait)
        if self.log:
            self.log.close()


async def namespace_relays(args):
    control = await asyncio.start_unix_server(
        lambda r, w: bridge(r, w, tcp=("127.0.0.1", args.control_port)),
        str(args.control_socket))
    args.control_socket.chmod(0o600)
    async with control:
        if args.model_socket:
            model = await asyncio.start_server(
                lambda r, w: bridge(r, w, unix=str(args.model_socket)), "127.0.0.1", 18000)
            async with model:
                await asyncio.gather(control.serve_forever(), model.serve_forever())
        else:
            await control.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace-relays", action="store_true", required=True)
    parser.add_argument("--control-socket", type=Path, required=True)
    parser.add_argument("--control-port", type=int, required=True)
    parser.add_argument("--model-socket", type=Path)
    asyncio.run(namespace_relays(parser.parse_args()))
