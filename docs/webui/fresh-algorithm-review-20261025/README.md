# 从开发代码变动审查 GUI / Web 数值语义

2026-10-25；独立 fresh Astra / max 审查。先读取固定 Git 差异、完整函数和调用点，形成下面的代码判断，再读取上一轮数值报告核对覆盖范围。本次没有运行产品、NumPy、仿真、coopt、COM 或 AMI 库；没有修改产品代码。

## 直接回答

**当前 GUI 和 Web 的主要数值计算同源，但“同源”有输入、状态、分支和成功条件。开发期间也确实改变了若干数值语义，不能用已有数组相等推导“算法完全没变”。**

- Native Run 两边调用同一个 `my_run_simulation`，DFE/CDR/Viterbi 本体、channel/jitter 数学 helper 和 COM 本体有直接的 Git 对象未变证据。Native EQ 的评分、搜索顺序和 winner 规则没有发现被 Web 重写。
- S8P/S12P 的 through/FEXT 物理端口选择确实修正；同一个差分公式因此接收不同的导体组合，通道及下游结果会变。
- AMI 的参数返回接口、Init/GetWave 状态和 clocks 有效域、Rx response probe 与 Main 的状态隔离、clock→sample→decision→Eye/CDR 的采样定义确实改变。它们不是纯 metadata。最新真实 AMI 数值与模型资格仍未证明。
- Web 的 fresh worker、输入冻结、严格拒绝条件、独立 COM，以及图表投影和 archive 恢复与 GUI 会话有差别。即使核心代码相同，任意 GUI 操作历史与一个新 Web Run 也不自动等价。
- 新识别一项 **P2 历史兼容性问题**：`bits` 缓存不依赖 `seed`，GUI 旧实例只改非零 seed 后可以保留旧 PRBS，而 Web fresh 实例从新 seed 生成。此缺口在开发前已存在；本次是静态可达性判断，未动态重现 GUI 操作，不是此次 Web 新回归。

本次未发现有足够代码证据支持的、新增且尚未解决的 Web 算法迁移回归；这不把下面列出的未知分支提升为通过。

## 固定对象和证据强度

| 对象 | 审查版本 |
|---|---|
| 开发前 PyBERT | `1bc905d577d2f3bd9471421cfbf3d422d4e6080e` |
| 当前 master | `ab36b656a61cb6866da98105d72f6cacfb118031`；tree `8412b639f4dd6f51c227e19d649a333fbad9d6a2` |
| 只读源码 checkout | `C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator`；HEAD `54964c2c098e3a3807c4d68f96ce51621939f372` 与上述 master 同 tree |
| PyAMI | Gitlink `5270d713e40bac2be5747bef09b92df79df9085b` → `d6d1f7fe7e58536546a1cfb9430c750cc2cb103e`；从独立 clone 读取两端对象，实际 checkout 与目标 tree 相同 |
| PyChOpMarg | 两端 Gitlink 均为 `ca905e793fcf6330929471317ca32e7611578e5d`；独立 clone 对象与 checkout 已核对 |
| 其他依赖 | `chaco` Gitlink 未变；lock 中已有数值依赖版本未变。新增 Web 依赖不等于运行环境完全冻结；PyAMI 改为固定 fork SHA |

[static-inventory.json](static-inventory.json) 覆盖全部 `src/` 及根层依赖/配置对象，共 83 项：36 未变、15 修改、32 新增。源码变化为 8 个既有文件加 32 个新文件；没有删掉既有产品文件。清单还保存每个修改 Python 文件的完整函数/类 AST hash、两端行号和开发提交。

[static_inventory.py](static_inventory.py) 只使用 stdlib、Git 和 AST。它**不删除观察代码、不改写 AST、不导入产品**。完整文件 blob 相同是最强的“此实现未改”证据；完整函数 AST 相同覆盖该函数的语法结构。两者都不能单独证明调用输入、对象状态、依赖运行时或外部 DLL 相同。修改过的主函数则按实际分支和数据流逐段审查，不伪称整体 AST 等价。

开发轨迹中与数值有关的主要节点：

