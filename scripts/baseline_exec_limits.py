#!/usr/bin/env python3
"""Run a container launcher inside its exact systemd memory scope and CPU set."""
import argparse
import ctypes
import os
import sys

from asi_baseline_limits import affinity_filter, verify_memory_limit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpus", type=int, required=True)
    parser.add_argument("--memory-bytes", type=int, required=True)
    parser.add_argument("--cpu-offset", type=int, default=0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if os.environ.get("APEX_NO_SYSTEMD_LIMITS") != "1":
        verify_memory_limit(args.memory_bytes)
    if args.cpu_offset:
        available = sorted(os.sched_getaffinity(0))
        os.sched_setaffinity(0, available[args.cpu_offset:])
    bpf, _ = affinity_filter(args.cpus)
    program = bpf.read()
    buffer = ctypes.create_string_buffer(program)

    class Filter(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ushort), ("instructions", ctypes.c_void_p)]

    libc = ctypes.CDLL(None, use_errno=True)
    filt = Filter(len(program) // 8, ctypes.addressof(buffer))
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(filt)):
        raise OSError(ctypes.get_errno(), "Cannot install inherited affinity filter")
    bpf.close()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    os.execvpe(command[0], command, os.environ)


if __name__ == "__main__":
    sys.exit(main())
