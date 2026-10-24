# #10 B/C/D clocks 接口合同与串行实施计划

2026-10-24（Asia/Shanghai）。**这是设计交付，不是产品修复或 clocks 资格验收。** A 已按 PR23 集成；本阶段不重复 A。E 仍 `SOURCE_BLOCKED`，有效 NRZ/PAM4 clocks 仍 `BLOCKED`。

本次修订响应 PM 对设计提交 `ed23bfb6ca0fb8f252849a655c9e8240609e1ff2` 的 P2：原合同漏列 Web 自有数值消费，只有 Native update_results 与 metadata 仍不足。新增 [Web 数值消费/保存合同](web-consumers-p2.md)，补齐 collect、eye_data、clock_data、extend_analysis 两处 Eye、masked period/raw、真实 FFT 窗与预算。没有启动产品实施；ed23 工具、receipts 和旧 seal 原 bytes 不变，README/review 的旧版仍可在该 commit 查阅。

基线 HEAD `35a71a6b79a00693a2f2862184552894752899c0`，tree `d8334daffacbc19cc638b03bbdc2dc3f9736be7e`。新 worktree `C:/Users/yx/.codex/worktrees/pybert-clocks-contract/serial-bus-simulator`；显式分支 `codex/pybert-clocks-contract`。PyAMI 固定 `5270d713e40bac2be5747bef09b92df79df9085b`，PyChOpMarg 固定 `ca905e793fcf6330929471317ca32e7611578e5d`。未初始化/修改 submodule。产品、依赖、旧证据全部只读；仅本目录有新写入，无新 PR。

## 1. 决策摘要：现状—候选—推荐—影响—验证

以下推荐都须由 PM 审查后另定义实施票，**不是本阶段已批准的产品行为**。

| 事项 | 现状 | 候选与推荐 | 会改变的分支 | 必要验证 |
|---|---|---|---|---|
| B 严格性 | getWave 无 use_clocks 参数；整 buffer 聚合，没有格式失败状态 | **推荐保留三元组，默认严格拒绝 malformed**；合法无 clocks 返回空有效向量。若需保留坏 clocks 的 waveform-only 用途，另票设计结构化结果，不把坏数据变空 | 所有调用 getWave 的路径，包括不消费 clocks、response probes、Init helper 中的 GW probes | 合法/非法 prefix、返回码、跨 wrapper epoch；明确兼容接受后实施 |
| B 依赖来源 | 上游 gitlink、uv editable；普通 pip 仍 registry 范围 | **推荐经 yx fork 固定 commit F，再让 workspace/gitlink 与标准直接 URL 依赖一致**；需接受 PyPI 发布限制。另一选项是 registry+显式 requirements，但裸 pip 不获修复 | uv、源码 pip、未来发布包 | 双安装来源/hash；禁止隐藏 site-packages patch |
| C 清理 | initialize 先 Close 旧 handle，后面才重设；析构 Close 不清 handle | **推荐公开幂等 close() + finally**，在 Init/析构复用；对照“修幂等析构后显式调 __del__”最小方案，后者耦合私有生命周期且不推荐 | PyAMI 对象生命周期，失败路径 | 已 Close 后准备失败、显式 close 后析构、Init 失败非空 handle、Close 失败不重试 |
| C 状态 | 两次响应 probe 和真实 wave 共用 Init epoch | **推荐顺序独立 probe/main 实例**；可行备选为同实例 Close+重新 Init，节省一次逻辑加载 | 首阶段只接 Native/Init Tx + Rx GW，含不请求 clocks；不附带改 TxGW/Init Rx | 角色/输入/Init/Close 次数、main 首次 GW 原点、失败清理 |
| C 分块 | 原 helper 的 0 实际沿用 probe 设的 40，而非 Init 默认 | **推荐在上述 Rx 分支显式保持当前有效 40**（仅请求为 0 时）；实际非零请求原样保留。恢复 Init block 是另一个行为变化 | Rx GW 的 C 分块、params 历史、成本；PyAMI 0 的公共含义不改 | row_size/nspui、实际 block、短末块；模型限制必须在 freeze 中满足 |
| C 随机性 | get_responses 的 default_rng() 独立于全局 seed | **推荐可选私有 rng API**；目标 Rx 调用用已冻结非零 run seed，其他调用默认行为保持 | Ignore_Bits>0 时的响应 probe 输入/响应；不消耗 main 全局 RNG | 正/零 seed 区分、输入 bytes、全局 RNG 未被 probe 抽样 |
| D 半 UI/最后 tick | 注释及 slicer 将向量当 edge；pairwise 操作对象错误；Viterbi 使用 ceil grid，Eye 使用 floor grid | **推荐分离 edge、target、producer index，逐 tick 消费，包括末 tick**；canonical engine clock_times 为实际 grid times，AMI 下游复用 producer indices | AMI branch 的 decisions、Viterbi、Eye、interval 分析；Eye 新增最小索引入口，Native 原入口不改 | off-grid 与浮点 floor、末 tick、尾部选择、相对裁剪索引；不假定所有 DLL 遵守 edge 合同 |
| D Ignore_Bits | 378 初值 0，仅 396 TxGW+RxGW 读取，实际可用 Rx clocks 分支未读 | **推荐实际 Rx 能力与声明单位驱动，以 elapsed UI 判适应就绪**；不将其叫模型 CDR lock | AMI clocks 的适应窗口及标签 | delayed clocks、NRZ/PAM4、fixture 对旧版本单位的声明 |

## 2. 固定主源与证据分级

