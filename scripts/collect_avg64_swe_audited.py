"""Read-only AVG64 SWE snapshot with one explicitly approved native-zero audit."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from collect_swe249_audited import approved_row, aware_time, read, sha256


def collect(root, manifest_path):
    manifest = read(manifest_path)
    source = root / manifest['source_output']
    source_path = root / manifest['source_summary']
    data = source_path.read_bytes()
    raw = json.loads(data)
    ids = read(root / manifest['task_manifest'])['task_ids']
    assert len(ids) == len(set(ids)) == raw['expected'] == 51
    assert raw['model'] == manifest['model'] and raw['checkpoint'] == manifest['checkpoint']
    by_id = {row['task_id']: row for row in raw['tasks']}
    assert len(raw['tasks']) == len(by_id) == 51 and set(by_id) == set(ids)
    active, pending, terminal = set(raw['active']), set(raw['pending']), set(raw['terminal'])
    assert len(pending) == len(raw['pending'])
    assert not (active & pending or active & terminal or pending & terminal)
    assert active | pending | terminal == set(ids)
    audits = {row['task_id']: row for row in manifest['approved_native_zero']}
    assert len(manifest['approved_native_zero']) == len(audits) == 1
    assert set(audits) <= terminal
    rows = []
    for name in ids:
        previous = by_id[name]
        row = dict(previous)
        if name in audits:
            audit = audits[name]
            assert Path(previous['result']) == root / audit['original_result']
            assert previous['invalid_reason'] == audit['original_invalid_reason']
            generation = read(source / 'generation' / name / 'config.json')
            assert generation['agent']['model_name'] == manifest['generation_model']
            row.update(approved_row(root, source, audit))
            row.update(previous_invalid=dict(previous), audit_source=str(manifest_path),
                       original_invalid_reason=previous['invalid_reason'],
                       source_patch=str(root / audit['source_patch']), audit_result_bytes_pinned=True)
        rows.append(row)  # All other native valid/invalid/pending rows stay unchanged.
    valid = [row for row in rows if row.get('invalid_reason') is None
             and row.get('status') in (None, 'valid_scored')
             and type(row.get('reward')) in (int, float) and row['reward'] in (0, 1)]
    resolved = sum(row['reward'] == 1 for row in valid)
    model_path = root / manifest['model_consumer_marker']
    cpu_path = root / manifest['all_cpu_consumers_marker']
    model = read(model_path) if model_path.exists() else {}
    cpu = read(cpu_path) if cpu_path.exists() else {}
    model_done = (model.get('model') == manifest['model'] and model.get('expected') == 51
                  and model.get('model_consumer_finished') is True
                  and model.get('scoring_may_still_be_running') is False)
    cpu_done = (cpu.get('state') == 'finished' and cpu.get('model') == manifest['model']
                and cpu.get('expected') == cpu.get('attempted') == 51
                and cpu.get('all_cpu_consumers_finished') is True
                and cpu.get('cpu_consumers_finished') is True
                and cpu.get('model_consumer_finished') is True
                and cpu.get('source_all_consumers_finished') is True
                and cpu.get('active') == {} and cpu.get('pending') == []
                and cpu.get('remaining_cpu_scopes') == []
                and sorted(cpu.get('cpu_ids', [])) == sorted(manifest['source_cpu_ids']))
    ordered = (model_done and cpu_done and
               aware_time(raw['as_of']) <= aware_time(model['at']) <= aware_time(cpu['at']))
    gates = {'all51_effectively_scored': len(valid) == 51,
             'all51_original_attempts_terminal': terminal == set(ids),
             'original_active_empty': raw['active'] == {}, 'original_pending_empty': raw['pending'] == [],
             'owner_final_state': raw['state'] == 'all51_attempts_finished',
             'owner_model_and_scoring_finished': model_done,
             'owner_all_cpu_consumers_finished': cpu_done,
             'owner_completion_timestamps_ordered': bool(ordered)}
    complete = all(gates.values())
    return {'as_of': datetime.now(timezone.utc).isoformat(),
        'state': 'complete' if complete else 'audited_snapshot_incomplete',
        'model': raw['model'], 'checkpoint': raw['checkpoint'], 'expected': 51,
        'valid_scored': len(valid), 'unscored': 51 - len(valid), 'resolved': resolved,
        'complete': complete, 'primary_score_percent': 100 * resolved / 51 if complete else None,
        'invalid_pending': sum(row.get('invalid_reason') is not None
                               and row['task_id'] in terminal for row in rows),
        'awaiting_generation_or_replay': len(active | pending),
        'active': raw['active'], 'pending': raw['pending'], 'terminal': raw['terminal'],
        'source_summary': str(source_path), 'source_summary_sha256': hashlib.sha256(data).hexdigest(),
        'source_as_of': raw['as_of'], 'original_valid_scored': raw['valid_scored'],
        'original_complete': raw['complete'], 'audit_source': str(manifest_path),
        'audit_manifest_sha256': sha256(manifest_path), 'audited_native_zero_count': len(audits),
        'completion_gates': gates, 'model_consumer_marker': str(model_path),
        'model_consumer_marker_observed': model, 'all_cpu_consumers_marker': str(cpu_path),
        'all_cpu_consumers_marker_observed': cpu, 'new_model_calls': 0, 'new_replays': 0,
        'selection_policy': 'One exact root-approved AVG64 native-zero audit; all other rows copied unchanged; no reward search.',
        'tasks': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest', type=Path,
                        default=Path('configs/eval/avg64_swe_audited_hard51_20261017.json'))
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
        ['expected', 'valid_scored', 'original_valid_scored', 'audited_native_zero_count',
         'resolved', 'complete', 'primary_score_percent']}))
