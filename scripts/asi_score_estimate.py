#!/usr/bin/env python3
"""No-API conservative native ASI Judge cost estimate for a frozen first-valid selection."""
import argparse
from collections import Counter
import json
from pathlib import Path

from ai4sci_bench.core.task import TaskLoader
from ai4sci_bench.scorers import _judge_common, llm_judge, multimodal
from asi_score_transport import digest, input_token_bound, write_json


def main(args):
    root = args.project.resolve()
    selection = json.loads(args.selection.read_text())
    loader = TaskLoader(root/'artifacts/benchmarks/asi/tasks')
    rows, disabled = [], []
    for entry in selection['entries']:
        condition = entry['condition']
        result = Path(entry['result'])
        task_id = condition.rsplit('__seed31415__',1)[0]
        task = loader.load_task_by_id(task_id)
        evaluation = task['evaluation']
        pred = result.parent/(result.stem+'.outputs')
        ref = args.instances/(task_id+'__seed31415')/'reference'
        for phase in ['gates','scoring']:
            for index, spec in enumerate(evaluation.get(phase, [])):
                name, config = spec['scorer'], spec.get('config',{})
                if name == 'llm_judge':
                    scorer = llm_judge.LLMJudgeScorer()
                    max_chars = config.get('max_chars',10000)
                    prompt = scorer._build_judge_prompt(config.get('rubric',llm_judge.DEFAULT_RUBRIC),
                        config.get('pred_file'), scorer._read_content(pred,config.get('pred_file'),max_chars=max_chars) or '',
                        config.get('ref_file'), scorer._read_content(ref,config.get('ref_file'),max_chars=max_chars),
                        scorer._read_named_contents(pred,config.get('extra_pred_files'),max_chars=max_chars),
                        scorer._read_named_contents(ref,config.get('extra_ref_files'),max_chars=max_chars))
                    bound = input_token_bound([{'content':llm_judge.JUDGE_SYSTEM_PROMPT},{'content':prompt}])
                    images = 0
                elif name in ['multimodal','nnls_modulus_multimodal_quality']:
                    if config.get('mode','vlm_judge') != 'vlm_judge': continue
                    images = 1+int(bool(config.get('ref_image')))
                    # Same original system/rubric/response schema; count labels conservatively.
                    bound = (1024*images + 1024 + len(multimodal.VLM_SYSTEM_PROMPT.encode()) +
                             len(config.get('rubric',multimodal.DEFAULT_VLM_RUBRIC).encode()))
                elif name == 'cmos_opamp_netlist_strict_gate':
                    if not config.get('strict_netlist_gate',{}).get('code_only'):
                        raise ValueError('Unestimated custom netlist Judge branch')
                    disabled.append({'condition':condition,'phase':phase,'scorer':name,'reason':'native code_only=true'})
                    continue
                elif name in ['cmos_opamp_spec_compliance','cmos_opamp_testbench_judge']:
                    if config.get('testbench_judge',{}).get('agent') != 'grounded':
                        raise ValueError('Unestimated custom CMOS vector Judge branch')
                    disabled.append({'condition':condition,'phase':phase,'scorer':name,'reason':'native grounded ngspice; no API'})
                    continue
                else:
                    continue
                judges, cap = config.get('num_judges',1), config.get('max_tokens',1024)
                cost = (bound*.3+cap*1.2)/1e6*8
                rows.append({'condition':condition,'task_id':task_id,'phase':phase,'index':index,
                    'scorer':name,'num_judges':judges,'max_tokens':cap,'input_token_upper_bound':bound,
                    'image_count_per_call':images,'per_call_ceiling_cny':cost,
                    'native_no_retry_ceiling_cny':judges*cost,
                    'native_all_retries_ceiling_cny':judges*_judge_common.MAX_RETRIES*cost})
    calls = sum(r['num_judges'] for r in rows)
    cost = sum(r['native_no_retry_ceiling_cny'] for r in rows)
    worst = sum(r['native_all_retries_ceiling_cny'] for r in rows)
    report = {'scope':'No API; upper bound assumes every configured Judge is reached regardless of gates/files',
        'expected_conditions':240,'selected_conditions':len(selection['entries']),
        'selection_sha256':digest(selection),'selection_sources':dict(Counter(e['status'] for e in selection['entries'])),
        'prepared_report':str(args.prepared_report),
        'native_judge_rounds':calls,'native_MAX_RETRIES':_judge_common.MAX_RETRIES,
        'all_native_retries_generation_cap':calls*_judge_common.MAX_RETRIES,
        'native_output_caps_counts':dict(Counter({str(cap):sum(r['num_judges'] for r in rows if r['max_tokens']==cap)
            for cap in sorted({r['max_tokens'] for r in rows})})),
        'native_no_retry_input_upper_bound':sum(r['num_judges']*r['input_token_upper_bound'] for r in rows),
        'native_no_retry_output_upper_bound':sum(r['num_judges']*r['max_tokens'] for r in rows),
        'native_no_retry_image_exposures':sum(r['num_judges']*r['image_count_per_call'] for r in rows),
        'native_no_retry_ceiling_cny':cost,'all_native_retries_ceiling_cny':worst,
        'other_data_cost_cny':6.896572704,'calibration_conservative_reserved_cny':.3157632,
        'night_total_cny':30,'night_remaining_before_formal_cny':30-6.896572704-.3157632,
        'entire_formal_worst_case_fits_night_budget':worst<=30-6.896572704-.3157632,
        'suggested_runtime_max_cny':round(worst+.01,2),
        'pricing':{'input_usd_per_million':.3,'output_usd_per_million':1.2,'cny_per_usd_budget_multiplier':8},
        'input_bound':'UTF-8 bytes plus framing; 1024 tokens per image upper bound; native text truncation retained',
        'vision_token_source':'https://api-docs.deepseek.com/guides/vision/',
        'disabled_custom_api_branches':disabled,'judge_contracts':rows,'paid_calls':0}
    prepared=json.loads(args.prepared_report.read_text())
    if prepared['prepared_instance_count']!=240 or prepared['scorer_error_count']!=0:
        raise ValueError('Full frozen preparation is not clean')
    write_json(args.output,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['judge_contracts','disabled_custom_api_branches']}))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--instances',type=Path,required=True)
    p.add_argument('--prepared-report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    main(p.parse_args())
