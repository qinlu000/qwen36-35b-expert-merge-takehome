"""Bind two candidate-caused native zeros to their unchanged Base result and patch."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def audit(root, official):
    source = root / 'artifacts/eval/base_swe_v2_20261016_clean28'
    rows = []
    for short, needle in [('protonmail', 'webclients-5f0745'), ('flipt', 'flipt-c188284')]:
        task = next(p.name for p in (source / 'replay').iterdir() if needle in p.name)
        result_path = source / 'replay' / task / 'result.json'
        result = json.loads(result_path.read_text())
        patch_path = source / 'generation' / task / 'agent/model.patch'
        patch = patch_path.read_bytes()
        text = patch.decode()
        native = (result.get('verifier_result') or {}).get('rewards', {}).get('reward')
        assert native == 0 and result.get('exception_info') is None
        row = {'task_id': task, 'original_result': str(result_path),
               'source_patch': str(patch_path), 'patch_bytes': len(patch),
               'source_patch_sha256': hashlib.sha256(patch).hexdigest(),
               'native_reward': native, 'audited_reward': 0, 'model_calls': 0,
               'original_result_unchanged': True, 'original_patch_unchanged': True,
               'tests_unchanged': True}
        if short == 'protonmail':
            trace = source / 'replay' / task / 'verifier/run-script-stderr.txt'
            assert 'useConfig) is not a function' in trace.read_text()
            assert "+import { useConfig } from '../../../hooks';" in text
            row.update(original_invalid_reason='empty_tests_requires_audit',
                       audit_reason='Candidate-added BitcoinInfoMessage.tsx imports useConfig from the wrong hooks module and throws before test reporting; native failure is a candidate runtime error.',
                       evidence=[str(trace), str(source / 'replay' / task / 'verifier/test-stdout.txt')],
                       candidate_added_line="import { useConfig } from '../../../hooks';",
                       runtime_error='TypeError: (0 , _hooks.useConfig) is not a function at BitcoinInfoMessage.tsx:11:35')
        else:
            prep = source / 'replay' / task / 'agent/native-go-workspace-preparation.json'
            preparation = json.loads(prep.read_text())
            assert preparation['return_code'] == 1 and 'checksum mismatch' in preparation['stdout']
            module = 'github.com/aws/aws-sdk-go-v2/service/ecr v1.30.0'
            bad_mod = 'h1:llcoVwwEApfkkMRXVjpIwazMtP3i3Sk2GZdkp3tKu2M='
            bad_zip = 'h1:Zvgqv7vu8OcMpmuwM0NXnlkqxUfMmZErUI+AbsF3XqU='
            assert '+' + module + '/go.mod ' + bad_mod in text
            assert '+' + module + ' ' + bad_zip in text
            good_mod = 'h1:WadVIk+UrTvWuAsCp6BKGX4i2snurpz8mPWhJQnS7Dg='
            good_zip = 'h1:WsWG+jupMFNpMCF3g4y1jVWbXKBsG1DyTs2tM48yuJE='
            assert module + '/go.mod ' + good_mod in official
            assert module + ' ' + good_zip in official
            row.update(original_invalid_reason='verifier_public_go_dependency_timeout',
                       audit_reason='The frozen candidate adds ECR v1.30.0 with two incorrect go.sum entries. Original native preparation fails checksum verification, and the official Go checksum database confirms that downloaded checksum. The later network timeout does not make this candidate buildable. No dependency or checksum is changed.',
                       evidence=[str(prep), str(patch_path)],
                       candidate_go_mod_sum=bad_mod, official_go_mod_sum=good_mod,
                       candidate_module_sum=bad_zip, official_module_sum=good_zip,
                       security_validation_preserved=True)
        rows.append(row)
    return {'as_of': datetime.now(timezone.utc).isoformat(),
            'scope': 'Base clean28 frozen results only', 'audits': rows,
            'canonical_scores_modified': False, 'model_calls': 0,
            'official_checksum_database': {
                'url': 'https://sum.golang.org/lookup/github.com/aws/aws-sdk-go-v2/service/ecr@v1.30.0',
                'tls_verification_preserved': True, 'response': official}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--official-checksums', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root, args.official_checksums.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
