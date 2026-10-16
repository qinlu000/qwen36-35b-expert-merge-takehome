#!/usr/bin/env python3
"""Statically bind one retained answer and prepare its exact /etc delta; no execution."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import stat
import subprocess
import tarfile


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def kind(member):
    if member.isdir():
        return 'directory'
    if member.issym():
        return 'symlink'
    if member.isfile():
        return 'file'
    raise ValueError('Unsupported archive member: ' + member.name)


def static_entries(base):
    # Never follow absolute SIF symlinks into the host filesystem.
    entries = {'etc': base / 'etc'}
    for directory, dirs, files in os.walk(base / 'etc', followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            entries[path.relative_to(base).as_posix()] = path
    return entries


def equal(member, archive, path):
    if path is None:
        return False
    info = path.lstat()
    if stat.S_IMODE(info.st_mode) != member.mode:
        return False
    if member.isdir():
        return stat.S_ISDIR(info.st_mode)
    if member.issym():
        return stat.S_ISLNK(info.st_mode) and os.readlink(path) == member.linkname
    return (stat.S_ISREG(info.st_mode)
            and archive.extractfile(member).read() == path.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('/data/caoqinlu/projects/apex-takehome'))
    parser.add_argument('--config', type=Path, default=Path('configs/eval/terminal250_nginx_grade_only_20261017.json'))
    args = parser.parse_args()
    root = args.project.resolve()
    config_path = root / args.config
    config = json.loads(config_path.read_text())
    assert sorted(os.sched_getaffinity(0)) == [10], 'Static preparation uses metadata CPU10 only'
    original = root / config['original_result']
    archive_path = root / config['archive']
    snapshot_path = root / config['snapshot']
    bound = []
    for relative, expected in config['small_file_sha256'].items():
        path = root / relative
        actual = sha256(path)
        assert actual == expected, 'Original source identity changed: ' + relative
        bound.append({'path': str(path), 'sha256': actual, 'size_bytes': path.stat().st_size})
    result = json.loads(original.read_text())
    snapshot = json.loads(snapshot_path.read_text())
    trial = result['config']
    assert result['trial_name'] == config['trial_name']
    assert Path(result['task_id']['path']).name == config['task_id']
    assert result['task_checksum'] == config['task_checksum']
    assert trial['agent']['model_name'] == config['model']
    assert trial['agent']['kwargs']['seed'] == config['seed']
    assert trial['environment']['override_cpus'] == 4
    assert trial['environment']['override_memory_mb'] == 8192
    assert trial['agent']['override_timeout_sec'] == 1800
    assert trial['verifier']['override_timeout_sec'] == 900
    assert trial['timeout_multiplier'] == 1
    assert result['verifier_result'] is None
    assert result['exception_info']['exception_type'] == 'RuntimeError'
    assert 'unconfirmed solver cleanup' in result['exception_info']['exception_message']
    assert snapshot['captured_before_verifier'] and snapshot['return_code'] == 0
    assert snapshot['stderr'] == ''
    assert snapshot['complete_prefixes'] == ['app', 'etc']
    image = root / config['sif_tag']
    assert image.is_symlink() and image.resolve() == root / config['sif_resolved']
    image_stat = image.stat()
    assert image_stat.st_size == config['sif_size_bytes']
    assert image_stat.st_mtime_ns == config['sif_mtime_ns']
    output = root / config['output']
    output.mkdir(parents=True, exist_ok=False)
    base = output / 'same-sif-static'
    with image.open('rb') as stream:
        offset = stream.read(1048576).find(b'hsqs')
    assert offset >= 0
    command = ['unsquashfs', '-no-progress', '-no-xattrs', '-processors', '1',
               '-o', str(offset), '-dest', str(base), str(image), 'etc']
    with (output / 'unsquashfs.log').open('w') as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
    baseline = static_entries(base)
    delta_path = output / 'etc-delta.tar'
    with tarfile.open(archive_path) as archive, tarfile.open(delta_path, 'w') as delta:
        members = archive.getmembers()
        names = [m.name.rstrip('/') for m in members]
        assert len(names) == len(set(names))
        for member in members:
            path = PurePosixPath(member.name)
            assert not path.is_absolute() and '..' not in path.parts
            kind(member)
        etc = [m for m in members if m.name == 'etc' or m.name.startswith('etc/')]
        changed = [m for m in etc if not equal(m, archive, baseline.get(m.name.rstrip('/')))]
        managed = [m for m in changed if m.name == 'etc/resolv.conf']
        changed = [m for m in changed if m.name != 'etc/resolv.conf']
        absent = sorted(set(baseline) - set(names) - {'etc/resolv.conf'},
                        key=lambda name: (-name.count('/'), name))
        for member in changed:
            delta.addfile(member, archive.extractfile(member) if member.isfile() else None)
        details = [{'path': m.name, 'kind': kind(m), 'mode': oct(m.mode),
                    'size_bytes': m.size, 'added': m.name not in baseline,
                    'symlink_target': m.linkname if m.issym() else None} for m in changed]
        non_etc = [m.name for m in members if m.name != 'etc' and not m.name.startswith('etc/')]
        assert non_etc == ['app', 'tmp/resolv.conf', 'var/log/apt/eipp.log.xz']
        replacements = [m.name for m in changed if m.name in baseline and not m.isdir()]
        directories = [m for m in changed if m.isdir()]
    commands = []
    if absent:
        commands.append({'command': 'rm -rf -- ' + shlex.join('/' + name for name in absent),
                         'timeout_sec': 30, 'source_evidence': 'Complete archived /etc versus same original SIF'})
    if replacements:
        commands.append({'command': 'rm -rf -- ' + shlex.join('/' + name for name in replacements),
                         'timeout_sec': 30, 'source_evidence': str(archive_path)})
    commands.append({'command': 'tar --overwrite -xf /staging/saved-final-state.tar -C / -- '
                     + shlex.join(non_etc), 'timeout_sec': 180, 'source_evidence': str(archive_path)})
    for member in directories:
        commands.append({'command': 'mkdir -p -- ' + shlex.quote('/' + member.name),
                         'timeout_sec': 30, 'source_evidence': str(archive_path)})
    if changed:
        commands.append({'command': 'tar --overwrite -xf /staging/saved-etc-delta.tar -C /',
                         'timeout_sec': 60, 'source_evidence': str(archive_path)})
    # Commands are a proposal for an isolated same-SIF environment, never executed here.
    manifest = {'original_result': str(original), 'model': config['model'], 'seed': config['seed'],
                'task_checksum': config['task_checksum'], 'sif': str(image.resolve()),
                'files': [{'source': str(archive_path), 'target': '/staging/saved-final-state.tar'},
                          {'source': str(delta_path), 'target': '/staging/saved-etc-delta.tar'}],
                'commands': commands, 'new_model_calls': 0,
                'resolver_policy': {'excluded': '/etc/resolv.conf',
                    'reason': 'Frozen NetworkNamespace owns the read-only resolver bind; retain its phase policy.',
                    'preserved_candidate_file': '/tmp/resolv.conf',
                    'use_candidate_file_as_runtime_resolver': False},
                'no_install_or_service_start': True, 'status': 'prepared_not_executed'}
    save(output / 'restore.json', manifest)
    lock_path = root / config['future_grade']['shared_lock']
    lock_stat = lock_path.stat()
    held = [line for line in Path('/proc/locks').read_text().splitlines()
            if line.split()[5].split(':')[-1] == str(lock_stat.st_ino)]
    receipt = {'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
               'state': 'static_preparation_only', 'config': str(config_path),
               'config_sha256': sha256(config_path), 'sources': bound,
               'same_sif': {'tag': str(image), 'resolved': str(image.resolve()),
                            'size_bytes': image_stat.st_size, 'mtime_ns': image_stat.st_mtime_ns,
                            'squashfs_offset': offset, 'whole_sif_hash_recomputed': False},
               'static_comparison': {'archive_members': len(members), 'archived_etc_entries': len(etc),
                    'same_sif_etc_entries': len(baseline), 'unchanged_etc_entries': len(etc) - len(changed) - len(managed),
                    'changed_entries': details, 'absent_entries': absent,
                    'runtime_managed_excluded': [m.name for m in managed], 'non_etc_restored_paths': non_etc,
                    'comparison': 'type, mode, exact symlink target or file bytes; no symlink following'},
               'prepared_files': [{'path': str(p), 'sha256': sha256(p), 'size_bytes': p.stat().st_size}
                                  for p in (output / 'restore.json', delta_path)],
               'shared_lock_observation': {'path': str(lock_path), 'inode': lock_stat.st_ino,
                    'device': lock_stat.st_dev, 'kernel_locks': held, 'acquired': False,
                    'observation_is_not_a_release_or_claim': True},
               'cpu_affinity': sorted(os.sched_getaffinity(0)), 'new_model_calls': 0,
               'verifier_runs': 0, 'containers_started': 0, 'network_changes': 0,
               'original_small_files_unchanged': all(sha256(Path(row['path'])) == row['sha256'] for row in bound),
               'limitations': ['The archive is not a complete filesystem or process checkpoint.',
                              'No nginx installation or running service is present in the archived candidate evidence.',
                              'Grade-only execution needs separate approval and the shared CPU lease.']}
    save(output / 'preparation.json', receipt)
    print(json.dumps({'receipt': str(output / 'preparation.json'),
                      'changed_etc': len(changed), 'deleted_etc': len(absent),
                      'excluded_managed_resolver': len(managed), 'verifier_runs': 0}))


if __name__ == '__main__':
    main()
