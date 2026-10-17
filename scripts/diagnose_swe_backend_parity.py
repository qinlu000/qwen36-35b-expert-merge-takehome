"""Fixed synthetic next-token loading diagnostic; no benchmark or server requests.

Run hf, vllm, compare in separate processes (the Slurm wrapper does this).
The default plan and self-test phases use only the Python standard library.
"""
import argparse
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import socket


REVISION = '995ad96eacd98c81ed38be0c5b274b04031597b0'
BASE = 'artifacts/models/Qwen3.6-35B-A3B/' + REVISION
ADAPTER = 'artifacts/runs/swe2k-sft-r16-726335/training/checkpoint-249'
TARGETS = ['qkv_proj', 'o_proj', 'in_proj_qkv', 'in_proj_z', 'in_proj_ba',
           'out_proj', 'gate_up_proj', 'down_proj']
TOOLS = [{'type': 'function', 'function': {'name': 'bash',
          'description': 'Execute a shell command.', 'parameters': {'type': 'object',
          'properties': {'command': {'type': 'string'}}, 'required': ['command']}}}]
SYSTEM = 'You are a helpful assistant that can interact with a computer.'
POSITIONS = {'assistant_start': '',
             'command_start': '<tool_call>\n<function=bash>\n<parameter=command>\n'}


def call(command, number):
    return {'id': 'fixture_call_' + str(number), 'type': 'function',
            'function': {'name': 'bash', 'arguments': json.dumps({'command': command})}}


def fixtures():
    return [
        {'id': 'bash_typo_correction', 'messages': [
            {'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': 'Use bash to print diagnostic-ready. Correct the typo in: eho diagnostic-ready. Do not execute any other command.'}]},
        {'id': 'missing_ls_observation', 'messages': [
            {'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': 'Inspect the current directory using bash.'},
            {'role': 'assistant', 'content': '', 'tool_calls': [call('ls /fixture-missing', 1)]},
            {'role': 'tool', 'tool_call_id': 'fixture_call_1', 'content': json.dumps({'output': "ls: cannot access '/fixture-missing': No such file or directory", 'returncode': 2})}]},
        {'id': 'two_prior_tool_calls', 'messages': [
            {'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': 'Inspect the fixture directory, then print diagnostic-ready using bash.'},
            {'role': 'assistant', 'content': '', 'tool_calls': [call('pwd', 1), call('ls', 2)]},
            {'role': 'tool', 'tool_call_id': 'fixture_call_1', 'content': json.dumps({'output': '/fixture\n', 'returncode': 0})},
            {'role': 'tool', 'tool_call_id': 'fixture_call_2', 'content': json.dumps({'output': 'README.txt\n', 'returncode': 0})}]},
    ]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def now():
    return datetime.now(timezone.utc).isoformat()


def progress(event, **fields):
    print(json.dumps({'at': now(), 'event': event, **fields}), flush=True)


def top20(logprobs, tokenizer):
    values, ids = logprobs.topk(20)
    return [{'token_id': int(i), 'logprob': float(v),
             'token': tokenizer.decode([int(i)])} for i, v in zip(ids.tolist(), values.tolist())]


def distribution_metrics(base, adapted):
    """Unfiltered, temperature-one, full-vocabulary quantities in nats."""
    hb = hs = kb = ks = js = topb = tops = 0.0
    assert len(base) == len(adapted)
    for b, s in zip(base, adapted):
        b, s = float(b), float(s)
        pb, ps = math.exp(b), math.exp(s)
        topb, tops = max(topb, pb), max(tops, ps)
        maximum = max(b, s)
        middle = maximum + math.log1p(math.exp(-abs(b - s))) - math.log(2) if maximum != -math.inf else -math.inf
        if pb:
            hb -= pb * b
            kb += pb * (b - s)
            js += 0.5 * pb * (b - middle)
        if ps:
            hs -= ps * s
            ks += ps * (s - b)
            js += 0.5 * ps * (s - middle)
    return {'base_entropy_nats': hb, 'swe_entropy_nats': hs,
            'base_top1_probability': topb, 'swe_top1_probability': tops,
            'kl_base_to_swe_nats': kb, 'kl_swe_to_base_nats': ks, 'js_nats': js}


