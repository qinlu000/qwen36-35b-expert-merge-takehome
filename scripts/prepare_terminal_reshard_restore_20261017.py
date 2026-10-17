#!/usr/bin/env python3
"""Prepare one saved reshard answer; never execute a sandbox, candidate or verifier."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import tarfile
from datetime import datetime, timezone

KEY = 'reshard-c4-data/seed1'
EXTERNAL = [
    'root/.cache/uv/interpreter-v4/85046238252ff06c/4a442d62a8d6ade5.msgpack',
    'root/.cache/uv/interpreter-v4/85046238252ff06c/5242bf85c8a339f7.msgpack',
    'root/.cache/uv/interpreter-v4/85046238252ff06c/a6ff54ed077d5bdd.msgpack',
    'tmp/uv-1c83b73deef05048.lock',
]
ETC = ['etc/apt/apt.conf.d/99-apex-rootmap', 'etc/dpkg', 'etc/dpkg/dpkg.cfg',
       'etc/dpkg/dpkg.cfg.d', 'etc/dpkg/dpkg.cfg.d/docker',
       'etc/dpkg/dpkg.cfg.d/docker-apt-speedup', 'etc/dpkg/dpkg.cfg.d/singularity-compat',
       'etc/dpkg/origins', 'etc/dpkg/origins/debian', 'etc/dpkg/origins/default']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
now = lambda: datetime.now(timezone.utc).isoformat()


def write_once(path, data):
    if path.exists():
        assert path.read_bytes() == data, f'Existing preparation differs: {path}'
    else:
        with path.open('xb') as stream:
            stream.write(data)


def process(pid):
    p = Path('/proc', str(pid))
    try:
        fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
        return {'pid': pid, 'startticks': fields[19], 'state': fields[0],
                'scope': (p / 'cgroup').read_text().strip().split('/')[-1]}
    except FileNotFoundError:
        return None


def pid_evidence(root, config, snapshot, directory):
    path = directory / 'pid-source.json'
    if path.exists():
        return path
    trial = str((root / config['original_result']).parent)
    env = dict(os.environ, XDG_RUNTIME_DIR='/run/user/1012', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1012/bus')
    journal = subprocess.run(['journalctl', '--user', '--since', '2026-10-17 09:25:00',
        '--until', '2026-10-17 09:58:00', '--no-pager', '-o', 'json'],
        env=env, text=True, capture_output=True, check=True)
    rows = [json.loads(line) for line in journal.stdout.splitlines() if line.strip()]
    matches = [r for r in rows if trial + '/agent:/logs/agent' in r.get('MESSAGE', '')]
    assert len(matches) == 1
    row = matches[0]; message = row['MESSAGE']; scope = row['USER_UNIT']
    assert scope == 'apex-baseline-af8481795ec4.scope'
    assert '--cpus 4 --memory-bytes 8589934592 --cpu-offset 20 --' in message
    net = '/data/caoqinlu/apex-terminal250-tmp/apex_baseline_net_mewefyzm'
    staging = '/data/caoqinlu/apex-terminal250-tmp/apex_baseline_staging_ef6pmnj2'
    assert net in message and staging in message and '-- nsenter -t 1778318 ' in message
    related = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit() or int(p.name) == os.getpid():
            continue
        try:
            text = (p / 'cmdline').read_bytes().decode(errors='replace')
            info = process(int(p.name))
            if info and info['state'] != 'Z' and (info['scope'] == scope or any(x in text for x in (trial, net, staging))):
                related.append(info)
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    cleanup = json.loads(snapshot['reason'].split(': ', 1)[1])
    captured = [{'pid': p['pid'], 'startticks': None,
        'pid_namespace': 'original container; not a host PID',
        'captured_namespace_startticks': p['start'], 'host_identity': 'unknown'}
        for p in cleanup['remaining_processes']]
    clear = not related and not Path(net).exists()
    assert clear, 'Original trial namespace/scope not proven drained'
    value = {'at_utc': now(), 'original_result': config['original_result'], 'old_scope': scope,
        'old_namespace_solver_clear': clear, 'captured_solver_processes': captured,
        'live_related_host_processes': related, 'old_namespace_directory_exists': Path(net).exists(),
        'old_staging_directory_exists': Path(staging).exists(),
        'retained_staging_files': sorted(p.name for p in Path(staging).iterdir()) if Path(staging).exists() else [],
        'staging_log_retention_is_not_a_live_namespace': True,
        'original_namespace_keeper_host_pid': 1778318, 'keeper_current': process(1778318),
        'journal': {'matched_records': 1, 'realtime_timestamp_us': row['__REALTIME_TIMESTAMP'],
            'message_sha256': hashlib.sha256(message.encode()).hexdigest(),
            'original_resource_argv_matches': True, 'exact_original_trial_mount_matches': True,
            'full_argv_or_instance_token_saved': False},
        'unknown_namespace_pid_host_identity_not_asserted': True}
    write_once(path, (json.dumps(value, indent=2) + '\n').encode())
    return path


def commands():
    staging = '/staging/reshard-final-state.tar'
    parents = sorted({str(PurePosixPath('/' + x).parent) for x in EXTERNAL})
    restore_app = ('set -e\nsha256sum /etc/resolv.conf > /staging/reshard-resolver.sha256\n'
        'rm -rf -- /app\n' + 'mkdir -p -- ' + ' '.join(map(shlex.quote, parents)) + '\n'
        'tar -xpf ' + staging + ' -C / app ' + ' '.join(map(shlex.quote, EXTERNAL)))
    restore_etc = ('set -e\nrm -f -- /etc/dpkg/origins/default\n'
        'tar -xpf /staging/reshard-etc-delta.tar -C /\n'
        'sha256sum -c /staging/reshard-resolver.sha256')
    checker = '''import hashlib,json,os,stat,tarfile
from pathlib import Path
ETC=ETC_VALUE
EXTERNAL=EXTERNAL_VALUE
archive=tarfile.open('/staging/reshard-final-state.tar')
members=archive.getmembers()
assert len(members)==20311 and len({m.name for m in members})==20311
selected=[m for m in members if m.name=='app' or m.name.startswith('app/') or m.name in ETC+EXTERNAL]
assert len(selected)==19845
checked=0
for m in selected:
 p=Path('/'+m.name);s=p.lstat()
 assert stat.S_IMODE(s.st_mode)==m.mode, 'mode mismatch: '+m.name
 assert (m.isdir() and stat.S_ISDIR(s.st_mode)) or (m.isfile() and stat.S_ISREG(s.st_mode)) or (m.issym() and stat.S_ISLNK(s.st_mode)), 'type mismatch: '+m.name
 if m.issym():
  assert os.readlink(p)==m.linkname, 'symlink mismatch: '+m.name
 elif m.isfile():
  assert s.st_size==m.size, 'size mismatch: '+m.name
  with archive.extractfile(m) as expected,p.open('rb') as actual:
   while True:
    a=expected.read(1048576);b=actual.read(1048576)
    assert a==b, 'content mismatch: '+m.name
    if not a:break
 checked+=1
expected={m.name for m in members if m.name=='app' or m.name.startswith('app/')}
actual={'app'}
for base,dirs,files in os.walk('/app',followlinks=False):
 for name in dirs+files:actual.add(str(Path(base,name)).lstrip('/'))
assert actual==expected, 'app inventory mismatch'
assert Path('/usr/local/bin/python3.13').is_file(), 'original symlink target missing'
line=Path('/staging/reshard-resolver.sha256').read_text().split()[0]
assert hashlib.sha256(Path('/etc/resolv.conf').read_bytes()).hexdigest()==line, 'managed resolver changed'
print(json.dumps({'strict_restored_members':checked,'app_members':len(expected),'external_members':len(EXTERNAL),'etc_delta_members':len(ETC),'app_inventory_same':True,'content_mode_type_symlinks_same':True,'managed_resolver_unchanged':True,'candidate_code_executed':False}))
'''.replace('ETC_VALUE', repr(ETC), 1).replace('EXTERNAL_VALUE', repr(EXTERNAL), 1)
    compile(checker, '<reshard-restore-check>', 'exec')
    return [{'command': restore_app, 'timeout_sec': 600}, {'command': restore_etc, 'timeout_sec': 60},
        {'command': '/opt/harbor-server/bin/python3 -I -S -c ' + shlex.quote(checker), 'timeout_sec': 600}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest', default='configs/eval/terminal_reshard_saved_grade_20261017.json')
    args = parser.parse_args(); root = args.project.absolute(); manifest = root / args.manifest
    config = read(manifest); assert (config['key'], config['model']) == (KEY, 'apex-terminal250')
    for p, h in config['source_sha256'].items():
        assert sha(root / p) == h, p
    for p, expected in config['source_stat'].items():
        st = (root / p).stat()
        assert (st.st_size, str(st.st_mtime_ns)) == (expected['size'], expected['mtime_ns']), p
    original = read(root / config['original_result']); snapshot = read(root / config['snapshot'])
    assert original['config']['agent']['model_name'] in ('apex-terminal250', 'openai/apex-terminal250')
    assert snapshot['return_code'] == 0 and not snapshot['stderr'] and snapshot['captured_before_verifier']
    assert snapshot['complete_prefixes'] == ['app', 'etc'] and snapshot['changed_external_files'] == EXTERNAL
    directory = root / config['output'] / 'prepared'; directory.mkdir(parents=True, exist_ok=True)
    delta = directory / 'etc-delta.tar'
    with tarfile.open(root / config['archive']) as archive:
        members = archive.getmembers(); names = [m.name for m in members]
        assert len(members) == 20311 and len(set(names)) == 20311
        assert sum(n == 'app' or n.startswith('app/') for n in names) == 19831
        for m in members:
            p = PurePosixPath(m.name)
            assert not p.is_absolute() and '..' not in p.parts
            assert m.isdir() or m.isfile() or m.issym()
            assert m.name == 'app' or m.name.startswith(('app/', 'etc/')) or m.name == 'etc' or m.name in EXTERNAL
            if m.issym() and m.name.startswith('app/'):
                assert not PurePosixPath(m.linkname).is_absolute() or (m.name, m.linkname) == ('app/.venv/bin/python', '/usr/local/bin/python3.13')
        if not delta.exists():
            with tarfile.open(delta, 'w') as out:
                for name in ETC:
                    m = archive.getmember(name)
                    out.addfile(m, archive.extractfile(m) if m.isfile() else None)
        assert tarfile.open(delta).getnames() == ETC
        externals = [{'path': name, 'mode': oct(archive.getmember(name).mode),
            'bytes': archive.getmember(name).size,
            'sha256': hashlib.sha256(archive.extractfile(name).read()).hexdigest(),
            'role': 'uv interpreter-discovery metadata; original paths /usr/local or /app/.venv' if name.endswith('.msgpack') else 'empty uv advisory-lock file; no process/held lock restored'} for name in EXTERNAL]
    restore = {'key': KEY, 'model': config['model'], 'status': 'prepared_not_executed',
        'original_result': str(root / config['original_result']), 'new_model_calls': 0,
        'files': [{'source': str(root / config['archive']), 'target': '/staging/reshard-final-state.tar'},
                  {'source': str(delta), 'target': '/staging/reshard-etc-delta.tar'}],
        'commands': commands(), 'external_original_members': externals,
        'etc_delta': ETC, 'managed_resolver_excluded': '/etc/resolv.conf',
        'original_public_verifier_phase_unchanged': True, 'new_solver_dependency_or_dataset_substitution': False}
    restore_path = directory / 'restore.json'
    write_once(restore_path, (json.dumps(restore, indent=2) + '\n').encode())
    pid = pid_evidence(root, config, snapshot, directory)
    runtime = root / config['runtime'] / 'scripts'
    sources = [Path(__file__).absolute(), delta, restore_path, pid,
        root / config['fixed_cache_map']] + sorted(p for p in runtime.iterdir() if p.suffix in ('.py', '.sh') and p.is_file())
    assert all(p.stat().st_size < 1000000 for p in sources)
    cache = read(root / config['fixed_cache_map']); item = cache.get('tasks', cache)['reshard-c4-data']
    assert item['ready'] is True and 'group-20' in item['uv_cache_dir']
    config['source_sha256'].update({str(p.relative_to(root)): sha(p) for p in sources})
    config['restore_manifest'] = str(restore_path.relative_to(root)); config['pid_source'] = str(pid.relative_to(root))
    manifest.write_text(json.dumps(config, indent=2) + '\n')
    receipt = {'at_utc': now(), 'mode': 'prepare_only', 'key': KEY,
        'manifest': str(manifest), 'manifest_sha256': sha(manifest),
        'source_bindings': len(config['source_sha256']), 'large_source_stat_bindings': config['source_stat'],
        'archive_or_sif_full_hash_recomputed': False, 'archive_member_count': 20311,
        'app_members': 19831, 'strict_restore_member_count': 19845, 'external_members': externals,
        'etc_delta_members': len(ETC), 'restore_path': str(restore_path), 'restore_sha256': sha(restore_path),
        'delta_sha256': sha(delta), 'pid_source_sha256': sha(pid), 'claim_created': False,
        'lock_acquired': False, 'guard_created': False, 'native_started': False, 'model_calls': 0,
        'original_public_phase_and_cache_supply_retained': True}
    receipt['original_uv_cache_map_entry'] = item
    path = directory / 'preparation.json'
    if not path.exists():
        write_once(path, (json.dumps(receipt, indent=2) + '\n').encode())
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