| 提交 | 作用 |
|---|---|
| `7b4336b`、`086fff2` | Web Run / 分析和 channel / FEXT 观察；新 runtime/显示投影 |
| `b87c80c`（#13 / PR #14） | 多端口物理映射修复 |
| `e393c7c`、`d838995`（#8） | Native coopt 候选及 MMSE 上下文观察 |
| `d1a5979`（#9） | decoder 观察、trellis 共享与 Web 保存 |
| `e0d089e`（#10） | AMI 配置、执行与候选观察 |
| `80100e2`（#22 / PR #23） | GetWave tuple / 参数历史兼容修复 |
| PyAMI `2b475fa`、`81c4e5a`；PyBERT `fa76df8`、`8ad70c4` | AMI ABI 包装、clocks、Close 与可注入 probe RNG；依赖固定 |
| `ec72c92`（#30 / PR #31） | 指定 Rx GetWave 分支 probe / Main 分离 |
| `782c31b`、`85dfed8`、`2a0a265`、`acdfee7`、`418d72b`（D1 / PR #32） | AMI clock 生产、实际采样、Eye 与 GUI CDR 接线 |
| `1b0877f` 至 `8cec174`（D2 / PR #33，具体逐文件提交见清单） | Web 消费、有效窗口、mask、归档和 partial 记录 |
| `0a7a036`（PR #34） | Traits Dict 写入形式修复；恢复无条件 Main 入口可执行性 |

## 调用图与“同源”的条件

```text
GUI Run → MyHandler.do_run_simulation → RunSimThread → my_run_simulation
Web Run → Tasks spawn → new_engine + load_config + configure → my_run_simulation
                                                          → collect / extend_analysis

GUI Tune → OptThread.run → coopt → native score_candidate 或 AMI objective
Web Tune → run_optimization → 同一个 coopt → 保存候选 → 显式 Use EQ

GUI COM → compute_com → models.com.calc_com → 固定 PyChOpMarg COM
Web COM → 独立 worker → models.com.calc_com → 同一个固定 PyChOpMarg COM
```

GUI 的 [handler:32–40][handler] 重用 `info.object`；[sim.py][sim] 直接调用共享 Main。Web 的 [worker:94–137][worker] 构造新对象，完整加载配置、核对 requested/effective identity、绑定实际资源，再调用同一 Main；`update_plots=False` 由 Web 自己投影显示。`new_engine()` 明确为 `run_simulation=False`（[config:97–103][config-new]）。

因此，当前 Native GUI/Web 比较至少应固定：相同源码和实际依赖、完整有效配置及 runtime extension、资源内容与顺序、首次读取缓存前的对象状态、非零 seed、相同支持分支和分析窗口。不能仅对比几个可见控件，或把同一 YAML 当作全部隐藏状态证明。`PyBertCfg` 未表达的 `rlm`、`rx_use_clocks`、AMI 参数树、优化初值等由 Web 扩展单独保存；导出原生 YAML 的能力不等于这些扩展天然存在于 GUI。

Web [config:106–184][config-validation] 及 [resources:213–310][resources] 还缩小了允许执行域：time-domain CSV/TXT、非零 `impulse_length`、实际会执行的 CTLE File、package+FEXT 等被明确拒绝；cascade 只接有序 S4P。不是把这些模式换成近似算法。FEC 和 AMI+Viterbi 在 Web 仍有支持边界。一个路径在 GUI 能进入、在 Web 提前拒绝，不应计成“所有运行行为等价”。

## 开发前后没有发现算法改写的部分