def hf_phase(root, output):
    progress('hf_import_start')
    import numpy as np
    import torch
    import transformers
    import peft
    from transformers import AutoModelForImageTextToText, AutoTokenizer
    from peft import PeftModel

    progress('hf_import_finished')
    output.mkdir(parents=True, exist_ok=False)
    save(output / 'claim.json', {'at': now(), 'job_id': os.environ['SLURM_JOB_ID'],
         'hostname': socket.gethostname(), 'pid': os.getpid(), 'base_revision': REVISION,
         'adapter': ADAPTER, 'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'slurm_sha256': hashlib.sha256((root / 'scripts/diagnose_swe_backend_parity.slurm').read_bytes()).hexdigest(),
         'scope': '3 fixed synthetic tool histories at 2 positions; no commands executed; next token only'})
    torch.manual_seed(0)
    assert torch.cuda.device_count() == 2
    tokenizer = AutoTokenizer.from_pretrained(root / BASE, local_files_only=True)
    inputs = []
    for fixture in fixtures():
        rendered = tokenizer.apply_chat_template(fixture['messages'], tools=TOOLS,
              add_generation_prompt=True, tokenize=False,
              enable_thinking=False, preserve_thinking=False)
        for position, forced_suffix in POSITIONS.items():
            ids = tokenizer.encode(rendered + forced_suffix, add_special_tokens=False)
            assert isinstance(ids, list) and ids and len(ids) < 2048
            inputs.append({'id': fixture['id'] + '__' + position,
                           'fixture_id': fixture['id'], 'position': position,
                           'prompt_token_ids': ids, 'token_count': len(ids),
                           'token_ids_sha256': digest(ids)})
    save(output / 'frozen_inputs.json', {'fixture_definition_sha256': digest(fixtures()),
         'tools_sha256': digest(TOOLS), 'positions': POSITIONS, 'inputs': inputs})
    progress('hf_base_load_start')
    model = AutoModelForImageTextToText.from_pretrained(root / BASE,
            local_files_only=True, dtype=torch.bfloat16, device_map='balanced',
            max_memory={0: '70GiB', 1: '70GiB'}, low_cpu_mem_usage=True,
            attn_implementation='sdpa')
    assert all(str(device) in ('0', '1', 'cuda:0', 'cuda:1')
               for device in model.hf_device_map.values()), model.hf_device_map
    model.eval()
    progress('hf_base_loaded')
    rows = []
    baseline = {}
    full_logprobs = {}
    entropy_rows = []
    disabled_drift = []
    for mode in ['base', 'swe249', 'base_after_disable']:
        if mode == 'swe249':
            progress('hf_adapter_load_start')
            model = PeftModel.from_pretrained(model, root / ADAPTER,
                    is_trainable=False, autocast_adapter_dtype=False)
            model.eval()
            factors = [(name, p) for name, p in model.named_parameters()
                       if '.lora_A.' in name or '.lora_B.' in name]
            assert len(factors) == 620
            assert {p.dtype for _, p in factors} == {torch.bfloat16}
            scaling = Counter(str(layer.scaling['default']) for layer in model.modules()
                              if isinstance(getattr(layer, 'scaling', None), dict)
                              and 'default' in layer.scaling)
            assert sum(scaling.values()) == 310 and set(scaling) == {'2.0'}
            progress('hf_adapter_loaded', factor_tensors=len(factors))
        context = model.disable_adapter() if mode == 'base_after_disable' else nullcontext()
        with context, torch.inference_mode():
            for item in inputs:
                ids = torch.tensor([item['prompt_token_ids']], device=model.get_input_embeddings().weight.device)
                logits = model(input_ids=ids, attention_mask=torch.ones_like(ids),
                               use_cache=False, logits_to_keep=1).logits[0, -1].float()
                lp = logits.log_softmax(-1).cpu()
                assert torch.isfinite(lp).all()
                rows.append({'fixture_id': item['id'], 'mode': mode,
                             'history_id': item['fixture_id'], 'position': item['position'],
                             'token_ids_sha256': item['token_ids_sha256'],
                             'top20': top20(lp, tokenizer)})
                if mode == 'base':
                    baseline[item['id']] = lp
                    full_logprobs['base__' + item['id']] = lp.numpy()
                elif mode == 'swe249':
                    full_logprobs['swe249__' + item['id']] = lp.numpy()
                    entropy_rows.append({'fixture_id': item['id'],
                        'history_id': item['fixture_id'], 'position': item['position'],
                        'vocabulary_size': lp.numel(),
                        **distribution_metrics(baseline[item['id']].numpy(), lp.numpy())})
                elif mode == 'base_after_disable':
                    disabled_drift.append({'fixture_id': item['id'],
                          'full_vocab_max_abs_logprob_difference': float((lp - baseline[item['id']]).abs().max())})
        progress('hf_mode_finished', mode=mode, prefixes=len(inputs))
    np.savez_compressed(output / 'hf_full_logprobs.npz', **full_logprobs)
    save(output / 'hf.json', {'finished_at': now(), 'torch': torch.__version__,
         'transformers': transformers.__version__, 'peft': peft.__version__,
         'dtype': 'bfloat16', 'attention_backend': 'sdpa; native HF GDN implementation',
         'hf_device_map': {k: str(v) for k, v in model.hf_device_map.items()},
         'adapter_factor_tensors': len(factors), 'adapter_scaling_counts': dict(scaling),
         'rows': rows, 'disable_adapter_control': disabled_drift,
         'full_vocabulary_distribution_metrics': entropy_rows,
         'entropy_definition': 'Shannon entropy of full-vocabulary softmax(raw logits / 1), no top-k/top-p/penalties; nats',
         'full_logprobs_file': 'hf_full_logprobs.npz',
         'full_logprobs_bytes': (output / 'hf_full_logprobs.npz').stat().st_size,
         'quality_or_validation_selection': False})


