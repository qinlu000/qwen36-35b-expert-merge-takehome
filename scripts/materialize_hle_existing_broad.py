"""Reproduce the manually reviewed broad HLE candidates from existing caches.

No downloads or model API calls. The allowlist freezes the 2026-10-16 review,
including domain overrides; it does not rescreen sources with keyword rules.
Original screening helpers are retained in the broad artifact cache. The final
2k mixture independently takes 98 of these 100 candidates (87 engineering).

Example on 80:
  artifacts/envs/hle/bin/python scripts/materialize_hle_existing_broad.py

Lengths are checked by the final shared export, using the base tokenizer.
This script never truncates questions or final responses.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re

from candidate_selection import text_hash
from prepare_night_hle_proxy import HLE_REV, ngrams


V4_SOURCE = 'trjxter/DeepSeek-V4-Pro-Reasoning-8000x'
V4_REVISION = '7329257a28babc5998be072a3d8add1dd8ad0fda'
GLM_SOURCE = 'Jackrong/GLM-5.1-Reasoning-1M-Cleaned'
GLM_REVISION = 'f6d6ccafe40359d5ec2515ee25e92aac8cae9c3d'
CACHE = 'artifacts/data/candidates/hle_existing_2k_20261016/broad'
GLM_RANGE_STARTS = (0, 1_000_000_000, 4_000_000_000, 8_000_000_000)

# Stable upstream IDs, rather than transient row numbers, preserve manual review.
SELECTED_TASK_IDS = {'v4:deepseek_v4_pro_row_phd_science_716af91a621f243c': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_76a90ba9dfd152d2': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_f1ac42f67d470741': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_27656f695f0446a1': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_eb7a7ec33619f7b7': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_c51ca96e9eb3efee': 'Engineering',
 'v4:deepseek_v4_pro_row_main_5cb9e8e4defb8b8f': 'Engineering',
 'v4:deepseek_v4_pro_row_main_1f2da9cb199529cb': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_f59ed6955ab81b88': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_f200c10524535022': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_3064fbff25028d76': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_7c49823f4cc76da8': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_49893dc53c42e870': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_4d76e9220a2d76ba': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_936bd09efff254f2': 'Engineering',
 'v4:deepseek_v4_pro_row_main_503c769882cac0e6': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_52fe4d5f62a06533': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_3a98a6f4391598e0': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_ba15751824dea6a1': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_614fd4a4241bbf15': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_51089b3d722a922b': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_514975c02c25e1c7': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_2f971c3b21d03e12': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_cc184a16bc28db2f': 'Engineering',
 'v4:deepseek_v4_pro_row_main_1cf8c22643779e4f': 'Humanities/Social Science',
 'v4:deepseek_v4_pro_row_phd_science_4f4c24bfd721e00c': 'Engineering',
 'v4:deepseek_v4_pro_row_main_362a4ab491e977d9': 'Engineering',
 'v4:deepseek_v4_pro_row_main_6b6cecd23e30ef72': 'Engineering',
 'v4:deepseek_v4_pro_row_main_eb5362a301fd004c': 'Humanities/Social Science',
 'v4:deepseek_v4_pro_row_phd_science_21829547f3e69db4': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_6412f78a36997213': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_d0df0282c2f6c105': 'Engineering',
 'v4:deepseek_v4_pro_row_main_8ef1d2553d0af094': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_8d5e8f0d0bbac52b': 'Engineering',
 'v4:deepseek_v4_pro_row_main_f87a1c4bf95c27ac': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_c6db9815a5361301': 'Engineering',
 'v4:deepseek_v4_pro_row_main_46e3cf0f72f00488': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_eb577ca6418cec6a': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_59cbdd0dbef824fa': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_4fd75422ab472773': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_6ad9bfc58fba7371': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_ef487bde1666666a': 'Engineering',
 'v4:deepseek_v4_pro_row_main_dcfbf1091376cc1a': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_ff1052c0c49047e6': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_4801bc69e9b0e818': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_819f632742e5b5ea': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_1e6bac88bde5126e': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_9a9ae4d821852c0a': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_5bf09c77216c934d': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_fd53d4f06246fc1d': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_04728907f4d1a56f': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_7eb6758545dd40f0': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_6fe1fc7a60592440': 'Engineering',
 'v4:deepseek_v4_pro_row_main_e66155ed01dbd956': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_214b72a9c7567a07': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_844e5ef32fe5b384': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_6d0dbc01b0713bc4': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_bf8a46439154bee5': 'Engineering',
 'v4:deepseek_v4_pro_row_main_49925d68908728fc': 'Humanities/Social Science',
 'v4:deepseek_v4_pro_row_phd_science_c49b1f872e0e53b1': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_664ba6054b7a121b': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_c0d5fa91c437099c': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_0fa7485fc81710b6': 'Engineering',
 'v4:deepseek_v4_pro_row_main_8b815661879ffbca': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_0a0c2030aaeee7f5': 'Engineering',
 'v4:deepseek_v4_pro_row_main_b4133c499e691f10': 'Humanities/Social Science',
 'v4:deepseek_v4_pro_row_main_26055b2a3bf64280': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_f56f2de2e80328e5': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_dbfd991d17d8bc0e': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_3999df27f9e3b8c0': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_e71ad1b679b2f533': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_f4ff0120675b3ba3': 'Engineering',
 'v4:deepseek_v4_pro_row_main_3770a317cfdeb920': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_fd794e8130acdbfd': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_c90ac55f4f9506b5': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_0b68b2c991cc0c31': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_49d7b7f27b2158d0': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_fba8dafc3a94fa3b': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_b355fa0c5ecb4b16': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_cbc8caaa7c51eb43': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_45a1337788880d0f': 'Engineering',
 'v4:deepseek_v4_pro_row_phd_science_90ff2a80c932c5bf': 'Engineering',
 'glm:063cd76307d6c4642cf5775e94beaa0d': 'Humanities/Social Science',
 'glm:1f9886f2efaf0bd04cd6d752c3b41d23': 'Engineering',
 'glm:757aa60fa2e0e50eebc60e2389543aaf': 'Engineering',
 'glm:c4747671989353ae92c81e194440134a': 'Engineering',
 'glm:eb76ad9ba8fe8f53e9aaf59ded0d3458': 'Engineering',
 'glm:9ae94096a366cc923909915e5224b562': 'Engineering',
 'glm:073dd33d83ff15305977263f9ef6ecb6': 'Engineering',
 'glm:02d4f254201162c54e243924a1081a9f': 'Engineering',
 'glm:7152dbbc88207a39f0794c4311d23d49': 'Humanities/Social Science',
 'glm:bfc83bd95f7f1daba8e5eae7aad426ae': 'Engineering',
 'glm:01a9e4513f564d30b260ab0a7c0080df': 'Humanities/Social Science',
 'glm:db6d23db2fc838cbcf4a6483fe79d460': 'Engineering',
 'glm:ebf578bc6239ab2d27917822a1eb9751': 'Engineering',
 'glm:9f9901c78590caadf652fbe95b19088c': 'Humanities/Social Science',
 'glm:a4179de5a565098ab2767244fed19dd8': 'Humanities/Social Science',
 'glm:0fda38375341bee08c0ffb2c70b48d0d': 'Humanities/Social Science',
 'glm:561a27663194506506041214ef56a8dc': 'Humanities/Social Science',
 'glm:abbb1d429d136135486d2c3ab13b120f': 'Engineering'}

# Rejected after prompt review. Other keyword hits were not selected.
MANUAL_REJECTIONS = {'v4:deepseek_v4_pro_row_main_3047a2893e7e3471': 'missing image',
 'v4:deepseek_v4_pro_row_main_75420bca5d1d07c5': 'missing circuit diagram',
 'v4:deepseek_v4_pro_row_main_a1984f119bdccb52': 'missing numeric parameters',
 'v4:deepseek_v4_pro_row_phd_science_587cb50a8da14493': 'pure theoretical physics',
 'v4:deepseek_v4_pro_row_main_486ff089854b4bed': 'personal project ideation',
 'v4:deepseek_v4_pro_row_phd_science_ba5ea4d7f5f95555': 'unsupported speculative premise combining PT quantum '
                                                        'field theory and batteries',
 'v4:deepseek_v4_pro_row_phd_science_2c1463be7b802b6c': 'near duplicate of grain-boundary creep question 100',
 'v4:deepseek_v4_pro_row_phd_science_046a55b92b556340': 'near duplicate of SEI spectroscopy question 83',
 'v4:deepseek_v4_pro_row_phd_science_a2031ec35994123f': 'near duplicate of Majorana architecture question 41',
 'v4:deepseek_v4_pro_row_main_01f5b548250693f8': 'question relies on linked prior discussion',
 'v4:deepseek_v4_pro_row_main_0bb960856dc3a3ba': 'elementary substituted resistor arithmetic',
 'v4:deepseek_v4_pro_row_phd_science_315620ab76fc1ef3': 'near duplicate of grain-boundary dislocation question '
                                                        '10',
 'v4:deepseek_v4_pro_row_phd_science_d5617500db0ef0d4': 'near duplicate of superconducting code/noise question '
                                                        '148',
 'v4:deepseek_v4_pro_row_phd_science_ef9b19c5734ac792': 'near duplicate of grain-boundary dislocation question '
                                                        '10',
 'v4:deepseek_v4_pro_row_main_8f6b0a38e8f193e5': 'unfinished measurement context',
 'v4:deepseek_v4_pro_row_main_7f973c5187e0237d': 'pure theoretical physics',
 'v4:deepseek_v4_pro_row_main_7b3e52e9177f5ab4': 'missing SET diagram',
 'glm:1cc797bdf8a2fb4d23d919c83a266266': 'elementary substituted resistor arithmetic',
 'glm:4a8485dbad2f19349fc5a626f88a3072': 'basic potential convention, physics',
 'glm:c1fa89eb26a3c14a0d1edd62bc2c2a6a': 'elementary substituted resistor arithmetic',
 'glm:d7f3ab0093a98084297d04c259e6b5ef': 'high-school elementary circuit explanation',
 'glm:91354c96084e6983bddaad6c5298236d': 'missing video evidence'}


def write_rows(path, records):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output-dir', type=Path,
                        help='Default: broad/reproduced; leaves the active candidate export untouched.')
    args = parser.parse_args()
    root = args.repo
    cache = root / CACHE
    out = args.output_dir or cache / 'reproduced'
    out.mkdir(parents=True, exist_ok=True)
    assert not set(SELECTED_TASK_IDS) & set(MANUAL_REJECTIONS)

    # Only questions are used from formal HLE and the frozen proxy validation.
    import pyarrow.parquet as pq
    formal = pq.read_table(root / 'artifacts/benchmarks/hle' / HLE_REV /
                           'test-00000-of-00001.parquet', columns=['question']).to_pylist()
    val = [json.loads(line) for line in
           (root / 'artifacts/data/candidates/night_hle_20261016/proxy_val_100.jsonl').open()]
    questions = [r['question'] for r in formal] + [r['question'] for r in val]
    banned = {text_hash(q) for q in questions}
    banned_grams = set().union(*(ngrams(q) for q in questions))

    sources = [(cache / 'v4pro8k.raw.jsonl', True)] + [
        (cache / f'glm51_main_range_{start}.jsonl', False) for start in GLM_RANGE_STARTS]
    found, accepted, rejected, seen = set(), [], [], set()
    for path, is_v4 in sources:
        for line in path.open():
            raw = json.loads(line)
            task_id = ('v4:' if is_v4 else 'glm:') + raw['id']
            if task_id not in SELECTED_TASK_IDS or task_id in found:
                continue
            found.add(task_id)
            teacher = 'DeepSeek-V4-Pro' if is_v4 else 'GLM-5.1'
            assert raw['meta']['teacher_model'] == teacher
            assert raw['meta'].get('finish_reason', 'stop') == 'stop'
            assert 'final_content_may_be_truncated' not in str(raw['meta'].get('warnings', ''))
            question = raw['input'].strip()
            final = re.sub(r'^\s*<think>.*?</think>\s*', '', raw['output'], flags=re.S).strip()
            assert question and final and '<think>' not in final and '</think>' not in final
            h = text_hash(question)
            reason = None
            if h in seen:
                reason = 'duplicate_normalized_question'
            elif h in banned or ngrams(question) & banned_grams:
                reason = 'formal_hle_or_frozen_val_exact_or_13gram'
            seen.add(h)
            if reason:
                rejected.append({'task_id': task_id, 'reason': reason})
                continue
            domain = SELECTED_TASK_IDS[task_id]
            dataset = V4_SOURCE if is_v4 else GLM_SOURCE
            accepted.append({'task_id': task_id, 'domain': domain, 'source_id': raw['id'],
                'teacher': teacher,
                'messages': [{'role': 'user', 'content': question},
                             {'role': 'assistant', 'content': final}],
                'source_meta': {'source': dataset, 'source_dataset': dataset,
                    'revision': V4_REVISION if is_v4 else GLM_REVISION,
                    'domain': domain, 'original_domain': raw.get('domain'),
                    'source_file': 'train.jsonl' if is_v4 else 'main.jsonl',
                    'source_byte_range': raw.get('source_byte_range'),
                    'original_metadata': raw['meta'], 'teacher': teacher,
                    'teacher_mode': 'not_disclosed', 'hidden_reasoning_removed': True,
                    'final_preserved_complete': True,
                    'answer_evidence': 'publisher_teacher_response_no_independent_gold',
                    'source_prompt_provenance': 'GLM5.1 cleaned -> clzoro GLM5.1 -> ianncity KimiK2.5 -> unspecified modified Datagen prompts',
                    'category_assignment': 'frozen researcher prompt review allowlist',
                    'license': 'Apache-2.0 publisher card', 'family_key': 'qa:' + h,
                    'formal_hle_columns_read': ['question'], 'frozen_val_rows': len(val),
                    'overlap_check': 'existing exact normalized question + 13gram policy; gold not used',
                    'token_limits_pending_root': True}})
    assert found == set(SELECTED_TASK_IDS), sorted(set(SELECTED_TASK_IDS) - found)
    write_rows(out / 'candidates.jsonl', accepted)
    write_rows(out / 'overlap_rejections.jsonl', rejected)
    summary = {'rows': len(accepted), 'domains': dict(Counter(r['domain'] for r in accepted)),
        'teachers': dict(Counter(r['teacher'] for r in accepted)),
        'selected_upstream_ids': len(SELECTED_TASK_IDS), 'manual_rejections': len(MANUAL_REJECTIONS),
        'formal_question_rows': len(formal), 'frozen_val_rows': len(val),
        'formal_columns_read': ['question'], 'rejected': dict(Counter(r['reason'] for r in rejected)),
        'sequence_limit': 65536, 'assistant_limit': 8192,
        'token_validation': 'final shared export; no truncation',
        'source_uniqueness': 'normalized question unique; original semantic families incomplete',
        'new_downloads': False, 'new_teacher_api': False}
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
