#!/usr/bin/env python3
"""Prepare one exact hardlink-header validation repair; retain every candidate byte and mode."""
import argparse
import json
from pathlib import Path
import shlex

import run_terminal_git_leak_grade_only_20261017 as parent


def payload(original, archive_sha256):
    argv = shlex.split(original['commands'][2]['command'])
    assert argv[:4] == ['/opt/harbor-server/bin/python3', '-I', '-S', '-c'] and len(argv) == 5
    code = argv[-1]
    binding = '''ALIAS='etc/apt/apt.conf.d/01-vendor-ubuntu'
TARGET='app/repo/.git/info/refs'
assert hashlib.sha256(Path('/staging/git-leak-final-state.tar').read_bytes()).hexdigest()==ARCHIVE_SHA, 'original archive changed'
assert [(m.name,m.linkname) for m in archive.getmembers() if m.islnk()]==[(ALIAS,TARGET)], 'unexpected hardlink mapping'
alias=archive.getmember(ALIAS);regular=archive.getmember(TARGET)
assert alias.islnk() and alias.mode==0o644 and alias.linkname==TARGET, 'unexpected alias header'
assert regular.isfile() and regular.mode==0o600, 'unexpected canonical regular header'
canonical_mode=regular.mode
'''.replace('ARCHIVE_SHA', repr(archive_sha256), 1)
    assert code.count('checked=0\n') == 1
    code = code.replace('checked=0\n', 'checked=0\n' + binding, 1)
    old = " assert stat.S_IMODE(s.st_mode)==m.mode, 'restore mode mismatch'"
    assert code.count(old) == 1
    code = code.replace(old, " expected_mode=canonical_mode if m.name==ALIAS else m.mode\n"
                        " assert stat.S_IMODE(s.st_mode)==expected_mode, 'restore mode mismatch'", 1)
    assert code.count('print(json.dumps(') == 1
    code = code.replace('print(json.dumps(', 'assert checked==73, \'restore member count mismatch\'\nprint(json.dumps(', 1)
    code = code.replace("'cross_path_hardlink_verified':True", "'cross_path_hardlink_verified':True,"
        "'exact_hardlink_header_mode_normalized':True,'raw_alias_mode':'0o644','canonical_regular_mode':'0o600'", 1)
    return '/opt/harbor-server/bin/python3 -I -S -c ' + shlex.quote(code)


def prepare(config):
    original = parent.read(parent.ROOT / config['original_restore'])
    restore = json.loads(json.dumps(original))
    restore['commands'][2] = {'command': payload(original, config['source_sha256'][config['archive']]), 'timeout_sec': 60}
    assert restore['commands'][:2] == original['commands'][:2] and len(restore['commands']) == 3
    restore.update(status='exact_hardlink_header_validation_repair_prepared_not_executed',
        mode_audit={'key': parent.KEY, 'archive_sha256': config['source_sha256'][config['archive']],
        'alias': '/etc/apt/apt.conf.d/01-vendor-ubuntu', 'raw_alias_mode': '0o644',
        'regular_target': '/app/repo/.git/info/refs', 'canonical_mode': '0o600',
        'candidate_chmod_or_hardlink_split': False, 'all_other_mode_checks_unchanged': True})
    directory = parent.ROOT / config['output'] / 'prepared'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'restore.json'
    parent.write_once(path, (json.dumps(restore, indent=2) + '\n').encode())
    return path, parent.ROOT / config['original_delta']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=parent.ROOT / 'configs/eval/terminal_git_leak_header_mode_recovery_20261017.json')
    parser.add_argument('--execute', action='store_true', help='Only after root/independent review: first native verification of this frozen answer')
    args = parser.parse_args()
    args.manifest = args.manifest.absolute()
    config = parent.read(args.manifest)
    assert config['output'] == 'artifacts/recovery/terminal250-git-leak-seed1-header-mode-recovery-20261017'
    checks = parent.validate(config)
    diagnostic = parent.read(parent.ROOT / config['diagnosis_receipt'])
    assert diagnostic['diagnostic_payload']['members'] == 73 and diagnostic['diagnostic_payload']['differences'] == 1
    assert diagnostic['diagnostic_payload']['app_inventory_same'] and not diagnostic['native_result']['official_tests_started']
    restore, delta = prepare(config)
    if args.execute:
        parent.run(args, config, restore, delta)
        return
    print(json.dumps({'at_utc': parent.now(), 'mode': 'exact_header_mode_recovery_prepare_only', **checks,
        'script_sha256': parent.sha(Path(__file__)), 'manifest_sha256': parent.sha(args.manifest),
        'frozen_parent_sha256': parent.sha(Path(parent.__file__)),
        'restore': {'path': str(restore), 'sha256': parent.sha(restore)},
        'commands0_1_identical_to_frozen_restore': True, 'all73_members_strictly_checked': True,
        'exact_alias_uses_regular_target_mode0600': True, 'candidate_chmod_or_hardlink_split': False,
        'priority_swe_drained': parent.swe_drained(config), 'priority_asi_ready_for_grader': parent.asi_ready(config),
        'execution_claim_created': False, 'guard_created': False, 'shared_lock_acquired': False,
        'native_started': False, 'model_calls': 0, 'new_api_calls': 0}, indent=2))


if __name__ == '__main__':
    main()
