#!/usr/bin/env python3
"""Check one frozen nginx restoration; --execute performs exactly one leased native grade."""
import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from run_terminal_native_gap_queue_20261017 import busy_scopes, now, save

CONFIG_SHA256 = 'eca70b4f22346232efb0da8693e3b42faa2b8869c84990350af794ef7de39b45'
PREPARATION_SHA256 = '204b266e6473b3b5d2be422767d51395ec13f86b7ff911513e358cd0ec5a2ada'
LEASE_HELPER_SHA256 = '0cf19a9b8b5b4e3f661c2087678777635f43b859177b095c5157dee18c21a4ab'
CORE_DEADLINE = '2026-10-18T02:20:00+08:00'
CORE_END = datetime.fromisoformat(CORE_DEADLINE).timestamp()
MIN_ADMISSION_RUNWAY_SECONDS = 1800
BOOTSTRAP_OLD_SHA256 = {
    'execution-claim.json': 'b4ff1f0cd7878e1f72129e603f0698867b64fd57f4689fe927956ce85ad26843',
    'parent-state.json': 'd2c8b47769ad282368c0e1f4f42c9084229982feb5310162b6da67d37bace9ac',
    'parent-events.jsonl': '34a4aabc96e8da62d4db8ff97897dfc35b176fb3205bf2ce8cdd6b0d59f97946',
    'parent-launch.json': 'e8c47506c156cc2d3ba1040eea621d21b5608ff7e060c67c1770bc9eca35d1d2',
    'parent-launch.log': '32bbb03c629cdd361e0709f499261e4327f4e458d6200552a69b6e5e849c7143',
    'native-child.log': '7ce6413a0d2f3ee6b1a1ef460f728a9cf4bd939d8887c4b1da7a75a3057c4ea1',
}
CPU_BOOTSTRAP_SHA256 = {
    'bootstrap-recovery-20261017/execution-claim.json': 'f28b70a4b3669131ab6adf3c0c43e1316412c3b85941b97930de787c258faeec',
    'bootstrap-recovery-20261017/parent-state.json': 'f25991b1be06d203f2ecaaee33eb17862a9cb56ca549eca5d45e9721d95455a1',
    'bootstrap-recovery-20261017/parent-events.jsonl': '1dc725fd623af65314501b7d199241711c6a0667b08d854a3211a6c1bc703feb',
    'bootstrap-recovery-20261017/parent-launch.json': '4875634a6e9af7d275d35455d559fe86880b6e5efa1113656c8e45f3f1ee2d6d',
    'bootstrap-recovery-20261017/native-child.log': 'bae62c66b92778686f48fddf73784bd421dfa5e7d45c2bb4c19c9a9f744a5337',
    'native-grade/result.json': 'e084c7343a0bfb1b95d37d26c4c54b3d84170c06b21489ef8dbebdd4618ad1c2',
    'cpu-bootstrap-smoke-observer2-20261017/smoke.json': '9765981266c185d9691b89c2cd83fdf821b663679de828bd8e719f5b13b9c962',
}
CPU_FAILURE_LOG = Path('/data/caoqinlu/apex-terminal250-tmp/apex_baseline_staging_xln34_n9/server.log')
CPU_FAILURE_LOG_SHA256 = '07637fa86387ce6ef62d9452055c3c36779f9f4b10d43b2d7d1357d24a176c20'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def startticks(pid):
    try:
        return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[19]
    except FileNotFoundError:
        return None  # A setup/import error can make the child exit before this observation.


def effective_cpus():
    group = Path('/proc/self/cgroup').read_text().strip().split('::')[-1]
    directory = Path('/sys/fs/cgroup') / group.lstrip('/')
    # A session scope without its own cpuset controller inherits its ancestor's mask.
    while not (directory / 'cpuset.cpus.effective').exists():
        directory = directory.parent
    text = (directory / 'cpuset.cpus.effective').read_text().strip()
    cpus = set()
    for part in text.split(','):
        ends = [int(value) for value in part.split('-')]
        cpus.update(range(ends[0], ends[-1] + 1))
    return cpus


def same_process_alive(pid, ticks):
    try:
        fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
        return fields[0] != 'Z' and fields[19] == ticks
    except FileNotFoundError:
        return False