| 部分 | 实际检查结果与范围 |
|---|---|
| DFE / CDR | `models/dfe.py`、`models/cdr.py` 整文件 blob 相同；tap update、slicer、clock recovery 本体未改。Main 的 **Native 分支**仍以原输入调用原 `DFE.run`；AMI clock 分支绕开这些算法，不能混在同一结论里 |
| bits / symbols / 时间频率轴 | `PyBERT._get_bits/_get_symbols/_get_t/_get_f/_get_ui/_get_nui` 完整 AST 相同。非零 seed 的全局 NumPy seed 设置在基线已存在；不是 Web 新加。缓存依赖的既有缺口见 P2 |
| channel 数学 | `utility/channel.py` 整文件相同；`sdd_21/se2mm/interp_s2p` 完整 AST 相同；package channel 方法相同。普通 channel 的终端处理、`irfft` 前 raised cosine、cubic 时间插值、`t[1]/t_irfft[1]` 离散幅度比例与 99.9% energy trimming 未改（[pybert.py:1416–1629][channel]）。**输入端口映射改变另列** |
| Tx / CTLE / Rx FFE | Native symbol repeat、Tx convolution、原 `get_ctle_h`、Rx FFE convolution / crop / tap 使用顺序保留（[bert.py:285–561][native-chain]）；`make_ctle/make_ctle_h/calc_resps` 完整 AST 相同。未发现 Web 另实现一套 EQ 公式 |
| BER | Native `pad_front`、相关峰定位和 error count 路径保留；AMI branch 新增“必须有真实足量 decision”的路径（[bert.py:685–735][ber]）。因此 `calc_ber` 整体不是 AST 未变 |
| jitter / bathtub | `utility/jitter.py`、`utility/math.py` 整文件相同；原 channel/Tx/CTLE/DFE crossing 与 jitter 调用保留。Web 额外 FFE 观察调用同一 helper，原四点统计未被替换 |
| Viterbi / FEC | `models/viterbi.py`、`models/fec.py` 整文件相同。Native Main 的原 W+1 clock 筛选、cursor phase、sigma 与 decode 输入规则保留（[bert.py:759–846][viterbi-main]）。trellis 绘图代码抽成 [update_trellis:1502][trellis] 共享；Web 不重写 trellis 概率。AMI sampling 输入变化仍可传播到 decoder；Web 当前不接受 AMI+Viterbi |
| COM | `models/com.py` 整文件相同，`compute_com` 完整 AST 相同，PyChOpMarg Gitlink 相同。此证据说明实现未变，不等于已经计算或证明 IEEE/MATLAB 等价 |

观察代码也检查了数据归属：FEXT 的 `h_t/H` 和 jitter 结果有保存引用的地方，并非所有值在产生时就 deepcopy；在本次完整后续路径中，没有发现这些引用被回写进计算或在采集前被原地改写。FEXT 累加旧代码是 `noise = noise + expression`；新代码只是先命名 `contribution` 再作同次加法，保留累加顺序。`self.noise` 仍是 FEXT 前的基底噪声，`noise_total` 是另存观察，不能混为同一个输出。

优化输入/候选显式 `.copy()`（[optimization.py:247–310、429–431][opt-core]）；Web AMI capture 把输入/返回数组复制到独立证据，再原样返回 helper result（[ami.py:298–368][ami-capture]）。这些检查支持“未发现观察值反馈到成功数值路径”，但**不支持“加观察完全无副作用”**：复制耗时/内存、序列化、取消检查、非有限值校验和观察预算都能让任务失败或停止；[NativeObservations:36–64][opt-observation] 会在超限时抛错。

## 实质变化一：多端口 channel / FEXT

修复来源为 `b87c80c`，当前 [sparam.py:265–405][sparam]。旧、新都使用原 `sdd_21` / `se2mm`；变化发生在送进去的单端子网络。

| 场景 | 旧行为 → 当前行为 | 数值含义 |
|---|---|---|
| 普通 S8P/S12P through | lane k 旧取 `[4k,4k+2,4k+1,4k+3]` → 当前 natural `[4k,4k+1,4k+2,4k+3]`，按源 lane 的 through 检测决定是否交换中两项 | 匹配 `sdd_21` 的交错 `(TX+,RX+,TX−,RX−)` 定义；不再把同端导体当作 through 另一端 |
| S8P/S12P FEXT | 旧按 `[agg+,agg−,victim+,victim−]` 构子网络并可能在 cross-lane 网络上检测 through → 当前先在各自 lane 检测，再取 `[agg0,victim1,agg2,victim3]` | 差分传输项来自正确 aggressor 输入与 victim 输出。cross-lane 不能用 through 强弱判端口 |
| S4P / S2P / S1P / VITA | 相关分支保持旧调用与映射 | 修复不是所有 Touchstone 模式统一重排；不能把 S8P 的结论外推到未变分支 |

使用 1-based 记号，原差分 `Sdd21 = (S21 − S23 − S41 + S43)/2` 公式未改；**四个 S 的物理含义变了**。这是“修 bug，同时改变计算结果”的典型情形。修复不是保证 insertion loss、FEXT、BER 一律增/减；某些原本可被 `renumber=True` 检测补偿的 through 输入可以不变，其他结果方向取决于实际矩阵。

