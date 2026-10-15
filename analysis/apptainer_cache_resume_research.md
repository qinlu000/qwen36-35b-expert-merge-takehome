# Apptainer 1.4.5：OCI layer 续传与缓存复用研究

**后续实现/实测入口（2026-10-16）**：经 root 授权，已实现 [`scripts/pull_oci_resumable.py`](../scripts/pull_oci_resumable.py)，并在 prefetch 增加 `--transport ranged-oci`。私有共享 blob 用 digest flock、8 MiB Range、严格 206/Content-Range/长度、完整 size/SHA 与原子发布；native cache 仅校验后复用完整对象，不修改其 index 或在途文件。

- [`scripts/check_oci_resumable.py`](../scripts/check_oci_resumable.py) 在同一自造 registry 复现原生 255 / unexpected EOF，再验证首次 Range 被截断后重试、8 MiB 后非零 offset、整 SHA、缓存二次零 GET；80 与本地回执为 `artifacts/preflight/swe_tb/oci-eof-20261015T185024Z/summary.json`。
- 自造 OCI layout 已实际通过官方 `pull --disable-cache ... oci:/absolute/layout` 转换，未执行镜像；80 回执 `artifacts/preflight/swe_tb/ranged-oci-syntax/receipt.json`。
- root 的真实 GHCR layer 分段 probe 已验证 598,841,604 bytes 与完整 SHA，回执 `artifacts/preflight/swe_tb/range-layer-32926d178d6ee589692d2128a260a6f0dda1c17d66ba2a6b9dc294fe53f833c8/receipt.json`；已发布私有 blob cache 供后续复用。
- 固定 Navidrome child manifest `sha256:3f506b30838750b681489f4e7a476379ebe4d9d4acc67b9bbb0299c6531841dc` 的完整镜像验证已通过：29 个逻辑 OCI 对象 size/SHA 校验、官方本地 OCI → SIF 退出 0、`sif list` 退出 0；598 MB 预验层直接复用，未再次下载。80 产物 `artifacts/preflight/swe_tb/ranged-image-probe.sif` 为 1,034,416,128 bytes，SHA256 `fae86a5071fe326f2dd80a9deffa3c2479a691f3b0b9e539650ba4a287da89ef`；回执 `ranged-image-probe.sif.oci.json` 与 `ranged-image-probe.validation.json` 在同目录。实际 helper SHA256 为 `a4a1ec83ce99f9c91b3c119ab743742c5c645c94112016bf1566ede79524f2b8`。

当前复现入口为 `artifacts/envs/harbor/bin/python scripts/pull_oci_resumable.py --root "$PWD" --image <repository@sha256:child-manifest> --output <independent.sif>`；批量入口 `scripts/prefetch_benchmark_images.py --transport ranged-oci` 仍由主任务统一调度。本 agent 未 promote probe 到 canonical 缓存，未停止旧队列或启动新全量队列。

下文保留最初**只读研究时间点**；其中“未实现/尚未实测”描述当时状态，当前实现与验收以本段及相应回执为准。没有执行正式题、agent/verifier、模型 API 或 GPU。

日期：2026-10-16。范围：官方固定版本源码和同任务提供的 80 只读观察。没有写入任何镜像缓存、发送 blob 下载请求、安装工具或执行镜像；以下均为待单镜像验证的候选方案。

## 结论

