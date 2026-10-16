#!/usr/bin/env python3
"""Build a grader-only pinned current official python-slim/ngspice runtime."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from pull_oci_resumable import Registry
from asi_score_transport import write_json


def main(root):
    out=root/'artifacts/asi/scoring_ngspice_20261016'
    out.mkdir(parents=True,exist_ok=True)
    index=json.loads((out/'python-3.12-slim-index.json').read_text())
    amd=next(m for m in index['manifests'] if m.get('platform')=={'architecture':'amd64','os':'linux'})
    registry=Registry(); registry.session.trust_env=False
    base='https://docker.m.daocloud.io/v2/library/python'
    r=registry.get(base+'/manifests/'+amd['digest'],headers={'Accept':amd['mediaType']},timeout=30)
    r.raise_for_status(); raw=r.content
    assert 'sha256:'+hashlib.sha256(raw).hexdigest()==amd['digest']
    manifest=json.loads(raw)
    layout=out/'oci'; blobs=layout/'blobs/sha256'; blobs.mkdir(parents=True,exist_ok=True)
    (blobs/amd['digest'].split(':')[1]).write_bytes(raw)
    for descriptor in [manifest['config']]+manifest['layers']:
        target=blobs/descriptor['digest'].split(':')[1]
        if not target.exists():
            with registry.get(base+'/blobs/'+descriptor['digest'],stream=True,timeout=(20,120)) as response:
                response.raise_for_status()
                with target.with_suffix('.tmp').open('wb') as stream:
                    for block in response.iter_content(1024*1024): stream.write(block)
            target.with_suffix('.tmp').replace(target)
        assert target.stat().st_size==descriptor['size']
        assert 'sha256:'+hashlib.sha256(target.read_bytes()).hexdigest()==descriptor['digest']
        print('verified',descriptor['digest'],descriptor['size'],flush=True)
    write_json(layout/'index.json',{'schemaVersion':2,'manifests':[amd]})
    write_json(layout/'oci-layout',{'imageLayoutVersion':'1.0.0'})
    runtime=out/'rootfs'
    env={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'APPTAINER_IGNORE_SUBUID':'1',
         'APPTAINER_TMPDIR':str(out/'tmp')}
    (out/'tmp').mkdir(exist_ok=True)
    if not (runtime/'etc/os-release').exists():
        subprocess.run([str(root/'artifacts/tools/apptainer-1.4.5/rootfs/usr/bin/apptainer'),
            'build','--sandbox',str(runtime),'oci:'+str(layout)],env=env,check=True)
    prefix=['/usr/bin/bwrap','--unshare-user','--uid','0','--gid','0','--unshare-pid',
        '--new-session','--die-with-parent','--bind',str(runtime),'/',
        '--proc','/proc','--dev','/dev','--ro-bind','/etc/resolv.conf','/etc/resolv.conf']
    # Rootless namespace only; host package database and proxy are never modified.
    subprocess.run(prefix+['/bin/sh','-ec',
        "sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g; "
        "s|https://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources; "
        "apt-get -o APT::Sandbox::User=root -o Acquire::Languages=none -o Acquire::ForceIPv4=true update; "
        "apt-get -o APT::Sandbox::User=root -o Acquire::ForceIPv4=true -o APT::Keep-Downloaded-Packages=true "
        "-o Binary::apt::APT::Keep-Downloaded-Packages=true install -y --no-install-recommends ngspice=44.2+ds-1"],
        env={'PATH':'/usr/bin:/bin','HOME':'/root','LANG':'C.UTF-8'},check=True,timeout=240)
    version=subprocess.check_output(prefix+['ngspice','--version'],text=True)
    packages=subprocess.check_output(prefix+['dpkg-query','-W','-f=${Package}\t${Version}\n'],text=True)
    # Native Dockerfile creates /workspace; the read-only runtime needs the mountpoint too.
    (runtime/'workspace').mkdir(exist_ok=True)
    receipt={'official_floating_base_resolution':amd,'python_index_sha256':hashlib.sha256((out/'python-3.12-slim-index.json').read_bytes()).hexdigest(),
        'current_resolution_not_historical_image':True,'native_dockerfile_sha256':hashlib.sha256((root/'artifacts/benchmarks/asi/tasks/electrical_engineering/cmos_opamp_design/Dockerfile.os').read_bytes()).hexdigest(),
        'ngspice_version':version,'packages':packages.splitlines(),
        'debs':{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (runtime/'var/cache/apt/archives').glob('*.deb')},
        'runtime_files':{str(p.relative_to(runtime)):hashlib.sha256(p.read_bytes()).hexdigest() for p in runtime.rglob('*') if p.is_file() and not p.is_symlink()},
        'solver_mounts':False,'private_credentials_mounted':False}
    write_json(out/'runtime_receipt.json',receipt)
    print(json.dumps({k:receipt[k] for k in ['ngspice_version','current_resolution_not_historical_image']}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1])
    main(p.parse_args().project.resolve())
