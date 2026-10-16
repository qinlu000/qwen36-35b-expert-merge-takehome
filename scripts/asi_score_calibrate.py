#!/usr/bin/env python3
"""Paid scientific calibration on invented artifacts only; never reads formal answers."""
import argparse
import base64
from dataclasses import asdict
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch

from PIL import Image
import yaml
from ai4sci_bench.scorers import _judge_common, llm_judge, multimodal
from asi_score_transport import DeepSeekJudgeTransport, digest, write_json


CORRECT_EXTRACTION = '''import numpy as np
def extract(frequency, open_loop_gain, times, output, step_targets,
            vdd, supply_current, noise_frequency, output_noise_density, vid, vout):
    gain_db_10khz = np.interp(10000, frequency, 20*np.log10(np.abs(open_loop_gain)))
    # Gain-of-two feedback factor 0.5: crossover is |A|=2, not |A|=1.
    k = np.where(np.diff(np.abs(open_loop_gain) >= 2))[0][0]
    fc = np.interp(2, np.abs(open_loop_gain)[k:k+2][::-1], frequency[k:k+2][::-1])
    phase = np.unwrap(np.angle(open_loop_gain))*180/np.pi
    phase_margin = 180 + np.interp(fc, frequency, phase)
    settling = []
    for start, end, target in step_targets:
        use = (times >= start) & (times < end)
        t, y = times[use], output[use]
        outside = np.where(np.abs(y-target) > .001)[0]
        settling.append(t[outside[-1]+1]-start if len(outside) and outside[-1]+1 < len(t)
                        else (0 if not len(outside) else float('inf')))
    power_w = vdd * abs(supply_current)
    band = (noise_frequency >= 1e6) & (noise_frequency <= 500e6)
    noise_vrms = np.sqrt(np.trapezoid(output_noise_density[band]**2, noise_frequency[band]))
    # vid is Vip minus unity-feedback helper offset-cancel voltage Vcancel.
    valid = np.abs(np.gradient(vout, vid)) >= 500
    swing_v = np.max(vout[valid])-np.min(vout[valid])
    return gain_db_10khz, phase_margin, settling, power_w, noise_vrms, swing_v
'''
WRONG_EXTRACTION = '''def extract(*args):
    # No AC, transient, DC, noise or transfer data are read or simulated.
    # These arbitrary constants are reported as all six measured metrics.
    gain_db_10khz = phase_margin = settling = power_w = noise_vrms = swing_v = 12345
    return gain_db_10khz, phase_margin, settling, power_w, noise_vrms, swing_v
'''