标准原文：[IBIS 5.1 §10.3，印刷 170–171 页](https://ibis.org/ver5.1/ver5_1.pdf#page=170)；[IBIS 6.1 §10.2.3，印刷 188–189 页](https://ibis.org/ver6.1/ver6_1.pdf#page=188)；6.1 §10.6 印刷 232 页解释 PAM4 symbol time。5.1 的 clocks 合同不依赖后来的 PAM4 参数；不能把新规范所有参数强套旧模型。

本文以 **S（规范要求）／P（推荐实现选择）／U（未知或待模型证据）** 区分。源码事实可追溯到：

- [PyAMI model.py@5270d713](https://github.com/capn-freako/PyAMI/blob/5270d713e40bac2be5747bef09b92df79df9085b/src/pyibisami/ami/model.py)：335–345 析构，364–455 Init，458–523 GW，525–640 response probes。
- [PyBERT utility/ibisami.py@35a71a6b](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/utility/ibisami.py#L77)：helper 的输入/返回、Init、probes 和真实 wave。
- [bert.py@35a71a6b](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/models/bert.py#L368)：378/396 Ignore_Bits，433 Rx GW，562–563 入口，599–625 采样，721–729 Viterbi，831–833 保存，1258–1275 CDR 图，1414–1421 Eye。
- [pybert.py@35a71a6b](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/pybert.py#L588)：588–598 time grid，651–678 UI/nui/eye_uis；1323–1332 原生 DLL observer。
- [dfe.py@35a71a6b](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/models/dfe.py#L324)：324/334 初始化采样时刻，352 实际采样，388–389 每次消费后追加下一预测时刻；[sigproc.py::calc_eye](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/utility/sigproc.py#L395)：408 将 clocks 定义为 eye centers，433–438 直接从该时刻的 grid 位置取 2 UI trace，没有隐式加半 UI。
- [web/worker.py](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/web/worker.py#L84)、[web/ami.py](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/web/ami.py#L205)：worker 85/105 两次 new_engine，configure 210 每 active AMI side 的未 Init 加载，capture 从 114 才开始；360–384 为现有弱谓词 metadata。
- P2 新增 owning source：[web/data.py::collect](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/web/data.py#L89)、[web/analysis.py](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/web/analysis.py#L50)、[archive.py](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/web/archive.py#L50)、[web/viterbi.py](https://github.com/yx520143-G/PyBERT/blob/35a71a6b79a00693a2f2862184552894752899c0/src/pybert/web/viterbi.py#L107) 及 web/__init__.py 版本声明。精确入口/行号/静态图在补充合同；新增 source hashes 与旧15输入的并集由新 `verification-v2.json` 记录。

[stub-results-v2.json](stub-results-v2.json) 保存 13 个只读输入的运行前后 SHA256、工具 SHA、AST 定点核对、普通数组/状态例子；[downstream-source-check.json](downstream-source-check.json) 补充 bert/dfe/sigproc 三个源码输入的 AST 表达式检查，合计 15 个不同只读输入。源码 hash 是磁盘原 bytes；Windows checkout 与 Git blob 可有 EOL 差异，以固定 commit/AST/clean 状态判来源，不把这种差异说成算法变更。

## 3. B：每次 C call 到 Python API 的合同

### 3.1 必须规则、实现选择和未知

| 合同 | 级别与具体预期 |
|---|---|
| 有效长度 | **S**：每次 C call 的精确首个 `-1` 之前是有效 prefix；无 clocks 时首项 `-1`。其后槽位没有有效 tick 身份，不判其 NaN/陈旧值为有效 prefix 错误 |
| tick 时间 | **S**：seconds，相对本 Init epoch 首次 GW 的仿真起点；非负，**0 合法**；单次及跨 call 严格递增，相同也失败 |
| 跨 wrapper | **P，落实 S**：last_tick 属于 model Init epoch，跨 Python getWave 保留；空 prefix 不清 last；成功新 Init 重置。格式错误后 epoch 标成不可继续，禁止从部分成功聚合续跑 |
| 数量和短末块 | **S**：clock 数不要求等于 waveform UI 数；wave_size 可变化。短末块只按实际 waveform 长度调用，不从短块长度推测 clocks；不得按 UI 截断、补 tick、排序或过滤正值 |
| 半 UI | **S**：采样为 tick+bit_time/2，PAM4 为半 symbol time；可以落下一波形段。B 不按当前 C chunk 时窗过滤 |
| NaN/Inf | **P**：有效 prefix 要 finite；标准该段未逐项使用 NaN/Inf 字样。不能用未写槽位的 NaN 作为 sentinel |
| buffer 初始化 | **P**：每 C call 前整 buffer 填 NaN；不能填 `-1` 掩盖模型漏写。保留当前 `B+8` 兼容余量，不循环复用陈旧尾槽 |
| 容量 | **S**：EDA 容量大于预期 clocks；**U**：标准没有 `B+8` 普适上界。后验 sentinel 检查不能防止 DLL 已越界；fixture 必须给 max/expected clocks 的容量依据，未知则不执行真预检 |
| C 返回码 | **S**：GW 1 成功、0 失败；成功不等于 CDR locked。当前 505–508 未检查返回码，B 应保存并检查；异常码也不得当成功 |

### 3.2 API、错误与兼容

真正落点是 **PyAMI** `src/pyibisami/ami/model.py`：最小纯 prefix helper、`AMIModel.getWave`、Init epoch reset，以及定向纯测试。保留 `getWave(wave, bits_per_call=0) -> (wave, valid_ticks, params)` 三元组和 waveform/params 顺序；clocks 变成纯有效 edge 向量，不含每块 sentinel/padding。合法全 `[-1]` 归一为空向量；这是 no-clocks，不是 model failure。

推荐格式错误/返回码失败抛带 epoch、C/Python call index、原因的专用异常；原 per-call buffer、C 状态和已经返回的 wave/params 应在 fail 原件里保存，不能发布部分数组为成功。边界对象已推进，失败后需要新 Init；不自动重试/继续。

**默认 strict 是需要 PM 接受的兼容变化。** 当前 getWave 无 use_clocks，所以严格性也作用于：不请求消费 clocks 的 Rx/Tx GW、被丢弃 clocks 的 probes、以及 use_getwave=False 但模型提供 GW 时仍调用 probes 的 Init helper。过去忽略错误 clocks 而得到波形的情况会失败；不改写其历史成功原件。如果 PM 要保留 waveform-only 接受坏 clocks，需另立结构化结果 API（`malformed` 与 `no_clocks` 分开，前者 usable_ticks=None），而非把错误藏进空数组。

### 3.3 来源交付路线

2026-10-24 的只读连接调查：`yx520143-G/PyAMI` 查询 404；owner 的 9 个当前可见仓库未发现可用 PyAMI fork。上游 capn-freako/PyAMI pull=true/push=false，yx/PyBERT 可 push。**只能说当前连接未发现，不能证明账号全局不存在不可见 fork。** 本轮未创建或 push fork。

集成来源：`.gitmodules:1–3` 指上游 PyAMI；`pyproject.toml:24` 仍 `pyibis-ami[gui]>=10,<11`，140–148 uv workspace editable；`uv.lock:3654–3657` 为 PyAMI 10.0.0 editable。只移 gitlink 只能覆盖该 workspace，不能覆盖普通 pip。此区别由 [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/) 和 [dependency sources](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-sources) 官方文档确认。

推荐后续来源票：PM 授权创建/确认 yx 拥有的 fork，从固定 5270d713 做 B/C0 最小改动，独立 PR 审查固定 commit **F（本轮未产生）**；PyBERT 再更换 `.gitmodules` URL、gitlink、标准 dependency 的完整 commit direct URL，并从实际 metadata 重新生成 uv.lock；workspace 同样必须 checkout F。禁止只改本地 editable/site-packages 或另藏 patch。

直接 URL 可使源码 uv/pip 自动指向同一 F，但 [setuptools 官方文档](https://setuptools.pypa.io/en/latest/userguide/dependency_management.html#direct-url-dependencies) 说明含此类依赖的发行不能上传 PyPI；[pip VCS 文档](https://pip.pypa.io/en/stable/topics/vcs-support/#git) 支持完整 hash pin。若必须保留 PyPI 发布，则用 registry dependency+审核过的显式 pip requirements，清楚标记裸 pip 不含 fork 修复，等待正式发行。两条路线不能混称“全部安装方式已迁移”。版本号、F、lock diff、双安装来源核验仍未执行。

## 4. C：状态、时基、分块和清理

### 4.1 当前调用图（不是本轮执行记录）

```mermaid
flowchart TD
  Q[可选 prepare: 每 active AMI side 加载未 Init 模型 Q] --> H[run_ami_model: Load S]
  H --> I[Init S 一次]
  I --> P[get_responses: Bp=40]
  P --> P1[Python GW step: I+20 UI / C分块]
  P1 --> P2[Python GW channel-step: 同一 S / I+20 UI]
  P2 --> M[真实 Python GW: 同一 S / N UI]
  M --> R[返回 wave/clocks/params 与 responses]
  R -.-> Z[析构 Close: 实际时机 UNKNOWN]
```

`I=Reserved Ignore_Bits`；同一个 probe 输入 u 用于两次 probe。get_responses 的局部 `default_rng()` 不受 main 的 `np.random.seed(self.seed)` 绑定；I=0 时没有随机适应前缀，I>0 时不能声称 probes 可由 main seed 重放。现有 probes 设置实例 block=40，主 wave 的请求 0 继承它；Init 原始 block 则是 row_size/int(UI/ts)。

模型符合规范时，真实 wave 时钟原点仍是 S 的第一次 probe GW；toy I=0 时主 wave 在 40 UI 后开始。这与旧 4 ns 观察相符，但不是对任何 DLL 的保证，更不是减 4 ns 修旧结果的许可。

### 4.2 推荐调用图与备选

```mermaid
flowchart TD
  Q[prepare Q: 保留现有 ABI-only 检查] --> P[Load probe P / 新 Init P]
  P --> R[get_responses P: 两次 probes / 原相对顺序]
  R --> PC[复制响应与角色诊断 / finally close P]
  PC --> W[Load main W / 新 Init W]
  W --> G[真实 GW W / 显式 effective Bm]
  G --> WC[复制 wave/clocks/params/msg / finally close W]
  WC --> O[原6元helper返回 / 另保留角色与epoch诊断]
```

推荐 **顺序独立实例**：同时至多一个有效 AMI memory handle，probe/main 角色和输出来源清楚；不承诺 OS DLL 映像重新加载或全局静态变量重置。h/out_h 来自 P；wave/params/clocks 和主要 Init msg 来自 W；两个 Init 的实际输入/输出/msg 分别留证，不能把 probe 信息冒作 main。所有在 Close 后使用的结果必须是已复制的 host-owned 数据。

同实例重新 Init 是可行备选：逻辑 load 1、Init 2、Close 2，main 也获得新 memory epoch；但角色/残留 wrapper 状态更难审查。当前 initialize 虽已先 Close，却直到参数准备/能力检查之后才重设 handle；中间异常会让析构仍看到旧非空 handle。两方案都先依赖生命周期修复，不能直接复用当前 unsafe 失败路径。

**生命周期对照**：最小无新公开名方案可修幂等 `__del__`、initialize 的 handle 清理，并在 host finally 显式调 `__del__()`；可达到清理，但 host 绑定析构实现，关闭后使用规则不清。推荐公开 `close()`，不顺带增加 context-manager 框架：取旧 handle、先置空再调用 C Close，initialize 和析构复用；host finally 显式 close。重复 close/析构为 no-op。Init 返回 0 不进入 GW，若返回非空 handle则清理一次；Close 失败保留原错误与 cleanup 状态，已关闭对象不自动重试，资源释放是否成功为 UNKNOWN。未 Init 的 Q 不产生 C Close。此 API 当前不存在，尚未获实施授权。

### 4.3 推荐 scope、输入与变化

- 先仅在 Native/Init Tx + Rx GW 的 helper 调用选择隔离，不附带改变 TxGW 或 Rx Init 的现有调度。`run_ami_model` 的公开默认保持兼容，可用最小内部 keyword 明确选择隔离；不新增用户 UI 开关。其余分支受 B strict 的影响另见兼容表，不能借 C 顺手停掉 Init probes。
- Bp=40、probe nbits=20、max_run_length=10 只是固定源码的现值，保留原 probe 顺序，不声称标准或所有模型的合法默认。主请求非零 B 保留；请求 0 时，推荐仅在隔离的 PyBERT Rx helper 明确传有效 Bm=40，以保持原分块。PyAMI 的 0 仍指 Init/实例已有值，不全局改默认。每个 fixture 必须冻结其真正允许的 B 和短末块。
- 推荐 `get_responses(..., rng=None)` 可选 API，默认保持原行为；目标 Rx 调用传私有、非零已冻结 run seed 的 Generator，不抽 main 全局 RNG。seed=0 继续 fresh entropy，不作为可精确重放的资格输入；若未捕获实际 entropy，保留 UNKNOWN。
- main 新 Init 后从实际原 waveform 第一个样本开始，不加/删适应输入，不用 probe 结果“补训练”。其前 I 个输出 UI 是实际 main 适应期；wave、params、clocks 都可能与旧共享状态结果改变，方向/幅度 UNKNOWN。I>0 时固定私有 probe seed 还会改变旧未冻结 probe 输入，应在 C 票中单列。
- 当前 response probe 即使在 PAM4 下仍是两电平 ±0.5 step；本票保留该算法，不据此声称得到 PAM4 自适应响应或 golden。fresh main 也可能返回不同 params 历史/结构，应由已经集成的 A 合同真实校验，不能放宽 A 或合成旧历史来掩盖变化。
- Init 输入矩阵、FEXT 行、AMI 树、ts/UI 必须重新按同一冻结内容构造，不能让 P 修改的输出 matrix 或参数成为 W 输入；两个 Init 内部仍可能有模型随机性，需 golden。
- 当前 `int(UI/ts)` 的非整数采样比问题不在本次最小票；首批资格要求冻结整数 ratio，非整数保持 unsupported，不能悄悄取整后声称支持。

## 5. D：全局记录上的采样与证据合同

### 5.1 时间、末 tick 与分析窗

**S** 定义的是模型 edge ticks；当前代码将返回向量解释为 edge 是源码事实，不证明任意实际 DLL 遵守。只有 B 格式/epoch 和合法模型声明验证后才能用半 UI 转换。PyBERT `_get_ui` 已对普通 PAM4 将二进制 bit period 乘 2；D 应直接加传入 symbol UI 的一半，不能再乘 2。具有非零 PAM4 三眼 offset、不同 mapping/threshold 的模型，若现有 dummy slicer 不能解释其声明，则应明确 unsupported，另立消费范围，不能从“输入 PAM4”推断已支持。首批限定声明与冻结 native slicer 一致、nominal eye offset 为 0 的 profile。

推荐最小纯采样规划函数以 `(valid_edges, t_grid, symbol_UI, Ignore_UI, frozen_analysis_window)` 输入。分析窗同时冻结 `[start,end]`、所需 W 个实际决策、连续 period 区间及实际 timed-eye trace 条件；目标时刻与 actual grid time 都必须落窗内，不用只有下界的检查替代完整窗：

1. 再核对有效 edge 向量 finite、非负、严格递增，且不再含 sentinel；保留 raw buffer 和有效 edge 原文。
2. 对 **每个** tick 计算 `s=edge+UI/2`，包括末 tick；用整个已收齐的 waveform grid，不以 C chunk 边界裁剪。
3. 仅 `t[0] <= s <= t[-1]` 可消费，索引为第一个 `t[i]>=s`，与原循环意图一致；不改成 nearest/interpolation，不夹到首末格，也不放宽 epsilon。最后一个 grid sample 的精确等值可消费；稍后时刻只能标记 deferred/out-of-record。
4. 原始 future tick 是合法格式，可因下个 chunk 有数据而变可消费；到全记录结束仍无数据时保留其 deferred 原因，不补波形。负/非有限是格式错误；不能用“窗外”名义修复它。
5. 多 tick 映射同一 grid index 时，当前 binary clocks mask 无法无损表达：拒绝为 unsupported_resolution，不去重或丢一个 decision。
6. 分别保留 `ami_clock_edges_s`、`ami_sample_targets_s=edge+UI/2`、实际消费的 `sample_indices` 及 `sample_grid_times_s=t[sample_indices]`。推荐 AMI 的 canonical `clock_times` 为后者实际 grid times；目标时刻不是实际取到数据的时刻。Viterbi 与 Eye 复用 producer indices，不再各自从秒数舍入。另一可行合同是 canonical 保持 consumed targets、所有消费者另读 indices，但更易误读，本文不推荐。两种路线都必须保存原 targets 与量化延时，且需 PM 冻结。此项会改变旧 AMI 分支的后续半 UI 相位；ceil 量化延时为 `[0,ts)`，不是放宽 tick 合法性的容差。Native CDR 的既有 basis 不改。
7. 消费所有可消费 tick，与估计 period 解耦。N tick 有 N 次可能采样、N-1 个已观察 interval；不能因 pairwise 少一个 interval 而删末 tick，也不能复制 nominal UI 造末 interval。

**下游尾部规则必须联动。** Native `run_dfe` 每次实际采样后会追加下一预测点，原 `clock_times[-(eye_uis+1):]`、过滤窗外、再取 `[:eye_uis]` 的 Viterbi 规则利用了这个未来尾点。AMI 新 canonical 向量只有实际消费点，不能沿用该截取：手工例子 tmax=2.75、eye_uis=2，Native `[0.5,1.5,2.5,3.5]` 得 `[1.5,2.5]`；实际点 `[0.5,1.5,2.5]` 沿旧规则却得 `[0.5,1.5]`。D1 必须为 AMI 选择冻结分析窗内实际最后 W 个点/producer indices，得到 `[1.5,2.5]`；Native 原规则保留。这里仅执行提取的 AST 表达式与手工数组，不是实际 Viterbi、重采样或解码运行。

`calc_eye` 当前对 clock time 使用 `int(clock_time // tsamp)`，没有隐藏半 UI 修正；**仅传相同秒数还不够**。off-grid target=0.6、ts=0.25 时，decision 的 ceil index=3，而旧 Eye floor index=2；即便 canonical 改成 grid times，也不能用浮点整除反推 index。推荐给 `calc_eye` 增加最小可选 `clock_indices` 入口，仅 AMI timed-eye 调用传 producer index 减去实际 waveform 裁剪的 `ignore_samps`，过滤负值和不足完整 2 UI trace 的末尾；Native 原 clock_times 入口与绘图算法保持。Viterbi 同样复用所选 indices，phase 计算基于 actual grid times，保留 targets/quantization delay 供复核。记录末尾的有效采样点可能没有后续完整 2 UI trace；分别记录 consumed sample count 与实际 timed-eye trace count。完整分析必须满足冻结窗实际 trace 条件；没有实际 timed trace 时不得用 auto-timed Eye 冒充 AMI clocks 图。原手工 edge=0 / target=0.5、ts=0.25 的 first_ix=0 / 2 仅证明没有隐藏半 UI 修正，不能证明 off-grid 消费一致，更不构成图像/数值验收。

**P，完整建议**：period 原数值为相邻有效 edge 差；映射到 ui_ests 时仅使用相邻实际消费的 producer indices 之间的 grid 区间，区间值仍是对应 edge 差，不是量化后的 grid-time 差。前后未知用显式 mask/NaN 表示，不能填 0；不借尚未消费的 future tick 伪造一次采样。AMI 分支的 histogram 只用已知值，FFT 只用冻结分析窗内连续、已知的原 ts grid（至少 2 点），保存实际 window/axis；不把无效 mask 当均匀零噪声。Native 分支保持现流程。`update_results` 的 histogram/FFT/plot 必须随此合同一起适配，不能只修 pairwise。

Ignore_Bits 不是模型 lock：6.1 印刷 206 页仍使用 bits 名称；[IBIS 8.0 §10.4 印刷 252 页](https://ibis.org/ver8.0/ver8_0.pdf#page=252) 明确为输出 UI 个数。推荐项目按 UI 记录 `Ignore_UI`，NRZ 无歧义；旧 PAM4 模型必须有提供方对单位的确认，不能静默除 2 或用新规范替旧模型作承诺。适应就绪以 target sample time 达到 `Ignore_UI*symbol_UI` 判断，不能因 ceil 量化越过门槛就提前就绪，也不按第几个返回 tick；模型可以延迟/稀疏出 clocks。所有正式 Rx GW 路径读取真实配置，缺省按对应声明 0，未返回真实 cdr_locked 则 model-lock 仍 unavailable。

完整 Main 资格还要求冻结分析窗内有足够实际 decisions/samples 供原 eye_bits/eye_uis，以及有效 period 窗。此为 **P，声明分析的可用性条件**，不是“每 UI 必须一个 tick”的格式要求。合法但只有一个 tick/覆盖不足：format-valid，但 full-analysis 不 eligible，不以 Native fallback 或 BER 前补零掩盖；原始失败/部分采样保留。不得事后缩短窗口或将自动无时钟 Eye 当 AMI timing 验收。

### 5.2 returned / format-valid / eligible / consumed

| 阶段 | 必须来自的实际证据 | 不能推出的结论 |
|---|---|---|
| returned | C call 返回状态、完整容量 buffer、params、wave_size、role、Init epoch；失败也可以已返回部分数据 | 返回码 1 不代表 CDR 锁定或采样成功 |
| format-valid | B 每 call sentinel/prefix、finite、非负、跨 epoch 合同；合法全空另记 no-clocks | 格式合规不代表覆盖当前记录/分析窗或调制匹配 |
| eligible | 请求/模式为 RxGW、排除当前 TxGW 限制、格式合规、main origin 可证、grid/调制/窗口/唯一索引满足本 profile | 计划可消费不代表循环真的完成 |
| consumed | producer 记录实际分支、sample times/indices、消费数量、末 tick/deferred、完成/取消/失败；来自采样 loop 后的观察结果 | 不能由原先 len/first 的谓词或 adapter 重算替代 |

`consumption_status=not_attempted/partial/completed` 应明确分开；有部分数组的 failed 任务不能标 completed。Native 执行也须有 run_dfe 完成证据，不能仅因为 AMI 不 eligible 就说 Native 已执行。

合法 no-clocks+请求 clocks：允许原 Native DFE/CDR/AGC fallback，标签说明真实执行范围；malformed/未知 origin/非空覆盖不足：推荐失败且不自动 fallback。未请求 clocks、非 RxGW：维持原模式；B strict 若先失败不得被 D 吞掉。TxGW+RxGW 当前丢弃 Rx clocks，继续 unsupported 消费并按原实际 Native 分支记录，不借本票接通它。

推荐 metadata schema v2：raw C buffer 是 slot 轴，valid_edges 是 epoch 绝对 seconds；targets 保留半 UI 转换值，producer indices/grid times 才是实际取样位置，engine clock_times 使用后者。period 与 mask 有实际窗口/来源，索引保留完整 waveform 与 Eye 裁剪后两种 origin。记录 role、epoch、requested、format status、eligibility reason、consumption status/count、timed-eye trace count 与实际 producer 分支。旧 schema1 保留历史原字段语义和未知，不重标签为新资格。失败/取消的 raw 与 producer partial 信息要由 finally 留存。producer 可用最小 `ami_clock_info`/interval mask 状态让 GUI 与 Web 共享；不另造模型内 taps/lock。

### 5.3 Web 数值消费者是 D 的必要边界

上文 metadata v2 指拟议 AMI clock contract；不能与当前 Web manifest schema1/raw5 混同。worker 的 Main 使用 `update_plots=False`；其后的 `collect` 与 `extend_analysis` 自己调用 Eye、histogram、FFT，且不在当前 AMI capture 内。只修 Native update_results 不覆盖 Web。

具体合同见 [P2 补充第2–4节](web-consumers-p2.md#2-masked-period-的-raw派生显示与-archive)：ui_ests 保留 full t 长度/ps/原未知 NaN，配 producer bool `ami.cdr.period_known`，只经专用 masked-period 保存/读取校验，普通 raw finite gate 不变。新 AMI 记录建议 raw6+明确 feature 门禁，Native/旧 raw2–5 保持；archive 也必须配对验证 mask，不能全局关闭 finite 检查。manifest 无 NaN；known compact/分段显示与原 dense raw 分开，无伪造0。

collect 的 DFE Eye 和 extend_analysis→eye_data 的 DFE Eye 同时使用绝对 producer indices，扣各自实际 slice 的 ignore_samps，核对完整2UI trace及冻结 stop，分别保存 consumed/selected/trace count；无完整 trace 两处都 unavailable，不自动 nominal fold。histogram 只取冻结窗内 known grid 值；FFT 只取预冻连续全known窗，频轴按 `k/(n_fft*ts)`，ts不取裁剪后的绝对t[1]；空/断裂/不足窗不计算。末尾source/window更新不得覆盖实际子窗为full_record。Web Viterbi 的旧W+1说明/校验也须与D1新indices相符。

这属于 D2 的实际数值实现与保存依赖，不是可选 metadata 接线。D1先提供可信 producer 契约，D2全部接通后才可声称D完整；当前仅新增普通数组/AST示意，相关真实入口仍0。

## 6. 可转实施票的串行边界

| 顺序 | 仓库／精确文件/API | 零真实调用验收与依赖 | 影响/风险 |
|---|---|---|---|
| S0 来源与政策 | PM 确认 yx fork 和 strict/发布路线；无本轮仓库创建 | 只读权限/许可/固定基线；决定 direct URL 的发行限制 | 还没有 F，不能给执行环境打隐藏 patch |
| B1 prefix/状态 | PyAMI model.py：最小纯 prefix helper、getWave、Init epoch reset；定向 tests | 真实模型/引擎 0；普通 buffers/假 C status；覆盖跨两次 Python GW、空 prefix、缺 sentinel、短末块和 poison epoch | 默认 strict 扩大失败范围；clocks shape/API含义改变，wave/params不靠过滤修复 |
| C0 生命周期/rng | 同 fork model.py：close、__del__、initialize 状态与返回码；get_responses 可选私有 rng | 纯对象/状态 replay，特别 Close 后准备失败；复制结果后释放；B1基础上固定 F | 新公开 close/rng API，老默认调用保留；不能假定 DLL globals 已重置 |
| S1 安装迁移 | PyBERT .gitmodules、PyAMI gitlink、pyproject.toml、uv.lock；必要安装说明/来源测试 | 两种安装方式确认 commit/path/hash，均不构造模型或跑引擎；F经独立review | 元数据/锁实际变化待产生，安装成功≠数值验收 |
| C1 Rx 协调 | utility/ibisami.py::run_ami_model；bert.py Native/InitTx+RxGW 调用点；纯调度 seam/tests | 只验证普通状态调度或提取的实际纯协调函数，不能用实数值helper代替；依赖 S1 的 close/rng | main fresh Init、前 I 输出、seed、B 的前后改变逐项冻结；TxGW/InitRx不附带改 |
| D1 Native 消费 | bert.py::my_run_simulation、update_results；pybert.py 必要 clock-info/mask 状态；sigproc.py::calc_eye 可选 clock_indices 入口；最小纯采样规划 helper/tests | B/C合同到位；手工 arrays 证明每tick、末tick、halfUI、双边界分析窗、Ignore、collision、off-grid/floor、尾部选择、Eye 相对索引与 trace 覆盖；0真实计算 | canonical actual grid times 连同 AMI Viterbi indices、Eye 索引入口、AMI period mask 一起落地；Native原路径不变 |
| D2 Web数值消费/采集/保存 | data.py::collect/add/两处前置Eye与CDR投影；analysis.py::eye_data/clock_data/clock_display/extend_analysis及末尾窗口；web/viterbi.py::extend/validate；archive.py::read_arrays/validate_run/save_archive/load_archive与版本能力；ami.py::Execution、worker capture/finally | 依赖D1的mask/绝对indices/真实分支；[P2零模型矩阵](web-consumers-p2.md#5-串行票依赖与零模型验收矩阵)覆盖masked raw、两处Eye、known histogram、连续FFT窗/轴、旧schema和失败保存 | 全部是必要数值消费者；不只改metadata；不全局放宽finite、不补0、不用auto Eye伪装；计入Web实际helper成本 |
| E1 合法包/有界真预检 | 来源原包、许可、ABI、调制、容量、连续 call golden；新预检 harness | **必须**资源到位且 PM 新预算；本轮无额度 | 现存 NRZ示例 build mapping/尾sentinel仍未知，PAM4缺合法fixture |
| E2 真正配对验收 | 固定最终源码/依赖/配置/每角色 input/seed/B/epoch/窗/容差与 instrumented harness | NativeTx+RxGW 每调制 direct/worker 独立实例；raw、wave/params、采样、分析与实际metadata | 一致性不替代 golden；failed/partial不计通过；其他3x3模式另freeze另预算 |

最小真实资源清单沿用 [既有 E 候选与清单](../clocks-gate-audit-20261024/README.md#候选-fixture-与获取路径)，本轮不泛查供应商、不账号取包、不联系、不下载/构建 DLL。可先交付 B1/C0/S1/C1/D1/D2 的零模型软件证据，但不能因此写真实 NRZ/PAM4 通过。

## 7. 后续预算草案：按所推荐图计算，未授权执行

仅 **Native Tx + 单 Rx GW**，两边不含其他 AMI side，COM/coopt=0。令 S=nspui，N=真实输入 symbols/UI，I=确认单位后的 Ignore_UI，Bp=冻结 probe block，Bm=冻结 main block，P=I+20；

`Gp=ceil(P/Bp)`，`Gm=ceil(N/Bm)`，每次 helper 的 C GW 上限为 `2*Gp+Gm`。实际短末块必须按样本数再核对；以下整数 ratio freeze下等价，非整数不套用。

| 一个完整 helper 成功的 API | 现有共享模型 | 推荐顺序双实例 | 同实例安全 reinit 备选 |
|---|---:|---:|---:|
| run_ami_model | 1 | 1 | 1 |
| AMIModel 逻辑构造/库绑定 | 1 | 2 | 1 |
| Python initialize / C Init | 1 / 1 | 2 / 2 | 2 / 2 |
| get_responses | 1 | 1 | 1 |
| Python getWave | 3 | 3 | 3 |
| C GetWave | 2Gp+Gm | 2Gp+Gm | 2Gp+Gm |
| 显式 C Close | 0，实际析构时机/次数不由该接口保证 | 2 | 2 |

双实例表的 load 是两次 AMIModel/CDLL 绑定尝试，不等于两个 OS 映像映射，后者 UNKNOWN。失败即停且不重试；Close 上限按已取得非空 handle 计，不承诺失败调用实际释放资源。

**额外准备成本不可漏计**：当前 worker 每 case new_engine 2 次；configure 每 active AMI side 加载未 Init 模型 Q 一次，但该 Q 没有 Init/Close。其 loader 不在当前 Main 内 capture。未来 direct harness 若复用同样 configure+defaults 校验，明确也按 2 engine、Q=1 计；若选择不同 harness，须另改 freeze，不能沿用这张数表。

| 拟阶段／每 fixture | load绑定 | C Init | C GW | C Close | Python helper / responses / getWave | engine / Main |
|---|---:|---:|---:|---:|---|---|
| E1 原 C buffer 两块预检；不走response/helper | 1 | 1 | 2 | ≤1 | 0 / 0 / 0 | 0 / 0 |
| E1b 可选 helper-only角色验证，不额外configure | 2 | 2 | 2Gp+Gm | ≤2 | 1 / 1 / 3 | 0 / 0 |
| E2 direct一条，按同样prepare路线 | Q1+2=3 | 2 | 2Gp+Gm | ≤2 | 1 / 1 / 3 | 2 / 1 |
| E2 worker一条 | Q1+2=3 | 2 | 2Gp+Gm | ≤2 | 1 / 1 / 3 | 2 / 1 |
| E2 两条合计／同fixture | 6 | 4 | 4Gp+2Gm | ≤4 | 2 / 2 / 6 | 4 / 2 |

NRZ/PAM4 各一合法 fixture 的 E1 合计 load2/Init2/GW4/Close≤2，Main/helper/engine0。E2 两 fixture 四条 Main 合计 load12、Init8、Close≤8、engine8、helper4/responses4/Python GW12；C GW 为 `2*(2Gp_N+Gm_N)+2*(2Gp_P+Gm_P)`，不是一个固定377。E1b是可选新增预算，不藏进E1或4Main。

算例只用于校验公式：I=0、N=15000、Bp=Bm=40时，Gp=1/Gm=375，helper C GW=377；两fixture若恰取相同算例，四条合计1508。若隔离后错误沿用 toy Init block128，会变成120/helper；I=81 时381/helper。**这些不是新fixture参数或合法默认，也不是可运行freeze。** 串行 stub 验证了这些差异，不启动实际模型。Tx AMI侧、额外资源检查/normalize、失败重试、其它3x3模式、前后helper数值对照均不包含；若新增，必须另列具体路线和各 side/Q/Init/GW/Close预算。

本表中的 helper 指列明的 AMI Python API；Main 内其他 DSP helper 不是零调用，其细目须随最终 source/path freeze 列出或纳入明确 Main 执行上限，不能把“helper4”当所有数学函数总数。本轮所有这些实际调用均0。未来任何真执行前还缺 F、合法包/容量、实际 seed/B/I/bit-sample-eye窗口、golden、具体trace及预算，不能以本草案继续跑。

Web 数值段另见 [P2调用账](web-consumers-p2.md#6-e2-数值调用预算必须另-freeze)：当前每次collect直接calc_eye至多2、extend_analysis→eye_data至多6/内部calc_eye至多6，叶calc_eye总计至多8；clock_data/histogram/rfft/clock_display各至多1。E2若四条run都复用一次collect且Main不更新plots，仅Web对应上界为collect4、extend_analysis4、eye_data24、calc_eye32、clock_data/histogram/rfft/clock_display各4；包装器与叶调用分账，不相加为“总helper”。这些仍待freeze，未授权执行。其他FFE/jitter/bathtub/显示/可选trellis以及Main内DSP另计，额外replay再加账，不能由原AMI API数量覆盖。

## 8. 本阶段普通 stub、自审与成本

[contract_stubs.py](contract_stubs.py) 仅 stdlib，读取 AST/hash，不 import 产品或 PyAMI，不使用 ctypes、真实 ABI、DLL、slicer、FFT、BER、模型构造或服务。prefix/sampler 都是**拟议合同的参考例子**，不是生产修复，也不是独立数值引擎；state events 为普通计数，不算真实 C calls。

- v1：[stub-results-v1.json](stub-results-v1.json)，25 buffer/array例子、5 state plans，内部 elapsed `0.0922147999954177 s`。原工具保存在 [contract_stubs-v1.py](contract_stubs-v1.py)。其中 `state_plan_assertions_passed=9` 是记账标签错误，应为7；不改原件。
- v2：[stub-results-v2.json](stub-results-v2.json)，34个明确例子、6 state plans、8 state assertions，内部 elapsed `0.09037920000264421 s`。补了 embedded sentinel、冻结分析窗、TxGW/fallback/消费完成分层和 Close后prepare失败；修正state记账。不把两批通过例子相加作覆盖。
- v2 的 `sample_times` 是 targets，不是 actual grid times；`eligible_full_analysis` 只检查采样及 period 数量、仅有窗口下界，未覆盖窗口上界、Eye trace、Viterbi 尾部、完整模式/epoch 条件。它们是原型局部字段，不可直接映射产品资格。原件保留；复核后的合同以第5节为准，不把原通过例子重标签为完整新合同通过。
- 下游检查：[inspect_downstream.py](inspect_downstream.py) / [downstream-source-check.json](downstream-source-check.json)，只提取源码 AST 表达式并对手工数组求值，3 个源码输入前后 hash 不变；内部 elapsed `0.025493399996776134 s`。揭示只保留实际采样点后旧 Viterbi 尾部规则漏点，以及 Eye 未隐式加半 UI；不调用实际 helper/解码/Eye。
- 复核补例：[sample_index_stubs.py](sample_index_stubs.py) / [sample-index-results.json](sample-index-results.json)，只对普通数组/索引求值，2 个源码输入前后 hash 不变；内部 elapsed `0.006801399998948909 s`。覆盖 target/actual grid 分离、off-grid ceil/floor、浮点整除、双边界窗、Eye 裁剪后索引/完整 trace、实际尾部选择、Ignore 阈值；不是完整产品 eligibility 的实现或证明。
- v1/v2 每批13输入前后 hash不变；连同下游检查合计15个不同输入。记录实际probe block AST=40、worker new_engine AST count=2。未执行A的750串/parser回归。所有实际 Main/COM/coopt候选/Init/GW/Close/库加载/引擎/原生helper/模型下载编译/AMI parser 均 **0**。
- 四次工具内部 elapsed 合计 `0.21488879999378696 s`；全任务wall/peak RSS UNKNOWN。一次源码 rg 查询含不存在的 runner.py，返回exit1及其他有效匹配，已通过 rg --files纠正；不是数值失败。没有失败stub批次。两次文档 apply_patch 因上下文不匹配而拒绝，未改文件；按原文修正后成功，不涉及产品文件。
- 以上是ed23阶段原账，未重跑/改写工具或receipt。P2追加 [web_consumer_stubs.py](web_consumer_stubs.py) / [web-consumer-results-p2.json](web-consumer-results-p2.json)：8源码AST/哈希、普通masked数组的原bytes/known输入、连续窗与频轴算术、两处Eye索引/完整trace计划、静态调用图；内部elapsed `0.0740020000084769 s`。没有运行实际collect、eye_data、clock_data、extend_analysis、calc_eye、histogram/rfft、archive或其他产品helper；示例也没有计算FFT。5次工具历史内部合计 `0.28889080000226386 s`，不是任务wall或产品成本。
- P2保留旧seal，新增 `verification-v2.json` 记录ed23旧文件关系、20个保护输入、新证据hash与成本。修订中一次rg查询含不存在的test_web_data.py，exit2及有效匹配；已用rg --files发现实际测试路径，未执行测试；不算数值失败。旧receipt不证明新增Web数值/保存合同，也不证明serializer/consumer已经实现。

## 9. 尚待 PM 冻结的决定

仅建议下一轮先做 S0，再按第6节顺序开票；当前没有实施/真运行授权。PM 需分别决定：

1. 是否接受全局 getWave 默认 strict 的兼容影响；若要 waveform-only 容忍，先另定义结构化 API。
2. fork 的实际权限、固定 F 与 direct URL / PyPI 发布路线；未核实或未审查的 F 不能进入环境。
3. 是否采用公开 close()、顺序独立 P/W；或选择已修生命周期的同实例 reinit，并按实际路线重算账。
4. 是否保持目标 Rx 分支的有效 Bm=40，以及私有非零 probe seed；每个模型另确认支持的 B、Ignore 单位和 fresh-main 输入。
5. 是否采用 actual grid times 为 AMI canonical、producer indices 为所有消费者依据，包含 Native及Web两处Eye/Viterbi、masked原始保存/版本门禁、known histogram/连续FFT窗与双边界分析窗的联动；也可选 consumed-target canonical，但必须明确不同字段和同索引消费。raw6/clock-contract2及精确mask保存路线仍是建议。
6. 合法 NRZ/PAM4 包、容量上界、golden 与最终 E1/E2 freeze/预算。当前单 Rx 草案不能授权 Tx AMI side 或完整3×3矩阵。

只读合同复核记录见 [review.md](review.md)。它只评估设计自洽与已读取范围；不能替代实施后的独立审查、真实模型预检或数值验收。

固定合同自审与最终范围/hash检查另记录；最终本地提交HEAD/tree、证据SHA及停止写入返权由交接消息给出。本阶段不push、不发PR、不关闭票，不修改旧raw/失败/source/freeze/费用。
