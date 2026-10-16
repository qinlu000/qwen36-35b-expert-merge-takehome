# SWE generation PATH deviation: exact audit and separate rerun plan

Update at20:04CST: the user authorized the separate experiment and clean28 production has started. Both runtime families now have the adaptation described below. See `analysis/swe_clean28_execution_20261016.md`. The original read-only audit and historical5/51 are retained below.

This is a read-only audit. No model request, task test, GPU job or original result was changed. Historical score remains5/51=9.8039215686%.

The concrete cause is the pinned Harbor Singularity server, `/data/caoqinlu/projects/apex-takehome/artifacts/benchmarks/harbor/src/harbor/environments/singularity/server.py`: line81 and line125 prepend `/usr/bin:/usr/local/bin:` to the image PATH; line127 allows a request environment override. The older `SweRuntimeEnvironment` did not restore the task image PATH on each exec. Consequently `python`/`python3` could select the Debian system interpreter before the image's prepared `/usr/local/bin` interpreter. This is separate from inference configuration and does not mean every task used managedPython3.12.

The old glibc layer also bind-mounted manageduv at `/usr/local/bin/uv` and a managedPython3.12 wrapper at `/usr/local/bin/python3.12`. It mounted the managed interpreter tree at its private absolute path and the Harbor server at `/opt/harbor-server`. The old musl layer used the same native target mounts plus its private ABI wrappers. These mounts could replace an image's same-named uv/python3.12, but direct self-test evidence establishes PATH selection as the observed cause; it does not establish that all native Python binaries were overwritten.

The corrected `SweNativeRuntimeEnvironment` obtains the original image PATH with Singularity inspect, passes it explicitly in each exec request so it overrides the server prefix, leaves `/usr/local/bin` task tools intact, and places helperuv at `/opt/apex-swe-tools/uv`. `SweBaselineNativeV2` installs mini with its private Python3.12 while its task shell inherits native PATH.

Direct original generation evidence, rather than verifier-only failures:

| Task | Original model command | Observed result | Strong control within the same old trajectory |
| --- | --- | --- | --- |
| Ansible d33bed | `python -c "import jinja2; print(jinja2.__version__)"`; `which python && python --version` | Missingjinja2; `/usr/bin/python`,3.11.2 | Explicit `/usr/local/bin/python3` importsjinja2 successfully and runs the same custom self-test to process returncode0. This is not a claim all assertions passed. |
| Ansible d62496 | `PYTHONPATH=/app/lib python -m pytest .../test_human_to_bytes.py -v` | `/usr/bin/python: No module named pytest`; subsequentpip also missing | Existing repaired replay context shows native `/usr/local/bin/python`3.11.13 withpytest/pip present. No new probe was run. |
| Ansible de5858 | `python /tmp/test_cache.py`; `python3 -c "import sys; print(sys.executable); print(sys.path)"` | Missingyaml; system `/usr/bin/python3` andPython3.11 library paths | Its own laterpip3 output reportsPyYAML already installed under `/usr/local/lib/python3.9/site-packages`, demonstrating interpreter/library mismatch. |
| Ansible e9e600, originally successful | `python -m pytest .../test_winrm.py...` | SystemPython cannot importpytest | Explicit `/usr/local/bin/python -m pytest` startspytest; it then has a separate configuration INTERNALERROR. This task ultimately resolved after fresh replay. |

Exact commands, original absolute trajectory paths and message indices are in the compact evidence JSONs. Four tasks in the 28-task cohort have direct observed Python self-test interruptions. This proves lost time/debugging opportunity, not a particular number of lost successful patches. The other 24 are not thereby proven unaffected or affected.

Selected generation provenance divides51into18oldglibc+10oldmusl+23native. The23native include17first generations plus6manual infrastructure replacements; these6must not be counted again as old candidates. Of5resolved cases,2came from the old28(Ansiblee9e600 andFlipte2bd19),3from the new23(twoOpenLibrary andoneQutebrowser). Thus old28 is not synonymous with28failures.

All old task shells traversed the different PATH ordering, but only commands whose resolution conflicts actually select another program. Python projects show direct damage; Go/Node/tool commands with no earlier conflicting executable may still resolve exactly as intended. A claim that all28were equivalently damaged is unsupported.

