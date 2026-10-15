# ASI baseline v2 implementation and acceptance

Current production status: infrastructure incident; the first formal attempt has ended, no controller/worker/ASI scope remains. Original acceptance below passed before launch. Do not restart this run automatically. Final10/10 synthetic checks, actual native scientific Base generation/execution, and live cancellation acceptance all passed. At incident audit, 240 conditions were admitted and240 failed results were saved; three responses were preserved, eight generation transports were ambiguous, and229 failed before any generation. No Judge request has run.

The runner inherits the fixed official DirectLLMAdapter solve, default system prompt, prompt.md input, code-block selection, single program execution, and declared output collection. Its only hooks are model transport/deadline and isolated execution. `run_asi_baseline_v2.py` fixes the full seed31415 open scope at 60 tasks × b1–b4 = 240 conditions; produce-only results are explicitly unscored.

Explicit per-request settings are 65536 context, 8192 output, temperature 0.7, top_p 0.8, top_k 20, min_p 0, presence_penalty 0, repetition_penalty 1, seed 0, thinking=false, preserve_thinking=false. Native messages are counted by the same serving endpoint's /tokenize, including its generation prompt. Generation usage must agree with the guard. A prompt above 57344 fails without generation; no truncation or repaired second answer is added.

A single 1200-second monotonic deadline covers guard, connection, generation, extraction/write, and execution. SIGALRM supplies a total bound in addition to HTTP/subprocess timeouts. There is one HTTP retry layer: at most two ConnectError/ConnectTimeout attempts known to have failed before sending; read timeout, response disconnect, 429, provider errors and length results do not trigger another answer. Program execution receives only the remaining time. Forced scope cleanup is outside the generation/execution budget and retains failure evidence.

The 80 host's user systemd manager delegates memory/pids, but not CPU/cpuset: CPUQuota and AllowedCPUs silently create no actual cpu.max/cpuset constraint. The execution helper therefore verifies actual memory.max=8589934592 and memory.swap.max=0, fixes inherited affinity to four available CPUs, and applies a bwrap seccomp filter returning EPERM for sched_setaffinity. Generated programs and their children cannot widen that set. The existing bwrap mount/network boundary and clean environment remain in use; controller keys, project source/reference tree and model sockets are absent from the program namespace. No GPU device is mounted.

The runner saves a start journal before a condition is admitted. Completed failures are retained. If a previous attempt was interrupted, resume saves a failed condition without a new model request and preserves the previous workspace and partial artifacts. Native result and artifact persistence are retained. A missing/invalid JSON result is never silently regenerated. There are up to eight admitted conditions per dedicated TP2 service (default8; CLI --parallel1..8). A spawn process pool owns independent adapters, request/deadline state, and native orchestrators. Each worker has a distinct four-CPU set; --cpu-offset reserves separate host regions from Terminal/SWE. Only already cached runtimes are used; dependency installation is never run concurrently. The entire submission order follows the fixed manifest then b1,b2,b3,b4. Server queuing shares each condition's wall clock after admission.

## Evidence

- Synthetic HTTP server plus real task runtimes: final10/10 checks passed on 80, including the production condition_worker in eight processes with peak8 live memory scopes and disjoint four-CPU sets, length-response persistence and conservative resume, receipt `analysis/source_snapshots/baseline_asi_v2_smoke_20261016.json` (remote `artifacts/preflight/asi/baseline-v2-oz67cltc/summary.json`).
- Three real cached environment groups: NumPy/SciPy/SymPy/Matplotlib and ngspice divider 0.5V; pandas/sklearn regression; PyTorch CPU matrix multiplication. Each preserved native extraction/collector and had one generation/one execution.
- All science processes and child processes saw four CPUs; attempts to widen affinity returned EPERM. The helper read back actual 8GiB memory and zero swap limits.
- A 4-second shared deadline, including a 1-second fake generation delay, stopped execution at 4.012 seconds and removed even a newly detached child process; no namespace process or continuing heartbeat remained.
- 57345 prompt tokens led to zero generation requests. A server disconnect after request receipt produced exactly one generation attempt. A synthetic connect failure before sending retried once and produced only one server request.
- Native official result persistence/resume checked success skip, failed result skip, and interrupted attempt preservation, all without regeneration.
- Fixed formal scope and all task runtime caches checked with `--prepare-only`; 240 conditions, zero model requests, no task prompts printed, no answers/references read.

