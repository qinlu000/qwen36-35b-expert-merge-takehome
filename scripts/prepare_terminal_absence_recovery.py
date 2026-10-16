"""Record two frozen timeout attempts whose native answer files were never written."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    trials = root / 'artifacts/results/base-terminal-v2-recovery-20261016/trials'
    cases = [
        ('dna-insert', 'dna-insert__seed0__first', '/app/primers.fasta'),
        ('db-wal-recovery', 'db-wal-recovery__seed0__manual1', '/app/recovered.json'),
    ]
    for task, name, answer in cases:
        source = trials / name
        original = json.loads((source / 'result.json').read_text())
        trajectory = json.loads((source / 'agent/trajectory.json').read_text())
        assert original['exception_info']['exception_type'] == 'AgentTimeoutError'
        commands = [dict(step_id=step['step_id'], **call['arguments'])
            for step in trajectory['steps'] for call in step.get('tool_calls', [])]
        if task == 'dna-insert':
            mentions = [row for row in commands if 'primers.fasta' in row['keystrokes']]
            assert len(mentions) == 1 and mentions[0]['step_id'] == 9
            step = next(row for row in trajectory['steps'] if row['step_id'] == 9)
            observation = '\n'.join(row['content'] for row in step['observation']['results'])
            assert 'Found 0 valid primer pairs\nNo valid primer pairs found!' in observation
            detail = ('The only potential answer write is conditional in step9. Its recorded execution '
                'found zero pairs and did not enter the write branch. Later steps only write and run '
                'Tm diagnostic scripts; all original commands are retained in commands.json.')
        else:
            assert not any('recovered.json' in row['keystrokes'] for row in commands)
            detail = ('All 25 recorded agent steps were audited. They inspect or modify the database, '
                'read logs, or run inline diagnostics; none writes recovered.json. The official '
                'verifier reads only that JSON output, and the image provides only DB/WAL inputs.')
        output = root / 'artifacts/recovery/terminal-v2' / (task + '__seed0')
        output.mkdir(parents=True, exist_ok=True)
        (output / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        manifest = {
            'files': [], 'commands': [], 'reconstructed_from_transcript': True,
            'byte_identical': False, 'verifier_observable_state_identical': True,
            'restoration_scope': 'Only the missing native answer file; no whole-filesystem identity claim',
            'answer_path': answer, 'answer_state': 'absent_at_original_solver_deadline',
            'original_result': str(source / 'result.json'),
            'source_trajectory': str(source / 'agent/trajectory.json'),
            'source_terminal': str(source / 'agent/terminus_2.pane'),
            'source_commands': str(output / 'commands.json'),
            'official_verifier': str(Path(original['config']['task']['path']) / 'tests/test_outputs.py'),
            'evidence': detail, 'new_model_calls': 0,
            'new_solver_commands': 0, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        }
        (output / 'restore.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(json.dumps({'task': task, 'restore_manifest': str(output / 'restore.json')}))


if __name__ == '__main__':
    main()
