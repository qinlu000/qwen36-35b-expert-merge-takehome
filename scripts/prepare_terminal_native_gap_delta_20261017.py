#!/usr/bin/env python3
"""Restore changed /etc entries without copying unchanged SIF lower-layer files."""
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import tarfile

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
REPAIR = ROOT / 'artifacts/recovery/terminal-v2/native-gaps-20261017'


def equal(member, archive, path):
    if not os.path.lexists(path):
        return False
    info = path.lstat()
    if stat.S_IMODE(info.st_mode) != member.mode:
        return False
    if member.isdir():
        return path.is_dir() and not path.is_symlink()
    if member.issym():
        return path.is_symlink() and os.readlink(path) == member.linkname
    if member.isfile():
        return path.is_file() and not path.is_symlink() and archive.extractfile(member).read() == path.read_bytes()
    return False


def main():
    plan = json.loads((REPAIR / 'plan.json').read_text())
    records = []
    for row in plan['entries']:
        original = json.loads(Path(row['original_result']).read_text())
        images = list((ROOT / 'artifacts/benchmarks/sif').glob('*_' + row['task_id'] + '_*.sif'))
        assert len(images) == 1
        image = images[0]
        base = REPAIR / 'sif-static-etc' / row['task_id']
        base.parent.mkdir(parents=True, exist_ok=True)
        if not base.exists():
            with image.open('rb') as stream:
                offset = stream.read(1048576).find(b'hsqs')
            subprocess.run(['unsquashfs', '-no-progress', '-no-xattrs', '-processors', '1',
                '-o', str(offset), '-dest', str(base), str(image), 'etc'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        manifest_path = Path(row['restore_manifest'])
        full_manifest = REPAIR / 'manifests-full-etc-attempt0' / manifest_path.parent.name / 'restore.json'
        manifest = json.loads(full_manifest.read_text())
        archive_path = Path(manifest['files'][0]['source'])
        delta_path = manifest_path.parent / 'etc-delta.tar'
        with tarfile.open(archive_path) as archive, tarfile.open(delta_path, 'w') as delta:
            all_members = archive.getmembers()
            etc = [m for m in all_members if m.name == 'etc' or m.name.startswith('etc/')]
            names = {m.name.rstrip('/') for m in etc}
            observed_changed = [m for m in etc if not equal(m, archive, base / m.name)]
            # NetworkNamespace owns this read-only bind mount and switches its
            # nameserver between no-network restoration and public verification.
            managed = [m for m in observed_changed if m.name == 'etc/resolv.conf']
            managed_records = [{'path': m.name,
                'captured_content': archive.extractfile(m).read().decode(errors='replace') if m.isfile() else None,
                'restore': 'Do not overwrite read-only NetworkNamespace resolver bind; normal public phase recreates its resolver.'} for m in managed]
            changed = [m for m in observed_changed if m not in managed]
            for member in changed:
                if member.isdir():
                    continue
                delta.addfile(member, archive.extractfile(member) if member.isfile() else None)
            baseline = [base / 'etc', *(base / 'etc').rglob('*')]
            absent = [str(p.relative_to(base)) for p in baseline if str(p.relative_to(base)) not in names
                      and str(p.relative_to(base)) != 'etc/resolv.conf']
            absent = sorted(absent, key=lambda n: n.count('/'), reverse=True)
            roots = sorted({m.name.split('/')[0] for m in all_members if m.name.split('/')[0] != 'etc'})
        manifest['files'].append({'source': str(delta_path), 'target': '/staging/saved-etc-delta.tar'})
        manifest['commands'][0] = {'command': 'tar -xf /staging/saved-final-state.tar -C / -- ' + shlex.join(roots),
            'timeout_sec': 180, 'source_evidence': str(archive_path)}
        manifest['commands'].insert(1, {'command': 'rm -f -- ' + shlex.join(
            '/' + m.name for m in changed if not m.isdir()),
            'timeout_sec': 30, 'source_evidence': str(archive_path)})
        manifest['commands'].insert(2, {'command': 'tar --overwrite -xf /staging/saved-etc-delta.tar -C /',
            'timeout_sec': 60, 'source_evidence': str(archive_path)})
        directories = [m for m in changed if m.isdir()]
        if directories:
            manifest['commands'].insert(1, {'command': ' && '.join(
                'mkdir -p ' + shlex.quote('/' + m.name) for m in directories),
                'timeout_sec': 30, 'source_evidence': str(archive_path)})
            manifest['commands'].insert(4, {'command': ' && '.join(
                'chmod ' + oct(m.mode)[2:] + ' ' + shlex.quote('/' + m.name) for m in directories),
                'timeout_sec': 30, 'source_evidence': str(archive_path)})
        if absent:
            manifest['commands'].insert(1, {'command': 'rm -rf -- ' + shlex.join('/' + p for p in absent),
                'timeout_sec': 30, 'source_evidence': 'Entries present in original SIF /etc and absent from complete pre-verifier /etc archive.'})
        manifest['etc_restore'] = {'same_sif': str(image), 'method': 'Direct byte comparison, no content hashing; preserve original archived changed entries.',
            'unchanged_lower_layer_entries': len(etc) - len(changed),
            'changed_entries': [m.name for m in changed], 'absent_entries': absent,
            'changed_entry_details': [{'path': m.name,
                'kind': 'symlink' if m.issym() else 'directory' if m.isdir() else 'file',
                'symlink_target': m.linkname if m.issym() else None,
                'mode': oct(m.mode), 'added': not os.path.lexists(base / m.name)} for m in changed],
            'runtime_managed_entries': managed_records,
            'reason': 'Full /etc extraction stalls in fuse-overlayfs copy-up of unchanged dpkg/origins/debian; preserve original state through the smallest exact delta.'}
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        records.append({'key': row['key'], **manifest['etc_restore']})
    (REPAIR / 'etc-delta-receipt.json').write_text(json.dumps({'records': records,
        'tests_run': False, 'model_calls': 0, 'original_archives_unchanged': True}, indent=2) + '\n')
    print(json.dumps({'delta_manifests_ready': len(records)}))


if __name__ == '__main__':
    main()