def vllm_phase(root, output):
    progress('vllm_import_start')
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest
    import vllm

    progress('vllm_import_finished')
    assert (output / 'hf.json').is_file()
    with (output / 'vllm-intent.json').open('x') as stream:
        json.dump({'at': now(), 'job_id': os.environ['SLURM_JOB_ID'], 'pid': os.getpid()}, stream)
    frozen = json.loads((output / 'frozen_inputs.json').read_text())
    assert frozen['fixture_definition_sha256'] == digest(fixtures())
    progress('vllm_model_load_start')
    llm = LLM(model=str(root / BASE), tokenizer=str(root / BASE), dtype='bfloat16',
          tensor_parallel_size=2, distributed_executor_backend='mp',
          max_model_len=65536, max_num_seqs=20, max_num_batched_tokens=8192,
          enable_chunked_prefill=True, enable_prefix_caching=False,
          gpu_memory_utilization=0.85, enforce_eager=True,
          gdn_prefill_backend='triton', moe_backend='triton',
          enable_lora=True, max_lora_rank=16, max_loras=1, max_cpu_loras=4,
          lora_dtype='bfloat16', lora_target_modules=TARGETS,
          max_logprobs=20, logprobs_mode='raw_logprobs', seed=0,
          generation_config='vllm', disable_log_stats=True)
    progress('vllm_model_loaded')
    sampling = SamplingParams(max_tokens=1, temperature=0, top_p=1, top_k=-1,
               min_p=0, repetition_penalty=1, presence_penalty=0, frequency_penalty=0,
               seed=0, logprobs=20, ignore_eos=True)
    rows = []
    for mode in ['base', 'swe249']:
        adapter = LoRARequest('diagnostic-swe249', 1, str(root / ADAPTER)) if mode == 'swe249' else None
        for item in frozen['inputs']:
            assert digest(item['prompt_token_ids']) == item['token_ids_sha256']
            result = llm.generate([{'prompt_token_ids': item['prompt_token_ids']}],
                     sampling, lora_request=adapter, use_tqdm=False)[0]
            completion = result.outputs[0]
            assert len(completion.token_ids) == 1 and completion.logprobs
            probs = completion.logprobs[0]
            ranked = sorted(probs.items(), key=lambda pair: pair[1].logprob, reverse=True)[:20]
            rows.append({'fixture_id': item['id'], 'mode': mode,
                         'history_id': item['fixture_id'], 'position': item['position'],
                         'token_ids_sha256': item['token_ids_sha256'],
                         'generated_token_id': int(completion.token_ids[0]),
                         'finish_reason': completion.finish_reason,
                         'top20': [{'token_id': int(token), 'logprob': float(prob.logprob),
                                    'token': prob.decoded_token} for token, prob in ranked]})
        progress('vllm_mode_finished', mode=mode, prefixes=len(frozen['inputs']))
    save(output / 'vllm.json', {'finished_at': now(), 'vllm': vllm.__version__,
         'raw_logprobs': True, 'prefix_caching': False, 'rows': rows,
         'scope': 'offline LLM.generate engine; bypasses OpenAI chat/tool parser to isolate numerical loading'})