def bootstrap_recovery_gate(prepared, native_output, bindings):
    """Admit only the exact import failure, which never created a native environment."""
    old = json.loads((prepared / 'parent-state.json').read_text())
    assert old['pid'] == 851972 and old['startticks'] == '868587717'
    assert not same_process_alive(old['pid'], old['startticks']), 'Original parent still running'
    assert old['state'] == 'finished_pending_review' and old['child_returncode'] == 1
    assert not old['lock_held'] and not old['native_result_exists']
    assert old['original_and_restore_files_unchanged']
    assert not os.path.lexists(native_output), 'Native output exists; bootstrap recovery forbidden'
    assert len(old['consecutive_empty_scope_samples']) == 2
    assert all(not row['remaining_cpu_scopes'] for row in old['consecutive_empty_scope_samples'])
    text = (prepared / 'native-child.log').read_text()
    assert 'PackageNotFoundError: No package metadata was found for harbor' in text
    evidence = {str(prepared / name): expected for name, expected in BOOTSTRAP_OLD_SHA256.items()}
    assert all(sha256(Path(path)) == expected for path, expected in evidence.items()), 'Old attempt evidence changed'
    assert all(sha256(Path(path)) == expected for path, expected in bindings.items()), 'Original candidate binding changed'
    return {'old_pid': old['pid'], 'old_startticks': old['startticks'],
            'old_child_returncode': 1, 'native_environment_or_test_started': False,
            'preserved_old_evidence_sha256': evidence}


def bootstrap_cpu_recovery_gate(prepared, native_output, bindings):
    """Admit only parent1209420's exact pre-restore affinity-index failure."""
    old = json.loads((prepared / 'bootstrap-recovery-20261017/parent-state.json').read_text())
    assert old['pid'] == 1209420 and old['startticks'] == '869108324'
    assert not same_process_alive(old['pid'], old['startticks']), 'Bootstrap parent still running'
    assert not same_process_alive(old['child_pid'], old['child_startticks']), 'Bootstrap child still running'
    assert old['state'] == 'finished_pending_review' and old['child_returncode'] == 0
    assert not old['lock_held'] and old['native_result_exists'] and old['native_reward'] is None
    assert old['original_and_restore_files_unchanged'] and not old['accepted_into_formal_summary']
    assert len(old['consecutive_empty_scope_samples']) == 2
    assert all(not row['remaining_cpu_scopes'] for row in old['consecutive_empty_scope_samples'])
    failed_output = prepared / 'native-grade'
    assert [str(path.relative_to(failed_output)) for path in failed_output.rglob('*') if path.is_file()] == ['result.json'], 'Restore or test evidence exists'
    failed = json.loads((failed_output / 'result.json').read_text())
    assert failed['verifier_result'] is None
    error = failed['exception_info']
    assert error['exception_type'] == 'RuntimeError'
    assert error['exception_message'] == 'Baseline bootstrap failed; see ' + str(CPU_FAILURE_LOG)
    assert 'await environment.start(force_build=False)' in error['exception_traceback']
    assert old['command'][-2:] == ['--cpu-offset', '92']
    assert old['command'][:3] == ['taskset', '-c', '92-95']
    text = CPU_FAILURE_LOG.read_text()
    assert 'os.sched_setaffinity(0, available[args.cpu_offset:])' in text
    assert text.endswith('OSError: [Errno 22] Invalid argument\n')
    evidence = {str(prepared / name): expected for name, expected in
                {**BOOTSTRAP_OLD_SHA256, **CPU_BOOTSTRAP_SHA256}.items()}
    evidence[str(CPU_FAILURE_LOG)] = CPU_FAILURE_LOG_SHA256
    assert all(sha256(Path(path)) == expected for path, expected in evidence.items()), 'Prior attempt or smoke evidence changed'
    assert all(sha256(Path(path)) == expected for path, expected in bindings.items()), 'Original candidate binding changed'
    smoke = json.loads((prepared / 'cpu-bootstrap-smoke-observer2-20261017/smoke.json').read_text())
    assert smoke['passed'] and smoke['state'] == 'finished' and not smoke['lock_held']
    assert smoke['actual_affinity'] == [92, 93, 94, 95] and smoke['logical_cpu_offset'] == 0
    assert smoke['memory_max_bytes'] == 8589934592 and smoke['memory_swap_max_bytes'] == 0
    assert smoke['model_calls'] == smoke['candidate_restore_commands'] == smoke['verifier_runs'] == 0
    assert smoke['all_original_attempt_bytes_unchanged'] and smoke['lock_released_at_utc']
    assert len(smoke['consecutive_empty_scope_samples']) == 2
    assert all(not row['remaining_cpu_scopes'] for row in smoke['consecutive_empty_scope_samples'])
    assert not os.path.lexists(native_output), 'New CPU-recovery output already exists'
    return {'old_pid': old['pid'], 'old_startticks': old['startticks'],
            'old_child_returncode': 0, 'old_failure_stage': 'environment_start_before_restore',
            'new_logical_cpu_offset': 0, 'physical_cpu_ids': [92, 93, 94, 95],
            'preserved_old_evidence_sha256': evidence}


