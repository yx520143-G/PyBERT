# GUI → WebUI 迁移边界与逐项保留／回退建议

2026-10-25，原 fresh Astra 审查者继续判断。本文是建议，**没有回退或修改产品代码**。对象仍为 PyBERT `1bc905d577d2f3bd9471421cfbf3d422d4e6080e` → `ab36b656a61cb6866da98105d72f6cacfb118031`，PyAMI `5270d713e40bac2be5747bef09b92df79df9085b` → `d6d1f7fe7e58536546a1cfb9430c750cc2cb103e`。原 [独立审查](README.md)、脚本和清单不改写；此处补充“是否属于迁移”的判断，并纠正其中容易过度概括的 AMI sampling 描述。

## 决策摘要

**如果目标只是把已有 GUI 能力搬到 Web，必要的是输入与资源绑定、同一引擎调用、进程隔离、结果观察和可靠归档。重定义 AMI 的适应初态、随机前缀和 timed-clock 成功条件，不是迁移必需。**

建议保留 Web 适配；把有明确缺陷的少量 native 修复单列接受；将 C1 fresh Main 和 D1/D2 新 timed-clock 运行合同撤出“迁移默认行为”，另作 native 功能工作。这里的“撤出”不是恢复已知坏循环并声称支持，也不是删除已生成归档的读取能力。

| 项目 | 是否迁移必需 | 保留／回退建议 |
|---|---|---|
| A：Web 配置、资源、参数树传递；#22 tuple 消费 | Web 适配必需；tuple 修复是独立 native bug fix | 保留适配和最小 tuple/string 修复；更强的全历史一致性拒绝规则单列，不能统称接口搬运 |
| B：PyAMI fork | 不是一个不可拆的必要包 | status 失败处理、handle 所有权及幂等 Close 建议保留为独立修复；有效前缀提取也有保留价值。NaN 预填、全路径严格 clocks、跨 Python call 单调和由此触发的整 epoch 失效，不应默认捆入迁移 |
| C：可选 probe RNG 参数与调用策略 | 可选 API 本身兼容；自动 seed 绑定不必需 | API 保留；取消纯迁移默认路径上的 `seed → probe RNG` 新策略，除非另行接受新的可复现性合同 |
| D：C1 probe / fresh Main | 否，改变 AMI 适应状态 | 建议从迁移默认路径撤出，单独评价；不把 probe 训练过的 Main 和 fresh Main 当作等价 |
| E：D1 clocks → decisions / BER / Eye / CDR | 最小旧 bug 修复与新合同混在一起 | 不把整个 D1 认作迁移必需；新 live pipeline 单列。半 UI 和首个不早于目标的网格点**不是新算法**；旧分支确实有独立循环缺陷 |
| F：D2 Web 消费、raw6、archive | 历史读取兼容必需；新生产合同依赖 D1 | 保留 raw6 读取、校验、已保存的 mask/轴/来源和失败证据；live 消费与 D1 成组处理，撤出必须全 Eye/CDR 可用才发布 Run 的新默认门槛 |
| G：PR #34 Traits Dict 写法 | 保留相关写入时属于必要修复 | 当前应保留；只有关联 producer / consumer 一起撤除后才能删去孤立部分，不能先回退此修复 |
| H：多端口修复、显示、运行隔离、优化／COM | 各自不同 | 运行隔离和原引擎复用保留；多端口修复单列接受；显示差别明示；不扩大 COM、AMI 或优化资格结论 |

“独立修复”表示它值得保留，但理由是修复 native 缺陷，而非 GUI/Web 迁移本身要求改变计算行为。下面不把“超出迁移范围”自动等同于“错误”，也不以代码量或提交标题代替逐项判断。

## A. Web 适配与 #22 参数返回兼容

主要来源：`e0d089e`（#10 Web AMI 接入）、`80100e2`（#22 / PR #23）；[Web AMI capture][ami-capture]、[配置加载][config-load]、[getwave_parameters][ami-params]。

