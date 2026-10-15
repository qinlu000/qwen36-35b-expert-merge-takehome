# Harbor Singularity startup patch

状态：经 root 审阅批准，已在 80 和 HPC 的原固定源码路径应用；已装环境以 editable 方式使用同一源码，没有复制另一份 Harbor。基于 Harbor 0.24.0 / `f527f8e447038fd242d08ecfa8aaa8029100da97`，两份原文件 SHA256：

```text
53a311a61eb32feb3d36dc238951456098e17ec227d0b2dc0db1e9fe8e73eb75  singularity.py
1c4966bc330e6bd010ec9201f947389bb858defe6bc8e9647a24980f2e0d6b5c  server.py
```

`harbor_startup.patch` 修改上述两份文件；`harbor_startup_apex.patch` 移除项目 Apex 子类旧的通用 `/shutdown` stop override。**两份 patch 必须同次应用**，否则旧 override 仍可能先关闭端口复用的外部旧 server，绕过新 native 身份保护。镜像、任务、模型协议、资源和网络能力不变。

- 新增 `singularity_startup_timeout_sec=300.0`，使用单调时钟；所有端口尝试共享 readiness deadline，不是每次额外 300 秒。
- 每次启动生成本地 expected token；`/health` 必须返回同一 token。客户端固定请求 `127.0.0.1`，关闭代理与重定向。
- shutdown 仍使用 server 既有处理逻辑，但路径为 `/shutdown/<expected-token>` 并验证 token。POST 200 后最多等 2 秒确认该 token 的服务已不再可达，覆盖 handler 原有的延迟 SIGTERM；如端口换成另一个实例则停止操作，不向它发送关闭请求。旧 server 的通用 `/shutdown` 不会被调用。token 只防实例混淆，不是抵御同机恶意用户的凭证。
- stdout/stderr 直接写本次 staging 的 `server-N.log`；不建 PIPE 或持续 tail task。失败报告日志路径并保留 staging，避免分离的子进程继承 PIPE 导致 `Process.wait()` 无界挂起。
- 失败先认证 shutdown（包含确认消失，整个步骤最多 4 秒），再仅对持有的 launcher handle terminate/wait（5 秒）、kill/wait（2 秒），最后有界关闭客户端（2 秒）。取消或意外启动异常也进入该清理并保留原异常；任何未确认关闭的分支都保留日志。移除原有 `pkill -P`；不按端口、进程名或 `/proc` 猜测其他 PID。无法确认 server shutdown 时不继续盲目复制启动。

**边界**：如果 bootstrap 在监听前已经脱离 launcher，无法认证它是否仍存在。补丁保证有界返回和不误关其他 server，不保证该分支零孤儿；日志会明确写 `Server shutdown unconfirmed`。没有引入 cgroup、PGID 假设或进程管理框架。正常 stop 也只有认证服务已消失时才沿原语义删除 staging；未确认时保留诊断记录。

本地检查只用标准库假 HTTP/launcher；执行两份补丁后的实际 native/Apex 方法，HTTP fixture 调用实际 server handler 的延迟 SIGTERM，不采用同步假关闭，`stop()` 返回后立即检查端口。不安装 Harbor，不运行镜像、正式题、模型 API 或 GPU。Python 3.12.11 的原 PIPE 模式可确定复现等待超时；成功启动/认证关闭、readiness 超时、启动中取消、ready 后上传时取消、外部端口碰撞、旧服务复用端口、terminate 与 kill 均不退出的 8 项合成检查已通过。另已执行以下真实容器正常冷启动回归；没有故意触发真实容器 timeout。

`scripts/apply_harbor_startup_patch.sh` 对固定 revision 和两份 native 源码的原始/已 patch SHA256 做校验，先验证两份 patch，再变更文件；重复执行识别已应用状态。80 的 Git checkout 拒绝 staged、其他 tracked 修改和两份文件的未知字节；HPC 的 archive 验证 `SOURCE_REVISION`。`reverse-native` 只用于 80 setup 在 clean checkout 前恢复本次已知修改，随后重新 apply；项目 Apex companion 保持应用。两端 setup 仍使用官方 `uv sync --frozen`，未改依赖锁。

