#!/usr/bin/env python3
"""Stage the five fixed adapters; publishing requires explicit --mode publish."""
import argparse
from datetime import datetime, timezone
import filecmp
import json
import os
from pathlib import Path
import re
import shutil
import struct

os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
from huggingface_hub import HfApi, ModelCard, hf_hub_download
from huggingface_hub.errors import RepositoryNotFoundError
from huggingface_hub.utils import logging as hf_logging
hf_logging.set_verbosity_error()


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def header(path):
    with path.open('rb') as handle:
        size = struct.unpack('<Q', handle.read(8))[0]
        return json.loads(handle.read(size))


def public_card(text, repository=None):
    text = re.sub(r'^Intended Hugging Face repository:.*\n', '', text, flags=re.M)
    if repository:
        text = re.sub(r'^Model repository:.*\n', '', text, flags=re.M)
    text = text.replace('This is an unpublished model-card draft for a PEFT adapter, not a full base-weight release.',
                        'This repository contains a PEFT LoRA adapter; full base weights are not included.')
    text = text.replace('This unpublished draft describes', 'This repository contains')
    text = text.replace('No new task-level validation run is required by this release draft.',
                        'Frozen checkpoint choices were used; no new task-level validation benchmark selected this release.')
    if re.search(r'\bdraft\b|\bunpublished\b|pending creation', text, re.I):
        raise ValueError('Artifact publication placeholders remain in model card')
    if repository:
        text += f'\nModel repository: [{repository}](https://huggingface.co/{repository}).\n'
    return text


def prepare(root, manifest, release):
    allowlist = manifest['required_public_files']
    prepared = []
    for item in manifest['artifacts']:
        source = root / item['local_source_adapter']
        stage = release / 'stage' / item['name']
        stage.mkdir(parents=True, exist_ok=True)
        weight = source / 'adapter_model.safetensors'
        assert weight.stat().st_size == item['weights_bytes']
        destination = stage / 'adapter_model.safetensors'
        if not destination.exists():
            shutil.copyfile(weight, destination)
        assert filecmp.cmp(weight, destination, shallow=False), 'Staged weight differs from frozen source'
        original = json.loads((source / 'adapter_config.json').read_text())
        config = dict(original, **manifest['adapter_config_release_overrides'])
        assert config['r'] == item['rank'] and config['lora_alpha'] == item['alpha']
        save(stage / 'adapter_config.json', config)
        (stage / 'README.md').write_text(public_card((root / item['card']).read_text()))
        shutil.copyfile(root / manifest['license_source'], stage / 'LICENSE')
        shutil.copyfile(root / item['notice'], stage / 'NOTICE.md')
        (stage / 'licenses').mkdir(exist_ok=True)
        shutil.copyfile(root / manifest['standard_apache_text'], stage / 'licenses/APACHE-2.0.txt')
        assert sorted(str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()) == sorted(allowlist)
        ModelCard((stage / 'README.md').read_text())
        for filename in ('README.md', 'adapter_config.json', 'LICENSE', 'NOTICE.md'):
            text = (stage / filename).read_text()
            assert not re.search(r'/Users/|/data/(?:user|caoqinlu)/|/home/|hf_[A-Za-z0-9]{18,}', text)
        tensor_header = header(weight)
        tensors = [value for key, value in tensor_header.items() if key != '__metadata__']
        assert len(tensors) == 620 and all(value['dtype'] == 'F32' for value in tensors)
        prepared.append({'name': item['name'], 'source_adapter': item['local_source_adapter'],
            'stage': str(stage.relative_to(root)), 'required_public_files': allowlist,
            'file_bytes': {name: (stage / name).stat().st_size for name in allowlist},
            'source_weights_unchanged_stream_compare': True, 'tensors': len(tensors),
            'source_config_changed': False,
            'release_config_overrides': manifest['adapter_config_release_overrides']})
    save(release / 'prepare_receipt.json', {'state': 'prepared', 'at_utc': now(), 'artifacts': prepared})
    return prepared


def model_info_or_none(api, repository):
    try:
        return api.model_info(repository, files_metadata=True)
    except RepositoryNotFoundError:
        return None


