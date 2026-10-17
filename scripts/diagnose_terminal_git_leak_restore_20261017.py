#!/usr/bin/env python3
"""Prepare a metadata-only restore probe; deliberate exit86 prevents native verification."""
import argparse
import json
from pathlib import Path
import shlex

import run_terminal_git_leak_grade_only_20261017 as parent


def prepare(config):
    original = parent.read(parent.ROOT / config['original_restore'])
    restore = json.loads(json.dumps(original))
    selected = {row['path'].lstrip('/') for row in config['etc_delta']}
    code = '''import hashlib,json,os,stat,sys,tarfile
from pathlib import Path
rows=[]
try:
 archive=tarfile.open('/staging/git-leak-final-state.tar')
 selected=SELECTED
 for m in archive.getmembers():
  if not(m.name=='app' or m.name.startswith('app/') or m.name in selected):continue
  p=Path('/')/m.name
  expected='dir' if m.isdir() else 'symlink' if m.issym() else 'hardlink' if m.islnk() else 'file'
  row={'path':str(p),'expected_type':expected,'expected_mode':oct(m.mode)}
  try:
   s=p.lstat();actual='dir' if stat.S_ISDIR(s.st_mode) else 'symlink' if stat.S_ISLNK(s.st_mode) else 'file' if stat.S_ISREG(s.st_mode) else 'other'
   row.update(exists=True,actual_type=actual,actual_mode=oct(stat.S_IMODE(s.st_mode)),mode_same=stat.S_IMODE(s.st_mode)==m.mode)
   row['type_same']=actual==('file' if m.islnk() else expected)
   if m.isfile() or m.islnk():
    row['content_hash_same']=actual=='file' and hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(archive.extractfile(m).read()).digest()
   if m.issym():row['link_target_same']=actual=='symlink' and os.readlink(p)==m.linkname
   if m.islnk():row['hardlink_samefile']=os.path.samefile(p,Path('/')/m.linkname)
  except OSError as error:row.update(exists=os.path.lexists(p),error_type=type(error).__name__)
  row['difference']=bool(row.get('error_type')) or any(row.get(k) is False for k in ['type_same','mode_same','content_hash_same','link_target_same','hardlink_samefile'])
  rows.append(row)
 expected_app={m.name.rstrip('/') for m in archive.getmembers() if m.name=='app' or m.name.startswith('app/')}
 actual_app={'app'}
 for root,ds,fs in os.walk('/app',followlinks=False):actual_app.update(str((Path(root)/n).relative_to('/')) for n in ds+fs)
 print(json.dumps({'purpose':'metadata_only_restore_diagnosis','rows':rows,'members':len(rows),'differences':sum(r['difference'] for r in rows),'app_inventory_same':actual_app==expected_app,'app_missing_paths':sorted(expected_app-actual_app),'app_extra_paths':sorted(actual_app-expected_app),'official_verifier_started':False,'deliberate_exit_code':86}),flush=True)
except BaseException as error:
 print(json.dumps({'purpose':'metadata_only_restore_diagnosis','error_type':type(error).__name__,'rows_before_error':rows,'official_verifier_started':False,'deliberate_exit_code':86}),flush=True)
finally:
 sys.exit(86)
'''.replace('SELECTED', repr(sorted(selected)), 1)
    restore['commands'][2] = {'command': '/opt/harbor-server/bin/python3 -I -S -c ' + shlex.quote(code), 'timeout_sec': 60}
    assert restore['commands'][:2] == original['commands'][:2]
    assert len(restore['commands']) == 3 and sum(x['timeout_sec'] for x in restore['commands']) == 240
    restore.update(status='metadata_only_diagnosis_prepared_not_executed',
                   official_verifier_structurally_blocked_by_restore_exit86=True)
    directory = parent.ROOT / config['output'] / 'prepared'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'restore.json'
    parent.write_once(path, (json.dumps(restore, indent=2) + '\n').encode())
    return path, parent.ROOT / config['original_delta']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=parent.ROOT / 'configs/eval/terminal_git_leak_restore_diagnosis_20261017.json')
    parser.add_argument('--execute', action='store_true', help='Only after root review: one metadata-only leased diagnosis')
    args = parser.parse_args()
    args.manifest = args.manifest.absolute()
    config = parent.read(args.manifest)
    assert config['diagnosis_only'] and config['deliberate_restore_exit_code'] == 86
    assert config['output'] == 'artifacts/recovery/terminal250-git-leak-seed1-restore-diagnosis-20261017'
    checks = parent.validate(config)
    restore, delta = prepare(config)
    if args.execute:
        parent.run(args, config, restore, delta)
        return
    print(json.dumps({'at_utc': parent.now(), 'mode': 'metadata_diagnosis_prepare_only', **checks,
        'script_sha256': parent.sha(Path(__file__)), 'manifest_sha256': parent.sha(args.manifest),
        'frozen_parent_sha256': parent.sha(Path(parent.__file__)),
        'restore': {'path': str(restore), 'sha256': parent.sha(restore)},
        'original_delta': {'path': str(delta), 'sha256': parent.sha(delta)},
        'commands0_1_identical_to_frozen_restore': True, 'restore2_deliberate_exit_code': 86,
        'official_verifier_structurally_blocked': True,
        'priority_swe_drained': parent.swe_drained(config), 'priority_asi_ready_for_grader': parent.asi_ready(config),
        'execution_claim_created': False, 'guard_created': False, 'shared_lock_acquired': False,
        'native_started': False, 'model_calls': 0, 'new_api_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
