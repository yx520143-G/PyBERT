# WebUI #2 实施与验收

## 交付范围

Native NRZ/PAM4 的信号链设置、真实 Run/Abort、四类单级/累计响应（含 Rx FFE、DFE 最终权重等效响应）、Channel-only/Rx input/CTLE/Rx FFE/DFE 波形、Rx input/DFE eye、DFE jitter Dist/Spec/Info、DFE/CDR adaptation、两个成功 run 的输入/summary 比较，以及 Native YAML Load/Save/Save As、只读日志和帮助版本入口。

启动：`uv sync --extra web`，然后 `uv run --extra web pybert web`；浏览器打开 `http://127.0.0.1:8765`。HTTP 仅绑定 localhost。默认 GUI、`pybert sim`、`pybert mcp` 入口保留；Web 依赖为可选 extra。Plotly JavaScript 由本机 Python package 提供，没有 CDN。

只支持 #2 正文声明的 Native 执行域。激活 AMI/IBIS、文件通道、FEXT、package、COM、Viterbi、Duo-binary 或手动 impulse length 会明确拒绝；资源路径在未激活模式下保留且不触发模型加载。Native Tx/Rx 且 CTLE disabled 时，File 预设为 inactive，可正常旁路。优化、完整结果档案和其他观察点按 #3–#5/#8–#10 后续交付。MM 是原生固定锁定点；Rx Cac 未被原生消费；RLM 只属于优化。

## 输入与进程契约

- 默认来自真实无仿真构造。完整配置调用原 `PyBertCfg` 加载/tap tuple 恢复；有序 patch 在新实例上触发 observer。Npre 只移位一次，完整 100 槽保存；DFE 使用连续启用前缀，空洞后的原值保留并提示。
- 每次 Run 新建 spawn 子进程。服务内只有一个数值槽，observer normalize 同样占槽；缓存的构造默认 metadata 不产生新引擎。取消请求、观察和真正退出分别记录，父进程 join 后才释放槽。正常 return 或 Ready 均不单独证明成功。
- requested/effective input、输入 hash、run ID、raw、显示投影和训练输出分离。AGC 最终 Level、DFE adaptation 不写回草稿。图/summary/归档日志绑定所选成功 run；当前任务日志另有 task ID。失败/取消不会覆盖两次成功缓存，刷新不取消 worker；服务重启使临时结果不可用。
- raw 保存完整数组及各观察点自己的 crossing/TIE/bin/frequency 上下文。`models/bert.py` 只新增可选局部数据收集参数，默认调用语义与计算顺序不变。实际 source `x` 被保全，没有用 ideal_signal 替代。显示 waveform 取最后20UI有界整数索引；CDR 显示投影取全记录最多4096个索引；两者不参与原始数值/eye/jitter计算。
- 原生 YAML 浏览器下载使用逻辑文件名；不承诺覆盖原路径。Load 失败/文件选择取消保留原草稿、名称和结果，Save As 取消保留原名。只读/未运行字段不会混进输入；没有把 runtime 扩展静默塞进 PyBertCfg。

## 固定来源与计算前冻结

