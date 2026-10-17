# git-leak：metadata-only 诊断执行与原header冲突

root 于2026-10-17 **10:24:22 CST** 唯一启动诊断 parent **2170741/start870288696**，child **2170746/start870288825**。冻结wrapper83fc/manifest2831及原e0ad/db12、旧attempt均未修改。恢复命令0/1原样返回0，resolver明确 `OK`；metadata命令2按设计返回 **86**，随后frozen CLI在恢复循环停止。verifier目录为空，`verifier_result=null`，无官方测试、solver/model或API调用，无成绩或collector变更。

独立根 `O=/data/caoqinlu/projects/apex-takehome/artifacts/recovery/terminal250-git-leak-seed1-restore-diagnosis-20261017`。诊断原结果 `O/attempt1/native-grade/result.json` SHA256 **`c9a1557633b6657ae4d2fbca7128bb80d280c1a75726c3891920a84a43caef46`**，finished_at **10:24:26.659675 CST**；异常 `RuntimeError: Original restore command 2 returned 86` 是预定阻断，不是原题判错。

## 唯一差异与可定位原因

命令2完整记录app50+etc23共**73项**，app名单完整、无额外/缺失路径；仅下列一项mode不同。其余72项mode、全部type、内容hash一致性及链接检查均通过，硬链两端实际samefile。

| 原归档成员 | 原type/mode | 诊断实际mode | 内容/硬链 |
|---|---|---|---|
| `app/repo/.git/info/refs` | 普通文件，0600 | 0600 | 内容一致 |
| `etc/apt/apt.conf.d/01-vendor-ubuntu` | hardlink→上述成员，0644 | 0600 | 内容一致、samefile=true |

原tar的**原始header字段**也分别为 `0000600` / `0000644`，不是Python格式化误差；uid/gid均0。普通文件header mtime为1792195310、硬链header却为1711102304，存在同类metadata冲突。一个真实inode无法同时拥有两个mode/mtime。

因此本次严格检查失败的直接原因已定位为：验证器将hardlink别名header中的0644当作独立inode权限要求，而恢复后同inode正确使用了普通目标header的0600。**改变别名为0644会同时改变app中目标文件，反而破坏其0600检查。** 本次没有证据表明每exec递归chmod导致问题。原tar为何产生互斥header（例如fakeroot表示或捕获时序）尚未证明，不将其具体归因模型、Harbor或tar实现。

## 来源与释放审核

10:25:48 CST独立复核 **42个claim绑定全部不变**，原archive/raw result/config/task/tests、旧失败结果/claim/state、frozen源码、新wrapper/manifest/payload均保留。同SIF resolved路径、92987392 bytes、mtime_ns1792079169674202869匹配；未做大文件全hash。

parent记录实际guard affinity92–95、32MiB/swap0；这是可见租约guard，不是native限额。原native配置仍4CPU/8192MiB、offset0；诊断很快结束，未独立采到live native cgroup，不能冒充资源实测。原900s verifier因exit86结构上未进入。

完整清理证据为：native scope双空 **10:24:28.899586、10:24:30.963138** → guard停止 → 全scope双空 **10:24:31.025029、10:24:33.103197** → **10:24:33.175955解锁**。parent状态 `finished_pending_root_review`、child rc0、lock_held=false、guard_stopped=true。10:25:46.156493和10:25:48.234366又独立见scope双空；父子已不存在，global锁inode90775088在capture时无holder，未为检查取锁。

机器收据：[terminal_git_leak_restore_diagnosis_execution_20261017.json](source_snapshots/terminal_git_leak_restore_diagnosis_execution_20261017.json)，含全部73项安全metadata、原tar两端header、绑定与排空证据；80副本 `O/execution-review.json`。无文件bytes、secret或答案内容。

## root授权准备的最小修复边界

仅准备新的独立bootstrap恢复wrapper/manifest/payload供root和merge审阅，不执行、不改旧源码或payload。恢复命令0/1完全不动；命令2只对**exact task/key/archive SHA**及上述唯一hardlink定义canonical mode：要求普通target仍是归档内0600普通文件、alias raw header仍0644且linkname精确，实际两端仍samefile，alias实际mode也必须严格为0600。其他72项原mode/type/hash、全部73项与app名单检查不变。

这修正的是对一个互斥hardlink header的校验假设，不能泛忽略mode、chmod候选或拆链接。原raw0644及0600冲突须保留为audit来源，真实capture末态权限来源仍有上述限制。新的实际官方verifier将是该原答案**首次进入原测试**，保持原900s/4CPU8GiB；本次与先前均在测试前停止，不据reward重试。root/merge审后另行唯一启动，未获执行前继续null。

## 10:28：最小恢复payload已准备，未执行

新 [82行wrapper](../scripts/recover_terminal_git_leak_header_mode_20261017.py) 和 [独立manifest](../configs/eval/terminal_git_leak_header_mode_recovery_20261017.json) 直接复用e0ad parent的validate/run。来源绑定为原37加诊断result/receipt、冻结83fc/2831及新wrapper，共42个，默认prepare实际通过；没有改任何旧源码、manifest、payload或attempt。

独立新根为 `R/artifacts/recovery/terminal250-git-leak-seed1-header-mode-recovery-20261017`。新 `prepared/restore.json` SHA256 `21b88d338071b430a956c0e96f42c0b74218fc8e93aecd0fd9457652dba9f09a`，恢复命令0/1与原95017对象完全相同。仅命令2从原严格checker生成：先重新核容器内原archive SHA及唯一hardlink mapping，断言alias raw0644、target是0600普通文件，再令该alias的mode预期取target0600。所有实际mode仍需精确相等，73项type/hash/链接/app名单校验均保留，另显式要求checked=73。没有chmod、拆硬链或跳过mode。

10:28:25.068–10:28:25.326 CST 的**合成73成员**小夹具（普通文件均仅synthetic text，没有原内容）完成一轮适当检查：原header冲突使旧checker RED；新checker严格GREEN并校验全73项；错误hardlink target、错误regular header mode、错误实际inode mode、错误archive SHA均仍RED。它不是SIF/native/原题测试，也不证明原任务将通过。

10:28:25.381972 CST默认prepare记录SWE已drain、ASI尚未评分就绪、Terminal未接管；新attempt不存在，0claim/guard/取锁/native/model/API。生产环境、同global guard与自然清理、2400s准入门、4CPU8GiB900s与短TMP58B均沿用e0ad，不新建scheduler或授权机制。准备命令为：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/data/caoqinlu/projects/apex-takehome/scripts \
taskset -c 10 /data/caoqinlu/projects/apex-takehome/artifacts/envs/harbor/bin/python \
  /data/caoqinlu/projects/apex-takehome/scripts/recover_terminal_git_leak_header_mode_20261017.py
```

**本轮没有添加 `--execute`。** root/merge审阅及fresh资源核验后，才可另行唯一启动并记root-launch/PID/startticks；实际native结果仍须独立审核后决定是否接入只读collector。

最终wrapper SHA256 `a13001baf6656973a9553d78a0b107ca36ee5035023c48992ce02dca18c5b447`；manifest SHA256 `e56b4e8327ba748d72f37e77bce1ec8c46dec1ee85b633087720f34dc90494c0`。准备收据：[terminal_git_leak_header_mode_recovery_preparation_20261017.json](source_snapshots/terminal_git_leak_header_mode_recovery_preparation_20261017.json)。
