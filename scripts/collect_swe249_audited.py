"""One read-only source snapshot with four explicitly approved native-zero audits."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def active_scopes(cpus):
    found = set()
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            group = (process / 'cgroup').read_text()
            if (('apex-baseline-' in group or 'ai4sci-submission-' in group)
                    and set(cpus).intersection(os.sched_getaffinity(int(process.name)))):
                found.add(group.strip().split('/')[-1])
        except (OSError, ProcessLookupError):
            pass
    return sorted(found)


def valid_handoff(marker, handoff, cpus):
    if (handoff.get('swe_expert_all_cpu_and_model_consumers_finished') is not True
            or handoff.get('base_scopes_on_target_cpus') != []
            or sorted(handoff.get('cpu_ids', [])) != sorted(cpus)):
        return False
    try:
        marker_at = datetime.fromisoformat(marker['at'].replace('Z', '+00:00'))
        handoff_at = datetime.fromisoformat(handoff['at'].replace('Z', '+00:00'))
        return (marker_at.utcoffset() is not None and handoff_at.utcoffset() is not None
                and handoff_at >= marker_at)
    except (KeyError, ValueError):
        return False


def approved_row(root, source, audit):
    name = audit['task_id']
    original = root / audit['original_result']
    accepted = root / audit['accepted_result']
    patch = root / audit['source_patch']
    assert original == source / 'replay' / name / 'result.json', 'Original result source mismatch'
    assert patch == source / 'generation' / name / 'agent/model.patch', 'Patch source mismatch'
    assert accepted.parent.name == name and accepted.name == 'result.json', 'Accepted result task mismatch'
    assert sha256(original) == audit['original_result_sha256'], 'Original result bytes changed'
    assert sha256(accepted) == audit['accepted_result_sha256'], 'Accepted result bytes changed'
    assert patch.stat().st_size == audit['patch_bytes']
    assert sha256(patch) == audit['patch_sha256'], 'Frozen patch changed'
    for result_path in (original, accepted):
        config = read(result_path.parent / 'config.json')
        assert Path(config['task']['path']) == source / 'tasks' / name, 'Frozen task source mismatch'
        assert config['agent']['import_path'] == 'patch_replay:PatchReplayAgent'
        assert Path(config['agent']['kwargs']['source_job']) == source / 'generation', 'Generation source mismatch'
        replay = read(result_path.parent / 'agent/replay.json')
        assert replay['task'] == name
        if audit['patch_bytes'] == 0:
            assert replay['patch'] is None, 'Empty patch replay identity mismatch'
        else:
            assert Path(replay['patch']) == patch and replay['apply_rc'] == 0
    result = read(accepted)
    reward = ((result.get('verifier_result') or {}).get('rewards') or {}).get('reward')
    assert type(reward) in (int, float) and reward == 0, 'Accepted native reward must be zero'
    assert not result.get('exception_info'), 'Accepted replay has a Harbor exception'
    assert float((accepted.parent / 'verifier/reward.txt').read_text()) == 0
    return {'task_id': name, 'status': 'valid_scored', 'reward': reward,
        'native_reward': reward, 'invalid_reason': None, 'accepted_result': str(accepted),
        'result': str(accepted), 'finished_at': result.get('finished_at'),
        'previous_invalid_result': str(original), 'audit_reason': audit['reason'],
        'source_patch_sha256': audit['patch_sha256']}


def collect(root, manifest_path, scope_reader=active_scopes):
    manifest = read(manifest_path)
    source = root / manifest['source_output']
    source_path = root / manifest['source_summary']
    data = source_path.read_bytes()
    raw = json.loads(data)
    ids = read(root / manifest['task_manifest'])['task_ids']
    assert len(ids) == len(set(ids)) == 51 and raw['expected'] == 51
    assert raw['model'] == manifest['model']
    assert raw['checkpoint'] == manifest['checkpoint']
    by_id = {row['task_id']: row for row in raw['tasks']}
    assert len(raw['tasks']) == len(by_id) == 51 and set(by_id) == set(ids)
    audits = {row['task_id']: row for row in manifest['approved_native_zero']}
    assert len(manifest['approved_native_zero']) == len(audits) == 4
    assert set(audits) <= set(ids)
    rows = []
    for name in ids:
        previous = by_id[name]
        row = dict(previous)
        if name in audits:
            original = root / audits[name]['original_result']
            assert Path(previous['result']) == original, 'Source summary points to another result'
            assert previous.get('invalid_reason') == audits[name]['original_invalid_reason']
            row.update(approved_row(root, source, audits[name]))
            row.update(previous_invalid=dict(previous),
                audit_source=str(manifest_path), audit_result_bytes_pinned=True)
        elif row.get('invalid_reason') is None and row.get('status') in (None, 'valid_scored'):
            assert type(row.get('reward')) in (int, float) and row['reward'] in (0, 1)
            row['status'] = 'valid_scored'
        else:
            row['native_reward'] = row.get('reward')
            row['reward'] = None
            row['status'] = ('awaiting_generation_or_replay' if row.get('invalid_reason') == 'not_scored'
                             and name not in raw['terminal'] else 'invalid_requires_audit')
        rows.append(row)
    valid = [row for row in rows if row['status'] == 'valid_scored']
    resolved = sum(row['reward'] == 1 for row in valid)
    marker_path = root / manifest['resource_marker']
    marker = read(marker_path) if marker_path.exists() else {}
    scopes = scope_reader(manifest['source_cpu_ids'])
    assert manifest['source_cpu_handoff'] == 'artifacts/eval/avg64_swe_hard51_20261017/admission-opened.json'
    handoff_path = root / manifest['source_cpu_handoff']
    handoff = read(handoff_path) if handoff_path.exists() else {}
    handed_off = valid_handoff(marker, handoff, manifest['source_cpu_ids'])
    gates = {'all51_effectively_scored': len(valid) == 51,
        'all51_original_attempts_terminal': set(raw['terminal']) == set(ids),
        'original_active_empty': raw['active'] == {}, 'original_pending_empty': raw['pending'] == [],
        'original_model_consumer_finished': marker.get('model_consumer_finished') is True,
        'original_scoring_explicitly_finished': marker.get('scoring_may_still_be_running') is False,
        'source_cpu_drain_proven': scopes == [] or handed_off}
    complete = all(gates.values())
    return {'as_of': datetime.now(timezone.utc).isoformat(),
        'state': 'complete' if complete else 'audited_snapshot_incomplete',
        'model': raw['model'], 'checkpoint': raw.get('checkpoint'), 'expected': 51,
        'valid_scored': len(valid), 'unscored': 51 - len(valid), 'resolved': resolved,
        'complete': complete, 'primary_score_percent': 100 * resolved / 51 if complete else None,
        'conservative_resolved_percent': 100 * resolved / 51,
        'invalid_pending': sum(row['status'] == 'invalid_requires_audit' for row in rows),
        'awaiting_generation_or_replay': sum(row['status'] == 'awaiting_generation_or_replay' for row in rows),
        'active': raw['active'], 'pending': raw['pending'], 'terminal': raw['terminal'],
        'source_summary': str(source_path), 'source_summary_sha256': hashlib.sha256(data).hexdigest(),
        'source_as_of': raw['as_of'], 'original_valid_scored': raw['valid_scored'],
        'audit_source': str(manifest_path), 'audit_manifest_sha256': sha256(manifest_path),
        'audited_native_zero_count': len(audits), 'completion_gates': gates,
        'resource_marker': str(marker_path), 'resource_marker_observed': marker,
        'source_cpu_handoff': str(handoff_path), 'source_cpu_handoff_observed': handoff,
        'source_cpu_handoff_valid': handed_off,
        'active_source_cpu_scopes': scopes, 'new_model_calls': 0, 'new_replays': 0,
        'selection_policy': 'Four exact approved native-zero results; all other original validity retained; no reward search',
        'tasks': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest', type=Path, default=Path('configs/eval/swe249_audited_hard51_20261017.json'))
    args = parser.parse_args()
    root = args.project.resolve()
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    summary = collect(root, manifest)
    output = root / read(manifest)['output']
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / 'summary.tmp'
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(output / 'summary.json')
    print(json.dumps({key: summary[key] for key in
        ['expected', 'valid_scored', 'original_valid_scored', 'audited_native_zero_count', 'resolved', 'complete', 'primary_score_percent']}))
