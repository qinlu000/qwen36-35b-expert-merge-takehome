# SWE249 remaining scoring audit — 2026-10-17

Read-only review of the five gaps in the starting audited snapshot: 46/51 valid (42 native + 4 previously approved), source as of **2026-10-16 19:43:49 UTC** / **2026-10-17 03:43:49 +08**. This is an audit starting point, not a refreshed score. No model request, new scoring, container, budget change, or canonical edit was made.

| Case | Finding | Proposed disposition |
|---|---|---|
| OpenLibrary `630221ab` | Empty captured patch; native collection cannot import the task-required product module `openlibrary.core.bestbook`. Native reward 0; no Harbor exception. | Candidate failure; propose original native 0 for independent review. |
| Qutebrowser `3e21c821` | Required `KeySequence(KeyInfo(...))` input reaches unchanged product assertion at `keyutils.py:488` and fails. Applied captured patch changes four documentation/configuration files, not `keyutils.py`. Native reward 0; no Harbor exception. | Candidate failure; propose original native 0 for independent review. |
| Vuls `5af1a227` | Associated CPU-6 scope was killed by OOM at 03:28:13 +08; result ended 03:28:14 with `RemoteProtocolError`. | Keep null; resource termination confirmed, cause attribution unresolved. |
| NodeBB `8168c6c4` | Harbor verifier timeout; `reward.txt=1` exists but no `output.json` or durable run-script logs. | Keep null; successful official tests are not established. |
| Teleport `2b15263e` | Verifier timed out after 3000 seconds; no durable parsed result or test-stage logs. | Keep null; unresolved. |

## Two native-zero proposals

OpenLibrary's task explicitly requires `Bestbook.add/remove/get_awards` and `AwardConditionsError`. The original verifier's `run-script-stdout.txt` reports 0 collected items / 1 error and imports that missing product module. This is the missing deliverable required by the task; the log does not identify an external package dependency. The empty captured patch leaves the implementation absent.

Qutebrowser's task explicitly requires `KeySequence` to accept `KeyInfo`. The original official tests construct exactly that input; collection stops at the product check `assert isinstance(key, (int, Qt.KeyboardModifiers)), key` with `AssertionError: <Ctrl+Alt+y>`. The captured patch applies with return code 0, but contains only four file deletions and no functional change to `keyutils.py`. This audit does not infer who or what produced those deletions.

Both original results have `exception_info=null`, native reward 0, `reward.txt=0`, and `output.json={"tests":[]}`. The empty parsed test list caused the existing audit gap; the saved native traces establish the candidate failure. Their result, config, replay and patch identities were pinned using small-file SHA256 only. In each proposal, `original_result == accepted_result`; no replay or regenerated answer is substituted.

The two entries are **proposal only** in [proposed_audits.json](source_snapshots/swe_remaining_scoring_audit_20261017/proposed_audits.json), using the existing manifest entry fields. Root must independently approve before inclusion. The existing manifest and canonical result remain unchanged.

**Subsequent root review:** The main agent independently read both original task requirements and native error traces on host80 and confirmed the two missing required implementations described above. Both exact original native-zero entries were then approved in `configs/eval/swe249_audited_hard51_20261017.json`. The proposal file remains the historical pre-approval artifact; raw canonical results stay unchanged. The refreshed audit contains six approved native-zero entries, with three unresolved cases below still unscored. No model call or test rerun was made.

## Three unresolved cases

**Vuls.** The existing 03:05 raw snapshot associates the sole active Vuls replay with CPU 6 and `apex-baseline-fce8405d45d9.scope`. Its user journal reports an OOM kill at 2026-10-17 03:28:13 +08, immediately before the replay result's 19:28:14 UTC finish. Native Go workspace preparation had already succeeded (return code 0, 71.76 seconds), so a public dependency-download failure is not supported by these records. The journal does not identify the OOM victim; kernel messages were unavailable to the unprivileged reader. OOM does **not** automatically prove an environment fault or justify model score 0. Keep null and preserve the fixed **1 CPU / 4096 MiB** replay budget; no silent memory increase or new scoring.

**NodeBB.** The original result is `VerifierTimeoutError` after 3000 seconds, with no native verifier result. The reward file was written at 18:18:33.225447 UTC, but `test.sh` writes it through an EXIT trap based on shell exit status. Without parsed output or durable test logs, it cannot establish success or override the timeout. Saved stdout ends `Terminated`. The captured patch removes `.mocharc.yml`, including `exit:true`; the native mocha command has no explicit `--exit`. That is a lifecycle lead, not proven timeout causality; deletion provenance also remains unresolved. Keep null.

**Teleport.** Native Go preparation succeeded (return code 0, 84.24 seconds; 190 cache files copied / 37 retained), but the verifier later exceeded 3000 seconds. Saved stdout only covers resetting and applying official tests; there is no durable test result. The bounded user-journal query adds CPU-consumption evidence, not a decisive assertion or termination cause. No OOM line in that query is not proof that OOM did not occur. Keep null; do not retry without a specific, separately authorized scoring repair.

Exact task IDs, source paths, identities, and the small OOM evidence are in the [audit receipt](source_snapshots/swe_remaining_scoring_audit_20261017.json). Full machine logs and task outputs are not duplicated here.
