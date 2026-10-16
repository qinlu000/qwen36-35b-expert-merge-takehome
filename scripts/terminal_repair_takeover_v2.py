"""Continue untouched admissions and retain new unscored rows after natural drain."""
import json
from pathlib import Path

from harbor.job_plan import JobPlan
from harbor.models.job.config import JobConfig
from harbor.models.trial.config import TaskConfig, TrialConfig


def takeover_entries(old_manifest_path, old_checkpoint_path, old_summary_path, existing_keys):
    manifest = json.loads(Path(old_manifest_path).read_text())
    checkpoint = json.loads(Path(old_checkpoint_path).read_text())
    summary = json.loads(Path(old_summary_path).read_text())
    accepted = set(summary['accepted_first_valid']) | set(checkpoint.get('first_valid', {}))
    excluded = set(existing_keys) | accepted
    seed_configs = {}
    selected = []
    for original_entry in manifest['entries']:
        key = original_entry['key']
        status = checkpoint['statuses'][key]
        if key in excluded or status['state'] == 'admitted':
            continue
        seed, task_id = original_entry['seed'], original_entry['task_id']
        if status['state'] == 'pending':
            if seed not in seed_configs:
                path = Path(manifest['seed_job_configs'][str(seed)]['path'])
                seed_configs[seed] = JobConfig.model_validate_json(path.read_text())
            config = JobPlan.build_trial_configs(seed_configs[seed],
                [TaskConfig.model_validate(original_entry['task_config'])], job_id=None)[0]
            selected.append({
                'key': key, 'task_id': task_id, 'seed': seed,
                'mode': 'first_admission_continuation',
                'reason': 'Original controller stopped admission before this solver attempt started.',
                'base_trial_config': config.model_dump(mode='json'),
                'original_task_config': original_entry['task_config'],
                'original_manual_attempt': original_entry['manual_attempt'],
                'original_state': status['state'],
                'source_manifest': str(old_manifest_path),
                'source_checkpoint': str(old_checkpoint_path),
                'prior_infrastructure_result': original_entry.get('original_result'),
                'new_generation_attempt_added': False,
                'new_experiment_repeat_of_budget_complete_answer': False,
                'replace_original_first_valid': False,
            })
            continue
        # Membership, rather than reward, determines the scope. Both accepted
        # zeroes and ones above are preserved; no result is selected by success.
        if status['state'] in ('valid', 'first_valid_preserved'):
            continue
        path = Path(status['result_path'])
        result = json.loads(path.read_text())
        config = TrialConfig.model_validate(result['config'])
        exception = result.get('exception_info') or {}
        selected.append({
            'key': key, 'task_id': task_id, 'seed': seed,
            'mode': 'new_independent_generation',
            'reason': 'Additional terminal unscored row found when the original controller drained.',
            'base_trial_config': config.model_dump(mode='json'),
            'original_result': str(path),
            'original_trial_dir': str(path.parent),
            'original_task_config': original_entry['task_config'],
            'original_manual_attempt': original_entry['manual_attempt'],
            'original_state': status['state'],
            'original_exception_type': exception.get('exception_type'),
            'original_exception_message': exception.get('exception_message'),
            'original_agent_execution': result.get('agent_execution'),
            'source_manifest': str(old_manifest_path),
            'source_checkpoint': str(old_checkpoint_path),
            'original_answer_preserved': True,
            'new_generation_attempt_added': True,
            'previous_solver_execution_present': result.get('agent_execution') is not None,
            'replace_original_first_valid': False,
        })
    return selected
