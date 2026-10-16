"""Export all 102 SAB human reference programs; SFT needs no task environment.

Preserve source code, canaries and task-specific licenses. No execution or API.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random

# Native ASI DirectLLMAdapter: one system message, prompt.md, complete Python block.
SYSTEM = ('You are an expert scientific programmer. When asked to write code, output ONLY '
          'a single Python code block. Do not include any explanation outside the code block.')
CARD = 'https://huggingface.co/datasets/osunlp/ScienceAgentBench/blob/9c6e96c9e74572e979b0930ee735041cef528cb7/README.md'


def write_rows(path, rows):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows))


def prompt(row):
    parts = ['# Task\n'+row['task_inst'],
        '# Workspace and execution\nThe working directory is the task workspace. Input files '
        'are available under benchmark/datasets/ in the layout below. The pred_results/ '
        'directory already exists. Your complete program will be saved as solution.py '
        'and run with python solution.py, without command-line arguments.',
        '# Available input files\n'+(row['dataset_folder_tree'] or '')]
    if row.get('dataset_preview'):
        parts.append('# Data preview\n'+row['dataset_preview'])
    if row.get('domain_knowledge'):
        parts.append('# Scientific background\n'+row['domain_knowledge'])
    parts.append('# Output contract\nWrite all outputs requested by the task, including '
        +row['output_fname']+'. Return one complete Python code block with all imports.')
    return '\n\n'.join(parts)


def validation_repos(records, seed):
    groups = defaultdict(list)
    for row in records:
        groups[row['repo_group']].append(row['task_id'])
    order = sorted(groups)
    random.Random(seed).shuffle(order)
    sums = {0: []}
    for repo in order:
        for total, chosen in list(sums.items()):
            sums.setdefault(total+len(groups[repo]), chosen+[repo])
    target = round(len(records)*.2)
    size = min(sums, key=lambda n:(abs(n-target), abs(len(sums[n])-len(groups)*.2)))
    return set(sums[size])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=20261016)
    args = parser.parse_args()
    repo = args.repo.resolve()
    base = repo/'artifacts/data/candidates/scienceagentbench_verified_9c6e96c9'
    benchmark = repo/'artifacts/data/raw/scienceagentbench/verified_asset/benchmark'
    out = base/'swift_ready'
    out.mkdir(exist_ok=True)
    checks_path = base/'native_checks.json'
    checks = {r['task_id']:r for r in json.loads(checks_path.read_text())} if checks_path.exists() else {}
    records, samples = [], {}
    for row in [json.loads(s) for s in (base/'tasks.raw.jsonl').read_text().splitlines() if s.strip()]:
        task_id = row['instance_id']
        gold = benchmark/'gold_programs'/row['gold_program_name']
        checker = benchmark/'eval_programs'/row['eval_script_name']
        code = gold.read_text()  # Keep the complete reference, including its canary.
        upstream = 'hackingmaterials/matminer' if task_id==3 else 'rasterio/rasterio' if task_id in {32,46,53,54,84} else None
        license_info = {'name':'original_upstream_license', 'url':'https://github.com/'+upstream+'?tab=License-1-ov-file'} if upstream else {'name':'CC-BY-4.0','url':'https://creativecommons.org/licenses/by/4.0/'}
        local_passed = bool(checks.get(task_id, {}).get('passed'))
        records.append({'task_id':task_id, 'repo':row['github_name'],
            'repo_group':row['github_name'].removeprefix('https://github.com/').rstrip('/').lower(),
            'domain':row['domain'], 'gold':str(gold), 'checker':str(checker),
            'ready':True,
            'verification':'local_passed' if local_passed else 'publisher_verified',
            'local_verification':'passed' if local_passed else 'not_locally_rerun',
            'runtime_ready':local_passed, 'license':license_info, 'license_notice':CARD,
            'source':CARD, 'source_file':row['src_file_or_path'], 'original_code_unmodified':True,
            'source_contains_canary':'canary' in code.lower(), 'canary_preserved':True,
            'expected_output':row['output_fname']})
        samples[task_id] = {'messages':[{'role':'system','content':SYSTEM},
            {'role':'user','content':prompt(row)}, {'role':'assistant','content':'```python\n'+code+'\n```'}]}
    assert len(records)==102
    val_repos = validation_repos(records, args.seed)
    train, val, tasks = [], [], []
    for row in records:
        row['split'] = 'val' if row['repo_group'] in val_repos else 'train'
        sample = samples[row['task_id']]
        (val if row['split']=='val' else train).append(sample)
        if row['split']=='val':
            tasks.append({'task_id':row['task_id'], 'repo':row['repo'], 'prompt':sample['messages'][1]['content'],
                'gold_program':row['gold'], 'checker':row['checker'], 'expected_output':row['expected_output'],
                'benchmark_root':str(benchmark), 'evaluation_host':'80', 'verification':row['verification']})
    write_rows(out/'train.messages.jsonl', train)
    write_rows(out/'val.messages.jsonl', val)
    write_rows(out/'val.tasks.jsonl', tasks)
    summary = {'source_tasks':102, 'selected':102, 'train':len(train), 'val':len(val),
        'repo_groups':len({r['repo_group'] for r in records}), 'val_repos':sorted(val_repos), 'seed':args.seed,
        'local_passed_ids':[r['task_id'] for r in records if r['runtime_ready']],
        'publisher_verified_not_locally_rerun':sum(not r['runtime_ready'] for r in records),
        'train_domains':dict(Counter(r['domain'] for r in records if r['split']=='train')),
        'val_domains':dict(Counter(r['domain'] for r in records if r['split']=='val')),
        'filtered_tasks':0, 'length_filter_applied':False, 'hidden_reasoning_exported':False,
        'protocol':'ASI direct_llm system + single prompt + complete Python block; no fabricated tools',
        'raw_package_published':False, 'code_canary_and_licenses_preserved':True}
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    (out/'candidate_manifest.json').write_text(json.dumps({**summary,'records':records}, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__=='__main__':
    main()
