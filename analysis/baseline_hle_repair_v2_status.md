# HLE network infrastructure retry1

Launched on host80 as PID3887939, output artifacts/runs/base_hle_v2_724196_infra1, model service725539 on ACD1-16 (2H100,24h), endpoint127.0.0.1:28081. Initial checkpoint had8 admitted/active/started,0 completed, bounded admission rather than prequeueing1679.

The user explicitly confirmed overnight laptop network failure and permitted corresponding reruns. The manifest selects1671 failures before generation plus8 sent/disconnected without a response. Original309 complete responses and512 genuine300s budget timeouts remain unchanged; the full2500-question denominator remains. Original results, request costs and failure receipts are retained. Responses are persisted before validation; no answer selection or same-request read/disconnect retry. Only explicit pre-send connection errors or429 with generation-not-started proof may use one bounded HTTP retry.

The original runner and core/input/manifest/system/official source hashes are checked. Per-question300s,64K/8K/nonthinking, original messages/images/sampling/seed stay fixed. Independent async8-slot admission plus periodichealth pauses and cancels in-flight requests on transport failure, retaining journals/checkpoints. Existing results or unresolved started journals cannot silently regenerate.

Direct host80-to-HPC SSH forwarding runs remotely with a dedicated forwarding-only key; no laptop is involved. The tested HLE SSH child recovered3.615s after termination, while the Terminal child stayed unchanged. Real8-question synthetic HLE acceptance including4 images passed in<48s with actual token/usage/mode checks. An earlier synthetic-only overlap with deliberate disconnect failed and was preserved separately.

Receipts: analysis/source_snapshots/hle_manual_retry_manifest_20261016.json, hle_manual_retry_launch_20261016.json, hle_direct_acceptance_20261016.json and direct_hpc_tunnel_recovery_20261016.json. Formal grading is separate and has not run. The user chose remote-only continuation; no app recurring task was recreated.