| 子项 | 旧 → 当前与实际影响 | 分类与建议 |
|---|---|---|
| 模型、参数、资源绑定 | GUI 对象/配置 → Web 保存 requested/effective 配置、资源内容 identity，在 fresh worker 上设置同一 engine 与参数。它决定交给引擎的输入是否真相同 | **必要适配，保留。** 文件选取、目录隔离、参数树传递和输入冻结均不要求另写 AMI 算法 |
| tuple / string 最小修复 | 原 visitor 按 `.name` 访问节点，与固定 parser 实际 `(label, values)` 返回不符；tap 筛选还使用无效字符串方法。当前消费 tuple，并按 path 查找 tap | **独立 native 缺陷修复，建议保留。** 对会返回参数的实际路径，原代码不能正常取得结果；修复可以是迁移暴露的前置缺陷，但须独立记录“此前失败 → 现在可执行”，不能当数值恒等证据 |
| 完整路径、Table／非数值不造零 | 当前保留根以下完整 tuple path；非数值、空值、Table 行不伪造成浮点历史 | **观察／接口正确性，建议保留。** 路径能避免同名叶节点合并；缺失数据应显式 unavailable。这不是改 DLL 的 wave 算法 |
| 全 call key set、root、tap 长度检查 | 当前要求每个 call 的数值 path 集相同，root 不变，tap 列在同一次 call 等长；违反就从共享 Main 抛错 | **新增可接受输入与失败合同，超出最小 tuple 修复。** 保留“不能拼造一条合法历史”的原则；不应未经单列接受就让与 wave 无关的缺失诊断阻断所有 Run。具体模型哪些变化合法，本次 UNKNOWN |

最后一项不能仅靠“返回值格式不同”作整体保留理由。最小迁移需要把真实存在的字段传好；不需要给所有 AMI 模型加上新的“每次返回同一数值键集合”承诺。若将此校验留在生产默认路径，需明确它是额外支持边界，而非迁移前已有约束。

## B. PyAMI fork 必须拆开判断

主要来源：PyAMI `2b475fa`；PyBERT `fa76df8` / `8ad70c4` 及 #25 / #28 的依赖接入。[当前 wrapper][pyami-abi]、[clock-prefix helper][pyami-prefix]。这里讨论源码实际约束；未进行新的标准条文核证或真实模型执行，不声称所有模型已满足这些约束。

