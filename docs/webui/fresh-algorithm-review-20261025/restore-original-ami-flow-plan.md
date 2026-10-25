# 恢复原 AMI 初始化与自适应流程：最小方案

2026-10-25；同一位 fresh Astra 审查者的后续方案。用户已决定恢复原流程，本文据此给出改动边界，**不再重新讨论是否恢复，也未实施修改**。

## 结论和范围

**恢复为：一个模型、一次 Init、同一 handle 上的两次原 response probe，随后继续 Main；最后一次显式 Close。** 保留原 probe 输入构造与默认 entropy RNG；不复制模型内部状态到 fresh 实例，不增加训练，不通过处理输出补偿流程差异。

恢复的最小生产改动集是 **3 个 PyBERT 文件**：`utility/ibisami.py`、`models/bert.py`、`utility/ami_clock.py`。当前 legacy 路径还在，可直接恢复使用，无需整 PR revert，也无需为这一步先修改 PyAMI fork、依赖 pin 或 Web archive reader。

时钟原点另作独立问题：本步骤保留 raw absolute clocks；未建立有证据的 Main 坐标映射前，不让非空 clocks 冒充 `c1_fresh_main` 进入 D1。显式未请求 AMI clocks 的运行继续走原 Native CDR；合法空 clocks 保留既有 fallback。用户请求非空 AMI clocks 时保留明确的 unsupported／partial 状态，不能偷偷忽略请求。

真实 AMI 验收仍暂缓。以下调用数和状态结论来自源码，不是本次执行结果；产品、NumPy、engine、DLL、coopt、COM 数值调用均为 **0**。

## 只读来源核对

| 对象 | 本轮读取结果 |
|---|---|
| PyBERT 基线／目标 | `1bc905d577d2f3bd9471421cfbf3d422d4e6080e` → `ab36b656a61cb6866da98105d72f6cacfb118031` |
| 审查 worktree | HEAD `54964c2c098e3a3807c4d68f96ce51621939f372`，tree `8412b639f4dd6f51c227e19d649a333fbad9d6a2`，与目标同 tree；无 tracked 修改 |
| PyAMI 读取 clone | HEAD `3bc5d43f81160bd022624c6c48b4a42651a874b8`，tree `1a74ae9844f657e5567c435345fdd561a1f747fe`，与固定目标 `d6d1f7fe7e58536546a1cfb9430c750cc2cb103e` 同 tree；工作区干净 |
| 旧审查材料 | [README](README.md)、[上一份建议](migration-scope-recommendations.md)、静态脚本及清单的 SHA-256 与交付时相同；不改写它们 |

未发现本轮相关源码漂移。原代码明确写明：随机 `Ignore_Bits` 前缀用于模型适应，之后限制连续相同比特长度以避免 de-adaptation；调用链也确实在同一个对象上连续作两次 `getWave`。源码证明 probe 会实际驱动模型，且作者有意提供适应输入；具体模型的内部状态或数值是否变化，本次未动态证明。没有找到作者专门说明为何让 Main 继续复用该状态的文字，但也没有证据证明这个原流程有错。不能称其为“已证实的污染”。见 [基线 probe 构造与两次调用][old-probes]、[基线 helper][old-helper]。