def publish(root, manifest, release, token_file):
    token = token_file.read_text().strip()
    api = HfApi(token=token)
    identity = api.whoami()
    assert identity['name'] == 'csminion'
    assert identity.get('auth', {}).get('accessToken', {}).get('role') == 'write'
    receipt_path = release / 'publication_receipt.json'
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {
        'state': 'publishing', 'username': 'csminion', 'token_role': 'write',
        'authentication_at_utc': now(), 'artifacts': []}
    public_receipt = root / 'analysis/source_snapshots/hf_publication_20261017.json'
    def checkpoint():
        receipt['updated_at_utc'] = now()
        save(receipt_path, receipt)
        save(public_receipt, receipt)
    for item in manifest['artifacts']:
        known = next((value for value in receipt['artifacts'] if value['name'] == item['name']), None)
        stage = release / 'stage' / item['name']
        if known and known.get('state') == 'verified':
            continue
        if known:
            repository = known['repository']
            assert model_info_or_none(api, repository) is not None
        else:
            repository = item['planned_hf_repository']
            if model_info_or_none(api, repository) is not None:
                repository += '-20261017'
                if model_info_or_none(api, repository) is not None:
                    raise RuntimeError('Both intended and dated HF names exist outside this publication receipt')
            api.create_repo(repository, repo_type='model', private=False, exist_ok=False)
            known = {'name': item['name'], 'repository': repository,
                'url': 'https://huggingface.co/' + repository, 'state': 'created',
                'created_at_utc': now(), 'requested_repository': item['planned_hf_repository']}
            receipt['artifacts'].append(known)
            checkpoint()
        source_card = public_card((root / item['card']).read_text(), repository)
        (stage / 'README.md').write_text(source_card)
        if known.get('state') != 'uploaded':
            commit = api.upload_folder(repo_id=repository, repo_type='model', folder_path=str(stage),
                allow_patterns=manifest['required_public_files'],
                commit_message='Publish fixed Qwen3.6 adapter and reproducibility documentation')
            known.update(state='uploaded', revision=commit.oid, uploaded_at_utc=now())
            checkpoint()
        revision = known['revision']
        public = HfApi(token=False).model_info(repository, revision=revision, files_metadata=True)
        assert not public.private and public.gated in (False, None)
        remote_names = {sibling.rfilename for sibling in public.siblings}
        assert set(manifest['required_public_files']) <= remote_names
        assert remote_names <= set(manifest['required_public_files']) | {'.gitattributes'}
        verify = release / 'anonymous' / item['name']
        checked = []
        for filename in manifest['required_public_files']:
            downloaded = Path(hf_hub_download(repo_id=repository, repo_type='model', filename=filename,
                revision=revision, token=False, local_dir=str(verify), force_download=True))
            staged = stage / filename
            assert downloaded.stat().st_size == staged.stat().st_size
            assert filecmp.cmp(downloaded, staged, shallow=False), 'Anonymous bytes differ from staged release'
            checked.append({'file': filename, 'bytes': downloaded.stat().st_size, 'stream_compare': True})
        weight = root / item['local_source_adapter'] / 'adapter_model.safetensors'
        assert filecmp.cmp(weight, verify / 'adapter_model.safetensors', shallow=False)
        assert header(weight) == header(verify / 'adapter_model.safetensors')
        config = json.loads((verify / 'adapter_config.json').read_text())
        assert config['base_model_name_or_path'] == manifest['base_model']
        assert config['revision'] == manifest['base_revision']
        known.update(state='verified', public=True, gated=False, anonymous_token=False,
            verified_at_utc=now(), files=checked, safetensors_header_equal=True,
            source_weight_stream_compare=True, additional_manual_hash_pass=False)
        item.update(publication_state='published_verified', hf_repository=repository,
                    hf_url=known['url'], hf_revision=revision)
        (root / item['card']).write_text(source_card)
        save(root / 'models/release_manifest.json', manifest)
        checkpoint()
        print(json.dumps({'artifact': item['name'], 'state': 'public_anonymous_verified',
                          'repository': repository, 'revision': revision}), flush=True)
    receipt['state'] = 'all_five_public_anonymous_verified'
    manifest['status'] = 'published_public_anonymous_verified'
    save(root / 'models/release_manifest.json', manifest)
    checkpoint()
    readme = root / 'models/README.md'
    text = readme.read_text()
    text = text.replace('These are unpublished model-card drafts and a release manifest',
                        'These are the published model cards and verified release manifest')
    text = text.replace('Intended HF ID, pending creation', 'Published HF repository')
    for item in manifest['artifacts']:
        text = text.replace('`' + item['planned_hf_repository'] + '`',
                            '[' + item['hf_repository'] + '](' + item['hf_url'] + ')')
    text = text.replace('No repository URL or published commit is claimed.',
                        'The five public model repositories below were read back anonymously at their immutable commits.')
    text = text.replace('Until then, these IDs remain plans.', 'The verified publication receipt records the actual IDs and commits.')
    text = text.replace('This drafting task created no remote repositories and uploaded no artifacts.',
                        'The authorized publishing step created and verified the five public model repositories below.')
    text = text.split('\n## Verified public revisions\n', 1)[0]
    text += '\n## Verified public revisions\n\n| Model | Immutable HF revision |\n| --- | --- |\n'
    for item in manifest['artifacts']:
        text += f"| [{item['hf_repository']}]({item['hf_url']}) | `{item['hf_revision']}` |\n"
    text += '\nEach of the six release files was downloaded in full with `token=False` at the recorded revision. Sizes and streaming byte comparisons matched; safetensors headers and source weight bytes matched. Repositories are public and ungated. No additional manual large-file hash pass or model generation was run; normal Hub transfer integrity checks remain part of the SDK.\n'
    readme.write_text(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--mode', choices=['prepare', 'publish'], default='prepare')
    args = parser.parse_args()
    root = args.project.resolve()
    manifest = json.loads((root / 'models/release_manifest.json').read_text())
    release = root / 'artifacts/releases/hf_five_models_20261017'
    release.mkdir(parents=True, exist_ok=True)
    prepare(root, manifest, release)
    if args.mode == 'publish':
        publish(root, manifest, release, root / 'artifacts/private/hf_token')
    else:
        print(json.dumps({'state': 'prepared_only', 'artifacts': 5, 'network_calls': 0}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not echo SDK exceptions containing request credentials or signed URLs.
        print(json.dumps({'state': 'failed', 'error_type': type(error).__name__,
            'http_status': getattr(getattr(error, 'response', None), 'status_code', None)}), flush=True)
        raise SystemExit(1)