| 子项 | 旧 → 当前、影响范围 | 建议与必要边界 |
|---|---|---|
| Init / GetWave status | 旧忽略返回值；当前只有 `status == 1` 才接受，否则抛错并记录原始返回。成功数值路径不因此重算，但失败调用不再被当成有效输出 | **建议保留为独立 native correctness 修复。** 将显式失败当成功没有迁移价值。但具体目标 ABI 的成功码约定需成立；这不是用“检查 status”证明真实库已合格 |
| Close 所有权、幂等与异常记录 | 基线重新 initialize 前已有 Close 行为；当前在调用 Close 前先放弃 handle 所有权，重复 close 无 handle 时不调用，并记录失败；Init 失败亦做清理 | **建议保留为独立生命周期修复。** 防止同一拥有权重复 Close，与改变 probe/Main 次数不同。Close 返回仅能说明调用返回，当前也没有证明内存释放成功；不能把 `not_verified` 改成成功释放 |
| 有效前缀与 sentinel | 旧把整个 clocks buffer（含 sentinel/padding）拼接，再按 wave 长度截断；当前每次只取第一个 `-1` 之前的 prefix，首项就是 `-1` 表示本次无 clocks | **建议保留为独立返回接口修复，但与下列严格校验拆开。** 对采用这一终止合同的模型，它防止将 padding 当真实 clock。不能靠 trim 修复推导“所有模型必须提供有效 clocks” |
| NaN 预填 | 旧 buffer 初始化为 0 后跨 C chunks 复用；当前每次调用 C 前把全部槽改成 NaN，再据此暴露未写值 | **不属于纯观察。建议从最小迁移默认行为中移出／独立审议。** 它实际改变传给 DLL 的 buffer 初值，并与 sentinel / finite 检查耦合。能检测未填槽是价值，但还没有当前真实模型证据支持其默认兼容性；不能简单称为零影响的诊断 |
| missing sentinel / finite / nonnegative | 当前无 sentinel 或 prefix 内非有限／负 tick 会使整次 GetWave 失败；即使 caller 不消费 clocks 也执行 | **不应作为所有 AMI 路径的迁移默认前提。** 对确实请求并消费 timed clocks 的路径，拒绝无效输入有必要；对 Tx、response probe、Rx 不用 clocks 等路径，不应仅因未使用的时钟字段不满足新合同而丢弃 status 成功的 wave。两种模式需分开接受，不能用恢复 padding 解决 |
| chunk / Python call 严格递增 | 当前 `_last_clock` 在一次 Init epoch 中跨 C chunks、跨 Python `getWave` 调用保留；直到重新 initialize 才重置 | **新时间语义，建议撤出通用默认 wrapper，另按被接受的 clocks 合同判断。** chunk 连续性与跨 response probe／Main 阶段连续性不是同一个命题；禁止重复、重置、回退扩大了失败域。本次未证明全部调用者遵守绝对时间连续合同 |
| initialized / failed epoch | 当前要求先成功 initialize；异常后 `_epoch_failed=True`，后续 GetWave 必须重新 Init。异常包括 status 失败，也包括 clocks 校验失败 | **拆开保留。** “没有有效 Init 不调用”及实际 ABI 失败后不继续消费未知状态值得保留；仅因不被使用的 clocks 不满足新规则便污染整 epoch，是上述新合同的外溢，不能捆绑为迁移必需 |
| host-owned diagnostics | Init、Close、每 C call 保存状态、输入／输出、raw clocks、params，属性返回复制 | **观察价值可保留，受资源成本约束。** 不伪造成功，不以额外采集证明 DLL 状态 reset 或容量安全。是否保留全量波形属于观察成本选择，非计算公式 |

这些规则目前在同一个公共 wrapper 中执行，影响所有调用者，**不只影响新增的 Rx timed-clock 分支**。尤其 legacy helper 在某些名义 Init / Tune 路径仍调用 `get_responses()`，而该函数默认允许 GetWave response probes；不能只看 `use_getwave=False` 就断言不会经过新规则。这个历史耦合本身也不应在本轮迁移建议中悄悄扩大重构。

buffer 的 `bits_per_call + 8` 容量来自基线，当前未提供通用 ABI 容量证明。NaN、sentinel、status 检查都不能把这项 UNKNOWN 转为验证完成。

依赖固定本身应保留：未来若采用较小修复集合，应固定那个确切对象，并同步 `.gitmodules`、submodule Gitlink 与 `pyproject.toml` 的来源；不能为了“回退 fork”改回漂移的宽版本范围。`uv.lock` 的 workspace editable 路径也不是脱离实际 checkout 的 SHA 保证。

## C. RNG API 与非零 seed 默认策略是两件事

来源：PyAMI `81c4e5a` 的 [get_responses][pyami-response]，以及 PyBERT `ec72c92` 的 [Rx selector][rx-selector] / [probe helper][ami-epochs]。

- **可选 `rng=` 参数建议保留。** 不传时仍构造新的 entropy Generator；这也是基线行为。增加可选依赖注入，不会自动改变原调用者的随机序列合同。
- **自动把 `self.seed` 传到 Rx response probe，不是迁移必需，建议从迁移默认策略撤出。** 当前非零 seed 令 probe 的随机训练前缀固定，基线该前缀使用私有 entropy RNG；因此即使 Main 的全局 seed 同为 1，两者也不必给模型相同适应输入。这改变模型输入，而非只让日志可追踪。
- `seed=0` 的 probe 仍为 entropy，不意味着整个 C1 与基线等价：C1 另外重置 Main handle。反过来，取消 seed 绑定也不等于恢复 C1 的旧状态。
- 若日后接受确定性 probe 策略，应作为独立数值合同保留，说明它固定的是宿主生成的 prefix，不是 DLL 内部随机源、隐藏全局状态或整个工具链。当前真实 AMI 结果仍不能据此宣称可复现。

