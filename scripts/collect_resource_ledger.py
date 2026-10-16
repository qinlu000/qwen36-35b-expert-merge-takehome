#!/usr/bin/env python3
"""Read-only Slurm/API accounting capture; no training, generation, judging or mutations remotely."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
JOB_KEYS = {'job_id', 'service_job_id', 'service_job', 'source_job_id', 'target_job_id',
            'failed_previous_job_id', 'superseded_pending_job_id', 'cancelled_expansion_job_id',
            'failed_initial_job_id', 'cancelled_previous_job_id'}
ACTIVE = {'RUNNING', 'PENDING', 'CONFIGURING', 'COMPLETING', 'SUSPENDED', 'RESIZING'}


def remote(host, code, socket=None):
    command = ['ssh', '-o', 'BatchMode=yes']
    if socket:
        command += ['-S', socket]
    result = subprocess.run(command + [host, 'python3', '-'], input=code, text=True,
                            capture_output=True, check=True)
    return json.loads(result.stdout)


def known_jobs(config):
    evidence = defaultdict(list)
    def visit(value, source, trail=''):
        if isinstance(value, dict):
            for key, child in value.items():
                label = trail + '.' + key
                if key in JOB_KEYS and re.fullmatch(r'\d{6,}', str(child)):
                    evidence[str(child)].append(source + ':' + label)
                visit(child, source, label)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                visit(child, source, trail + '[' + str(i) + ']')
    for path in sorted((ROOT / 'configs').rglob('*.json')):
        visit(json.loads(path.read_text()), str(path.relative_to(ROOT)))
    for job, source in config['extra_jobs'].items():
        evidence[job].append(source)
    return dict(evidence)


def collect_slurm(config, evidence):
    code = '''import json, subprocess
from datetime import datetime
config = %r
jobs = %r
fields = 'JobIDRaw,JobName%%60,User,Account,Partition,State,Start,End,ElapsedRaw,AllocTRES%%200,ExitCode,WorkDir%%160'
base = ['sacct', '-X', '-n', '-P', '--format=' + fields]
def run(command):
    return subprocess.check_output(command, universal_newlines=True)
print(json.dumps({'captured_at': datetime.now().astimezone().isoformat(),
    'window_rows': run(base + ['-S', config['since'], '-u', config['account']]),
    'explicit_rows': run(base + ['-j', ','.join(jobs)]),
    'squeue': run(['squeue', '-u', config['account'], '-h', '-o', '%%i|%%j|%%T|%%M|%%b|%%Z'])}))
''' % (config, sorted(evidence))
    raw = remote(config['hpc_host'], code, config['hpc_socket'])
    columns = ['job_id', 'job_name', 'user', 'account', 'partition', 'state', 'start', 'end',
               'elapsed_seconds', 'alloc_tres', 'exit_code', 'workdir']
    rows = {}
    for line in (raw['window_rows'] + raw['explicit_rows']).splitlines():
        if line.strip():
            values = [part.strip() for part in line.split('|')]
            row = dict(zip(columns, values))
            rows[row['job_id']] = row
    owned, excluded = [], []
    for job, row in sorted(rows.items()):
        belongs = row['workdir'].rstrip('/') == config['hpc_project']
        if not belongs:
            excluded.append({'job_id': job, 'reason': 'different or missing project WorkDir',
                             'explicit_config_reference': evidence.get(job, [])})
            continue
        row['ownership_evidence'] = ['sacct WorkDir=' + row['workdir']] + evidence.get(job, [])
        row['elapsed_seconds'] = int(row['elapsed_seconds'])
        tres = dict(piece.split('=', 1) for piece in row['alloc_tres'].split(',') if '=' in piece)
        gpu = tres.get('gres/gpu')
        if gpu is None:
            typed = [int(value) for key, value in tres.items() if key.startswith('gres/gpu:')]
            gpu = sum(typed) if typed else (0 if tres or row['elapsed_seconds'] == 0 else None)
        row['gpus'] = int(gpu) if gpu is not None else None
        row['gpu_hours'] = row['gpus'] * row['elapsed_seconds'] / 3600 if gpu is not None else None
        row['active_at_capture'] = row['state'].split()[0].rstrip('+') in ACTIVE
        name = row['job_name']
        row['category'] = ('loss_only_validation' if 'sft-loss' in name else
                           'smoke' if 'smoke' in name else
                           'cpu_environment' if 'dev-env' in name else
                           'training' if 'sft' in name else 'inference_service')
        owned.append(row)
    return {'captured_at': raw['captured_at'], 'jobs': owned, 'excluded': excluded,
            'known_jobs_not_returned': sorted(set(evidence) - set(rows)),
            'squeue_project_rows': [line for line in raw['squeue'].splitlines()
                                   if line.endswith('|' + config['hpc_project'])]}


def collect_runner(config):
    # Return accounting fields only: teacher text, questions, API keys and response contents never leave host80.
    code = '''import json
from datetime import datetime, timezone
from pathlib import Path
config = %r
root = Path(config['runner_project'])
keep = {'status', 'event', 'id', 'usage', 'charged_cny', 'reserved_cny',
        'conservative_cost_usd', 'cost_upper_cny', 'max_reserved_cny', 'observed_ceiling_cny',
        'peak_usd_per_million', 'budget_conversion_safety_factor', 'budget_factor', 'pricing',
        'price_note', 'http_status', 'requested_model', 'returned_model', 'reported_model'}
ledgers = []
for item in config['api_ledgers']:
    p = root / item['path']
    result = dict(item, exists=p.exists())
    if p.exists():
        data = json.loads(p.read_text()) if p.suffix == '.json' else [json.loads(s) for s in p.read_text().splitlines() if s.strip()]
        rows = list(data['calls'].values()) if item['kind'] == 'budget' else data
        result.update(bytes=p.stat().st_size, mtime_utc=datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(),
                      records=[{k:v for k,v in row.items() if k in keep} for row in rows])
        if item['kind'] == 'budget':
            result['prices_cny_per_million'] = data['prices_cny_per_million']
    ledgers.append(result)
summaries = []
for name in config['raw_summaries']:
    p = root/name
    result = {'path': name, 'exists': p.exists()}
    if p.exists():
        data=json.loads(p.read_text())
        result['scalars']={k:v for k,v in data.items() if v is None or isinstance(v,(str,int,float,bool))}
    summaries.append(result)
print(json.dumps({'captured_at': datetime.now(timezone.utc).isoformat(), 'ledgers': ledgers, 'raw_summaries': summaries}))
''' % config
    return remote(config['runner_host'], code)


def collect_training(config):
    train = json.loads((ROOT / 'configs/train/four_experts_v1.json').read_text())
    runs = [(row['name'], row['job_id'], row['run_dir']) for row in train['experts']]
    runs += [('mixed', train['mixed_control']['job_id'], train['mixed_control']['run_dir'])]
    code = '''import json
from pathlib import Path
root = Path(%r)
runs = %r
rows = []
for name, job, directory in runs:
    summary = json.loads((root/directory/'summary.json').read_text())
    logs = [json.loads(s) for s in (root/directory/'training/logging.jsonl').read_text().splitlines() if s.strip()]
    final = next(row for row in reversed(logs) if 'train_runtime' in row)
    metrics = {k:v for k,v in final.items() if k.startswith('train_') or k in ('total_flos','memory(GiB)','global_step','epoch')}
    rows.append(dict(name=name, job_id=job, source=directory, world_size=summary['world_size'],
                     wall_seconds=summary['wall_seconds'], native_metrics=metrics))
print(json.dumps(rows))
''' % (config['hpc_project'], runs)
    rows = remote(config['hpc_host'], code, config['hpc_socket'])
    for row in rows:
        row['run_gpu_hours'] = row['wall_seconds'] * row['world_size'] / 3600
    return rows


def usage_sum(records):
    totals = Counter()
    for row in records:
        usage = row.get('usage') or {}
        for key in ['prompt_tokens', 'completion_tokens', 'total_tokens']:
            if key in usage and usage[key] is not None:
                totals[key] += usage[key]
    return dict(totals)


def account_ledger(source):
    result = {key: value for key, value in source.items() if key != 'records'}
    result.update(invoice_amount=None, invoice_status='not provided')
    if not source['exists']:
        return result
    records, kind = source['records'], source['kind']
    result['event_rows'] = len(records)
    observed = reserved = 0.0
    if kind == 'journal':
        groups = defaultdict(list)
        for row in records:
            if row.get('id'):
                groups[row['id']].append(row)
        charged_rows = []
        for events in groups.values():
            completed = [r for r in events if r['event'] == 'completed']
            starts = [r for r in events if r['event'] == 'started']
            if completed:
                row = completed[-1]
                usage = row.get('usage') or {}
                if 'observed_ceiling_cny' in row:
                    observed += row['observed_ceiling_cny']
                elif usage:
                    observed += (usage['prompt_tokens'] * .3 + usage['completion_tokens'] * 1.2) / 1e6 * 8
                else:
                    reserved += starts[0].get('reserved_cny', 0) if starts else 0
                charged_rows.append(row)
            elif starts:
                reserved += starts[0].get('reserved_cny', 0)
        result.update(calls=len(groups), completed_calls=sum(any(r['event']=='completed' for r in g) for g in groups.values()),
                      cache_reuses=sum(r.get('event')=='cache_reused' for r in records), currency='CNY',
                      price_basis='USD 0.3/M input + 1.2/M output, budget coefficient 8; no cache discount')
    else:
        charged_rows = records
        for row in records:
            amount = row.get('charged_cny', 0) if kind == 'budget' else row.get(
                'conservative_cost_usd' if kind == 'usd_rows' else 'cost_upper_cny', 0)
            settled = row.get('status') == 'completed' if kind == 'budget' else bool(row.get('usage'))
            if settled:
                observed += amount
            else:
                reserved += amount
        result.update(calls=len(records), completed_calls=sum(r.get('status') == 'completed' for r in records)
                      if kind == 'budget' else sum(bool(r.get('usage')) for r in records),
                      currency='USD' if kind == 'usd_rows' else 'CNY',
                      price_basis='recorded per-row conservative rates' if kind == 'usd_rows' else
                      'ledger prices_cny_per_million' if kind == 'budget' else 'recorded cost_upper_cny; budget coefficient 8')
    result.update(status_counts=dict(Counter(str(r.get('status', r.get('event', 'unspecified'))) for r in records)),
                  usage=usage_sum(charged_rows), observed_usage_estimate=observed,
                  unresolved_or_failure_reservation=reserved, accounted_total=observed+reserved,
                  missing_usage_calls=sum(not r.get('usage') for r in charged_rows),
                  calls_with_usage=sum(bool(r.get('usage')) for r in charged_rows))
    pricing = [{k:r[k] for k in ['peak_usd_per_million', 'budget_conversion_safety_factor',
               'budget_factor', 'pricing', 'price_note'] if k in r} for r in records]
    result['recorded_pricing'] = [json.loads(value) for value in sorted({json.dumps(p, sort_keys=True)
                                  for p in pricing if p})]
    return result


def write_csv(path, rows, fields):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main(args):
    config = json.loads(args.config.read_text())
    evidence = known_jobs(config)
    slurm = collect_slurm(config, evidence)
    runner = collect_runner(config)
    training = collect_training(config)
    api = [account_ledger(row) for row in runner['ledgers']]
    ended = [r for r in slurm['jobs'] if not r['active_at_capture']]
    active = [r for r in slurm['jobs'] if r['active_at_capture']]
    totals = {'ended_gpu_hours': sum(r['gpu_hours'] or 0 for r in ended),
              'active_provisional_gpu_hours': sum(r['gpu_hours'] or 0 for r in active),
              'active_gpu_count': sum(r['gpus'] or 0 for r in active),
              'unknown_gpu_hours_jobs': [r['job_id'] for r in slurm['jobs'] if r['gpu_hours'] is None],
              'five_final_trainer_run_gpu_hours_subset': sum(r['run_gpu_hours'] for r in training)}
    for group in ['state', 'category']:
        totals['by_' + group] = {value: {'jobs': len(rows), 'gpu_hours': sum(r['gpu_hours'] or 0 for r in rows)}
            for value in sorted({r[group] for r in slurm['jobs']})
            for rows in [[r for r in slurm['jobs'] if r[group] == value]]}
    result = {'captured_at_utc': datetime.now(timezone.utc).isoformat(), 'configuration': config,
              'slurm': slurm, 'totals': totals, 'training': training,
              'api': api, 'runner_captured_at': runner['captured_at'], 'raw_summaries': runner['raw_summaries'],
              'limitations': {'human_active_work_hours': None, 'school_hpc_currency_price': None,
                              'host80_cpu_hours': None, 'unledgered_api_calls': 'unknown',
                              'memory_metric': 'rank0 current CUDA device PyTorch peak_reserved GiB; not cross-rank peak'}}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'snapshot.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    write_csv(args.output/'slurm_jobs.csv', slurm['jobs'], ['job_id','job_name','state','category','start','end',
              'elapsed_seconds','gpus','gpu_hours','active_at_capture','partition','alloc_tres','exit_code','workdir','ownership_evidence'])
    write_csv(args.output/'api_ledgers.csv', api, ['name','path','exists','calls','completed_calls','event_rows','currency',
              'observed_usage_estimate','unresolved_or_failure_reservation','accounted_total','invoice_amount','price_basis','usage'])
    flat = [dict(row, **row['native_metrics']) for row in training]
    write_csv(args.output/'training_runs.csv', flat, ['name','job_id','source','world_size','wall_seconds','run_gpu_hours',
              'train_runtime','train_samples_per_second','train_steps_per_second','train_speed(s/it)','train_loss','total_flos','memory(GiB)'])
    print(json.dumps({'output': str(args.output), 'totals': totals, 'api': [
        {key:r.get(key) for key in ['name','exists','calls','currency','observed_usage_estimate','unresolved_or_failure_reservation']}
        for r in api]}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'configs/resource_ledger_20261017.json')
    parser.add_argument('--output', type=Path, default=ROOT/'analysis/source_snapshots/resource_ledger_20261017')
    main(parser.parse_args())
