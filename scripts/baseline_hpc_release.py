"""Forced SSH command: status/release only for this workflow's three GPU jobs."""
import json
import os
import shlex
import subprocess
import sys

ALLOWED_JOBS = {'725539', '725545', '725561'}
request = shlex.split(os.environ.get('SSH_ORIGINAL_COMMAND', ''))
if len(request) != 2 or request[0] not in {'status', 'release'} or request[1] not in ALLOWED_JOBS:
    sys.exit('Only this workflow\'s fixed GPU status/release requests are allowed')
action, job = request
if action == 'status':
    result = subprocess.run(['squeue', '-h', '-j', job, '-o', '%i %u %j %T'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    print(json.dumps({'job_id': job, 'status': result.stdout.strip(), 'returncode': result.returncode}))
else:
    status = subprocess.run(['squeue', '-h', '-j', job, '-o', '%i'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if not status.stdout.strip():
        print(json.dumps({'job_id': job, 'released': True, 'already_finished': True}))
        sys.exit(0)
    result = subprocess.run(['scancel', job], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    print(json.dumps({'job_id': job, 'released': result.returncode == 0,
                      'returncode': result.returncode, 'error': result.stderr.strip()}))
    sys.exit(result.returncode)