不建议用把 probe 移到 NumPy 全局 RNG 的方法“统一 seed”；那会引入另一种状态耦合。纯迁移只需保留实际旧策略，并诚实记录其 UNKNOWN。

## D. C1 fresh Main：超出迁移，建议单独接受后再作为默认

来源：`ec72c92`（#30 / PR #31），[ibisami.py][ami-epochs] 与 [bert.py selector][rx-selector]。

基线是同一 AMI 实例 / Init handle 先进行 response probes，再处理 Main waveform，Main 继承 probe 已发生的适应。C1 对指定路径变为：

```text
probe Init → GetWave responses → 复制 h/out_h → Close
main Init  → 从冻结 x 首样本执行 GetWave → 复制 wave/clocks/params → Close
```

这不是把 GUI 调用搬到后台线程。它改变初始适应状态、Init/Close 次数、可能的内部随机历程和 Main 返回 wave/clocks/params；且 h/out_h 仍来自 probe，Main 来自另一历程。模型结果可能改善、恶化或不变，本次不能给统一方向。

**建议：从“纯迁移默认路径”撤出 C1，保留其需求与源码证据作为独立 native 改进候选。** 若目标是建立定义更清楚的 fresh-Main 实验，那是合理但额外的目标；需要针对真实模型接受，不宜由 Web 迁移暗含授权。

范围也必须准确：当前只在 **Native/Init Tx + Rx GetWave** 的一个调用点选择 C1，且不取决于 `rx_use_clocks` 开关。Tx GetWave、双 GetWave、Rx Init/Tune 没有因此全部隔离。禁用 clocks 不会自动恢复 legacy Main 状态。

撤出依赖有两条必须一起处理：

1. C1 依赖新 PyAMI 的 `close`、`last_init_call`、`last_close_call` 和 `get_responses(rng=...)`。不能先将依赖 pin 回旧对象而保留该 caller。
2. Main 在该调用点将 origin 写为 `c1_fresh_main`，D1 以此为前提。去掉 fresh Main 但保留这个标识会产生错误来源声明；恢复 legacy probe→Main 又保留跨整个 epoch 的严格 clock 连续性，也可能在两个 probe 或 probe→Main 边界新增失败。状态、origin 和验证合同必须成组处理。

## E. D1：必须区分旧采样意图、旧缺陷与新增合同

来源：`782c31b`、`85dfed8`、`2a0a265`、`acdfee7`、`418d72b`（PR #32）。[旧分支][old-clock-loop]、[新 clock helper][clock-producer]、[当前 Main][clock-main]、[Eye helper][calc-eye]。

### 对上一份审查的明确细化

**`edge + UI/2` 和“在时间网格上找首个不早于该目标的样点”在基线已经存在。** 旧代码先计算 `sample_time = clock_time + ui / 2`，再 `while t[t_ix] < sample_time` 向前移动。新 `searchsorted(..., side='left')` 在时间网格有序、目标单调、落在记录内且映射索引互异的域上，实现相同选择。不能把它描述为迁移创造了一套新的半 UI 采样公式。

旧 timed 分支也已经用 `dfe.decide`，并绕过 native `run_dfe` 的 DFE/CDR/AGC 更新。这不是 D1 首次引入的结构。