def difference(left, right):
    a = {x['token_id']: x['logprob'] for x in left}
    b = {x['token_id']: x['logprob'] for x in right}
    common = sorted(a.keys() & b.keys())
    delta = [a[i] - b[i] for i in common]
    return {'top20_intersection': len(common), 'top1_equal': left[0]['token_id'] == right[0]['token_id'],
            'max_abs_logprob_on_intersection': max(map(abs, delta)) if delta else None,
            'mean_abs_logprob_on_intersection': sum(map(abs, delta)) / len(delta) if delta else None}


def compare_phase(output):
    import numpy as np
    hf = json.loads((output / 'hf.json').read_text())
    vl = json.loads((output / 'vllm.json').read_text())
    full = np.load(output / 'hf_full_logprobs.npz')
    frozen = json.loads((output / 'frozen_inputs.json').read_text())
    rows = []
    for item in frozen['inputs']:
        key = item['id']
        get = lambda source, mode: next(x for x in source['rows'] if x['fixture_id'] == key and x['mode'] == mode)
        hb, hs, vb, vs = get(hf, 'base'), get(hf, 'swe249'), get(vl, 'base'), get(vl, 'swe249')
        assert len({x['token_ids_sha256'] for x in [hb, hs, vb, vs]}) == 1
        maps = [{x['token_id']: x['logprob'] for x in row['top20']} for row in [hb, hs, vb, vs]]
        common = sorted(set.intersection(*(set(m) for m in maps)))
        residual = [(maps[1][t] - maps[0][t]) - (maps[3][t] - maps[2][t]) for t in common]
        vl_common = sorted(maps[2].keys() & maps[3].keys())
        hb_full, hs_full = full['base__' + key], full['swe249__' + key]
        residual_full_hf = [(float(hs_full[t]) - float(hb_full[t])) -
                            (maps[3][t] - maps[2][t]) for t in vl_common]
        backend_errors = {}
        for mode, full_lp, vl_map in [('base', hb_full, maps[2]), ('swe249', hs_full, maps[3])]:
            errors = [abs(float(full_lp[t]) - value) for t, value in vl_map.items()]
            backend_errors[mode] = {'tokens': len(errors),
                  'max_abs': max(errors), 'mean_abs': sum(errors) / len(errors)}
        rows.append({'fixture_id': key, 'history_id': item['fixture_id'], 'position': item['position'],
             'base_backend_drift': difference(hb['top20'], vb['top20']),
             'swe_backend_drift': difference(hs['top20'], vs['top20']),
             'hf_adapter_effect': difference(hs['top20'], hb['top20']),
             'vllm_adapter_effect': difference(vs['top20'], vb['top20']),
             'four_way_top20_intersection': len(common),
             'adapter_effect_residual_max_abs_on_intersection': max(map(abs, residual)) if residual else None,
             'vllm_top20_intersection_with_full_hf_lookup': len(vl_common),
             'adapter_effect_residual_max_abs_full_hf_lookup': max(map(abs, residual_full_hf)) if residual_full_hf else None,
             'backend_errors_at_each_vllm_top20_using_full_hf': backend_errors})
    save(output / 'comparison.json', {'finished_at': now(), 'rows': rows,
         'hf_disable_adapter_control': hf['disable_adapter_control'],
         'hf_full_vocabulary_distribution_metrics': hf['full_vocabulary_distribution_metrics'],
         'formal_evaluation': False, 'quality_or_checkpoint_selection': False,
         'numeric_pass_threshold': None,
         'limits': ['vLLM top20 omits probability tails; no full-vocabulary backend parity claim. HF entropy/KL/JS use the full vocabulary.',
                    'HF SDPA/native GDN versus vLLM FlashAttention/Triton GDN, with Base backend control.',
                    'Three short histories at two fixed positions do not reproduce long autoregressive loops or parser behavior.']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path)
    parser.add_argument('--phase', choices=['plan', 'self-test', 'hf', 'vllm', 'compare'], default='plan')
    args = parser.parse_args()
    if args.phase == 'plan':
        print(json.dumps({'fixture_ids': [x['id'] for x in fixtures()], 'fixture_sha256': digest(fixtures()),
              'positions': POSITIONS, 'prefixes': 6, 'hf_forwards': 18,
              'vllm_one_token_requests': 12, 'gpu_jobs_submitted': 0,
              'base': BASE, 'adapter': ADAPTER, 'phases': ['hf', 'vllm', 'compare']}))
        return
    if args.phase == 'self-test':
        a = [{'token_id': 1, 'logprob': -0.1}, {'token_id': 2, 'logprob': -2.0}]
        b = [{'token_id': 1, 'logprob': -0.2}, {'token_id': 3, 'logprob': -3.0}]
        assert difference(a, b)['top20_intersection'] == 1
        assert math.isclose(difference(a, b)['max_abs_logprob_on_intersection'], 0.1)
        assert len(fixtures()) == 3 and len({x['id'] for x in fixtures()}) == 3
        assert len(POSITIONS) * len(fixtures()) == 6
        assert all(x['messages'][-1]['role'] == 'tool' for x in fixtures()[1:])
        assert POSITIONS['command_start'] == '<tool_call>\n<function=bash>\n<parameter=command>\n'
        uniform, one_hot = [-math.log(2)] * 2, [0.0, -math.inf]
        identical = distribution_metrics(uniform, uniform)
        concentrated = distribution_metrics(one_hot, uniform)
        assert math.isclose(identical['base_entropy_nats'], math.log(2), abs_tol=1e-12)
        assert identical['kl_base_to_swe_nats'] == 0 and identical['js_nats'] == 0
        assert concentrated['base_entropy_nats'] == 0 and concentrated['base_top1_probability'] == 1
        assert math.isclose(concentrated['kl_base_to_swe_nats'], math.log(2), abs_tol=1e-12)
        assert math.isinf(concentrated['kl_swe_to_base_nats'])
        assert math.isclose(concentrated['js_nats'], 0.21576155433883565, abs_tol=1e-12)
        assert math.isclose(distribution_metrics(uniform, one_hot)['js_nats'], concentrated['js_nats'], abs_tol=1e-12)
        print('PASS: stdlib comparison, fixed fixtures, full entropy/KL/JS uniform/one-hot/identity/symmetry; no model imports')
        return
    assert args.output is not None
    progress('phase_start', phase=args.phase, pid=os.getpid())
    try:
        if args.phase == 'hf':
            hf_phase(args.project, args.output)
        elif args.phase == 'vllm':
            vllm_phase(args.project, args.output)
        else:
            compare_phase(args.output)
        progress('phase_finished', phase=args.phase)
    except BaseException as error:
        if args.output.exists():
            save(args.output / (args.phase + '-failed.json'), {'at': now(), 'type': type(error).__name__, 'message': str(error)[:600], 'automatic_retry': False})
        raise


if __name__ == '__main__':
    main()