**技术上可以先独立续传压缩 layer，完整校验 size/SHA-256 后原子发布到对应最终 blob 路径，再由官方 pull 复用。更推荐生成每镜像独立的 OCI layout，然后使用官方本地 `oci:` 输入转换 SIF。** 共享缓存注入不是官方支持的用户接口；手工改 `index.json`、把 partial 提前命名为最终 digest、并发修改仍在增长的临时文件都不在建议方案内。官方明确建议不要增改缓存文件。[Apptainer 1.4 缓存说明](https://apptainer.org/docs/user/1.4/build_env.html#cache-folders)

不能把该版本的 blob 下载实现当成 containers/image 的旧 BoltDB 缓存链。v1.4.5 同时依赖 `containers/image/v5 v5.33.1` 和 `google/go-containerregistry v0.20.2`；前者仍参与 URI、初始 manifest digest 和 registry 配置，实际 layer 写 OCI layout 的路径走后者。[固定 go.mod](https://github.com/apptainer/apptainer/blob/v1.4.5/go.mod#L18), [OCI SourceSink](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/ociimage/sourcesink.go#L232)

## 固定源码调用链

| 阶段 | 准确调用与证据 |
| --- | --- |
| CLI | `pullRun` → `oci.PullToFile`；没有 resume/分段选项。[pull.go](https://github.com/apptainer/apptainer/blob/v1.4.5/cmd/internal/cli/pull.go#L281) |
| 初始摘要与 SIF cache | `pull` 先调用 `build/oci.ImageDigest`，再 `convertOciToSIF` → `build.NewBuild(...).Full(ctx)`；SIF 使用 `oci-tmp` 文件缓存。[client/oci/pull.go](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/client/oci/pull.go#L53) |
| 构建 | `Build.Full` → `stage.c.Get` → `OCIConveyorPacker.Get` → `ociimage.FetchToLayout`。[build.go](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/build/build.go#L241), [conveyorPacker_oci.go](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/build/sources/conveyorPacker_oci.go#L123) |
| 获取/缓存 image | `FetchToLayout` → `SourceSink.Image`；启用 cache 时 `cachedImage` → `GetOciCacheDir("blob")` → `OCISourceSink.WriteImage`。[fetch.go](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/ociimage/fetch.go#L29) |
| OCI 写入 | `WriteImage` → GGCR `layout.AppendImage` → `WriteImage` → `writeLayer` → `writeBlob`，最后才更新 index descriptor。[GGCR write.go](https://github.com/google/go-containerregistry/blob/v0.20.2/pkg/v1/layout/write.go#L43) |

## 命名、发布和校验边界

`APPTAINER_CACHEDIR` 在该源码中是 parent；实际管理目录再追加 `cache/`。`blob` 为 OCI layout，最终对象为 `cache/blob/blobs/sha256/<64hex>`；`oci-tmp` 保存转换后 SIF。SIF cache key 经过 manifest digest、architecture、variant 再散列，不能拿 layer digest 或最终 SIF SHA 代替。[cache.go](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/cache/cache.go#L93), [ImageDigest/getRefDigest](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/build/oci/oci.go#L161)

GGCR 的关键行为如下；这些是源码行为，不是对人工修改 cache 的支持承诺。[writeBlob/writeLayer](https://github.com/google/go-containerregistry/blob/v0.20.2/pkg/v1/layout/write.go#L190)

- 最终路径存在、不是目录且大小匹配时直接复用，**不重算已有内容的 SHA**。
- 缺失 layer 用 `os.CreateTemp(dir, digestHex)` 创建临时文件；顺序 `io.Copy`，完整关闭后 `os.Rename` 到最终 digest 路径。随机尾不保证 `.tmp` 扩展名。
- 正常返回的下载错误会执行 deferred `os.Remove(temp)`，因此不能指望 unexpected EOF 后仍有旧 partial。进程异常终止可能留下临时文件，但文件名本身不证明完整性。
- config/manifest 的 `WriteBlob` 与 layer 临时发布路径不同；不要把所有 metadata 都概括为原子写入。

远端 layer 的 `Compressed()` 建立 GET，返回带 expected size/digest 的 `verify.ReadCloser`；读到 EOF 时验证哈希和长度。`writeLayer` **先调用 `Compressed()`，后检查目标文件存在性**，所以已有完整 cache layer 可避免消费整层 body，却仍可能要求 registry/auth/CDN GET 成功，不能保证离线。[remote image.go](https://github.com/google/go-containerregistry/blob/v0.20.2/pkg/v1/remote/image.go#L163), [verify.go](https://github.com/google/go-containerregistry/blob/v0.20.2/internal/verify/verify.go#L49)

本地 layout blob 读取只是 `os.Open`/`os.ReadFile`，descriptor 的 digest/size 也可以直接返回。不能把后续本地 pull 当作会替自己重新校验全部压缩 blob 的保证；续传程序须先做整文件 size + SHA 校验。[layout/blob.go](https://github.com/google/go-containerregistry/blob/v0.20.2/pkg/v1/layout/blob.go#L22), [layout/image.go](https://github.com/google/go-containerregistry/blob/v0.20.2/pkg/v1/layout/image.go#L105)

SIF 文件缓存的 `Entry.Finalize` 是 tmp → final rename；这和 OCI layout 的 index 更新是两件事。[cache/entry.go](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/cache/entry.go#L32)

## index 与并发

已检查从 `pullRun`、`pull/convertOciToSIF`、`Build.Full`、`OCIConveyorPacker.Get` 到 `FetchToLayout/cachedImage`、`SourceSink.WriteImage` 的这条调用链，未见包住 layout 更新的跨进程 flock。GGCR `AppendDescriptor` 读取当前 index、追加 descriptor，再通过 `WriteFile` → `os.WriteFile` 写回；其中 rename mutex 仅用于 Windows blob rename，并非 Linux index 锁。故不能依赖这条链替人工 index 改写做并发协调。[CLI](https://github.com/apptainer/apptainer/blob/v1.4.5/cmd/internal/cli/pull.go#L185), [build](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/build/build.go#L241), [SourceSink](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/ociimage/sourcesink.go#L248), [AppendDescriptor/WriteFile](https://github.com/google/go-containerregistry/blob/v0.20.2/pkg/v1/layout/write.go#L79)

这里仅描述所查源码链，未宣称整个程序所有代码均无锁。最小方案无需修 index 并发框架：不人工碰共享 index；独立 layout 的 index 由单一写者在全部 blobs 准备后发布。

## 两种候选路径

| 路径 | 最小做法 | 局限 |
| --- | --- | --- |
| 共享 cache 完整 layer 发布 | 在私有 `.part` 续传；核对 manifest size 和整 blob SHA；目标文件系统内 rename 至 `cache/blob/blobs/sha256/<hex>`；随后官方 remote pull 自己补 metadata/index | 技术可行但非官方支持接口；不手工改 index；仍可能发 GET；需避免与同 digest 活跃写者重复下载或覆盖未知对象 |
| **独立 OCI layout，推荐** | 每个已锁定的 linux/amd64 child manifest 一个目录；放原始 manifest、config 和全部压缩 layers，全部按 SHA 命名；最后写唯一 descriptor 的 index 和 `oci-layout` | 多一点磁盘/I/O；仍需官方解包、mksquashfs；尚未做该版本真实单镜像转换验证 |

标准 layout 包含 `oci-layout`（`imageLayoutVersion: "1.0.0"`）、`index.json` 和 `blobs/<algorithm>/<digest>`。所有被引用对象保留下载原始字节；不能为了美化 manifest JSON 或重新 gzip 而改变 digest。可从已有最终 cache blobs 复制/reflink 到独立目录，但须先验 SHA，且不使用活跃随机尾文件。[OCI image-layout v1.1.1](https://github.com/opencontainers/image-spec/blob/v1.1.1/image-layout.md#content)

**本地输入选单 descriptor、不带 tag/digest 后缀的绝对目录**，候选转换命令为 `apptainer pull --disable-cache out.sif oci:/absolute/layout`（本轮未执行）。GGCR reader 内部支持 `<dir>[@digest]`；但公开 pull 在此前还要经过 containers/image 的 `path[:annotation-tag]` parser。直接单 descriptor 目录是两条路径共同支持的形式；不要根据其中一条推断 `:tag` 或 `@sha256:...` 在完整 pull 链均兼容。[Apptainer getOCIImage](https://github.com/apptainer/apptainer/blob/v1.4.5/internal/pkg/ociimage/sourcesink.go#L116), [containers/image ParseReference/getManifestDescriptor](https://github.com/containers/image/blob/v5.33.1/oci/layout/oci_transport.go#L63), [SplitPathAndImage](https://github.com/containers/image/blob/v5.33.1/oci/internal/oci_util.go#L55)

## KISS 续传方案草案（未实现）

1. 锁定原 manifest digest、linux/amd64 child digest、每个 config/layer 的 digest 与 compressed size；按 digest 去重。
2. 只在项目私有下载目录维护 `<hex>.part`，一个 digest 一个写者。已有最终文件先验 size/SHA；未完成的只追加压缩原始字节，不使用 `--compressed` 解码 HTTP 内容。
3. 先对一个 blob 做小段 Range 能力检查（例如首段 64 MiB），确认 `206` 和正确 `Content-Range`；这一能力当前没有实测。OCI Distribution 对 Range 是 **SHOULD**，不是 MUST。[Distribution v1.1.1](https://github.com/opencontainers/distribution-spec/blob/v1.1.1/spec.md#pulling-blobs)
4. 80 已有 curl 7.81.0，可用 `curl -C -` 加有界外层重试保存 partial；鉴权/签名 URL 失效时重新取得同 digest 的入口。不能把返回的 200 全量 body 接在旧 partial 后；416 也不能直接当成功，必须核 size/SHA。[curl continue-at](https://curl.se/docs/manpage.html#-C)
5. 完成后重新读整个 `.part` 核对 size 和 SHA，再在同一文件系统 rename 发布。优先发布到私有 layout；只有另行决定采用共享注入时才发布到精确 cache blob 路径，且不动 index。
6. 先单镜像验证本地 OCI → SIF、来源 digest 记录及失败恢复，再讨论扩大并发；不能仅凭源码研究宣称生产已可续传。

aria2 的 `--continue` 也支持从其他程序产生的顺序前缀继续，但 80 当前没有 aria2c；KISS 方案无须新增工具。若以后使用分段 aria2，应保留它自己的控制文件，不把有洞或预分配文件的总 size 当连续已完成前缀。[aria2 官方手册](https://aria2.github.io/manual/en/html/aria2c.html#cmdoption-c)

## 80 只读观察（由同任务 setup agent 提供）

- `APPTAINER_CACHEDIR=artifacts/cache/apptainer`；实际 `cache/blob` 约 68G、`cache/oci-tmp` 约 56G。
- blob 是 OCI layout：`oci-layout` 版本 1.0.0；index 有 113 个 descriptor，含 Docker v2 manifest digest/size，没有 annotations。
- `blobs/sha256` 当时有 1149 个最终 64hex 文件及 67 个带随机十进制尾的文件；67 个的 mtime/size 均仍增长，属于**在途**，不能称为失败残留，不能更名、删除或接管。
- 观察到真实失败日志 `FATAL ... unexpected EOF`；源码清理行为解释了为何此前失败前缀通常已不存在。
- `~/.local/share/containers/cache/blob-info-cache-v1.boltdb` 不存在。官方 1.4 用户文档仍有 BoltDB 通用说明，但不能据此替代固定版本的实际调用链与该主机观察。
- `pull --help` 无 resume/分段参数；`--no-cleanup` 保留失败 build bundle，不改变 GGCR layer 下载错误时删除临时文件的逻辑。现有工具为 curl 7.81.0，无 aria2c。
- 实物抽检 `compile-compcert` 的 child manifest `sha256:f316947b7be23ad0d187320126eb1cbb5685f48342c6543fdd3ac839aa9e1a7f`：manifest、config、2 layers 共 4 对象、29,725,521 bytes，按 descriptor size/SHA 全部匹配；只读，没有解压或执行。其实际 `oci-tmp` key 为 `ae98945829507132f6b094def3ac5e61a76a3aff884a62b1dfe34df07edeea13`，与 `sha256(manifestDigestHex + "amd64" + "")` 一致。

上述是瞬时观察，未由本研究 agent 访问远端复验。共享 cache 原子注入、GHCR/CDN Range 响应和独立 OCI 本地转换均尚未实测；当前下载进程和在途文件保持原状。