但旧循环写成 `pairwise((clock_times, clock_times[1:]))`，迭代到的是两个数组，而不是相邻标量 clock；当 `len(clock_times)>1` 时，后续 `if clock_time == -1` 会遇到多元素数组布尔判断。**旧分支有实际代码缺陷，不能当作正常运行的数值 oracle。** 上述等价仅针对原代码表达的标量采样意图，并非“旧分支已执行且与新结果相等”。本次没有动态运行它。

### 逐项判断

| 子项 | 实际变化 | 建议 |
|---|---|---|
| 修正数组 pairwise 缺陷；保留半 UI / ceiling 选点 | 修复能使原意成立的循环；`searchsorted` 可以是该修复的一种实现 | **独立 native bug fix，有保留价值。** 如果只批准迁移，不应把整个新 pipeline 当作最小修复。回退也不能恢复坏循环后宣称功能可用 |
| clocks 来源与模式 | 新合同要求 `c1_fresh_main`，只消费特定单 Rx GetWave 路径；双 GetWave clocks 不消费 | **新增支持域。随 C1 单列处理。** 来源标识必须对应实际运行；去掉 C1 后不能继续声称该前提满足 |
| NRZ / PAM4 profile | 新 helper 对 NRZ 建立默认合同；非空 PAM4 clocks 要显式 profile，当前 Main 未传该 profile，会拒绝 | **新增能力边界。保留诚实的 unsupported 结论，不把拒绝算迁移成功。** 不能仅因 PAM4 在 GUI 有选项就声称该 timed 模式可用 |
| clock 格式与网格检查 | 不做修补/平移/clip；检查有限、非负、递增、域内及重复 sample index，异常拒绝 | **消费真实 timed clocks 时合理的输入合同，但不是所有旧模式等价。** duplicated-index 拒绝等是新成功条件，应单列；不消费 clocks 的分支不应无端受它牵连 |
| decision 数量 / 最后一 edge | 新实现为每个符合范围的 edge 取得真实 sample/decision，包括不需下一 edge 才能作决定的末项 | **行为定义变化。** 与“把旧数组循环改成标量 pairwise”的最小修复还不完全等价，后者会需要 next edge。因旧代码本来坏，不能报一个实际运行前后数值差来替代判断 |
| BER / Viterbi 窗口 | timed 路径要求足量实际 decisions，不再用 Native 的 pad-front；保存 producer 索引用于消费者窗口，Native 路径保留旧规则 | **新增数值输入与成功合同。建议从纯迁移默认集合撤出，与新 timed 功能一并接受。** 不应为了恢复旧成功率伪造真实 decisions；不够就明确该模式未支持或失败 |
| Eye 选点 | timed Eye 用已消费的实际 grid indices；每条完整 2 UI trace 和所需数量成为成功前提 | **派生分析输入发生改变。随 timed producer 处理。** `calc_eye` 的原 Native 分支仍可保留；不要以恢复旧外观为理由编造补足 traces |
| period 的归属和 mask | 新实现把相邻 edge 差放到对应 sample-index 区间；头尾未知用 NaN+mask，不外推。旧意图是在走向本次样点前填入 `ui_est` | **新时间解释与显示数据合同。不是单纯换横轴。** 有价值，但需和 timed producer / reader 成组，不能借 Web 绘图名义默认改变 native 数据语义 |
| period FFT / histogram | 新算法要求预定内部窗口完整有效；histogram 基于网格上的已知 period，不能当作逐 edge 统计 | **新增分析窗口与权重合同。超出最小迁移。** 不把不同窗口统计硬称同一输出；不足时 unavailable / failed 应如实保留 |
| lock 与 readiness | 旧意图以 `n_clks >= ignore_bits` 构造 locked；新逻辑不以 readiness 冒充模型 lock，保留有来源的返回或未知 | **观察语义修正，建议保留“readiness 不是 lock”的原则。** 这是可独立说明的修复，不是整个 D1 必需的证明；没有真实 lock 时不要补造锁定轨迹 |
| producer 状态、partial | 记录哪些 clocks 真被消费、到哪个阶段失败 | **观察可保留。** 不能只看请求开关或出现数组，就标记 native CDR 已运行、AMI clocks 已消费或结果完整 |

