# NodeBB完整官方报告审计：可行性与Base先例

**建议可行；专家现已自然timeout并完整排空，独立parse-only证据和未批准proposal已备妥，待root审核。** 不能把缺失reward、任意超时或EXIT trap的1直接作为分数。初步10:13:07–10:13:39只读核源码、旧收据与既存report；之后经新授权仅运行原官方parser，未运行候选、测试/native、模型或真实数据collector，未接分。机器可读证据见[JSON](swe_nodebb_parse_audit_feasibility_20261017.json)。

## Base先例是真正完整报告，但清理方式不同

Base原clean28结果为VerifierTimeoutError/native_reward=null；之后同一Base原patch的新evidence run已完成Mocha报告，root先保存原始stdout/stderr和原parser输出，再授权03:16提前清理仅挂退出的scope。该新evidence结果为RemoteProtocolError/null，**不是新鲜run自然等满3000秒**。两份原result和cleanup异常都保留，审定0存于独立candidate-failure-audits.json，未改reward文件。

真实来源为 `artifacts/eval/base_swe_gap_repair_20261017/{candidate-failure-audits.json,nodebb-completed-test-evidence.json,evidence/nodebb-completed-official-output.json}`；[完成证据](source_snapshots/base_swe_nodebb_completed_test_evidence_20261017.json)及[清理收据](source_snapshots/base_swe_nodebb_cleanup_20261017.json)与当前文件相符。`collect_base_gap_completion_20261017.py:98`有专用 `complete_official_test_report_with_failures` 分支，保留native_reward=null、audited reward0。该分支本身只断言311/307/4计数；本轮额外逐名验证required集合相等，不能仅照抄计数门槛。

## Base与专家完整性对照

|证据|Base已接受evidence|专家当前保存report|
|---|---:|---:|
|Mocha调用/通过/失败/pending|335/331/4/0|335/331/4/0|
|原parser按name去重|311|311（10:16原parser rc0；初步内存映射也一致）|
|重复调用/状态冲突|24/0|24/0|
|官方required集合|F2P4 + P2P307|相同|
|unique集合与required exact相等|是，无缺失/额外|是，无缺失/额外|
|P2P通过/F2P失败|307/4|307/4|
|原生终态/清理|授权提前清理，raw null|原3000秒自然timeout、raw null；cohort已完整清理|

Base现有official-output.json与本轮按原parser规则在内存重建的映射逐值相同。专家初步10:13核查仅重建内存映射；10:16经新授权已让原parser仅作用于保存文本，独立写official-output并记录rc/source SHA，没有重跑任何测试。

两模型的 `task.toml`、`tests/config.json`、`parser.py`、`test.sh`、`run_script.sh`、`test_patch.patch` **六份逐字相同**。parser SHA为55c24185…，config SHA37020fb8…。config的F2P/P2P字段实际是字符串列表，须按test.sh187–204的JSON优先、Python literal回退规则解码，不能把字符串当字符集合。

四个FAILED均精确属于原F2P，没有把331个raw passes当成四个必需测试通过：

|官方测试标识|状态|专家短错误证据|
|---|---|---|
|test/groups.js \| Groups groups cover should remove cover|FAILED|严格相等断言失败|
|test/user.js \| User profile methods should remove cover image|FAILED|getLocalCoverPath is not a function|
|test/user.js \| User profile methods user.uploadCroppedPicture should remove uploaded picture|FAILED|getLocalAvatarPath is not a function|
|test/user.js \| User socket methods should clean profile images after account deletion|FAILED|严格相等断言失败|

test.sh213–228的原标准是 `(F2P ∪ P2P) <= passed_tests`，当前明确为false。这是完整测试结果提供的失败证据；挂退出的准确机制仍unknown，不能由此声称hang必由模型造成。Base与专家保留**各自原patch**，不是跨模型同一patch：Base198102B/d8656fdc…，专家7422B/aff1970c…。

## 建议的精确绑定与终态门槛