本轮对上一份建议再作一处明确细化：**不能仅为恢复旧调用顺序，默认删除同一模拟内跨调用的严格 clock 单调检查。** 官方 IBIS 6.1 第 188 页规定 clock_times 以首次 GetWave 的模拟起点为原点，并要求连续调用的有效 ticks 严格递增；还允许一次调用给出的 tick 对应下一段 waveform 的采样点。这是 clocks 的时间合同，不是要求 fresh Init 的依据。[IBIS 6.1，第 188 页](https://ibis.org/ver6.1/ver6_1.pdf#page=188)

## 1. 原流程、当前 C1 与目标流程

| 阶段 | 原流程 | 当前 C1 指定 Rx 路径 | 本次目标 |
|---|---|---|---|
| initializer / 模型 | 构造一次 initializer；构造一个 AMIModel | 冻结输入；probe/main 各自重建 initializer、各自创建 AMIModel | 沿用当前 legacy 路径，一次 initializer、一个模型 |
| Init | 一次；产生 handle H | probe Init 得到 H₁，Main 另一次 Init 得到 H₂ | 一次，所有后续调用保持 H |
| probe 1 | GetWave(u)，先随机适应前缀，再原 limited-run 序列 | probe 模型上 GetWave(u)，随机生成器自动绑定 PyBERT seed | 恢复原 u 构造，不传新增的 `rng=`／seed 策略 |
| probe 2 | GetWave(convolve(u, channel)[:len(u)])，复用同一个 u 与 H | 仍在 H₁ 上执行 | 复用原 u 与 H，完整保留此第二次训练历程 |
| probe → Main 边界 | 不 Init、不 Close、不重建模型 | Close H₁；重建 initializer 和模型；Init H₂ | 不 Init、不 Close、不搬运隐藏状态 |
| Main | GetWave(x)，继续 H 的适应状态 | 从新 H₂ 开始处理 x | 原 x、原分块，继续 H |
| 返回与清理 | 返回 helper 结果；对象销毁清理不构成确定的宿主 finally 保证 | 每个 role 各有 finally Close | 先取得宿主拥有的返回值，整个 helper 生命周期在 finally 中 Close 一次 |

当前只在 **Native/Init Tx + Rx GetWave** 的一个 caller 传入 `_probe_seed=self.seed` 选择 C1，不受 `rx_use_clocks` 开关控制。移除此选择后，其余已有 Tx、双 GetWave、Init/Tune 的调用顺序无需随之重写。见 [当前 caller][current-caller] 和 [当前两条 helper 路径][current-helper]。

### initializer 的输入与构造时机

保留 `_make_ami_initializer(init_inputs)`，无需把函数重新内联。它把原准备逻辑抽出，仍以 `param_cfg.input_ami_params`、`info_ami_params`、`ui`、`ts`、`chnl_h`、`fext_hs` 构造 initializer：

- 每次 helper 开始时取该次调用的有效输入，**仅构造一次**；probe 后不重新取参数树、不重新准备 channel，也不重新 Init。
- 保留 `chnl_h / ts`、FEXT pad/truncate、通道行顺序、`row_size` 和 `num_aggressors`。保留先设置 `sample_interval` 再设置 `channel_response` 的顺序。
- 保留模型 Init 对真正输入 channel 的适应和 response deconvolution；不再用理想 channel 重新 Init，也不添加任何“预热”调用。
- 若保留输入快照，只用于宿主证据，不额外构造第二个 initializer，不把 probe 的 Init 输出、参数或权重装入另一模型。

`AMIModel.initialize()` 内部会先执行一次 Python `close()`；对刚构造、尚无 handle 的模型，该调用不进入 C `AMI_Close`。之后 `_initialize()` 执行一次 C `AMI_Init`。不要把这次无 handle 的 Python 调用误计为已关闭一个模型。见 [initializer 准备][initializer]、[PyAMI Init / Close][model-lifecycle]。

### 实际调用账与分块

正常、非空 GetWave 路径，目标调用账为：

| 项目 | 目标次数／不变量 |
|---|---|
| AMIModel 构造／initializer 构造 | 各 1 次 |
| C `AMI_Init` | 1 次 |
| Python `getWave` | 3 次：probe 1、probe 2、Main |
| C `AMI_GetWave` | 由各输入实际长度和有效 chunk size 决定，**不是固定 3 次** |
| probe → Main 间 C `AMI_Close`／Init | 均为 0 |
| 结束时 C `AMI_Close` | 正常取得 handle 后 1 次；后续幂等 close / 析构不得重复调用 |
| handle / epoch | 三次 Python GetWave 内全部 C chunks 均属于同一模型 handle 与 Init epoch |

令 `S = int(ui / ts)`，`I` 为该模型实际 `Ignore_Bits`，原 `get_responses` 默认 `nbits=20`、`max_run_length=10`。正常输入构造下，两次 probe 长度均为 `(I + 20) × S` samples；第二次是**同一 u** 经 channel convolution 后截取同长，不是重抽一次随机前缀。每次 probe 的有效 chunk size 为 `40 × S`，末尾不足整块时使用真实剩余长度，不补成整块。Main 传入原 `bits_per_call`；为 0 时沿用 probe 后对象内已有值 40，非零时保留原覆盖规则。[原 probe][old-probes]、[原 chunk 行为][old-chunks]、[当前 chunk 行为][current-chunks]

所以，在上述正常构造条件成立时，C calls 数可按三段各自向上取整求和；这只是源码推导。**用于时钟原点的值必须来自实际成功调用的 sample 数与 ts，不能拿公式或固定 40 UI 替代运行记录。**

### 最终 finally Close 可以保留

可以把当前 C1 中有效的清理原则放到恢复后的单次生命周期末尾：prepare → Init → 两次 probes → Main → 获取宿主返回值 → finally Close。要点是：

1. `y/clocks/h/out_h/params/msg` 在 Close 前已复制或确认由宿主拥有；关闭模型不能留下指向 DLL 已释放内容的借用。
2. Main 成功也执行 Close；probe、Main 或复制失败时亦清理已拥有的 handle。不得为“补偿失败”再 Init 或自动重试。
3. 保留 primary error 与 cleanup error 的区分，不能让 Close 错误掩盖原始失败，也不能把 Close 失败记录成释放成功。
4. Init 失败时 wrapper 可能已经清理 handle；外层 finally 的再次 `close()` 应是幂等 no-op，不再进入 C。Close 是否真的释放资源仍不由调用返回单独证明。

这是明确的生命周期修复。它不改变成功路径中 probe 与 Main 之间的模型状态，但清理错误会作为真实失败被保留；不能声称它与旧析构时机完全没有可见差别。

## 2. 最少需要修改的文件与函数

以下都是**待实施清单**，本轮未改代码。

| 文件 / 函数 | 最小改动 | 不必做的事 |
|---|---|---|
| `utility/ibisami.py`：`run_ami_model`、当前 `_run_probe_main` 路径 | 停用并清除 `_probe_seed` C1 分支；以现存 legacy 主体执行单模型流程；将末尾 finally Close 与返回值所有权保护落到这一个生命周期。删去因此孤立的 C1 helper、参数、专用错误文字／导入，或只保留实际复用的错误记录部分 | 不新建多模式 runner；不保留一个默认关闭但可误选的 fresh-Main 开关；不重写 probes、convolution、response 提取或 Init-only 计算 |
| `models/bert.py`：指定 Rx `run_ami_model` caller 与 `clock_info` 写入 | 去掉 `_probe_seed=self.seed`；停止写 `main_origin="c1_fresh_main"`。准确记录“probe 后同 epoch Main”，并保留未修改的 `returned_edges_s`。该字符串是生命周期来源，**不等于已证明 clocks 已映射到 Main** | 不把模型状态复位替换成参数回灌；不改原 x、noise、EQ 或 Native DFE/CDR；不全局关闭用户请求的 clocks |
| `utility/ami_clock.py`：`new_clock_info`、`plan_ami_clocks` 的 origin / 空 clocks 路由 | 明确 producer invocation ID 只是本次观测标识，不是新的模型 Init epoch；让合法空 clocks 在 fresh-origin 前提检查之前按既有 no-clocks 路径返回。对恢复后同 epoch 的**非空** clocks，因映射未交付而明确拒绝消费并保留 partial 原件 | 不给新 origin 冒填 `c1_fresh_main`；不把单纯重命名当坐标证明；不改半 UI 公式、slicer、BER 窗口或 period 算法 |

第三行是必要接线：当前 `plan_ami_clocks` 在判断空 clocks 之前就要求 `c1_fresh_main`。只删除 caller 的 C1 标记，会连本来合法的“没有 clocks → Native fallback”也一起拒绝。最小方案只移动／区分这一前提，不放行非空的未映射 ticks。[当前 D1 guard 与空分支][clock-plan]

用户显式不使用 AMI clocks 时，Main 已有 Native 分支可用；该分支不能被新的 origin 标签错误阻断。当前默认 `rx_use_clocks=False`，本方案不改这个默认值，也不偷偷修改存量配置。

## 3. 明确保留的修复与本次不动的策略

**恢复初始化／适应顺序不需要先重写或整体回退 PyAMI fork。** 本步骤保留当前固定依赖；这表示缩小变更范围，不表示重新认定整个 fork 都是迁移必需或已验证。

| 项目 | 本次处理与理由 |
|---|---|
| tuple / string 消费修复，`80100e2` | 保留。原节点访问与固定 parser 的 tuple 类型不兼容，tap 字符串方法也有实际缺陷；恢复原模型生命周期不要求恢复这些失败 |
| Init / GetWave 显式 status 失败处理 | 保留。失败调用不能当成有效成功输出，不自动重试；不以恢复顺序为由忽略错误 |
| handle 所有权、幂等 Close、Init 失败清理 | 保留，并让外层最终 Close 覆盖完整单 epoch 流程；不再在 probe/Main 之间 Close |
| 每次 C 返回的 sentinel / 有效 prefix | 保留。去掉 sentinel/padding 不是模型状态重置，也不应把它们重新送入采样器 |
| 同一模拟的 raw ticks 非负、有限、跨 call 严格单调 | 对适用的规范合同保留；绝对时间检查发生在**原始 epoch 坐标**。不能在 Main 开始清零 `_last_clock`，不能先减一个偏移再验证跨 call 顺序，也不能靠再 Init 避开失败 |
| 可选 `get_responses(rng=...)` API | 保留 API；生产 caller 不自动注入 `self.seed`。省略时恢复原 entropy 策略，不承诺重复运行逐值相同 |
| PR #34 Traits Dict 写入，`0a7a036` | 保留。相关 producer 状态仍需写入，回退它会带回入口错误；它不决定模型是否 fresh Init |
| NaN 预填、未消费 clocks 也使整个 GetWave 失败、全历史 key set 校验等 | **本次不改，另议。** 它们确实可能扩大失败域，但不是恢复单模型流程的必要依赖。不能把它们统称为已证实 bug 修复，也不应借本次恢复扩大成整个 wrapper 改造 |
| failed epoch、diagnostics | 保留真实失败状态和原件；不因本次恢复就清除失败。哪些非计算诊断应影响整个任务成功属于上述另议范围 |

若恢复同 epoch 后某模型在 probe 2 或 Main 返回了重置的 clock 时间，应按其实际合同记录失败／不支持；这不是重新启用 fresh Init 的充分理由。当前未执行真实模型，不能预判某个模型必然合规或必然失败。

## 4. C1 / D1 / D2 与旧归档的最小依赖关系

必须一起处理的是 **C1 caller + 单模型 helper + D1 origin/空 clocks 路由**。不能只去掉第二次 Init，却继续标 `c1_fresh_main`；也不能只把 D1 的字符串白名单扩大就假定输入已经在 Main 坐标。

**本步骤无需修改 D2、raw6 reader 或 archive 内容。** 理由来自现有分支，而不是假定这些层不相关：

- D2 `clock_context()` 先处理实际已返回的 Native 分支；显式未请求 clocks，或合法空 clocks 的 Native fallback，返回 `None`，沿用原 Native raw 路径，不要求 `c1_fresh_main`。
- 恢复后的非空 clocks 在 D1 明确拒绝消费，不能进入 D2 的“完整 AMI producer”发布路径；worker 既有 finally 保存 partial snapshot 和失败阶段，保留事实。
- 旧 raw6 / `ami-clock-grid-v2` 记录确实属于旧的 C1/D1 合同。`validate_clock_arrays()` 对其 `c1_fresh_main` 和 version 2 的校验应保持；不能放宽旧 reader 来掩盖新运行来源，也不能把旧档改成新 epoch 或重算覆盖。
- `web/ami.py` 的 annotation 已读取实际 producer 字段，不需要为了恢复流程重新发明一套状态；`invocation_id` 可继续用于新鲜度检查，但不可拿它当 DLL handle/epoch 证据。
- Native Viterbi、DFE/CDR、优化算法、COM、现有显示投影和资源绑定不在恢复范围。保留其既有支持边界。

见 [D2 live 分支][d2-live]、[D2 stored contract][d2-stored]、[AMI annotation][annotation]。本步骤不会生产一种伪装成旧 raw6 的新 timed-clock 成功档。

未来如果独立交付“同 epoch、probe 后 Main clocks 映射”，D1 producer 和 D2 live consumer / 新来源的保存合同才需要共同扩展；旧 version 2 的解释继续不变。不能先改 reader 接受任意 origin，再补生产证据。本轮不选新 schema 编号，也不设计新的归档框架。

## 5. 时钟原点独立处理

### 必要的两个选择

1. **当前推荐：先交付状态流程恢复；未验证的非空 clock 映射保持 unsupported。** raw clocks、实际 wave 和失败证据保留，不猜零点，不额外调用模型。这是本次最小方案。
2. **随后若单独接受时钟修复：以真实调用账建立 epoch → Main 坐标映射。** 推荐保存 raw epoch ticks，在派生采样目标上转换到现有 Main-local grid，避免移动所有 waveform 的原始时间轴。等价的 epoch-grid 表述可用于核对，但不需要增加两个产品模式。

### 映射依据和公式

以下是基于源码调用顺序推导的实现要求，不是已有运行结果。设 Main 之前，同一 Init epoch 中已成功处理的 C chunks 依次为 `(n₁, ts₁), …, (nₖ, tsₖ)`。由实际 `wave_size` 和该 epoch 的 sample interval 建立：

```text
T_pre = Σ(nᵢ × tsᵢ)                 # Main 输入开始前的实际连续时间
target_epoch = raw_edge_epoch + UI/2
target_main  = target_epoch - T_pre
sample_index = 第一个满足 t_main[index] >= target_main 的真实样点
```

固定 sample interval、完整成功的当前路径可简化为 `T_pre = N_pre × ts`。应保留整数 sample 计数再乘该次 Init 的 ts，避免把累计 clock tick、请求的 bit 数或浮点重复加法当作精确计数来源。`UI/2` 对应已经接受的符号时间合同；当前未确认的 PAM4 profile 不因此自动获得支持。

一个等价的检查是将 Main grid 表示为 `t_epoch[index] = T_pre + t_main[index]`，直接比较 `target_epoch`。两者都不改变 DLL 的输入、handle 或适应状态；只变换同一物理时刻的坐标。第一样点的约定必须和原 Main grid 一致，不能另猜一个 `+ts` 或 `−ts` 修正。

实际实现前必须具备这些证据：

- 计数与 raw clocks 来自同一模型实例、同一 Init epoch；两个 probes 均完整成功，Main 前没有隐含 Init、Close、额外 GetWave 或失败后继续运行。
- 每个成功 C call 的真实 `wave_size`、该 epoch 的 ts、阶段边界可追溯；Main 入场时保存 `N_pre`。当前仅有总调用次数不足以推导样点数；当前 `last_getwave_calls` 还会被每次 Python GetWave 覆盖，因此不能在 `get_responses()` 返回后只读最后一组记录就声称已经覆盖两个 probes。
- 将必要计数保存在现有调用记录／少量宿主计数中即可，不需要新框架。若未来修改 PyAMI，范围仅是记录既有调用处理了多少样点、保留必要边界 clocks，不改变 wave、chunks 或模型调用次序。
- 若任何前置调用失败、样点数量缺失、epoch 对不上、ts 不一致且无法解释，或模型的实际 clock 合同不成立，应保留 UNKNOWN／unsupported，不套用推算偏移。

不能固定减 4 ns、40 UI、`Ignore_Bits × UI`，也不能用第一／最后一个 clock 的数值猜 `T_pre`。clocks 可能被抑制或不规则；数量与已处理 waveform 样点数没有这种一一关系。虽然某些零 Ignore_Bits、整齐网格的特殊输入可能恰好产生简单偏移，不能把特例写成算法。

### 跨边界 tick 与原件

不能仅取 Main 自己返回的 ticks 就认为边界完整：最后一次 probe 返回的 tick，其 `edge + UI/2` 可能落在 Main 开头；Main 最后一个 tick 的采样点也可能尚在记录之外。未来独立修复应按同一 epoch 的真实返回次序保留边界 ticks，再按 **目标采样时刻是否落在 Main 记录内**选取；既不丢弃合法跨段事件，也不外推未来样点。

raw clocks 必须原样保留。派生的 Main-local edge 可能为负，但其加半 UI 后的 target 仍可位于 Main 内；不能把 raw epoch 的“非负”校验机械套到平移后的坐标，从而删掉合法边界 tick。由此也可见：给现有 D1 的 `edges_s` 简单减常数，并把 guard 改成接受新字符串，不是完整的时钟修复。

旧 archive 若未保存前置样点数、epoch 与边界返回，不能凭配置补造有效 origin。历史 raw6 继续按自己的旧合同读取，不追溯改写。

### Ignore_Bits、适应状态与分析窗口

模型的 `Ignore_Bits` 是 probe 输入构造的一部分：原 u 含该随机前缀，第二次 probe 又处理经 channel 的同一 u；这些输入在同一 handle 上被处理，累计处理时间随之推进，具体内部适应变化仍取决于模型。恢复原流程时必须保留这些输入，不能扣除它们、改成一次训练，或因要让 Main 从 0 开始就重新 Init。

但“已经输入了很多训练样点”不证明模型锁定、已收敛或 Main BER 合格。模型 `Ignore_Bits`、Main 的分析窗口和返回 lock 状态是不同信息。当前 D1 使用 Main-local 时间判断 readiness；把它换成 epoch elapsed time，或将阈值减去 `T_pre`，可能让更多 Main decisions 进入统计，**会改变采样集合／BER 窗口**，不属于仅坐标改名。

因此独立时钟修复应先固定 Main 的既有分析窗口，明确每个阈值属于哪个坐标系；不自动将“probe 已适应”折算为 Main 的统计资格。需要改变 Ignore_Bits readiness、边界 tick 纳入、完整 Eye trace 数、最后 W decisions 或 period FFT 窗口时，应单独列出并验证，不能把变化都归为显示坐标。

半 UI 偏移及首个不早于目标的选点规则在原代码已有，保留它们；原数组 `pairwise` 缺陷也不应恢复。时钟原点得到正确映射仍不等于整个 D1 新分析合同已被接受。

## 6. 未来有界验收：结构与数值分开

以下仅列成功标准，**未授权／未执行任何测试或真实模型运行**。不增加长期资格计划或开关矩阵。

| 小范围检查 | 成功标准 | 是否需要真实模型 |
|---|---|---|
| 单生命周期结构检查 | 一次 initializer、一个实例、一次 C Init；两 probe 后同 handle 继续 Main；无中途 Close/Init；正常结束一次 C Close；省略自动 rng 绑定 | 替身调用账可证明宿主编排；不能证明真实适应数值 |
| 输入与 chunk 结构检查 | 对一个非零 Ignore_Bits、Main 含尾部不足整块的输入，核对两 probe 的 u / channel 后输入、真实 lengths、末块及有效 bits_per_call；不新增或补齐训练 | 替身可核对宿主输入／次数；不证明 DLL 正确处理 |
| 错误与清理 | Init/GetWave 失败不再继续 Main、不自动重新 Init；已拥有 handle 清理一次；primary 与 cleanup 失败均保留 | 小型失败替身足够验证分支，不构成 ABI 资格 |
| 原流程数值对照 | 独立表达原单 handle 调用顺序作为参考，不调用待测 helper；参考与恢复后实现使用同一固定 PyAMI、相同已保留修复及同一份真实训练输入。一个固定 NRZ 输入，每条路径各一次，比较 h/out_h、Main wave、raw clocks、params；无法保证相同输入和可比模型内部状态时不宣称 exact | **需要真实模型，仍暂缓。** 验证夹具复用一次训练输入不改变产品 entropy 默认策略；DLL 自身不确定性也必须注明 |
| 独立时钟映射 | 用一组已知 sample 账的时钟样本检查非零前置长度、跨段 tick、无 clocks、记录末尾 deferred、索引及阈值坐标；再由一个真实、可追溯模型记录核对实际 origin | 数学样本只验证映射实现；真实 clock 合同与消费行为须另获授权后由真实模型确认 |

未来真实数值对照不得用新 C1 fresh Main 作为“原流程”参考，也不得因为双方共同调用同一新 helper 就声称验证了恢复。两边固定同一 PyAMI 与修复集合，是为了避免把旧 wrapper 的 sentinel/padding 等差异混入初始化／适应顺序的恢复效果；参考独立表达原调用顺序，不要求重新启用旧 wrapper 缺陷。实际训练输入可在测试边界固定重放，但不能因此把生产 entropy 策略重新改成自动 seed 绑定。C1 历史协调替身测试、两组 Native 数组相等均不能替代这里的真实 AMI 证据。

本轮可审阅方案已收束：**先恢复单 Init 的原适应历程和正确清理；不动 fork 策略与旧 reader；非空时钟映射有证据后单独接受。** 未决条件仅在未来真实模型对照及时钟 origin / 窗口验收，不影响当前最小方案的明确性。

<!-- Source links bind to the reviewed objects. -->
[old-helper]: https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/utility/ibisami.py#L126-L172
[old-probes]: https://github.com/yx520143-G/PyAMI/blob/5270d713e40bac2be5747bef09b92df79df9085b/src/pyibisami/ami/model.py#L575-L650
[old-chunks]: https://github.com/yx520143-G/PyAMI/blob/5270d713e40bac2be5747bef09b92df79df9085b/src/pyibisami/ami/model.py#L481-L528
[current-caller]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L450-L460
[current-helper]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/ibisami.py#L113-L290
[initializer]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/ibisami.py#L77-L99
[model-lifecycle]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L375-L535
[current-chunks]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L537-L626
[clock-plan]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/ami_clock.py#L8-L83
[d2-live]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/clocks.py#L42-L118
[d2-stored]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/clocks.py#L284-L317
[annotation]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/ami.py#L380-L412
