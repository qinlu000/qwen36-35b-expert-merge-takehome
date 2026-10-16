"""CMOS grader-only execution mapping; native decks, extraction and scores stay upstream."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
from unittest.mock import patch

from ai4sci_bench.core.scorer import get_scorer
from ai4sci_bench.scorers import custom
from asi_score_transport import write_json


class NgspiceRuntime:
    def __init__(self, runtime, audit):
        self.runtime, self.audit = Path(runtime).resolve(), Path(audit)
        self.receipt = json.loads((self.runtime.parent/'runtime_receipt.json').read_text())
        binary = self.runtime/'usr/bin/ngspice'
        expected=self.receipt['runtime_files']['usr/bin/ngspice']
        if hashlib.sha256(binary.read_bytes()).hexdigest()!=expected:
            raise RuntimeError('Frozen grader ngspice binary changed')
        if 'ngspice-44.2' not in self.receipt['ngspice_version']:
            raise RuntimeError('Grader needs the pinned current Debian ngspice 44.2')

    def prefix(self, work_dir):
        return ['/usr/bin/bwrap','--unshare-all','--new-session','--die-with-parent',
            '--cap-drop','ALL','--ro-bind',str(self.runtime),'/', '--proc','/proc','--dev','/dev',
            '--tmpfs','/tmp','--tmpfs','/home','--dir','/home/agent',
            '--bind',str(Path(work_dir).resolve()),'/workspace','--chdir','/workspace']

    def run(self, work_dir, netlist_name, timeout_s):
        command=self.prefix(work_dir)+['/usr/bin/ngspice','-b',netlist_name]
        env={'PATH':'/usr/bin:/bin','HOME':'/home/agent','LANG':'C.UTF-8'}
        started=time.monotonic()
        receipt={'native_command':['ngspice','-b',netlist_name], 'cwd':'/workspace',
            'timeout_seconds':timeout_s+30,'network':False,'rootfs_readonly':True,
            'only_write_mount':str(Path(work_dir).resolve()),'credentials_mounted':False,
            'gold_tree_mounted':False,'runtime_binary_sha256':self.receipt['runtime_files']['usr/bin/ngspice']}
        try:
            completed=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',
                errors='replace',timeout=timeout_s+30,env=env,stdin=subprocess.DEVNULL)
            receipt.update(returncode=completed.returncode,stdout=completed.stdout,stderr=completed.stderr)
            return completed
        except subprocess.TimeoutExpired:
            receipt['timeout']=True
            raise
        finally:
            receipt['elapsed_seconds']=time.monotonic()-started
            write_json(self.audit/(uuid.uuid4().hex+'.json'),receipt)


@contextmanager
def mapped_cmos_runtime(runtime, audit):
    """Patch only the task-local function after the official custom loader registers it."""
    original=custom.load_custom_scorer
    executor=NgspiceRuntime(runtime,audit)
    def load(task_dir):
        original(task_dir)
        if Path(task_dir).name=='cmos_opamp_design':
            namespace=type(get_scorer('cmos_opamp_spec_compliance')).score.__globals__
            namespace['_run_ngspice_in_task_image']=executor.run
    with patch.object(custom,'load_custom_scorer',load):
        yield executor