**总体建议：D1 的 expanded live contract 单列；若当前目标严格限于迁移，暂不把非空 AMI timed-clock 模式作为可用功能。** 对用户明确请求的 clocks，不能静默转为 native CDR 并标成功；真正没有返回 clocks 的已声明 fallback 与忽略有效 clocks 的行为应区分。保留配置/归档读取与明确 unsupported，优于恢复已知坏实现后宣称 parity。

以后若单独接受最小 timed bug 修复，范围应围绕“正确迭代标量、原半 UI 采样意图、真实 decision”界定，不必同时接受 fresh Main、随机前缀、period 重定义和所有窗口发布门槛。本次只给边界，不新增测试框架或执行数值验证。

## F. D2：保存格式要保留，live 默认合同随 D1 处理

来源：`1b0877f`、`6e99776`、`f14ef52`、`9bb89d1`、`5e85178`、`8180e00`、`8cec174`（PR #33）。[clock context][clock-context]、[data collect][d2-data]、[worker][d2-worker]、[archive][archive]。

| 部分 | 保留／撤出建议与原因 |
|---|---|
| raw6 / `ami-clock-grid-v2` 读取与校验 | **保留。** 它们已经定义已保存数据的解释，包括实际 grid clock、period mask、window、source 和相关 decoder contract。回退新运行默认行为，不授权将旧 raw6 改成 raw4、去掉 feature 标识或忽略一致性校验 |
| 现存 NPZ、manifest 与历史失败原件 | **原样保留。** archive 重开读取原 bytes，不调用 Main 重算。保留旧结果只是保存历史事实，不表示接受它为当前默认或已完成真实模型资格 |
| 生产时 `clock_context`、clock arrays 与 manifest 接线 | **与 D1 成组处理。** 当前 collect 从实际 producer snapshot 取得 clock context，raw6 必须有对应 capture；删 producer 而留 consumer 会失败或缺失，不能靠 fabricated default 消除错误 |
| 两个 timed Eye 与全部 period 分析必须 available 才发布 Run | **从最小迁移默认合同撤出，或作为新 timed 功能的明确支持条件单列接受。** 当前 `data.py` 会因缺少任一个必需 Eye/period analysis 拒绝发布，即使已有 Main wave。这是新增任务成功语义，不是只有展示层差别 |
| snapshot / partial / 阶段记录 | **保留有实际来源的诊断。** 失败时记录 raw clocks、producer 状态、phase 和错误，不把它转成功；若 D1 producer 移除，相关字段应 unavailable / unknown，不能从 `rx_use_clocks=True` 推断“已执行” |
| decoder schema 接线 | **历史 reader 保留；live 按 producer 成组调整。** raw6 即使 Viterbi 关闭也依赖已捕获 DFE/BER 合同；不能因 Web AMI+Viterbi 未支持就把整段 D2 decoder 读取删掉。Native Viterbi 的既有功能独立保留 |
| 前端轴、单位、mask 可见性 | **保留真实字段的显示。** 只要结果来源准确，显示 unavailable、partial 和旧合同标签属于迁移质量，不是改变物理计算 |

因此，“回退 D2”不能等同于 `git revert` 整个 PR。要保留历史格式识别与解释，移除或重接的是不再有对应 producer 的新运行调用和发布门槛。也不能通过给旧 Main 人工补一份 `c1_fresh_main` 或已消费状态来满足现有 validator。

## G. PR #34：不能先回退恢复入口失败

`0a7a036` 把向 Traits `Dict` 写入的形式修为兼容写法，关联 D1 新增的 `ami_clock_info` 和后续更新。它本身没有引入新的采样公式。