def validate(root, config_path):
    assert sha256(config_path) == CONFIG_SHA256, 'Approved configuration changed'
    config = json.loads(config_path.read_text())
    prepared = root / config['output']
    receipt_path = prepared / 'preparation.json'
    assert sha256(receipt_path) == PREPARATION_SHA256, 'Approved static receipt changed'
    receipt = json.loads(receipt_path.read_text())
    assert receipt['original_small_files_unchanged'] and receipt['verifier_runs'] == 0
    hashes = {}
    for relative, expected in config['small_file_sha256'].items():
        path = root / relative
        assert sha256(path) == expected, 'Frozen source changed: ' + relative
        hashes[str(path)] = expected
    for row in receipt['prepared_files']:
        path = Path(row['path'])
        assert sha256(path) == row['sha256'], 'Approved restoration changed: ' + str(path)
        hashes[str(path)] = row['sha256']
    helper = root / 'scripts/run_terminal_native_gap_queue_20261017.py'
    assert sha256(helper) == LEASE_HELPER_SHA256, 'Shared lease helper changed'
    image = root / config['sif_tag']
    assert image.is_symlink() and image.resolve() == root / config['sif_resolved']
    assert image.stat().st_size == config['sif_size_bytes']
    assert image.stat().st_mtime_ns == config['sif_mtime_ns']
    original = root / config['original_result']
    result = json.loads(original.read_text())
    trial = result['config']
    assert result['task_checksum'] == config['task_checksum']
    assert result['trial_name'] == config['trial_name']
    assert trial['agent']['model_name'] == config['model']
    assert trial['agent']['kwargs']['seed'] == config['seed']
    assert trial['environment']['override_cpus'] == 4
    assert trial['environment']['override_memory_mb'] == 8192
    assert trial['environment']['cpu_enforcement_policy'] == 'limit'
    assert trial['environment']['memory_enforcement_policy'] == 'limit'
    assert trial['verifier']['override_timeout_sec'] == 900
    assert trial['verifier'].get('max_timeout_sec') is None
    assert trial['timeout_multiplier'] == 1
    assert trial['agent']['override_timeout_sec'] == 1800
    assert result['verifier_result'] is None
    future = config['future_grade']
    assert future['cpu_ids'] == [92, 93, 94, 95] and future['memory_mib'] == 8192
    assert future['native_verifier_seconds'] == 900 and future['new_model_calls'] == 0
    manifest = prepared / 'restore.json'
    restoration = json.loads(manifest.read_text())
    assert restoration['original_result'] == str(original)
    assert restoration['model'] == config['model'] and restoration['seed'] == config['seed']
    assert restoration['resolver_policy']['excluded'] == '/etc/resolv.conf'
    assert not restoration['resolver_policy']['use_candidate_file_as_runtime_resolver']
    assert restoration['no_install_or_service_start']
    runtime = root / future['runtime']
    # Keep the production argv path: resolving this symlink loses the venv's package metadata.
    python = root / 'artifacts/envs/harbor/bin/python'
    assert python.is_file()
    # These are the existing frozen verifier/harness assets, not newly installed products.
    assets = [root / 'artifacts/cache/terminal-v2-native' / name for name in
              ('harness-only', 'native', 'verifier-bin', 'uv-wheel', 'python',
               'bootstrap.sh', 'server.py', 'rootmap.sh')]
    assets += [root / 'artifacts/cache/swe-v2-runtime/harbor-server',
               root / 'artifacts/tools/terminal_verifier_offline_20261016/core-uv-cache',
               root / 'artifacts/tools/terminal_verifier_offline_20261016/task_cache_map.json']
    assert all(path.exists() for path in assets), 'Original verifier assets unavailable'
    env = dict(os.environ, PYTHONPATH=str(runtime / 'scripts'), PYTHONDONTWRITEBYTECODE='1',
               XDG_RUNTIME_DIR='/run/user/1012', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1012/bus',
               TMPDIR='/data/caoqinlu/apex-terminal250-tmp', OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    env['PATH'] = (str(root / 'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin') + ':'
                   + str(root / 'artifacts/tools/fakeroot-1.25.3/rootfs/usr/bin')
                   + ':/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin')
    assert Path(env['TMPDIR']).is_dir()
    output = root / future['output']
    command = ['taskset', '-c', '92-95', str(python), str(runtime / 'scripts/run_terminal_repair_grade_v2.py'),
               '--original-result', str(original), '--restore-manifest', str(manifest),
               '--output', str(output), '--cpu-offset', '92']
    return config, prepared, output, command, env, hashes, assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('/data/caoqinlu/projects/apex-takehome'))
    parser.add_argument('--config', type=Path, default=Path('configs/eval/terminal250_nginx_grade_only_20261017.json'))
    parser.add_argument('--execute', action='store_true', help='After review: claim and run the one native attempt')
    recovery = parser.add_mutually_exclusive_group()
    recovery.add_argument('--bootstrap-recovery', action='store_true',
                        help='Explicitly recover the exact pre-native Harbor metadata failure; default remains checks only')
    recovery.add_argument('--bootstrap-cpu-recovery', action='store_true',
                          help='Explicitly recover only parent1209420 pre-restore CPU-index failure into a new output')
    args = parser.parse_args()
    root = args.project.resolve()
    config_path = root / args.config
    config, prepared, output, command, env, hashes, assets = validate(root, config_path)
    bootstrap = None
    original_prepared = prepared
    if args.bootstrap_recovery:
        bootstrap = bootstrap_recovery_gate(prepared, output, hashes)
        hashes.update(bootstrap['preserved_old_evidence_sha256'])
        prepared = prepared / 'bootstrap-recovery-20261017'
        prepared.mkdir(exist_ok=True)
    elif args.bootstrap_cpu_recovery:
        prepared = prepared / 'bootstrap-cpu-recovery-20261017'
        output = prepared / 'native-grade'
        bootstrap = bootstrap_cpu_recovery_gate(original_prepared, output, hashes)
        hashes.update(bootstrap['preserved_old_evidence_sha256'])
        command[command.index('--output') + 1] = str(output)
        command[-1] = '0'  # Relative index inside the unchanged physical taskset92-95.
        prepared.mkdir(exist_ok=True)
    claim = prepared / 'execution-claim.json'
    lease_path = root / config['future_grade']['shared_lock']
    lease_stat = lease_path.stat()
    checks = {'checked_at_utc': now(), 'mode': 'execute' if args.execute else 'pure_checks',
              'script_sha256': sha256(Path(__file__)), 'parent_affinity': sorted(os.sched_getaffinity(0)),
              'bindings_valid': True, 'native_output_exists': output.exists(),
              'execution_claim_exists': claim.exists(), 'command': command,
              'bootstrap_recovery': bootstrap,
              'bootstrap_cpu_recovery': args.bootstrap_cpu_recovery,
              'cpu_ids': [92, 93, 94, 95], 'memory_mib': 8192, 'native_verifier_seconds': 900,
              'parent_effective_cgroup_cpus': sorted(effective_cpus()),
              'shared_lock': {'path': str(lease_path), 'device': lease_stat.st_dev,
                              'inode': lease_stat.st_ino, 'acquired': False},
              'environment': {key: env[key] for key in ('PATH', 'PYTHONPATH', 'XDG_RUNTIME_DIR',
                              'DBUS_SESSION_BUS_ADDRESS', 'TMPDIR', 'OMP_NUM_THREADS',
                              'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
              'existing_verifier_assets': [str(path) for path in assets],
              'new_model_calls': 0, 'verifier_launched': False}
    if not args.execute:
        if args.bootstrap_recovery or args.bootstrap_cpu_recovery or not claim.exists():
            save(prepared / 'parent-preflight.json', checks)
        print(json.dumps(checks), flush=True)
        return
    assert not claim.exists() and not output.exists(), 'One-shot attempt already claimed; never retry automatically'
    assert set(range(92, 96)) <= effective_cpus(), 'Parent cgroup cannot admit child CPU92-95'
    os.sched_setaffinity(0, {10})  # Metadata parent must not count itself as a CPU92-95 native consumer.
    state = {'pid': os.getpid(), 'startticks': startticks(os.getpid()), 'state': 'claimed',
             'command': command, 'shared_lock': str(lease_path), 'lock_held': False,
             'new_model_calls': 0, 'native_output': str(output), 'stop_requested': False,
             'bootstrap_recovery': bool(bootstrap),
             'bootstrap_cpu_recovery': args.bootstrap_cpu_recovery,
             'core_deadline': CORE_DEADLINE,
             'minimum_admission_runway_seconds': MIN_ADMISSION_RUNWAY_SECONDS}
    with claim.open('x') as handle:
        json.dump({**state, 'claimed_at_utc': now(), 'script_sha256': sha256(Path(__file__)),
                   'bound_file_sha256': hashes}, handle, indent=2)
        handle.write('\n')

    def checkpoint(label, **fields):
        changed = label != state['state']
        state.update(state=label, updated_at_utc=now(),
                     remaining_core_runway_seconds=CORE_END - time.time(), **fields)
        save(prepared / 'parent-state.json', state)
        events = prepared / 'parent-events.jsonl'
        if changed or not events.exists():
            with events.open('a') as log:
                log.write(json.dumps(state) + '\n')

    def stop_requested(signum, frame):
        state['stop_requested'] = True  # Preserve an already running native attempt and its budget.

    signal.signal(signal.SIGTERM, stop_requested)
    signal.signal(signal.SIGINT, stop_requested)
    checkpoint('claimed')
    with lease_path.open('a+') as lease:
        while True:
            if CORE_END - time.time() < MIN_ADMISSION_RUNWAY_SECONDS:
                checkpoint('stopped_core_runway')
                return
            if state['stop_requested']:
                checkpoint('stopped_before_native_attempt')
                return
            try:
                fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                checkpoint('waiting_shared_cpu_lease')
                time.sleep(5)
                continue
            busy = busy_scopes()
            if busy:
                fcntl.flock(lease, fcntl.LOCK_UN)
                checkpoint('waiting_cpu_scope_drain', remaining_cpu_scopes=busy)
                time.sleep(5)
                continue
            break
        checkpoint('lease_acquired', lock_held=True, remaining_cpu_scopes=[])
        # Recheck after the potentially long lease wait, before creating any native output.
        try:
            validate(root, config_path)
            if args.bootstrap_recovery:
                bootstrap_recovery_gate(original_prepared, output, hashes)
            elif args.bootstrap_cpu_recovery:
                bootstrap_cpu_recovery_gate(original_prepared, output, hashes)
            assert not output.exists()
            if CORE_END - time.time() < MIN_ADMISSION_RUNWAY_SECONDS:
                fcntl.flock(lease, fcntl.LOCK_UN)
                checkpoint('stopped_core_runway', lock_held=False)
                return
            log = (prepared / 'native-child.log').open('x')
            try:
                child = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                         stdout=log, stderr=subprocess.STDOUT,
                                         pass_fds=(lease.fileno(),), start_new_session=True)
            finally:
                log.close()
        except Exception as exc:
            fcntl.flock(lease, fcntl.LOCK_UN)
            checkpoint('failed_before_native_child', lock_held=False, error_type=type(exc).__name__)
            raise
        else:
            checkpoint('native_grading', child_pid=child.pid, child_startticks=startticks(child.pid))
            while child.poll() is None:
                time.sleep(5)
                checkpoint('native_grading')
        checkpoint('waiting_scope_cleanup', child_returncode=child.returncode)
        drain_samples = []
        while len(drain_samples) < 2:
            busy = busy_scopes()
            sample = {'at_utc': now(), 'remaining_cpu_scopes': busy}
            drain_samples = [] if busy else drain_samples + [sample]
            checkpoint('waiting_scope_cleanup', remaining_cpu_scopes=busy,
                       consecutive_empty_scope_samples=drain_samples)
            if len(drain_samples) < 2:
                time.sleep(2)
        unchanged = all(sha256(Path(path)) == expected for path, expected in hashes.items())
        native_path = output / 'result.json'
        native = json.loads(native_path.read_text()) if native_path.exists() else {}
        checkpoint('native_finished_pending_review', original_and_restore_files_unchanged=unchanged,
                   native_result_exists=native_path.exists(),
                   native_reward=((native.get('verifier_result') or {}).get('rewards') or {}).get('reward'),
                   exception_type=(native.get('exception_info') or {}).get('exception_type'),
                   accepted_into_formal_summary=False)
        fcntl.flock(lease, fcntl.LOCK_UN)
        checkpoint('finished_pending_review', lock_held=False, released_at_utc=now())
    print(json.dumps(state), flush=True)


if __name__ == '__main__':
    main()