The synthetic HTTP token counts are a controlled stub. Actual vLLM /tokenize acceptance also passed on worker724241 at80 bridge127.0.0.1:18071:207 prompt tokens exactly matched generation usage,219 completion tokens, one native execution produced the correct matrix product, linear solution[2,3], and PNG in16.798s with the final implementation. The first self-authored task failed because the model used input.json instead of data/input.json; its failure receipt is retained, and only the independent dev prompt was clarified before a fresh acceptance case. No formal answer has been regenerated. Full8192-token decoding remains a separate service acceptance item. Root separately passed8 real concurrent service requests with running_peak4/waiting_peak4.

## Files and launch

- `scripts/run_asi_baseline_v2.py`: fixed manifest, inherited native agent, v2 hooks, produce-only journal/resume.
- `scripts/asi_baseline_limits.py`: verified Linux execution constraints; pure affinity/cgroup helpers can also be imported by the Harbor backend.
- `scripts/asi_baseline_smoke.py`: synthetic HTTP and native scientific/resource/resume acceptance.
- `scripts/asi_baseline_real_smoke.py`: one self-authored native task against the real fixed Base endpoint.
- `scripts/asi_baseline_cancel_smoke.py`: live client timeout and subsequent engine-idle acceptance; no benchmark input.

Root can launch on 80 from the project root:

```sh
artifacts/envs/asi-py312/bin/python scripts/run_asi_baseline_v2.py --endpoint http://127.0.0.1:18071 --key-file artifacts/private/base_smoke_api_key --output artifacts/eval/base_asi_v2_20261016 --parallel 8 --cpu-offset 0
```

No training, paid scoring API, official tasks, another project's job or original proxy setting has been changed by this implementation.

Original full model responses, including length-finished output, are written atomically to audit/<condition>.response.json before code extraction/execution. Run metadata freezes the protocol SHA, endpoint, exact runner/helper SHA, ASI requirements and official uv.lock SHA, fixed model revision and inference runtime lock SHA. The preliminary artifacts/eval/base_asi_v2 directory contains only the earlier parallel1 prepare-only metadata and no formal results; the formal launch should use a fresh output directory.

Live cancellation passed on the dedicated ASI endpoint: one synthetic request required at least4096 tokens, the client closed after6.063s with ReadTimeout, engine metrics were observed at running1 and then running0/waiting0 after disconnect, and remained idle. The preliminary0.8s probe was marked inconclusive because no positive running sample was observed; that receipt is retained. The final successful real native response was verified to exist on disk before the execution limits receipt was created. Full formal scope preflight with parallel8 and CPUoffset0 passed with zero model requests; final runner/helper and lock hashes are captured in the aggregate snapshot.

## Production infrastructure incident, 2026-10-16 03:55 Shanghai

Shared SSH model transport failed after launch. PID2473386 had already exited when the stop request arrived; no run_asi_baseline_v2.py worker, asi_baseline_limits.py process or apex-asi scope remained. No PID with a mismatched identity was signaled. All240 conditions have saved failed results.229 failed during /tokenize with Connection refused and never attempted generation; eight passed the guard and then disconnected after sending, without a response; three preserved complete responses and executed once, with failed execution outcomes. The audit inspected lifecycle/status/transport metadata and file presence only, without using formal answers/programs to tune the model or runner.

All original journal/response/program/result artifacts remain, and the five frozen ASI source files and run metadata SHA are unchanged. Automatic regeneration is disabled.229 pre-generation failures are eligible for manual same-ID/same-seed bounded infrastructure retry review (maximum two); eight ambiguous generation attempts must remain separately audited under the no-ambiguous-regeneration rule; the three received answers remain frozen for execution/scoring review. See analysis/source_snapshots/baseline_asi_infrastructure_20261016.json and the metadata-only condition inventory baseline_asi_infrastructure_conditions_20261016.json.
