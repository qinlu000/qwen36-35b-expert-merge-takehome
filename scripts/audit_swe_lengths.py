"""Read-only CPU length audit of fixed Open-SWE. No task execution or patch fields."""
import argparse
import copy
import hashlib
import json
import math
import os
import re
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

for key in ['OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'RAYON_NUM_THREADS']:
    os.environ[key] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

ROOT = Path('/data/caoqinlu/projects/apex-takehome')
MODEL_REV = '995ad96eacd98c81ed38be0c5b274b04031597b0'
BEGIN, END = '__APEX_ASSISTANT_2bc72fa8_BEGIN__', '__APEX_ASSISTANT_2bc72fa8_END__'
THRESHOLDS = [8192, 16384, 24576, 28672, 32768, 61440, 65536, 131072]


def initialize():
    global tokenizer, template, source_template
    import pyarrow as pa
    from tokenizers import Tokenizer
    from transformers.utils.chat_template_utils import _compile_jinja_template
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    tokenizer = Tokenizer.from_file(str(ROOT / 'artifacts/models/base_metadata' / MODEL_REV / 'tokenizer.json'))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    source_template = (ROOT / 'analysis/source_snapshots/model_chat_template.jinja').read_text()
    marked = source_template.replace('{%- elif message.role == "assistant" %}', '{%- elif message.role == "assistant" %}{{- "' + BEGIN + '" }}')
    marked = marked.replace('{%- elif message.role == "tool" %}', '{{- "' + END + '" }}{%- elif message.role == "tool" %}')
    template = _compile_jinja_template(marked)


def normalize(messages, clean):
    result = []
    for original in messages:
        msg = {k: copy.deepcopy(v) for k, v in original.items() if v is not None}
        msg.setdefault('content', '')
        for call in msg.get('tool_calls', []):
            call['function']['arguments'] = json.loads(call['function']['arguments'])
        if clean and msg['role'] == 'assistant':
            msg.pop('reasoning_content', None)
            content = msg['content']
            # Explicit published think blocks only; do not delete natural-language explanations.
            leading = re.match(r'\A\s*<think>.*?</think>\s*', content, flags=re.S)
            if leading:
                content = content[leading.end():]
            msg['content'] = content
        result.append(msg)
    return result


def render_parts(messages, tools, preserve):
    rendered = template.render(messages=messages, tools=tools, add_generation_prompt=False,
                               enable_thinking=False, preserve_thinking=preserve)
    parts = rendered.split(BEGIN)
    assistant = []
    for p in parts[1:]:
        payload = p.split(END, 1)[0]
        assert payload.startswith('<|im_start|>assistant\n')
        assistant.append(payload.removeprefix('<|im_start|>assistant\n'))
    full = rendered.replace(BEGIN, '').replace(END, '')
    assert len(assistant) == sum(m['role'] == 'assistant' for m in messages)
    return full, assistant


def audit_file(spec):
    import pyarrow.parquet as pq
    item, per_shard = spec
    path = ROOT / 'artifacts/data/raw/open_swe' / '1db674173119d71df45c22007af99e214600711a' / item
    pf = pq.ParquetFile(path)
    n = pf.metadata.num_rows
    count = min(n, per_shard) if per_shard else n
    indexes = set(range(n)) if count == n else {round(i * (n - 1) / (count - 1)) for i in range(count)}
    output = []
    offset = 0
    start = time.monotonic()
    for batch in pf.iter_batches(batch_size=64, columns=['messages', 'tools', 'resolved'], use_threads=False):
        wanted = [i - offset for i in indexes if offset <= i < offset + len(batch)]
        for j in sorted(wanted):
            row = batch.slice(j, 1).to_pylist()[0]
            tools = [json.loads(t) for t in row['tools']]
            raw, raw_asst = render_parts(normalize(row['messages'], False), tools, True)
            clean, clean_asst = render_parts(normalize(row['messages'], True), tools, False)
            texts = [raw, *raw_asst]
            same = raw == clean
            if not same:
                texts += [clean, *clean_asst]
            lengths = [len(encoded.ids) for encoded in tokenizer.encode_batch(texts, add_special_tokens=False)]
            raw_output = lengths[1:1 + len(raw_asst)]
            clean_total = lengths[0] if same else lengths[1 + len(raw_asst)]
            clean_output = raw_output if same else lengths[2 + len(raw_asst):]
            output.append({'row': offset + j, 'source': 'scale' if '/scale-swe/' in item else 'rebench',
                           'file': item, 'population': n, 'weight': n / count, 'resolved': row['resolved'],
                           'messages': len(row['messages']), 'assistant_turns': len(raw_asst),
                           'raw_total': lengths[0], 'clean_total': clean_total,
                           'raw_assistant': raw_output, 'clean_assistant': clean_output,
                           'reasoning_fields': sum(bool(m.get('reasoning_content')) for m in row['messages']),
                           'think_tag_messages': sum('<think>' in (m.get('content') or '') or '</think>' in (m.get('content') or '') for m in row['messages'] if m['role'] == 'assistant')})
        offset += len(batch)
    return output, {'file': item, 'population': n, 'sample': len(output), 'seconds': time.monotonic() - start}


def distribution(values, weights):
    ordered = sorted(zip(values, weights))
    total = sum(weights)
    result = {'n': len(values), 'weighted_population': total,
              'mean': sum(v * w for v, w in ordered) / total,
              'max': max(values), 'sample_unweighted_mean': sum(values) / len(values)}
    for name, q in [('median', .5), ('p90', .9), ('p95', .95), ('p99', .99)]:
        current = 0
        for value, weight in ordered:
            current += weight
            if current >= total * q:
                result[name] = value
                break
    result['fraction_le'] = {str(t): sum(w for v, w in ordered if v <= t) / total for t in THRESHOLDS}
    result['fraction_le'].update({str(t): sum(w for v, w in ordered if v <= t) / total for t in [4096]})
    return result


def summarize(rows):
    result = {'sample_records': len(rows), 'weighted_records': sum(r['weight'] for r in rows),
              'sample_resolved_counts': dict(Counter(str(r['resolved']) for r in rows)),
              'records_with_reasoning_content': sum(r['reasoning_fields'] > 0 for r in rows),
              'records_with_think_tags': sum(r['think_tag_messages'] > 0 for r in rows)}
    weights = [r['weight'] for r in rows]
    for mode in ['raw', 'clean']:
        per_turn = [v for r in rows for v in r[mode + '_assistant']]
        per_turn_weights = [r['weight'] for r in rows for v in r[mode + '_assistant']]
        result[mode] = {
            'full_trajectory': distribution([r[mode + '_total'] for r in rows], weights),
            'assistant_total_per_trajectory': distribution([sum(r[mode + '_assistant']) for r in rows], weights),
            'largest_assistant_output_per_trajectory': distribution([max(r[mode + '_assistant'], default=0) for r in rows], weights),
            'all_assistant_outputs': distribution(per_turn, per_turn_weights),
        }
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per-shard', type=int, default=128, help='0 means every row')
    ap.add_argument('--max-shards', type=int, default=0)
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--label', default='sample128')
    args = ap.parse_args()
    assert 1 <= args.workers <= 8
    source = json.loads((ROOT / 'data_sources.json').read_text())['open_swe']
    files = [x['path'] for x in source['files'] if x['path'].endswith('.parquet')]
    if args.max_shards:
        files = files[:args.max_shards]
    start = time.monotonic()
    rows, timings = [], []
    out_dir = ROOT / 'artifacts/data/audits'
    out_dir.mkdir(parents=True, exist_ok=True)
    numbers_path = out_dir / ('swe_lengths_' + args.label + '_20261016.rows.jsonl')
    with numbers_path.open('w') as stream, ProcessPoolExecutor(max_workers=args.workers, initializer=initialize) as pool:
        for result, timing in pool.map(audit_file, [(p, args.per_shard) for p in files]):
            rows.extend(result)
            timings.append(timing)
            for r in result:
                stream.write(json.dumps(r) + '\n')
            stream.flush()
            print(json.dumps({'completed_shards': len(timings), 'records': len(rows), 'elapsed_seconds': round(time.monotonic()-start, 2), 'file_seconds': round(timing['seconds'], 2)}), flush=True)
    groups = {}
    for source_name in ['all', 'scale', 'rebench']:
        for quality in ['all_labels', 'resolved_1']:
            subset = [r for r in rows if (source_name == 'all' or r['source'] == source_name) and (quality == 'all_labels' or r['resolved'] == 1)]
            if subset:
                groups[source_name + '/' + quality] = summarize(subset)
    report = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(), 'source_revision': source['revision'],
              'model_revision': MODEL_REV, 'tokenizer_sha256': hashlib.sha256((ROOT/'artifacts/models/base_metadata'/MODEL_REV/'tokenizer.json').read_bytes()).hexdigest(),
              'chat_template_sha256': hashlib.sha256((ROOT/'analysis/source_snapshots/model_chat_template.jinja').read_bytes()).hexdigest(),
              'selection': f'{args.per_shard} evenly spaced rows including endpoints per shard; N/n weighted distributions' if args.per_shard else 'complete selected shards',
              'workers': args.workers, 'total_seconds': time.monotonic() - start, 'sample_records': len(rows),
              'population_records': sum(t['population'] for t in timings), 'timings': timings, 'groups': groups,
              'scope': 'Full rendered static sequence, including all roles/tools/template; no historical compression, no fixed-size packing/padding, no execution. raw preserve_thinking=true; clean explicitly drops assistant reasoning_content and balanced leading published think spans then preserve=false. Assistant output counts rendered payload plus end token, excluding role header; not actual wire generation usage or final SFT loss mask. resolved=1 is source metadata only, not final quality or decontamination approval.'}
    dest = out_dir / ('swe_lengths_' + args.label + '_20261016.json')
    dest.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'report': str(dest), 'records': len(rows), 'seconds': report['total_seconds']}), flush=True)

if __name__ == '__main__':
    main()