既有 [#13 前记录](../native13/evidence/real-M-before.json) / [后记录](../native13/evidence/real-M-after.json) 与 [#16 外部 importer 报告](../issue16/evidence/final-importer-report.json) 支持特定物理 oracle 和外部 S8P/S12P 的修复。原记录中 through 15/15、FEXT 24/24 是各路径案例的覆盖，不是全部布线格式或硬件 qualification。本次未重跑这些输入。

## 实质变化二：AMI 返回接口、状态和随机性

| 变化 | 旧 → 当前；范围 / 原因 | 对数值与失败行为的判断 |
|---|---|---|
| 参数树 `80100e2` | 旧 visitor 假设 `.name`，tap 筛选还有无效字符串方法；当前 [getwave_parameters:85–145][ami-params] 消费固定 parser 的 `(label, values)` tuple，保留完整 tuple path，检查每 call key set / 历史长度，Table / 非数值不造零 | 解决有来源的接口失败（[#22 原需求](../issue22/params-compat-20261024/issue22.json)）。改变可成功输入、tap / lock / UI 历史的取得，不是换 AMI DSP 公式；语法非法仍失败 |
| PyAMI `2b475fa` | [model.py:368–624][pyami-abi] 在 Init/GetWave 检查 status=1、按 Init epoch 管理 Close/失败状态；clock buffer 预置 NaN，按 sentinel `−1` 取有效前缀，检查有限/非负/严格递增，包括同 epoch 跨 chunks / Python calls | 旧拼接 padding/sentinel 的值和长度被改变；不合法或未填充返回不再被默许。影响所有使用该 wrapper 的分支，不能只说影响 Rx timed clock。ABI buffer 容量、真实库遵守约定仍 UNKNOWN |
| 可注入 probe RNG `81c4e5a` | [get_responses:720–758][pyami-response] 允许传私有 Generator；省略时仍新建 entropy RNG，这是基线已有行为。当前指定 Rx probe 用 `default_rng(seed or None)` | 非零 seed 让该 probe 的 adaptation prefix 可复现，但不是全 DLL 随机性承诺；seed=0 仍 UNKNOWN。其他 legacy helper 未传 RNG，不能被“非零 Main seed”自动覆盖 |
| Rx fresh Main `ec72c92` | [ibisami.py:113–193、248–282][ami-epochs]：旧同一模型先 response probes，再 Main waveform；当前 probe Init→两次 GetWave probe→复制→Close，随后另一个模型 Init→从冻结 x 首样本 Main→复制→Close | **模型适应状态改变，可改变 wave/clocks/params 及响应**。Main 不再继承 probe handle 的训练。h/out_h 仍来自 probe；波形来自 fresh Main，二者不是同一连续适应历程的测量。影响方向/幅度依模型而定 |

fresh Main selector 只有 Main 中 **Native 或 Init Tx + Rx GetWave** 一个 helper 调用点传入 `_probe_seed=self.seed`（[bert.py:450–455][rx-selector]）；不依赖 `rx_use_clocks` 是否开启。Tx GetWave、双 GetWave、Rx Init / Tune 等保留 legacy helper 路径。不能把局部隔离写成全 AMI 路径均隔离。

还要保留两个容易漏掉的边界：

1. legacy helper 即使 `use_getwave=False`，仍调用 `get_responses(bits_per_call=40)`，未传 `calc_getw=False`（[ibisami.py:270–284][ami-epochs]）。因此支持 GetWave 的模型可在名义 Init / Tune 内被 probe；这是继承的调用关系，新 wrapper 校验会影响其成功域。不是“Init 模式必定 0 GetWave”。
2. probe/Main 的 Close 和新 Init 只建立 host / handle 生命周期隔离；代码自己不保证 DLL 静态/全局状态重置。不能把 process fresh、handle fresh 与物理模型同状态混为一谈。当前两电平 response probe 也不是 PAM4 真实响应资格证明。

[#30 软件 seam 记录](../issue30/probe-main-20261025/README.md)支持协调顺序、失败停止和复制归属；其中 stub 的常量 wave/clocks 不是 DSP golden。旧 [#10 实例模型矩阵](../issue10/README.md)发生在更早接口和生命周期上，不能证明当前 PyAMI / fresh Main 的真实模型数值。

## 实质变化三：AMI clock 的采样、判决和统计

当前 [ami_clock.py][clock-producer] 与 [bert.py:386–735][clock-caller] 是新增计算语义。基线条件宽松，且旧 `pairwise((clock_times, clock_times[1:]))` 迭代的是两个数组组成的一对，不是相邻 scalar clocks；其后 scalar `if` 对多项数组可能先报错。不能把旧路径当作正常工作的 reference sampler。

| 环节 | 当前定义 | 相对旧路径的意义 |
|---|---|---|
| 入口 | 只有指定 fresh Rx Main 来源可使用 timed branch；格式非法失败，合法空 clocks 可退回 Native；有限 nonempty clocks 不自动代表可消费 | 改变有效域和失败/回退语义，拒绝无 provenance 或不足量的“成功” |
| clock → sample | 目标时间 `edge + symbol_UI/2`，`searchsorted(..., side='left')` 选第一个实际 grid sample；不全局平移 clocks、不裁剪/修复非法序列；落到重复 sample index 会被拒绝 | 新增明确量化规则；真实 sample time 与模型 edge time 分开保存，不能互换 |
| decision | 对实际可消费 index 调用原 `dfe.decide`；timed branch 跳过 Native DFE/CDR/AGC 运行 | slicer 本体没改，但输入采样和启用算法变了；不能把该输出叫作 Native CDR 收敛结果 |
| 窗口 | 冻结最后 W 个分析 UI，检查 Ignore_UI、真实 decision 数、完整 2 UI eye trace 和预定 FFT 窗口；不足则保存 partial 并失败 | 不用 padding / 外推补足证据。BER timed branch 不使用 Native 的补前项路径 |
| period | 由相邻已消费 edge 的差，填到对应 sample-index 区间；其余为 NaN + bool known mask；末端不外推 | 与旧累积 period / 人造 lock 逻辑不同。`Ignore_Bits` 足够不是模型声明 lock |
| histogram / FFT | [period_projection:144–197][clock-projection] 在冻结窗口中每个已知 grid sample 计一次 histogram；FFT 需要整个既定内部窗口有效且 grid 通过检查 | 这是按 grid sample 加权，不是每 edge interval 一票；缺失不能靠压紧数组后假装均匀 FFT |
| Eye | [calc_eye:395–442][calc-eye] 新增显式 integer `clock_indices`，作为所给 waveform slice 的 2 UI **trace 起点**；GUI/Web 接同一 producer indices | 避免 seconds→index 重算；Native 原 clock_times / 无 clocks 分支未改。没有把 trace 起点重新解释为中心 |

NRZ 使用明确映射；PAM4 nonempty clocks 需要 profile，当前 Main 未传该 profile，所以该输入仍会 `unsupported_profile`。这是本次看到的明确资格边界，不能以无 clocks 的 PAM4 fallback 结果代替有效 PAM4 clocks 验收。

Web [clock_context][clock-context] 比 GUI 消费还多做 freshness、来源、坐标、mask 和窗口一致性校验；同一 producer 上成功的有效路径可共用数据，不代表所有输入都同样返回成功。Main 残留值、partial 或旧 invocation 不会被 Web 标为成功记录。

`0a7a036` 解决的是新增 `TraitDictObject.update(keyword=...)` 不能执行的问题：改用 `update(dict(...))`。它恢复 Native / AMI 无条件入口的可用性，没有另改公式或窗口；这项已修复 P1 仍说明只做源码浅审查不足以保证实际 runtime 可执行。

## 优化与 COM：算法共享，状态和返回合同不同

Native coopt 的候选生成函数完整 AST 相同：原 CTLE 外层、Tx 候选内层、`arange(lo, hi+step, step)`、中心 tap / all-zero 检查与严格 `>` 取第一个最优规则保留。MMSE 仍调用同一固定 PyChOpMarg；其内部噪声模型、约束和 normalization 没有在 Web 中另实现（[optimization.py:160–444][opt-core]）。

该优化器本来就不等于完整 Run 或 COM：MMSE context 使用固定 Av=0.5、SNRtx=25、DJ/RJ=0、`eta0=rn²/fNyquist×1e9`、空 FEXT；RLM 由优化消费，普通 Main 不消费。原非 MMSE score 也保留。不能拿同一界面上的两个分数当同一噪声/统计定义。

AMI coopt 的 TPE seed、trial count、零维单次评估、score 与 winner 规则未发现被改写（[optimization.py:445–615][opt-ami]）；但它调用的新 PyAMI / legacy probes 仍可能改变成功域、适应状态和结果，故“搜索代码未改”不等于“AMI 优化结果未变”。Web 拒绝 GetWave-only Init 评分等不适用模式，不沿用原 unsupported fallback 冒充有效候选。

GUI OptThread 会把 winner 写回 tuner / AMI 参数；Web 的 [run_optimization][opt-web] 保存不可变候选，使用原 handler 动作显式 Use / Reset。Web 还有预检/观察预算和有限值/winner 校验；超限或无效会失败，不是悄悄缩短原搜索。两边的后续 Run 只有在已明确应用同一候选后才有同输入前提。

COM 的 [原 wrapper][com-core] 与 [Web wrapper:38–157][com-web] 共享 `calc_com`，采用真实 XLS/XLSX 或显式 IEEE_8023dj defaults，Web 不把时域 EQ 注入 COM。Web 当前只接单个真实 S4P THRU，没有暴露原 helper 的 FEXT/NEXT 列表。

Web 设置 `PYCHOPMARG_PROCS=1`。已读固定依赖 [COM.opt_eq:1217–1418][com-search]：parallel 的 `pool.map` 返回候选顺序与 serial 一致，winner 均严格 `>` 保留 first tie；local search 强制 serial；`mmse` 在 `ts_window=0` 时不按 center 重排（[optimize.py:524–584][com-timing]）。这支持“没有改候选 / tie 规则”的静态判断，仍不是一次未执行 COM 的数值证明。

运行合同也不同：GUI 的 `compute_com` 出错记 `−999`；Web 拒绝 sentinel / 非有限值 / ERROR 日志。Web Run 先禁用 Main 内 COM，等主 worker 退出后另起 COM worker。代码记录 `full_search_fom_upper_bound`，**并没有在 `web/com.py` 用此数值实施硬预算拦截**；历史 `BLOCKED_BUDGET / NOT_EXECUTED` 是执行范围状态，不能写成已有代码自动阻止默认大搜索的保证。

既有 [真实 XLS direct/worker 记录](../issue4/evidence/native-tools-20261024-082936/report.json)支持那一个已执行配置；默认 139,756,144 候选没有因本次静态审查变成“已通过”，也没有在本次恢复执行。

## 显示与 archive 不是新的物理链路

| 部分 | 当前 GUI / Web 关系 |
|---|---|
| h / H / jitter 单位 | 离散 h 保留 V/sample，不在 Web 额外乘/除 Ts；H 显示 20 log10，jitter spectrum 沿用 10×(log10(raw)−log10(UI))；CDR spectrum 保留原无 ×10/20 的 log10 ratio。前端消费服务器给定轴/值，未发现另写 FFT / EQ |
| waveform / CDR | GUI 长记录全记录 1000 点插值；Web waveform 末 20 UI、最多 4096 个原索引，CDR 全记录最多 4096 索引。raw 相同也不会每个显示点相同（[bert:1272–1381][gui-display]；[data:205–207、383][web-display]） |
| Channel eye | GUI 在裁剪后的 waveform 上用全局 normal 加显示噪声；Web 另存 clean eye，并用固定 seed 34003 / PCG64 的 1 mV 噪声版本。噪声只在显示路径，不反馈 channel / BER；两边 realization 不同（[analysis:168–170][web-analysis]） |
| Eye 电压轴 | Web 以 `calc_eye` 实际整数 `y_scale/y_offset` 还原 bin 坐标；原 GUI `update_eyes` 使用全记录幅度的线性端点，CTLE 还沿用 DFE 幅度。原 count matrix 相同不能推出绘制电压坐标相同（[update_eyes:1604][gui-eye]；[data:321–348][web-display]） |
| 额外 FFE / single-stage pulse | Web 新算部分 helper 观察；GUI 没有对应 producer field 的图不应硬做同名比较（[analysis:30–69][web-analysis]） |
| 无法显示的数值 | Web 对零 fundamental、非有限或缺失数据标 unavailable；GUI 历史显示可能产生无效值。这里改变的是显示/成功合同，不是把未知值插成 0 |
| `.pybert_run` 重开 | [archive:164–220][archive] 原样保存/恢复 NPZ bytes 与源 manifest UTF-8，校验 dtype/shape/hash/axis/feature，不运行 Main，不重建 Eye / FFT。raw6 的 NaN 只允许有严格 mask 的 `ui_ests` 例外 |
| Replay draft | [server:227–236][replay] 返回原 requested input 和资源 hash guard；实际 Run 另建对象、用当前代码。archive 不内嵌模型/channel 资源 bytes，也不恢复 GUI 缓存/动态 DLL 状态；重开值相同不是重跑算法相同 |
| `.pybert_data` 旧档 | [legacy_results:18–64][legacy] 只展示真正保存的子集；缺物理轴/窗口/配置明确 unknown，频响已为 display dB 时不再 log。不能用当前 run 的轴为旧记录补造完整结果 |

## 新 finding：P2 历史 GUI seed 缓存兼容性

**位置：** [pybert.py:440–441][bits-property]、[pybert.py:635–651][bits-getter]；两处在开发前已有同样语义。

静态可达链条：

1. 常规 GUI 构造默认 `run_simulation=True`，会先调用 `simulate`（[pybert.py:485–530][constructor]）；Main 首次访问 `self.bits`，`@cached_property` 生成并保存 seed A 的 PRBS。
2. GUI 有直接编辑 seed 的字段（[view.py:142][seed-ui]）。仅将非零 A 改成另一个非零 B，不改 pattern、nbits、modulation 或其他列出的依赖。
3. `bits.depends_on` 列出 pattern/nbits/mod_type/run_count/Viterbi/FEC，**没有 seed**；`symbols` 又依赖 bits/vod。Main 只有 seed=0 才递增 run_count（[bert.py:227–242][seed-main]）。因此该编辑不会经已声明的依赖使缓存失效。
4. GUI Run handler 使用原对象；新的 Main 对全局噪声 RNG 使用 B，但仍可能读旧 seed A 的 bits/symbols。`PyBertCfg` 同时把 seed B 写进配置（[configuration.py:66][seed-config]）。
5. Web `new_engine(run_simulation=False)` / full load 不先访问 bits，实际 Main 首次读取时 seed 已是 B（[config:378–396][config-load]；[worker:94–137][worker]）。同一个保存 seed=B 的配置不能保证与旧 GUI 对象使用同一 PRBS。

**影响：** 在上述操作序列中，发射序列、波形、统计乃至误码结果可以不同；配置里显示的新 seed 不足以解释旧 GUI 的 PRBS。现有两个 fresh producer 配对没有覆盖该序列。

**分类与行动：** 这是基线继承的兼容性缺口，本次新识别；不是 Web 迁移新引入的计算回归。本次只完成静态因果/入口可达性论证，未打开 GUI、未执行 Traits 或数字反例。后续修复可将 seed 纳入缓存依赖并给“seed A Run → 只改 B → Run”增加有界状态测试；在修复之前，GUI/Web 一致性说明必须限定 fresh / 正确失效后的对象。此报告未实施修复。

另一项已明确的状态差别是 GUI Main 会把最终 `decision_scaler` 写回对象，下次 Run 从该 level 开始；Web 保存结果而不自动改草稿。它属于已设计的草稿/结果隔离，不能自动判成 bug，但比较时仍需给相同初始 level。

## 已有验证支持什么，没支持什么

本节在独立代码判断完成后才查阅原材料；只读取既有脚本/JSON，没有重跑它们。

| 既有证据 | 可以支持 | 不能支持 |
|---|---|---|
| [当前 NRZ](../final-numerical-review-20261025/fixed-v2/numerical-report.json) / [PAM4](../final-numerical-review-20261025/pam4-v3/numerical-report.json) | 两个冻结 Native 输入：444+445 数组 exact，seed=1、15,000 bits、32 samples/UI、相同配置/窗口；真实 spawn Web worker 与 fresh 原生 producer 配对 | 889 个数组不是 889 个独立场景；多数数组同源于两个运行。双方同用当前代码也可能共同包含同一算法变化。未覆盖 AMI、COM、优化、Viterbi enabled、多端口全域或 GUI 历史编辑 |
| [NRZ display 勘误](../final-numerical-review-20261025/fixed-v2/display-check-correction.json) | 原 57 项有 3 项 GUI producer 不存在；共有 54 项 exact。PAM4 54 项 exact | 原 NRZ 报告 `passed=false` / 三个 display failure 原件仍在；不能改写成原始 57 项全部通过，也不能由值相同推像素/轴全同 |
| [历史保存数组对照](../final-numerical-review-20261025/saved-baseline-comparison.json) 与 [脚本](../final-numerical-review-20261025/audit_saved.py) | 对保存的旧 Native 参考字段做 dtype/shape/bytes 比较：311+312 项 exact；保留输入文件 hash | 是同两个案例的历史结果比较；没有重新执行所有旧版本分支，也没有证明未采集状态或其他输入 |
| [#8](../issue8/evidence/delivery-audit-20261024-130843/report.json) / [#9](../issue9/evidence/delivery-audit-20261024-143549/report.json) | 原已执行 Native optimizer / Viterbi 范围；当前 Native 修改可结合代码增量判断 | 不把旧计数当本次新执行；不覆盖随后改变的 AMI sampling / PyAMI |
| [#16](../issue16/evidence/final-importer-report.json) | 特定外部多端口模型与物理映射 oracle | 不覆盖所有实际硬件、端口约定、package+FEXT |
| #10 早期模型及 D1/D2 软件测试 | 各自固定版本的配对或软件合同，partial / failure 仍有信息价值 | 不是当前合法 NRZ/PAM4 AMI clocks 的真实资格；旧 clocks 异常、接口失败不能因后续代码修复自动转成 pass |

最有效的结论组合是：**Git 对象/完整 AST 证明未变实现；逐分支数据流辨认实质变化；独立物理/合同 oracle 判断变化是否正确；有限运行只验证被实际执行的输入与状态。** 本次已完成前三者中的源码审查，并核查既有运行证据的边界；没有把未执行部分补成确定结论。

本次新增文件仅本报告、静态脚本和清单。新增 Main / 产品导入 / NumPy / coopt / COM / AMI library 调用均为 0；没有新增数值矩阵、环境安装、服务、提交、push、PR 或 issue。全部旧失败、费用、原件和 UNKNOWN 保留。

<!-- Source links bind to the fixed reviewed objects, not moving branch tips. -->
[handler]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/gui/handler.py#L32-L40
[sim]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/threads/sim.py#L32-L41
[worker]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/worker.py#L94-L137
[config-new]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/config.py#L97-L103
[config-load]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/config.py#L378-L396
[config-validation]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/config.py#L106-L184
[resources]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/resources.py#L213-L310
[channel]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/pybert.py#L1416-L1629
[native-chain]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L285-L561
[ber]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L685-L735
[viterbi-main]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L759-L846
[trellis]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L1502-L1601
[opt-core]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/threads/optimization.py#L160-L444
[opt-ami]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/threads/optimization.py#L445-L615
[opt-observation]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/optimization.py#L36-L64
[opt-web]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/optimization.py#L270-L474
[ami-capture]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/ami.py#L298-L368
[sparam]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/sparam.py#L265-L405
[ami-params]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L85-L145
[pyami-abi]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L368-L624
[pyami-response]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L720-L758
[ami-epochs]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/ibisami.py#L113-L284
[rx-selector]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L450-L455
[clock-producer]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/ami_clock.py#L18-L253
[clock-caller]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L386-L735
[clock-context]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/clocks.py#L42-L118
[clock-projection]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/clocks.py#L144-L197
[calc-eye]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/sigproc.py#L395-L442
[com-core]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/com.py#L19-L57
[com-web]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/com.py#L38-L157
[com-search]: https://github.com/capn-freako/PyChOpMarg/blob/ca905e793fcf6330929471317ca32e7611578e5d/src/pychopmarg/com.py#L1217-L1418
[com-timing]: https://github.com/capn-freako/PyChOpMarg/blob/ca905e793fcf6330929471317ca32e7611578e5d/src/pychopmarg/optimize.py#L524-L584
[gui-display]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L1272-L1381
[web-display]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/data.py#L205-L383
[web-analysis]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/analysis.py#L30-L426
[gui-eye]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L1604-L1652
[archive]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/archive.py#L164-L220
[replay]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/server.py#L227-L236
[legacy]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/legacy_results.py#L18-L64
[bits-property]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/pybert.py#L440-L441
[bits-getter]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/pybert.py#L635-L651
[constructor]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/pybert.py#L485-L530
[seed-ui]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/gui/view.py#L142-L144
[seed-main]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L227-L242
[seed-config]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/configuration.py#L66
