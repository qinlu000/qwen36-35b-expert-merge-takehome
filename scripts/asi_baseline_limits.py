#!/usr/bin/env python3
"""Linux execution helper: verified cgroup memory and immutable CPU affinity.

Run inside a systemd user scope with MemoryMax=8GiB and MemorySwapMax=0.
The user manager need not delegate the CPU controller: the program inherits
exactly four CPUs and a seccomp rule prevents it or its children widening them.
"""
import argparse
import ctypes
import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

def affinity_filter(cpus, cpu_list=None):
    """Set affinity and return an open, rewound BPF file for bwrap --seccomp."""
    available = sorted(os.sched_getaffinity(0))
    if len(available) < cpus:
        raise RuntimeError(f"Need {cpus} available CPUs, found {len(available)}")
    selected = available[:cpus] if cpu_list is None else list(cpu_list)
    if len(selected) != cpus or not set(selected).issubset(available):
        raise RuntimeError("Requested CPU set is not available or has the wrong size")
    os.sched_setaffinity(0, selected)
    seccomp = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    seccomp.seccomp_init.argtypes = [ctypes.c_uint32]
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    seccomp.seccomp_export_bpf.argtypes = [ctypes.c_void_p, ctypes.c_int]
    seccomp.seccomp_release.argtypes = [ctypes.c_void_p]
    context = seccomp.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    output = tempfile.TemporaryFile()
    try:
        syscall = seccomp.seccomp_syscall_resolve_name(b"sched_setaffinity")
        if not context or syscall < 0:
            raise RuntimeError("libseccomp cannot resolve sched_setaffinity")
        if seccomp.seccomp_rule_add(context, 0x00050000 | errno.EPERM, syscall, 0) != 0:
            raise RuntimeError("Cannot add the CPU affinity seccomp rule")
        if seccomp.seccomp_export_bpf(context, output.fileno()) != 0:
            raise RuntimeError("Cannot export the CPU affinity seccomp rule")
        output.seek(0)
        return output, selected
    finally:
        if context:
            seccomp.seccomp_release(context)


def verify_memory_limit(memory_bytes):
    group = Path("/sys/fs/cgroup") / Path("/proc/self/cgroup").read_text().strip().split("::", 1)[1].lstrip("/")
    actual = (group / "memory.max").read_text().strip()
    swap = (group / "memory.swap.max").read_text().strip()
    if actual != str(memory_bytes) or swap != "0":
        raise RuntimeError(f"cgroup memory is {actual}/swap {swap}, expected {memory_bytes}/0")
    return {"cgroup": str(group), "memory_max": int(actual), "memory_swap_max": int(swap)}


def main():
    from asi_bwrap import namespace_prefix, program_env

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--env-dir", type=Path, required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--ngspice", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--cpus", type=int, default=4)
    parser.add_argument("--cpu-list", help="Exact comma-separated CPU IDs assigned to this worker")
    parser.add_argument("--memory-bytes", type=int, default=8 * 1024**3)
    args = parser.parse_args()
    memory = verify_memory_limit(args.memory_bytes)
    bpf, cpus = affinity_filter(args.cpus, [int(n) for n in args.cpu_list.split(",")] if args.cpu_list else None)
    prefix, mounts, _ = namespace_prefix(args.workspace, args.env_dir, args.ngspice)
    command = prefix + ["--seccomp", str(bpf.fileno()), "--chdir", "/workspace", "--",
                        str(args.env_dir / "bin/python"), args.code]
    args.receipt.write_text(json.dumps({**memory, "allowed_cpus": cpus,
        "sched_setaffinity": "seccomp EPERM", "mounts": mounts}, indent=2) + "\n")
    with bpf:
        result = subprocess.run(command, env=program_env(args.env_dir, args.ngspice),
                                pass_fds=(bpf.fileno(),))
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