1. 固定原summary/result、模型/checkpoint、generation config与source_job；绑定专家7422B patch SHA、replay apply_rc0、task checksum与SIF大小/mtime。不能借Base patch/report替代专家来源。
2. 固定本次accepted timeout result/config/replay SHA、verifier实际起止时间及原1CPU/4096MiB/3000s；保留raw reward/exception。Base物理CPU11与当前专家CPU92、runtime wrapper/排程不同须披露，不称严格同一执行拓扑。
3. 终态后冻结durable stdout/stderr及完整raw JSON的SHA，确认有单个完成report、end时间、335/331/4/0、24个重复无冲突。保存原parser/config/test.sh/run_script/testpatch SHA及独立parse-only rc/report。
4. 明确验证unique311与F2P4+P2P307**exact集合**相等、缺失/额外均0；P2P307全PASSED、F2P4全FAILED。只看4 fail或总数335不够。
5. 等cohort所有child自然结束、两次native scope空、guard停止、两次全scope空、原锁解开，固定收据与时间顺序。初步10:13仍在途时不能宣布complete；10:15自然收尾及其历史收据已在10:16解析前核对。

test.sh12–24的EXIT trap按shell退出码写reward；异常退出或上游被截断时，它不等于213–228的必需测试判定已执行。**本次实际reward.txt=1（2B，SHA4355a46b…），但Harbor原result的native_reward仍null。** 该文件已单独固定，不能当成功或覆盖为0。新增显式 `approved_official_test_reports` 类型将 `audited_reward=0`、原result native_reward=null及原reward文件值1分开保留；只有根审核后才加入exact名单。现有native-zero分支要求raw0/noHarbor exception，不能塞入null来复用。

## 10:16授权后的实际准备

专家原生verifier从09:24:56.267900到10:14:56.273806，实际3000.006秒；结果为VerifierTimeoutError、raw native_reward仍null，SHA为**a7109bb07f12df026f91786b2b8a83e4146da398c9449be5c3ab9cf5b4669e36**。在独立确认cohort finished、父进程退出、两次native空、guard停、两次全scope空及解锁后，10:16:43于CPU10仅运行原Harbor lexical Python加原官方parser一次，读取durable stdout/stderr，未启动任何test/candidate。

独立artifact为80的`artifacts/recovery/swe-nodebb-parsed-official-audit-20261017/`：原文本、raw-mocha.json、frozen-parser.py、frozen-test-config.json、official-output.json和parse-receipt.json均独立保留。parser rc0，official输出311/307/4，SHA **0805fde98b1d8d5924a6595588d7e2b93f6ebe2d10f329814ea71f75f34e9ac3**；它与Base同一测试状态映射相同，但两组原stdout SHA不同，并各绑定自己的原patch和verifier时间窗。另保存frozen-runner.py与cohort manifest副本，均匹配原claim；没有覆盖原result/reward或live报告。

已为`collect_swe249_audited.py`准备**独立optional `approved_official_test_reports`**分支：不复用native-zero，不把rawnull改成native0；逐项核source/generation/patch/timeout/config/SIF metadata、parser命令和文本SHA、raw报告与原parser映射、完整exact311集合及cohort历史排空顺序。没有列表时，旧native-zero分支不变；只有root加入精确批准名单后才生效。新增返回单独audited report计数和score_source，原native_reward并列保留。

`check_swe249_audited_examples.py`的**26项人工检查通过**（原19+新7），覆盖缺1项、重复状态冲突、错patch/source（即使相关digest更新仍拒绝）、rawnull保留及native-zero/parsed-report两分支集成；额外验证EXIT-trap文件1不当成功，原文件/result字节保持。没有用真实数据运行collector。

未批准proposal已放在本地及80的`artifacts/proposals/swe249_nodebb_official_report_20261017.json`，SHA **cda861188e59047ecf247c065c3d07569381aad5aa0fbecd0539ec5285d128a9**，29份小文件精确绑定（包括原reward.txt=1）；`/artifacts/`在.gitignore中。它只标`proposal_not_approved`，**没有修改主manifest、接分或重判Base/AVG规则**。真正批准和执行collector由root另行处理。