原生语义 `1bc905d577d2f3bd9471421cfbf3d422d4e6080e`；原型/四修复及实际实施 parent `8542f10f4c137f79b3200638f5ee59d36202526a`；实现 PR 为 [#11](https://github.com/yx520143-G/PyBERT/pull/11)，叠加 base 为 `codex/pybert-signal-chain-webui`。#7 保持独立，由 PM 决定进入 master 的顺序。

最终实现代码提交为 `f67f07d54332143d10340b3fd56fedf63d5aab26`。两轴只读复核对该版本均为0新finding，前轮6项整改已闭环；其后的证据/交接提交不改变产品代码。最终Chrome补拍的两fixture成功run也记录此SHA。

首次计算前物化 [fixtures](fixtures/frozen-manifest.json)，其 SHA256 为 `f2bf44622304222455d0501235c230e11100e0cf2d6b0294b0b8284e33c51de9`。10个文件包含真实构造默认、完整 NRZ/PAM4 YAML/JSON、空 runtime 扩展与资源、窗口/容差、环境和整套原型/四修复文件 hash。原文件保持不变。首次实际计算前追加 [execution-freeze](evidence/execution-freeze.json)，SHA256 `934dac3effe4c0f399e41edacee8ffa563f3f2fa574a5ab812f5a4181d412e2a`，包含 Web 依赖、数据目录、producer/axis 和执行源码 hash；每轮报告另记实际源文件 hash。

本目录用局部 `.gitattributes` 的 `-text` 保留审计工件原始字节，避免Git autocrlf改变冻结hash；文本均为UTF-8 without BOM。冻结文件本身没有为此改写，提交前另核对暂存blob与冻结清单逐字节一致。

初次类型校验发现原生 Float 的构造默认可呈整数，而 YAML 加载变成浮点形式（如40→40.0）。输入 hash 改用 `native-json-v1-integral-floats`：排序 JSON key，将整值 float 按整数编码，bool 保持 bool。字段数值、seed、噪声、窗口和容差没有改动。旧扩展文件中的 legacy hash 与 canonical hash 的映射在独立报告逐项保留，不能把两种 hash 写成未变化。

## 已完成的数值与兼容证据

| 证据 | 实际检查与结果 |
| --- | --- |
| [最终数值轮报告](evidence/numeric-20261024-050800/report.json) | 固定原始 bert.py direct-reference 与 fresh Web worker 串行；NRZ311/PAM4312个 raw/context/eye/display 数组均过冻结门槛，最大绝对/相对差异均0；输入、window、metadata匹配；含原生start_ix精确整数 |
| [独立期望检查](evidence/independent-saved-data-numeric-20261024-050800.json) | 每fixture116项通过。只复用保存raw，调用固定原生 `update_results`，独立核对响应/显示转换、PDF/Spec轴、eye counts及电压映射、波形/CDR索引、non-performance summary、complex H real/imag分别比较、start_ix整数与单位；未重跑仿真 |
| [Web 契约测试](evidence/web-contract-af20605.xml) | 25 passed：0/1/100槽边界、15/5下调原生clamp、Npre observer与完整load、inactive File/路径、DFE空洞、YAML、原生preflight return、busy、missing envelope、cancel observed与join、真实spawn及不同cwd版本身份；历史上界用预填31旧记录+2保留记录后执行一次真实spawn检查，不是33次仿真 |
| [兼容测试](evidence/compatibility.xml) | 35 passed，0 failure/error/skip；覆盖原GUI producer、sim thread、MCP配置/Run/metrics/工具注册等 |
| CLI | `uv run --extra web pybert sim .../F-NRZ-01.yaml --results local/cli/F-NRZ-01.pybert_data` 实际成功，DFE errors=0；原生jitter拟合Covariance警告保留 |
| [实际服务失败](evidence/lifecycle-failure.json) | 故意错hash的任务 failed，worker退出后释放；两成功run ID不变 |
| [实际服务取消](evidence/lifecycle-cancel.json) | 在Running DFE/CDR请求取消，requested/observed/worker_exited均有证据；退出前normalize和第二Run均409；两成功run ID不变 |

初次失败分别保存在 `numeric-20261024-043035`（Float类型检查）和 `numeric-20261024-043119`（manifest warnings重复参数与Windows IPC watcher）；修复后 `043542`、`044431` 有效数值轮通过。没有将失败重命名成通过，没有调宽容差或更换fixture。raw NPZ保留在本 worktree 对应目录并被局部 gitignore 排除；Git记录输入、manifest、逐数组差异及复现工具，不把本期临时缓存称作#5完整档案。

最终raw schema为v2：首次v2计算前的 [补充冻结](evidence/capture-schema-v2-freeze.json) 明确增加原生 `start_ix` sample index，未反推时间轴或改变原fixture。`050800`全部数值源文件与交付代码一致，只有 `tasks.py` 在其后追加进程handle关闭、近期任务32项上界和请求落盘顺序；这些生命周期改动由最终25项契约测试覆盖。[版本适用表](evidence/delivery-applicability.json)逐文件记录hash，不声称该数值轮逐字节执行了最终所有源码。32项只限制服务临时任务日志，不清理本票冻结/失败验收材料。

有序patch的最后一项复核见 [真实record队列及原生normalize对照](evidence/ordered-patch-observer.json)：`f_max200 → nspui64 → f_max300`按原序得到300；错误合并顺序得到160。只合并相邻同字段，维数编辑不合并，没有运行数值仿真。输入错误与存储失败分离另由 `verify_web_storage.cjs`直接运行所交付的Native页面handler验证。

## Chrome 与原生 GUI 边界

真实桌面 Chrome 1280×720 的本票截图保存在 [chrome](evidence/chrome/)，并有当前焦点输入、YAML实际下载/原生重载 hash、失败/取消任务与旧成功 run 分离的记录。这些截图与历史 PR #7 原型截图分开；不跑窄屏或速率资格矩阵。标为 `premature-*` 的5张是抓取早于渲染稳定、与文件名内容不符的非通过记录，不能作所称图表证据；补拍及逐图支持范围以Chrome索引为准。

逐图索引见 [Chrome INDEX](evidence/chrome/INDEX.md) 与机器可读 `screenshot-index.json`。12张最终图表/帮助原帧已逐张目视确认；原5张过早截图、额外前帧及历史原件全部保留并排除在所称图表通过证据之外。PNG内容区1265×712与实测CSS viewport1280×720分别记录。配置提交、Undo、Escape、current-focus和Abort各自用实际DOM/任务ID/文件检查证明，不仅凭图片文件名判断。

原生 TraitsUI 窗口实际启动并可见/Ready；[当前日志](evidence/native-gui-smoke.stderr.txt)与[固定原始函数日志](evidence/native-gui-reference.stderr.txt)均保留 `_dfe_tap_tuners_changed` 的 `self.dfe` AttributeError各2次及Chaco GridMapper `NoneType.high_pos`异常各8次。`src/pybert/pybert.py` 相对原生SHA未改。该证据支持“当前环境下未见新增GUI启动回归”，不表示GUI零错误或全交互验收；本票没有趁机修这些原生/Chaco问题。

复现工具位于仓库 `tools/freeze_web_fixtures.py`、`verify_web_numerics.py`、`verify_web_saved_data.py`、`verify_web_lifecycle.py`、`smoke_native_gui.py`。freeze工具拒绝覆盖已有冻结目录；重新验收应保留旧结果与源码版本。

本票证据是对固定 Native 执行域的接入一致性验证，不代表 MATLAB COM correlation、IEEE 标准资格、硬件资格或任意输入范围的数值保证。最终风险终审/集成由 PM 收口；#2 在该流程完成前保持 open。
