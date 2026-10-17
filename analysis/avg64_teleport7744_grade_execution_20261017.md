# AVG64 Teleport T7744 grade-only waiter: execution observation

Read-only capture at **2026-10-17 10:43:31 CST**. The single root-launched waiter is running normally and has **not admitted native grading**. This is a startup receipt, not a score or completion claim.

Root uniquely launched PID **2223041**, startticks **870388084**, at 10:40:56 CST after root and independent review. Its current saved state (10:43:27 CST) is `waiting_source_or_route`, `lock_held=false`; the initial execution claim says `waiting_source_handoff`. Actual PID/startticks agree, process state is S, and metadata affinity is CPU10.

The original AVG ASI saved progress is **232/240**, active8, running, scored=false, timestamp **10:39:57 CST**. This is the saved progress count, not a fresh scan of all generated conditions. Its `generation_cpu_finished.json` is absent. No project scope intersects CPU124–127 at capture, but this transient emptiness does not satisfy source handoff: the original complete240/pool-shutdown marker remains mandatory.

The private lock file exists (inode90780234), with no kernel lock row. No native directory, native result, admission receipt or guard log exists. Thus the waiter is not holding its future lease or running a native child. The observed state and claim record zero model calls and no formal score acceptance.

The fixed contract remains one original AVG T7744 answer/patch/SIF/tests, future physicalCPU124/logical0, 1CPU/4GiB, original3000s verifier and1800s patch-replay agent budget. Its independent lease/guard covers124–127; it does not take the global grader92–95 lock. Previously bound Terminal initial/expansion pools end atCPU123. No source marker, queue, answer, scoring configuration or live dependency was changed.

All **43 execution-claim bindings** matched at capture, including the **41 fixed source/dependency bindings**; the original SIF size/mtime also matched. Frozen script SHA256 is `fb5a495bc3fceab502ce6983a905a846b58cf26ba885282849ec938b617292ce`; manifest SHA256 is `8cff408195321efd151b16eaeb42eae0bb55cf4c78670cebd2b6d9addb4f2abd`.

The immutable route receipt SHA256 remains `6d8f90eb63ba0104c2ff8782511ec9f22aa101b5dc8fe955413e9227cdfd0a7d`. Existing metadata shows one loopback listener at127.0.0.1:38444 and the recorded connection sshd2206906/start870351829 alive. User-visible `ss` does not expose its listener FD owner; this audit makes no direct FD-ownership claim and sends no HTTP/TLS probe or SSH-forward request. Root's prior dedicated Mac-route validation is preserved by the receipt.

Evidence paths on host80:

- Root launch: `artifacts/recovery/avg64-teleport7744-original-proxy-20261017/root-launch-20261017.json`
- Current state: `artifacts/recovery/avg64-teleport7744-original-proxy-20261017/attempt1/parent-state.json`
- Initial claim: `artifacts/recovery/avg64-teleport7744-original-proxy-20261017/attempt1/execution-claim.json`
- Route: `artifacts/recovery/avg64-teleport7744-original-proxy-20261017/route-receipt.json`
- Source gate: `artifacts/eval/avg64_asi240_20261017/generation_cpu_finished.json` (absent at capture)
- Compact observation: [source snapshot](source_snapshots/avg64_teleport7744_grade_execution_20261017.json)

This agent performed only metadata observation and wrote this receipt; it did not launch/restart grading, obtain a lease, create a route, probe the network or accept a result. No wait for native completion was required.