以下只对临时副本应用，供复审本地合成检查；当前项目 Apex 已含 companion，因此复制后检查 reverse，而不重复正向 apply：

```bash
task_root="$PWD"
review_dir="$(mktemp -d)"
mkdir -p "$review_dir/harbor" "$review_dir/project/scripts"
git -C artifacts/benchmarks/harbor archive f527f8e447038fd242d08ecfa8aaa8029100da97 | tar -xf - -C "$review_dir/harbor"
cp scripts/apex_singularity.py "$review_dir/project/scripts/"
git -C "$review_dir/harbor" apply --check "$task_root/scripts/harbor_startup.patch"
git -C "$review_dir/project" apply --reverse --check "$task_root/scripts/harbor_startup_apex.patch"
git -C "$review_dir/harbor" apply "$task_root/scripts/harbor_startup.patch"
python3.12 scripts/check_harbor_startup_patch.py \
  --source "$review_dir/harbor/src/harbor/environments/singularity/singularity.py" \
  --apex-source "$review_dir/project/scripts/apex_singularity.py"
```

现在可通过 `--ek singularity_startup_timeout_sec=300` 或 `environment.kwargs` 配置。该参数由本地 patch 提供，不是未修改上游的既有接口。部署/CLI 回执为两端 `artifacts/preflight/swe_tb/startup-patch-install-check.json` 和 `startup-patch-cli.json`；真实容器回归另记下方。

2026-10-16 实际验收：两端 helper 重复 apply 通过；80 setup 实际完成 reverse-native → clean pinned checkout → apply，HPC archive 也实际 reverse/apply 后复验。两个 setup 都完成官方冻结依赖检查，101 个 Harbor distribution 未变。两端版本为 Python 3.12.11、Harbor 0.24.0、LiteLLM 1.93.0、OpenAI 2.24.0；CLI 解析 `--ek singularity_startup_timeout_sec=300` 成功，四项 CPU/内存 capability 仍均为 false。80 的 `uv.lock`/`pyproject.toml` 无 Git diff，两端 `uv.lock` SHA256 均为 `26d9b45f79a5feb7e872fc19771865a04a71e746bb9bc687dcd3014a9a46f461`。

| 主机 | 冷启动 | 总耗时 | 结果 |
| --- | --- | --- | --- |
| 80 | 43.186 秒 | 44.266 秒 | start、两次 exec、临时文件保持、tmux、asciinema、stop 后端口关闭均通过 |
| HPC | 44.399 秒 | 45.701 秒 | 同上 |

回归使用既有 `scripts/smoke_harbor_singularity.py` 与固定 build-cython-ext SIF，只创建自造命令、临时文件、PTY 会话和录制；未读取镜像中的题面/测试，未运行 agent/verifier、模型 API 或 GPU。容器内 uid 0，FastAPI 0.143.2 / Uvicorn 0.54.0，tmux 3.3a / asciinema 2.2.0。镜像的 amd64 OCI digest 为 `3612a38fadb89a96f74a1a951fb0b0af734198fd160571eeaba6401593234594`，两端重新计算 SIF SHA256 均为 `0749503602dbf6a1a276c419ce15f24c79f01f4a47139c7e22a89f08ca070e77`。没有改固定 SIF、下载/mirror 进程、工具 binary、正式协议、资源和网络能力。

两端原始回执同相对路径：`artifacts/preflight/swe_tb/startup-patch-cold-20261016/smoke.log`、`image.sha256`、`artifacts/preflight/swe_tb/synthetic-harbor/result.json`（后者位于该独立回归目录下）。本轮是各一张真实镜像的正常生命周期验收，不代表 140 镜像全部 bootstrap 或 SWE locked 网络策略已就绪。

本次部署 patch SHA256：

```text
af9e4abea4130f1d1afd55c77cbef08f4b5519fd0554024f3fff84e8e9ba51f6  scripts/harbor_startup.patch
207279d377af3237ff865d675f375e01e4c193802ec2a4faec6716e864cbe0d6  scripts/harbor_startup_apex.patch
```