**只要这些写入仍存在，就保留修复。** 部分写入在 Main 无条件入口，先回退 #34 会使 Native 也可能在到达真正算法前失败。若最后完整撤除相关 live producer，才按实际引用删除由其产生的孤立字段、导入和写入；不要因“#34 是 D1 的后续提交”就先撤销。保留这个修复不等于 D1 的全部行为是迁移必需。

## H. 非 AMI 项的范围判断

| 项目 | 建议 |
|---|---|
| S8P/S12P through / FEXT 映射，`b87c80c` | **独立 native bug fix，建议明确接受后保留。** 修正的是输入物理导体组合，确实改变 channel 和下游数值；原公式未变不意味着结果未变。已有针对性外部模型/物理 oracle 比当前 AMI clocks 更充分，但不扩展成硬件资格。严格零 native 改动的迁移应声明这些模式未支持，不应为 parity 恢复错误布线 |
| fresh worker、取消、资源隔离 | **必要运行适配，保留。** NumPy 全局 RNG、共享 plot state 和可变 GUI 对象使并发隔离有实际理由。比较应固定完整初态；不要求复制 GUI 的隐藏缓存缺陷 |
| seed 缓存旧缺陷 | **单列 native 修复候选，不在迁移中悄改。** 原报告的“GUI 旧实例仅改非零 seed”反例是静态可达性，尚无动态 UI 重现；当前一致性声明应限定 fresh / 缓存正确失效的对象 |
| 自动回写适应参数 vs Web 草稿/结果 | **保留显式 Use candidate / 应用结果流程。** 若两次 Run 初始 decision scaler 或 EQ 候选不同，就说明状态不同，不能以同一 YAML 宣称任意操作历史等价 |
| waveform/CDR 取样显示、额外 FFE 图、轴修正 | **作为显示选择保留并明示窗口/来源。** 原始结果可一致而投影点或坐标不同。新增观察不应变成新物理链路或伪装成 GUI 已有字段 |
| channel Eye 显示噪声 | **保留 clean Eye 和可辨认的噪声展示来源。** 固定 seed 34003 的 display noise 与 GUI 的全局 RNG realization 不同；它不反馈 BER。不能用固定噪声掩盖“像素完全等价”的证据缺口，也不需要为迁移默认制造同一随机 realization |
| Native optimizer、Viterbi | **保留同一计算入口、候选观察、应用动作和既有支持边界。** 不扩大新搜索，不把前述 AMI wrapper 行为自动覆盖成 optimizer 已验证 |
| COM 独立任务 | **保留原 helper 和可见的完成/失败状态。** scheduling 可变，计算输入和候选顺序需守住；不执行默认大搜索，不把历史 `BLOCKED_BUDGET / NOT_EXECUTED` 当实现中已有硬预算阻止，更不把本次建议写成 COM 通过 |

## 推荐的最小迁移边界

建议以以下范围作为明确的产品目标；不是承诺当前代码已按此调整：

1. Web 收集和冻结与 GUI 同义的完整输入，在隔离进程调用原 Run / Tune / COM 入口；保留取消、资源身份、显式候选应用、实际异常与结果观察。
2. Native 支持域、旧 AMI 配置、已有保存结果和 archive 重开继续可用；对于 AMI 新 timed-clock 路径不宣称真实资格，明确标为未支持／待独立接受。既有 legacy AMI 路由是否可声明可用，只依据各自固定版本实际证据，不能从早期 #10 推导当前新 fork 全部通过。
3. tuple 最小兼容、status 错误处理、handle 生命周期、正确 prefix 提取及多端口映射作为**显式独立 native 修复清单**保留建议；不把全 PyAMI fork、C1、D1、D2 live 发布门槛捆成“必要修复”。
4. 移出新默认 probe seed 策略与 C1 fresh Main；D1/D2 live producer / consumer 作为单独 timed 功能成组处理。保留旧 raw6 reader、原件与故障证据，来源和 unsupported 状态始终准确。