For a clean comparison, a separate predetermined28-ID generation experiment is prepared, including both original successes. It is not an infrastructure retry of completed answers and does not modify the historical first-valid table. The original and new experiments must both be retained; no per-task max score selection. A separate corrected51metric, if later requested, must replace the entire predetermined28cohort and retain all23native entries, not select only improvements. The10oldmusl cases still need a clean compatible runtime adaptation before any claimed launch readiness. No execution was started. See `configs/eval/swe_clean_generation28_plan_20261016.json`.

Full28taskIDs and original generation provenance:

- instance_NodeBB__NodeBB-8168c6c40707478f71b8af60300830fe554c778c-vf2cf3cbd463b7ad942381f1c6d077626485a1e9e
- instance_ansible__ansible-40ade1f84b8bb10a63576b0ac320c13f57c87d34-v6382ea168a93d80a64aab1fbd8c4f02dc5ada5bf
- instance_ansible__ansible-b748edea457a4576847a10275678127895d2f02f-v1055803c3a812189a1133297f7f5468579283f86
- instance_ansible__ansible-c1f2df47538b884a43320f53e787197793b105e8-v906c969b551b346ef54a2c0b41e04f632b7b73c2
- instance_ansible__ansible-d33bedc48fdd933b5abd65a77c081876298e2f07-v0f01c69f1e2528b935359cfe578530722bca2c59
- instance_ansible__ansible-d62496fe416623e88b90139dc7917080cb04ce70-v0f01c69f1e2528b935359cfe578530722bca2c59
- instance_ansible__ansible-d72025be751c894673ba85caa063d835a0ad3a8c-v390e508d27db7a51eece36bb6d9698b63a5b638a
- instance_ansible__ansible-de5858f48dc9e1ce9117034e0d7e76806f420ca8-v1055803c3a812189a1133297f7f5468579283f86
- instance_ansible__ansible-e9e6001263f51103e96e58ad382660df0f3d0e39-v30a923fb5c164d6cd18280c02422f75e611e8fb2
- instance_flipt-io__flipt-524f277313606f8cd29b299617d6565c01642e15
- instance_flipt-io__flipt-c1728053367c753688f114ec26e703c8fdeda125
- instance_flipt-io__flipt-c188284ff0c094a4ee281afebebd849555ebee59
- instance_flipt-io__flipt-cd18e54a0371fa222304742c6312e9ac37ea86c1
- instance_flipt-io__flipt-e2bd19dafa7166c96b082fb2a59eb54b4be0d778
- instance_future-architect__vuls-5af1a227339e46c7abf3f2815e4c636a0c01098e
- instance_future-architect__vuls-ca3f6b1dbf2cd24d1537bfda43e788443ce03a0c
- instance_future-architect__vuls-e1fab805afcfc92a2a615371d0ec1e667503c254-v264a82e2f4818e30f5a25e4da53b27ba119f62b5
- instance_future-architect__vuls-ef2be3d6ea4c0a13674aaab08b182eca4e2b9a17-v264a82e2f4818e30f5a25e4da53b27ba119f62b5
- instance_gravitational__teleport-1316e6728a3ee2fc124e2ea0cc6a02044c87a144-v626ec2a48416b10a88641359a169d99e935ff037
- instance_gravitational__teleport-2b15263e49da5625922581569834eec4838a9257-vee9b09fb20c43af7e520f57e9239bbcf46b7113d
- instance_gravitational__teleport-65438e6e44b6ce51458d09b7bb028a2797cfb0ea-vce94f93ad1030e3136852817f2423c1b3ac37bc4
- instance_gravitational__teleport-7744f72c6eb631791434b648ba41083b5f6d2278-vce94f93ad1030e3136852817f2423c1b3ac37bc4
- instance_gravitational__teleport-eda668c30d9d3b56d9c69197b120b01013611186
- instance_protonmail__webclients-08bb09914d0d37b0cd6376d4cab5b77728a43e7b
- instance_protonmail__webclients-5f0745dd6993bb1430a951c62a49807c6635cd77
- instance_protonmail__webclients-715dbd4e6999499cd2a576a532d8214f75189116
- instance_protonmail__webclients-c5a2089ca2bfe9aa1d85a664b8ad87ef843a1c9c
- instance_protonmail__webclients-e65cc5f33719e02e1c378146fb981d27bc24bdf4