def request_input_bound(messages):
    """Conservative accounting allowance for small calibration plots, not provider tokenization."""
    bound = 256
    for message in messages:
        content = message['content']
        if isinstance(content, str):
            bound += len(content.encode())
            continue
        for part in content:
            if part['type'] == 'text':
                bound += len(part['text'].encode())
            else:
                raw = base64.b64decode(part['image_url']['url'].split(',', 1)[1])
                with Image.open(io.BytesIO(raw)) as image:
                    width, height = image.size
                # Two accounting tokens per 16x16 tile, plus 256 per image.
                # A full 8192-token reservation is charged before the request.
                bound += 2*((width+15)//16)*((height+15)//16)+256
    if bound > 8192:
        raise ValueError('Synthetic request exceeds its predeclared 8192-token allowance')
    return bound


class CalibrationTransport(DeepSeekJudgeTransport):
    def __call__(self, **kwargs):
        request_input_bound(kwargs['messages'])
        kwargs['input_token_bound'] = 8192
        return super().__call__(**kwargs)


def main(args):
    root, fixture, output = args.project.resolve(), args.fixture.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True, mode=0o700); output.chmod(0o700)
    contract = {'scope': 'invented science only; no formal policy artifacts',
        'correct_min_10': 8, 'wrong_max_10': 2, 'correct_must_exceed_wrong': True,
        'cmos_thresholds': 'same thresholds after dividing the native 0-12 score by 1.2',
        'planned_calls': 14, 'hard_calls': 24, 'hard_cny': 1,
        'input_reservation_tokens_per_call': 8192, 'request_retries': 0,
        'native_rounds': {'text': 3, 'vision': 1, 'cmos_vector': 3},
        'native_output_caps': {'text': 220, 'vision': 250, 'cmos_vector': 400},
        'pricing_ceiling_usd_per_million': {'input': .3, 'output': 1.2},
        'cny_per_usd_budget_multiplier': 8, 'fixture': str(fixture),
        'correct_cmos_sha256': digest(CORRECT_EXTRACTION), 'wrong_cmos_sha256': digest(WRONG_EXTRACTION)}
    path = output/'calibration_contract.json'
    if path.exists() and json.loads(path.read_text()) != contract:
        raise RuntimeError('Frozen calibration contract changed')
    write_json(path, contract)
    settings = {'output': str(output), 'mode': 'paid', 'credentials': str(args.credentials),
        'endpoint': 'https://api.deepseek.com', 'max_generation_calls': 24, 'max_cny': 1,
        'input_token_bound': 8192, 'http_timeout': 90, 'expected_reported_model': None}
    identity_path = output/'judge_identity.json'
    if not args.discover_only:
        identity = json.loads(identity_path.read_text())
        settings['expected_reported_model'] = identity['reported_model']
        write_json(output/'frozen_judge_identity.json', identity)
    rows = {}
    for case in ('correct', 'wrong'):
        task = yaml.safe_load((fixture/'tasks/physics'/case/'task_eval.yaml').read_text())
        pred = fixture/'results'/('synthetic.'+case)/f'synthetic.{case}__seed31415__b1.outputs'
        ref = fixture/'instances'/f'synthetic.{case}__seed31415/reference'
        for kind, module, cls in [('text', llm_judge, llm_judge.LLMJudgeScorer),
                                  ('vision', multimodal, multimodal.MultimodalScorer)]:
            config = dict(task['evaluation']['scoring'][0 if kind == 'text' else 1]['config'])
            transport = CalibrationTransport(settings, f'synthetic.{case}.{kind}')
            if args.discover_only:
                scorer = cls()
                prompt = scorer._build_judge_prompt(config['rubric'], config['pred_file'],
                    (pred/config['pred_file']).read_text(), config['ref_file'],
                    (ref/config['ref_file']).read_text(), [], [])
                transport(messages=[{'role':'system', 'content':llm_judge.JUDGE_SYSTEM_PROMPT},
                                    {'role':'user', 'content':prompt}], max_tokens=config['max_tokens'])
                print(json.dumps({'discovered_identity': json.loads(identity_path.read_text())}))
                return
            config.update(api_base=settings['endpoint'], api_protocol='openai', api_key=transport.key)
            with (patch.dict(_judge_common.SUPPORTED_MODELS, {'openai/gpt-5.5':'openai/deepseek-flash'}),
                  patch.object(module, 'MAX_RETRIES', 1), patch('litellm.completion', transport)):
                native = asdict(cls().score(pred, ref, config))
            rows[f'{case}.{kind}'] = native
            write_json(output/'native_results.json', rows)
    custom_path = root/'artifacts/benchmarks/asi/tasks/electrical_engineering/cmos_opamp_design/custom_scorer.py'
    spec = importlib.util.spec_from_file_location('synthetic_cmos_calibration', custom_path)
    custom = importlib.util.module_from_spec(spec); spec.loader.exec_module(custom)
    for case, source in [('correct', CORRECT_EXTRACTION), ('wrong', WRONG_EXTRACTION)]:
        pred, ref = output/'invented_cmos'/case, output/'invented_cmos/reference'
        pred.mkdir(parents=True, exist_ok=True); ref.mkdir(parents=True, exist_ok=True)
        (pred/'simulation.py').write_text(source); (ref/'extraction_ref.py').write_text(CORRECT_EXTRACTION)
        transport = CalibrationTransport(settings, 'synthetic.'+case+'.cmos')
        with (patch.dict(_judge_common.SUPPORTED_MODELS, {'openai/gpt-5.5':'openai/deepseek-flash'}),
              patch('litellm.completion', transport)):
            rows[case+'.cmos'] = custom._call_vector_judges(pred_dir=pred, ref_dir=ref,
                pred_file='simulation.py', ref_file='extraction_ref.py', rubric=custom.EXTRACTION_VECTOR_RUBRIC,
                model='openai/gpt-5.5', num_judges=3, temperature=0, max_tokens=400,
                max_chars=10000, api_key=transport.key, api_base=settings['endpoint'], api_protocol='openai')
        write_json(output/'native_results.json', rows)
    scores = {key: value.get('median_score', value.get('details', {}).get('median_score'))
              for key, value in rows.items()}
    checks = {kind: (scores['correct.'+kind] is not None and scores['wrong.'+kind] is not None and
        scores['correct.'+kind]/(1.2 if kind=='cmos' else 1) >= 8 and
        scores['wrong.'+kind]/(1.2 if kind=='cmos' else 1) <= 2 and
        scores['correct.'+kind] > scores['wrong.'+kind]) for kind in ['text','vision','cmos']}
    ledger = [json.loads(line) for line in (output/'judge_calls.jsonl').read_text().splitlines()]
    starts, completed = ([r for r in ledger if r['event']==event] for event in ['started','completed'])
    summary = {'passed': all(checks.values()), 'semantic_checks': checks, 'native_median_scores': scores,
        'paid_generation_calls':len(starts), 'completed_calls':len(completed),
        'conservatively_reserved_cny':sum(r['reserved_cny'] for r in starts),
        'observed_usage_ceiling_cny':sum(r['observed_ceiling_cny'] for r in completed),
        'total_input_tokens':sum(r['usage']['prompt_tokens'] for r in completed),
        'total_output_tokens':sum(r['usage']['completion_tokens'] for r in completed),
        'identity':json.loads(identity_path.read_text()), 'formal_answer_calls':0}
    write_json(output/'summary.json', summary); print(json.dumps(summary))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--credentials', type=Path, required=True)
    parser.add_argument('--discover-only', action='store_true')
    main(parser.parse_args())