如果要求字面意义的“一个 native 语义也不能变”，第 3 项也必须单列延期；相应坏路径应收窄支持范围。这种严格变体不应通过重引入已知错误再宣称功能完整来实现。本审查更建议保留有明确缺陷依据的小修复，同时公开它们超出迁移的事实。

## 若以后批准调整，按依赖成组进行

下列是避免破坏可运行性和历史可读性的顺序建议，**本次未执行任何一步**：

1. **先固定读取兼容。** 保留现存 raw6/feature reader、stored clock/decoder validators、保存 bytes、失败 raw snapshot 和来源说明。历史记录不得降 schema、重算覆盖或改成新结论。
2. **确定默认支持边界，再处理 D2 live 消费与 D1 producer。** 调整 live `clock_context`、analysis、Eye/period 发布条件、decoder capture、AMI annotation 和相关 GUI period 绘图，与 Main producer 同一逻辑变更交付；不能留下指向不存在 producer 的入口。请求 timed clocks 时要准确拒绝／报告未支持，不得静默忽略。PR #34 在关联写入仍有引用期间继续保留。
3. **随后移出 C1 selector 与新 seed 策略。** 同步去除或改准 `c1_fresh_main` provenance；不要把 legacy 初始化历程贴上 fresh 标签。D1 对 origin 的要求和 PyAMI 跨调用 clock 连续性要一起解除不成立的依赖，防止恢复 legacy 调用次序后被新 validator 阻断。
4. **最后替换 PyAMI 修复集合与 pin。** 先消除 C1 / capture 对新 API 的依赖，再选择确切依赖对象；保留已接受的窄修复，撤出未接受的通用 clocks 合同。更新所有 pin/source 声明一致，不回退到漂移版本范围；可选 `rng=` API 单独保留不会强制任何 caller 采用新策略。
5. **仅清理此次变更形成的孤立代码。** 不触及 Native DFE/CDR/Viterbi 本体、既有优化评分、channel 数学或无关历史材料。调整后的输入、实际分支、来源、成功/失败语义仍需重新核对，不能把当前有限 Native 数组相等直接搬作新版本的全域结论。

最危险的错误顺序是：先降 PyAMI 再留 C1 caller；先撤 #34 再留 Dict 写入；先删 D1 再留 D2 hard requirement；删 raw6 reader 导致旧归档无法打开；保留 strict 跨阶段 clocks 而恢复 legacy probe→Main；或恢复 legacy 状态却继续标 `c1_fresh_main`。

## 证据与执行边界

本次只依据已经读取的固定源码、Git 差异和上一轮保存的证据继续判断，没有扩展数值审查或引入新的实验。旧 889 项 exact 只属于两个固定 Native 场景的保存数组；它不能证明当前 AMI、C1/D1 或各类状态历史。真实 DLL 的适应影响、PAM4 profile 合法域、全调用者的绝对 clock 连续性和 ABI 容量仍 UNKNOWN。

本次只新增本建议文档，验证采用文本／Git／stdlib；产品修改、Main／NumPy／coopt／COM／AMI 调用、安装、提交、push、PR 和 issue 均为 0。原报告、脚本、清单与所有历史失败原件保留。本文给出保留／撤出建议，不表示用户已批准回退，也不把未执行的调整或验证写成完成。

<!-- Fixed source objects; no moving branch-tip references. -->
[config-load]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/config.py#L378-L396
[ami-capture]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/ami.py#L298-L368
[ami-params]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L85-L146
[pyami-prefix]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L311-L324
[pyami-abi]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L368-L624
[pyami-response]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L720-L758
[ami-epochs]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/ibisami.py#L113-L284
[rx-selector]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L450-L456
[old-clock-loop]: https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L519-L596
[clock-producer]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/ami_clock.py#L18-L253
[clock-main]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L583-L778
[calc-eye]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/sigproc.py#L395-L442
[clock-context]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/clocks.py#L42-L118
[d2-data]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/data.py#L426-L460
[d2-worker]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/worker.py#L139-L223
[archive]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/archive.py#L164-L220
