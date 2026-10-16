#!/usr/bin/env python3
"""Explicit one-call compact recovery for a fixed list of truncated HLE grades.

Default: read-only preparation. --execute is required to send any Judge request.
The original two-attempt ledger is immutable; recovery has its own ledger.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_text())


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_module(path):
    spec = importlib.util.spec_from_file_location('frozen_hle_recovery_source', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def process_alive(pid):
    path = Path('/proc') / str(pid) / 'stat'
    return path.exists() and path.read_text().rsplit(')', 1)[1].split()[0] != 'Z'


def validate_pair(source, requests, responses, identity):
    assert requests[0] == requests[1], 'Original requests differ'
    payload = requests[0]
    assert payload['model'] == source.MODEL == identity['requested_model']
    assert payload['temperature'] == 0 and payload['seed'] == 0 and payload['max_tokens'] == 4096
    assert payload['thinking'] == {'type': 'disabled'}
    assert payload['chat_template_kwargs'] == {'enable_thinking': False}
    assert payload['response_format'] == {'type': 'json_object'}
    assert [m['role'] for m in payload['messages']] == ['system', 'user']
    for response in responses:
        assert response['http_status'] == 200
        raw = json.loads(response['body'])
        assert raw['model'] == identity['reported_model']
        assert raw.get('system_fingerprint') == identity['system_fingerprint']
        assert raw['usage']['completion_tokens'] == 4096
        choice = raw['choices'][0]
        assert choice['finish_reason'] == 'length'
        message = choice['message']
        assert not message.get('reasoning_content') and not message.get('reasoning')
        try:
            source.parse_judge(message['content'])
        except (ValueError, AssertionError, KeyError, TypeError):
            pass
        else:
            raise AssertionError('Original response already parses; another call is ineligible')


def reserve(ledger, task, bound, source, original, config):
    assert task not in ledger['calls'], 'Existing recovery call: never resend, including unknown outcomes'
    amount = (bound * source.INPUT_PRICE + 4096 * source.OUTPUT_PRICE) / 1e6
    total = sum(r['charged_cny'] for r in original['calls'].values())
    total += sum(r['charged_cny'] for r in ledger['calls'].values())
    assert total + amount <= config['max_cny_per_model_combined']
    assert len(original['calls']) + len(ledger['calls']) + 1 <= config['max_calls_per_model_combined']
    row = {'status': 'reserved_unknown_outcome', 'reserved_cny': amount, 'charged_cny': amount,
        'input_token_bound': bound, 'output_token_cap': 4096, 'started_at_utc': now()}
    ledger['calls'][task] = row
    return row


def prepare_model(root, model, config):
    parent = root / model['scoring']
    source = source_module(parent / 'scorer_source.py')
    scoring = load(parent / 'scoring_config.json')
    assert scoring['model'] == source.MODEL and scoring['tls_tunnel_port'] == config['tls_tunnel_port']
    assert scoring['max_cny'] == config['max_cny_per_model_combined'] == 20
    assert scoring['max_calls'] == config['max_calls_per_model_combined'] == 5000
    assert load(parent / 'judge_identity.json') == config['judge_identity']
    original = load(parent / 'budget.json')
    assert original['prices_cny_per_million'] == {'input': source.INPUT_PRICE, 'output': source.OUTPUT_PRICE}
    recovery = parent / 'compact-recovery-20261017'
    ledger = load(recovery / 'budget.json') if (recovery / 'budget.json').exists() else {
        'recovery_id': config['recovery_id'], 'calls': {}, 'original_budget_sha256': digest(parent / 'budget.json')}
    assert ledger['original_budget_sha256'] == digest(parent / 'budget.json')
    entries = []
    for task in model['task_ids']:
        result_path = parent / 'results' / (task + '.json')
        previous = load(result_path)
        if task in ledger['calls']:
            entries.append({'task_id': task, 'already_reserved': True,
                'recovery_status': ledger['calls'][task]['status']})
            continue
        assert previous['id'] == task and previous['evaluation_status'] == 'evaluation_invalid'
        assert previous['correct'] is None and previous['judge_calls'] == 2
        item = load(parent / 'inputs' / (task + '.json'))
        solver = Path(item['source_result'])
        answer = load(solver)
        assert item['id'] == task and item['kind'] == 'answer'
        assert answer['id'] == task and answer['status'] == 'completed' and answer['finished_at_utc']
        assert answer['response'] == item['response']
        assert previous['source_result'] == str(solver) and previous['is_image'] == item['is_image']
        requests = [load(parent / 'requests' / f'{task}.{n}.json') for n in (1, 2)]
        responses = [load(parent / 'responses' / f'{task}.{n}.json') for n in (1, 2)]
        validate_pair(source, requests, responses, config['judge_identity'])
        expected_user = scoring['criteria'].format(question=item['question'],
            correct_answer=item['correct_answer'], response=item['response'])
        assert requests[0]['messages'] == [{'role': 'system', 'content': scoring['json_wrapper']},
            {'role': 'user', 'content': expected_user}]
        payload = json.loads(json.dumps(requests[0]))
        payload['messages'][0]['content'] += config['wrapper_append']
        assert payload['messages'][1] == requests[0]['messages'][1]
        bound = sum(len(m['content'].encode()) for m in payload['messages']) + 1024
        # A throwaway ledger verifies the aggregate worst-case reservation in default prepare mode.
        entries.append({'task_id': task, 'payload': payload, 'item': item, 'solver': solver,
            'solver_sha256': digest(solver), 'bound': bound, 'previous': previous})
    probe = json.loads(json.dumps(ledger))
    for entry in entries:
        if not entry.get('already_reserved'):
            reserve(probe, entry['task_id'], entry['bound'], source, original, config)
    return parent, recovery, source, original, ledger, entries, probe


def backup(parent, recovery, tasks):
    folder = recovery / 'original'
    folder.mkdir(parents=True, exist_ok=True)
    paths = ['summary.json', 'budget.json', 'scoring_config.json', 'judge_identity.json', 'scorer_source.py']
    for task in tasks:
        paths += [f'inputs/{task}.json', f'results/{task}.json']
        for n in (1, 2):
            paths += [f'requests/{task}.{n}.json', f'responses/{task}.{n}.json',
                f'responses/{task}.{n}.error.json']
    for relative in paths:
        source, target = parent / relative, folder / relative
        if not source.exists():
            continue
        if target.exists():
            assert target.read_bytes() == source.read_bytes(), 'Original backup must not change'
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    save(recovery / 'original_files.json', {p: digest(folder / p) for p in paths if (folder / p).exists()})


def update_summary(parent, recovery, original, ledger, config):
    results = [load(p) for p in (parent / 'results').glob('*.json')]
    valid = [r for r in results if r['evaluation_status'] in ('judged', 'native_no_answer')]
    summary = load(recovery / 'original/summary.json')
    complete = len(valid) == 2500
    correct = sum(r['correct'] for r in valid)
    summary.update(complete=complete, judged_answers=sum(r['evaluation_status'] == 'judged' for r in results),
        native_no_answer=sum(r['evaluation_status'] == 'native_no_answer' for r in results),
        evaluation_invalid=sum(r['evaluation_status'] == 'evaluation_invalid' for r in results),
        scored=len(valid), pending=2500-len(valid), correct=correct,
        accuracy_percent=round(100*correct/2500, 2) if complete else None,
        score=100*correct/2500 if complete else None,
        partial_correct_over_full_denominator_percent=100*correct/2500,
        judge_generation_calls=len(original['calls'])+len(ledger['calls']),
        accounted_cost_cny=sum(r['charged_cny'] for r in original['calls'].values())
            + sum(r['charged_cny'] for r in ledger['calls'].values()),
        updated_at_utc=now(), recovery_judge_calls=len(ledger['calls']),
        grader_only_recovery=str(recovery), recovery_budget=str(recovery/'budget.json'),
        original_budget_ledger_unchanged=True,
        protocol_exception='Original two attempts plus at most one explicit compact-wrapper recovery for listed length-truncated grades')
    for name, image in (('text', False), ('image', True)):
        group = [r for r in valid if r['is_image'] == image]
        total = summary['subgroups'][name]['denominator']
        group_correct = sum(r['correct'] for r in group)
        summary['subgroups'][name].update(scored=len(group), correct=group_correct,
            accuracy_percent=round(100*group_correct/total, 2) if len(group) == total else None)
    assert summary['accounted_cost_cny'] <= config['max_cny_per_model_combined']
    save(parent / 'summary.json', summary)
    save(recovery / 'summary.json', summary)
    return summary


def execute_model(prepared, config, credentials):
    parent, recovery, source, original, ledger, entries, _ = prepared
    recovery.mkdir(exist_ok=True, mode=0o700)
    fresh = [e for e in entries if not e.get('already_reserved')]
    if fresh:
        backup(parent, recovery, [e['task_id'] for e in fresh])
    for entry in fresh:
        task = entry['task_id']
        dest = recovery / task
        dest.mkdir(mode=0o700)
        row = reserve(ledger, task, entry['bound'], source, original, config)
        # Persist before any network activity; this entry can never be resent after an uncertain outcome.
        save(recovery / 'budget.json', ledger)
        save(dest / 'request.json', entry['payload'])
        save(dest / 'source_identity.json', {'source_result': str(entry['solver']),
            'source_sha256': entry['solver_sha256'], 'user_message_unchanged': True,
            'original_result': str(recovery / 'original/results' / (task+'.json'))})
        connection = source.SchoolTLS(config['tls_tunnel_port'])
        received = False
        try:
            connection.request('POST', '/v1/chat/completions', json.dumps(entry['payload'], ensure_ascii=False).encode(),
                {'Authorization': 'Bearer '+credentials['OPENAI_API_KEY'], 'Content-Type': 'application/json'})
            response = connection.getresponse()
            raw_text = response.read().decode('utf-8')
            save(dest / 'response.json', {'http_status': response.status, 'body': raw_text, 'at_utc': now()})
            received = True
            assert response.status == 200
            raw = json.loads(raw_text)
            identity = {'requested_model': source.MODEL, 'reported_model': raw.get('model'),
                'system_fingerprint': raw.get('system_fingerprint'), 'provider_revision_pinned': False}
            assert identity == config['judge_identity']
            message = raw['choices'][0]['message']
            assert not message.get('reasoning_content') and not message.get('reasoning')
            parsed = source.parse_judge(message['content'])
            usage = raw['usage']
            assert type(usage['prompt_tokens']) is int and 0 <= usage['prompt_tokens'] <= entry['bound']
            assert type(usage['completion_tokens']) is int and 0 <= usage['completion_tokens'] <= 4096
            assert digest(entry['solver']) == entry['solver_sha256']
            result_path = parent / 'results' / (task+'.json')
            assert load(result_path) == entry['previous']
            result = {'id': task, 'evaluation_status': 'judged', 'correct': parsed['correct'] == 'yes',
                'judge_response': parsed, 'judge_calls': 3, 'source_result': entry['item']['source_result'],
                'is_image': entry['item']['is_image'], 'reported_identity': identity, 'usage': usage,
                'finished_at_utc': now(), 'grader_only_recovery': str(dest),
                'original_invalid_result': str(recovery/'original/results'/(task+'.json'))}
            save(dest / 'result.json', result)
            save(result_path, result)
            row.update(status='completed', usage=usage,
                charged_cny=(usage['prompt_tokens']*source.INPUT_PRICE+usage['completion_tokens']*source.OUTPUT_PRICE)/1e6)
        except Exception as error:
            row.update(status='failed_full_reservation' if received else 'unknown_outcome_full_reservation',
                error_type=type(error).__name__)
        finally:
            connection.close()
            row['finished_at_utc'] = now()
            save(recovery / 'budget.json', ledger)
            assert digest(parent / 'budget.json') == ledger['original_budget_sha256']
    if (recovery / 'original/summary.json').exists():
        return update_summary(parent, recovery, original, ledger, config)
    return {'no_fresh_calls': True}


def sanity():
    # Tiny fixtures only: actual frozen parser, no files, credentials, tasks, or network.
    from score_hle_baseline_v2_rolling import parse_judge, INPUT_PRICE, OUTPUT_PRICE, MODEL
    from types import SimpleNamespace
    source = SimpleNamespace(parse_judge=parse_judge, INPUT_PRICE=INPUT_PRICE, OUTPUT_PRICE=OUTPUT_PRICE, MODEL=MODEL)
    identity = {'requested_model': MODEL, 'reported_model': MODEL, 'system_fingerprint': 'fixture'}
    request = {'model': MODEL, 'temperature': 0, 'seed': 0, 'max_tokens': 4096,
        'thinking': {'type': 'disabled'}, 'chat_template_kwargs': {'enable_thinking': False},
        'response_format': {'type': 'json_object'},
        'messages': [{'role': 'system', 'content': 'fixture'}, {'role': 'user', 'content': 'fixed fixture'}]}
    raw = {'model': MODEL, 'system_fingerprint': 'fixture', 'usage': {'completion_tokens': 4096},
        'choices': [{'finish_reason': 'length', 'message': {'content': '{"correct":'}}]}
    response = {'http_status': 200, 'body': json.dumps(raw)}
    validate_pair(source, [request, request], [response, response], identity)
    checks = ['eligible_200_length_pair']
    for name, change in [('http_failure', lambda d: d.update(http_status=503)),
            ('nonlength', lambda d: d.update(body=json.dumps({**raw, 'choices': [{'finish_reason': 'stop', 'message': {'content': '{'}}]}))),
            ('parseable_original', lambda d: d.update(body=json.dumps({**raw, 'choices': [{'finish_reason': 'length', 'message': {'content': json.dumps({'correct':'no','confidence':100,'strict':True,'extracted_final_answer':'x','reasoning':'Mismatch.'})}}]})))]:
        changed = dict(response); change(changed)
        try: validate_pair(source, [request, request], [changed, response], identity)
        except AssertionError: checks.append(name+'_rejected')
        else: raise AssertionError(name)
    changed = json.loads(json.dumps(request)); changed['messages'][1]['content'] += ' changed'
    try: validate_pair(source, [request, changed], [response, response], identity)
    except AssertionError: checks.append('changed_user_rejected')
    else: raise AssertionError('changed_user')
    config = {'max_cny_per_model_combined':20, 'max_calls_per_model_combined':5000}
    original = {'calls': {}}
    ledger = {'calls': {}}
    reserve(ledger, 'fixture', 1000, source, original, config)
    try: reserve(ledger, 'fixture', 1000, source, original, config)
    except AssertionError: checks.append('unknown_outcome_resend_rejected')
    else: raise AssertionError('resend')
    for name, prior in [('cost_cap', {'calls': {'old': {'charged_cny':20}}}),
                        ('call_cap', {'calls': {str(n):{'charged_cny':0} for n in range(5000)}})]:
        try: reserve({'calls':{}}, 'fixture', 1000, source, prior, config)
        except AssertionError: checks.append(name+'_rejected')
        else: raise AssertionError(name)
    for verdict in ('yes','no'):
        parse_judge(json.dumps({'correct':verdict,'confidence':100,'strict':True,'extracted_final_answer':'x','reasoning':'Fixture.'}))
    checks.append('both_verdicts_same_parser_no_reward_selection')
    return {'sanity_passed': True, 'checks': checks, 'network_calls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--config', type=Path, default=Path('configs/eval/hle_compact_judge_recovery_20261017.json'))
    parser.add_argument('--credentials', type=Path, default=Path('/data/caoqinlu/projects/data-perception/.env'))
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--sanity', action='store_true')
    args = parser.parse_args()
    if args.sanity:
        assert not args.execute
        print(json.dumps(sanity()))
        return
    root = args.project.resolve()
    config = load(args.config if args.config.is_absolute() else root / args.config)
    assert config['additional_calls_per_item'] == 1
    assert len({t for m in config['models'] for t in m['task_ids']}) == 8
    prepared = []
    with ExitStack() as stack:
        for model in config['models']:
            assert not process_alive(model['original_scorer_pid']), 'Original grader must have exited'
            lock = stack.enter_context((root/model['scoring']/'controller.lock').open('r'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            prepared.append((model, prepare_model(root, model, config)))
        if not args.execute:
            rows = []
            for model, data in prepared:
                parent, recovery, source, original, ledger, entries, probe = data
                rows.append({'model':model['model'], 'eligible_tasks':[e['task_id'] for e in entries if not e.get('already_reserved')],
                    'already_reserved':[{k:v for k,v in e.items()} for e in entries if e.get('already_reserved')],
                    'original_grader_exited':True, 'original_controller_lock_exclusive':True,
                    'original_calls':len(original['calls']), 'original_cost_cny':sum(r['charged_cny'] for r in original['calls'].values()),
                    'combined_calls_after_reservations':len(original['calls'])+len(probe['calls']),
                    'combined_cost_cny_after_reservations':sum(r['charged_cny'] for r in original['calls'].values())+sum(r['charged_cny'] for r in probe['calls'].values()),
                    'original_budget_sha256':digest(parent/'budget.json'), 'frozen_scorer_sha256':digest(parent/'scorer_source.py')})
            print(json.dumps({'at_utc':now(), 'mode':'prepare_only', 'network_calls':0, 'models':rows}))
            return
        os.umask(0o077)
        credentials = {}
        for line in args.credentials.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=',1); credentials[key.strip()] = value.strip().strip('\"\'')
        assert credentials['OPENAI_BASE_URL'].rstrip('/') == 'https://'+prepared[0][1][2].HOST+'/v1'
        for model, data in prepared:
            result = execute_model(data, config, credentials)
            print(json.dumps({'model':model['model'], 'summary':result}), flush=True)


if __name__ == '__main__':
    main()
