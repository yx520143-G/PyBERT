# 其余改动复审：修订保留／缩窄建议

2026-10-25；同一位 fresh Astra / max 继续只读复核。用户已决定恢复原单 Init、probe 后同 handle 继续 Main 的流程，并取消自动 probe seed 绑定；本报告不重新讨论这两项，也不把 [三文件恢复方案](restore-original-ami-flow-plan.md) 写成已经实施。

**修订后的判断是：保留有代码缺陷或适用接口规范依据的修复；收窄把诊断／可视化完整性升级为整个计算失败的部分。不能把整个 PyAMI fork 或整个 D1/D2 一起判为保留或回退。**

本轮固定对象未变：PyBERT `1bc905d577d2f3bd9471421cfbf3d422d4e6080e` → `ab36b656a61cb6866da98105d72f6cacfb118031`，审查 worktree HEAD `54964c2c098e3a3807c4d68f96ce51621939f372` / tree `8412b639f4dd6f51c227e19d649a333fbad9d6a2`；PyAMI `5270d713e40bac2be5747bef09b92df79df9085b` → `d6d1f7fe7e58536546a1cfb9430c750cc2cb103e`，读取 clone 与目标同 tree 且干净。已有五份文件 hash 未变。本轮只新增本文，产品／测试／依赖／refs 没有修改，数值调用为 0，真实 AMI 验收继续暂缓。

## 先纠正前表中不够准确的判断

1. **NaN 预填不应因“改变了 buffer 初值”就建议回退。** `clock_times` 是返回缓冲区；合规写入的有效 prefix 和 sentinel 会覆盖初值，sentinel 后的 NaN 不参与结果。它是合理的未写检测，不是已证明的算法改变。尚无真实模型资格证据，也不等于已有回退依据。
2. **跨 C chunk／Python call 的 absolute clocks 严格单调有规范依据。** Python 调用边界不重启模拟；恢复原连续流程不能成为删除检查、清零 `_last_clock` 或另 Init 的理由。
3. **“caller 没消费 clocks，所以无效 clocks 不应让它失败”过于绝对。** 合法无 clocks 有明确表示；未写、无 sentinel 或非法 prefix 不自动因此合法。应保留检查与失败证据，区分接口失败和结果用途，不能默认放行所有未消费路径。
4. **参数 root／应返回的参数集合并非完全没有规范基础。** 但当前按 `float()` 是否成功得到的 key set、名字包含 `tap` 就合成同一矩阵，并不等价于按 `.ami` 的 Type／Usage 验证；不能据此要求所有诊断都满足统一数组形状。
5. **D1 不宜整体回退。** 半 UI、向上选点和 `dfe.decide` 原本已有；旧循环有明确错误。有效末 tick、不伪造 decisions、记录实际索引有保留理由。真正需收窄的是额外支持域和分析完整性门槛，而不是恢复坏循环。

另有两项窄缺口应明确记录：当前 Close 未检查返回码；参数输出指针没有按每次调用重新置空来辨认“本次未写”。它们不能因已添加大量诊断就视为解决，也不要求把本轮扩成整个 wrapper 重写。

## 适用依据

本轮主规范限定 **IBIS 6.1** 的相关接口与参数条款，不宣称所有版本或具体 DLL 已验证兼容。后文的保留建议以目标模型适用该合同为条件；库返回 status=1 不等于功能收敛或数值合格。

| 标记 | 已核对的规范内容 |
|---|---|
| S1 | Init/GetWave/Close：1 成功、0 执行失败；CDR 不稳定不自动等于执行失败。[§10.2.3，186、189–190 页](https://ibis.org/ver6.1/ver6_1.pdf#page=186) |
| S2 | clocks 为输出；有效 prefix 以 −1 终止，空结果为 −1；从首次 GetWave 起计时，跨调用严格递增；采样为 edge 加半符号时间，可跨 waveform 段。[§10.2.3，188 页](https://ibis.org/ver6.1/ver6_1.pdf#page=188) |
| S3 | 参数输出须符合模型树和所声明 Out/InOut；返回根名有要求，宿主每 call 先清空输出指针；Table 返回行数可跨 call 改变。[§10.2.3、§10.3，189、197、202 页](https://ibis.org/ver6.1/ver6_1.pdf#page=189) |
| S4 | Ignore_Bits 表示应忽略的初始化输出长度；它不是 lock 状态。[§10.3，206 页](https://ibis.org/ver6.1/ver6_1.pdf#page=206) |

这些条款不规定 PyBERT 的完整 Eye 数、period histogram 权重、FFT 窗口、raw6 schema 或 Web Run 必须展示哪些图。下面涉及这些部分时，以代码的数据依赖和明确的产品合同判断，不借标准名义补充要求。

## A. 参数返回：接口修复保留，诊断形状要求最小缩窄

来源：`80100e2`；[getwave_parameters][params]、[实际调用与消费者][params-consumer]、[固定 parser][parser]。

| 子项 | 原 → 当前；真实作用域 | 结论 |
|---|---|---|
| tuple／string | 原按 `.name` 访问 parser tuple，tap 筛选还有无效字符串方法；当前按 `(label, values)` 解析并用正常字符串方法 | **保留明确 bug 修复。** 改变的是此前会失败的接口路径，不是 DLL 内部公式 |
| 完整 path | 旧叶名假设 → 当前保留根以下 tuple path，避免不同分支同名数据被混合 | **保留。** 但路径存在不等于它有连续时间轴，不能仅按名字推断其物理含义 |
| 非数值／空值／Table | 当前不把不可转换值填为 0；部分 Table rows 被当作非数值观察省略 | **保留“不伪造数值”原则。** 省略表示该观察不可用，不等于模型没返回参数。原始参数字符串须保留；合法 Table 也不应硬当成统一 tap history |
| root、重复／混合结构、语法异常 | 当前会抛错；S3 对树和 root 的有效性有基础要求 | **保留识别错误，不合并错误结构。** 但当前只比较各次观测 root，不等于核对了模型声明。已有 wave 仍是实际返回证据，不能被删除；参数接口无效也不能被重新标为模型资格通过 |
| 每 call 的全 numeric key set 必须一致 | 当前把“本次能转为 float 的路径集”与第一次比较，任何增减都使共享 Main 抛错 | **最小缩窄。** 需要按实际声明和消费者区分必需参数与辅助观察；S3 不能直接推出这个转换结果集就是规范参数集。缺少声明必需的 Out/InOut 仍应报告接口错误；仅辅助历史不可合并时，让该历史 unavailable，不应自动废弃其余有效计算 |
| 所有 tap 名叶节点等长 | 当前凡 path 任一名称包含 `tap` 都列为列，并要求同一 call 等长后 zip；没有按实际 tap 组、Type 或时间戳分组 | **最小缩窄到真正同一矩阵的列。** 发布矩阵必须对齐，但不应把所有名字像 tap 的叶节点强作一个矩阵；不等长不靠 padding／截断补齐。无法证明对应关系时保留 raw，停止该图／表的生成 |

`getwave_parameters()` 没有接收 `.ami` 的 Type／Usage 定义；它是数值历史投影，不是完整 AMI 参数验证器。因此“所有缺失都合法”与“所有 numeric key 变化都代表 DLL 计算失效”都没有充分依据。规范允许的数据结构变化，也不意味着可以任意删除所声明的必需参数。

当前 Main 从这些历史取 tap、`cdr_locked`、`cdr_ui`；它们没有回写为已经生成的 GetWave wave。需要进一步区分：某参数若是后续数值真正依赖的阈值／配置，缺失必须阻止该后续运算；若只是观测 trace，不应牵连不依赖它的 wave。这里的建议是按依赖缩窄失败，不是无条件容忍坏输出。

还有一个先于“严格 key set”的宿主问题：这是**基线已存在的接口缺口，不是迁移新增回归**。基线 [初始化:405–430][old-param-init] 同样建立 `c_char_p(b"")`，[GetWave:481–528][old-getwave] 在循环中复用该属性。当前 [PyAMI `_initialize`:492–494][init] 和 [getWave:594–608][getwave] 保留这一行为，每个 C call 前未先重置为 null。

影响条件是模型本次没有给输出指针赋新值：宿主可能继续观察到上次指针，不能据此证明本次参数完整；模型每 call 都正确写入新指针／null 时，不据此断言必然产生旧值。`_getAmiParamsOut()` 对 null／空内容生成 `(root )` 是宿主兼容表示，也不应说成模型本次确实返回了该字符串。[参数属性][param-property] 本轮仅完成静态条件判断，没有真实 DLL 触发记录。

**建议作为窄接口补齐处理：在调用边界按 S3 初始化输出指针，原 raw／缺失状态与宿主标准化表示分开。** 这是防止旧返回冒充新返回，不是改训练或重新 Init；本轮不实施，也不靠新增 key set 异常替代它。

## B. status 与 Close：保留错误处理，补齐 cleanup 观测

来源：PyAMI `2b475fa`；[生命周期代码][lifecycle]、[Init][init]、[GetWave][getwave]。基线 Close 也忽略返回码，故下面的 Close 缺口不是本次迁移新增的回归。[基线生命周期][old-lifecycle]

| 子项 | 当前作用／接受域变化 | 结论 |
|---|---|---|
| Init/GetWave 只接受 status=1 | 原不检查 → 当前非 1 抛错；显式执行失败不再被当作有效结果 | **保留。** 有 S1 支持。成功码只说明函数执行状态，不能推导 clock lock、适应收敛或 BER 合格 |
| 未成功 Init 不允许 GetWave | 当前 `_initialized` guard 保护 handle 生命周期 | **保留。** 不应为了兼容旧成功计数而调用没有有效初始化的状态 |
| Close 先放弃 handle 所有权、幂等 no-op | 避免同一 handle 被外层 finally、重复 close、析构再次释放 | **保留。** 不论成功或异常都不自动重试同一 handle；恢复流程只把最终 Close 放到两 probes＋Main 之后 |
| Init 失败清理 | 已取得宿主认为拥有的 handle 时尝试 Close；原始错误和 cleanup 错误分别保存 | **保留，有边界。** 不凭 non-null 就证明 DLL 完全正常；失败、资源是否真的释放仍需准确记录 |
| Close 返回状态 | 当前 `_amiClose(handle)` 的返回值未读取；只记录 `returned=True` / `release_status="not_verified"` | **明确窄缺口，建议补齐。** S1 同样规定 Close 返回码。应记录 status；0 为 cleanup 失败，不能只因调用返回就当 cleanup 成功。仍不自动重试，也不把 status=1 等同于物理资源释放已独立验证 |

当前 `not_verified` 没有谎称已释放；问题是缺少可获得的返回状态，外层只能看到“没有抛 Python 异常”。精确对比是基线析构 [334–344][old-lifecycle]／重新 Init 前 [381–383][old-lifecycle] 与当前 `close()` [375–390][lifecycle] 都没有保存 C Close 的返回码。实际影响条件是 Close 正常返回失败码 0 而不抛 Python 异常，此时不会被识别为 cleanup failure；并非每次 Close 必然失败，也不是已有内存泄漏的动态证明。这应按 cleanup 事实补齐，不应倒过来删除幂等 Close，或在清理失败后静默新建模型继续 Main。

补 Close status 将是额外的 PyAMI 小改动及相应 pin 同步；它与既有三文件恢复方案在目标上独立。不能因为发现这个缺口，就把尚未修改的恢复方案报告成已经检查了 Close 成功。

## C. clocks wrapper：规范检查与异常策略分层

来源：[prefix helper][prefix]、[GetWave buffer／拼接／异常路径][getwave]。wrapper 是公共入口，影响 Tx、Rx、response probes、名义 Init/Tune helper 中实际触发的 probes，以及不采用 Rx clocks 的运行；不是只影响 D1。

| 子项 | 原 → 当前与影响 | 修订建议 |
|---|---|---|
| sentinel / prefix | 原拼接全部 buffer 后截断 → 当前只提取首个 −1 前的数据 | **保留明确修复。** 合同见 S2；不能为“相等”恢复 sentinel/padding 作为有效 tick |
| 合法无 clocks | 首槽 −1 → 空 prefix；尾部无须成为有效时钟 | **保留并贯通 fallback。** 不要求至少返回一个 tick；空结果不破坏此前有效 tick 的连续性记录 |
| 每 call NaN 预填 | 原 0 初始化后 buffer 跨 chunks 复用 → 当前每次 C call 前重填 NaN | **保留合理诊断，撤回先前默认回退建议。** 合规 prefix/sentinel 会覆盖被消费部分，后缀被忽略。此输出接口没有要求宿主提供上次 ticks 作为模型输入 |
| 未写／部分未写 buffer | NaN 留在 prefix 中或没有 sentinel 时失败；可发现原先可能读到的 0／旧内容 | **保留检测。** 未写不能自动解释为无 clocks，合法空结果已有明确表示。模型若依赖旧输出 buffer 内容，应单列其实际接口合同；不能把这种依赖假设成标准义务 |
| finite / raw 非负 | prefix 内 NaN、Inf、负 tick 被拒绝；sentinel 后的值不校验 | **保留。** 不静默过滤、排序、clip 或重造 tick。派生 Main-local 坐标可为负的问题另属坐标映射，不应用来放宽 raw epoch 数据校验 |
| 跨 C chunk 严格递增 | 每一 chunk 的首 tick 必须晚于此前最后有效 tick | **保留。** S2 支持，Python 包装分块不重启模拟 |
| 跨 Python GetWave 严格递增 | `_last_clock` 跨两 probes 与 Main 保留，成功 Init 才重置 | **保留，修正早期过度概括。** 正确时间原点需独立映射，不能通过删除检查、每 call 清零或重新 Init 来让不连续数据看起来有效 |
| 所有 caller 都检查 | 当前无“Tx／probe／不用 clocks 就跳过”分支；无效时整次 GetWave 不正常返回 | **默认不删除规范校验。** 所读公共接口条款不以 PyBERT 是否消费 clocks 为放行依据。可保留已返回 wave 作为部分证据，但不能自动把接口失败改成完整成功。若支持不同的、明确声明的模型合同，应单独界定，不能凭 caller 名称猜例外 |

### NaN 初值的具体影响边界

在模型完整写入本次有效 prefix 和 sentinel 的前提下，当前宿主返回的 clocks 只来自被覆盖后的 prefix；尾部 NaN 不参与结果，首项 −1 的合法空结果也能通过。因而**对这一合规输入域，没有代码证据表明 NaN 预填改变模型算法输出**。这是条件判断，不是所有现存 DLL 的数值证明。

它确实可能使曾经依赖旧内容、未写 sentinel 或漏填槽的模型暴露失败，但不能把“暴露接口失败”直接叫作应回退的数值回归。反过来，它也不证明 `bits_per_call + 8` 容量普遍足够；该容量来自基线，预填无法检测或修复 C 越界，真实模型容量边界仍 UNKNOWN。

### `_epoch_failed` 不能只分成保留／删除两种

当前并非所有 Python 异常都会设置它：波形准备等在部分 `try` 之外；会设置它的是 C 调用、raw capture、prefix 与参数取值这一段捕获的 `Exception`。同一个 flag 混合了不同原因：

| 原因 | 可以确定什么 | 建议 |
|---|---|---|
| C 函数失败码或原生调用异常 | 当前调用不具备成功执行合同；模型状态或消费进度不宜继续假定 | **保留停止当前 epoch 的保护。** 保存原件，不能重发同一 chunk 或自动 Init 后接着冒充同一次运行 |
| 非法 raw clocks | 时钟输出／连续性不符合采用的接口合同；wave 可能已被 C 修改 | **保留失败与停止策略，记录原因。** 不能用 `epoch_failed` 推导 wave 从未产生，也不能把已有 wave 提升为合格 timed 结果 |
| C 已成功，随后参数解码／辅助捕获失败 | 不足以证明模型内部状态失效；但它可能已经推进，重试会再次输入数据 | **最小缩窄错误分类和非必要诊断的耦合。** 若实际 wave、进度和必需输出已保存，辅助观察可 unavailable；若进度不可安全恢复，继续阻止续跑。不要仅删 flag，也不要将所有宿主异常称为 DLL 失败 |
| 进入 C 前的取消／宿主错误 | 不一定已有任何新样点被消费 | **按实际阶段记录。** 任务取消仍停止，不靠“epoch 失效”证明模型错误，也不自动重启模型 |

因此建议保留“不能安全续跑就停止”的保护，收窄的是**物理模型失效的断言，以及让可选诊断失败不必要地切断可用数据**。完整成功、部分 wave、无效 clocks 和未知进度要保持各自证据含义，不需要新建一套状态框架。

## D. RNG 和 C1：已决定的处理保持

| 项目 | 结论 |
|---|---|
| 可选 `get_responses(rng=...)` | **保留。** 省略时仍为基线的私有 entropy RNG，API 本身不强迫改变旧 caller 的输入 |
| `_probe_seed=self.seed` 自动策略 | **按用户决定取消。** 非零 seed 改变了原随机训练前缀策略；本轮没有实施 |
| C1 两实例／两 Init 的 probe/Main | **按用户决定恢复原单 handle 流程。** 不恢复曾经有错的参数解析、padding 或重复 Close；具体方案见既有文件 |

这三项互不等同。恢复生命周期不要求取消可选 API，也不要求取消 S2 支持的 clocks 校验。

## E. D1：保留正确采样部分，缩窄分析门槛

来源：PR #32 的 [plan][clock-plan]、[consume][clock-consume]、[Eye／period helper][clock-analysis]，以及 [Main BER/Viterbi][main-decisions]。本节不假定新的同 epoch 原点映射已交付；那仍按独立方案处理。

| 子项 | 原／现行为与数值影响 | 建议 |
|---|---|---|
| 旧 pairwise 缺陷 | 原 `pairwise((clock_times, clock_times[1:]))` 得到数组对，后续标量布尔判断有错误 | **保留最小修复，不恢复坏循环。** 旧故障分支不是已成功运行的数值 oracle |
| 半 UI、ceiling 选点、slicer 与 bypass | `edge + UI/2`、首个不早于目标的样点、`dfe.decide` 和绕过 native run_dfe 已在原意中存在；当前 searchsorted 在相应有效域实现同一选点 | **保留。** 不能再把这些统称为 D1 新算法；原循环缺陷与新分析合同仍分开 |
| 最后一个有效 tick | 当前不为取得 next period 而自动丢掉最后 tick；域内 target 可采样，未来 target defer | **保留。** 采样不必等待下一 tick，period 差分才需要相邻 tick；边界 tick 的来源完整性与原点映射要另核对，不 clip 到末样点 |
| 重复 grid index 拒绝 | 不同的严格递增 tick 仍可能被粗网格映到同一索引；当前拒绝这种分辨率 | **保留为明确支持边界，不能称为 raw clock 非法。** 不静默去重、合并 bits；本轮也不增加插值／重采样算法 |
| NRZ / PAM4 profile | NRZ 自动给软件 profile；PAM4 非空 clocks 要显式 profile，而当前 Main 未提供 | **暂维持明确的 timed 支持边界。** profile 不是 DLL 资格证据；PAM4 符号时间、门限、eye offset、编码与 Ignore_Bits 的解释不能凭 profile 字符串补齐。这不意味着所有 PAM4 或 clocks 关闭模式被禁止 |
| 必须真实 decisions，不再前补零 | timed BER 分支要求足量实际 bits；Native 原 padding 路径保持 | **保留不伪造样本。** 不足时 BER 不可得，不能以补零恢复“成功”。但已有 Main wave 与已产生的 decisions 仍应保留，不必被说成没有计算 |
| 最后 W decisions／BER-Viterbi 窗口 | 当前保存 producer indices，AMI Viterbi 从这些真实索引取样；Native 保留原 W+1 预测点规则 | **保留同一 producer 索引作为消费者依据。** 改 Ignore_Bits 或选窗会改变统计，需独立接受；Web 仍不支持 AMI+Viterbi，不由此新增资格 |
| Eye indices | 当前直接用采样索引，避免 seconds→index 再次量化；每条 trace 要覆盖完整 2 UI | **保留索引与单条 trace 完整性。** 当前索引是 trace start，不额外解释为中心。规定整个 Eye 至少 `W−2` 条并让不足牵连 Run，则属于可收窄的展示合同 |
| period 归属、NaN+mask | 当前将相邻 edge 差分保持在相邻实际 sample indices 区间；无依据的头尾未知，不填造值。与旧填充意图的时间归属不同 | **保留为明确标注的派生观察，不当作未变的物理估计。** mask/shape/unit 一致性必须保留；不恢复伪造的 period，也不把未知 period 自动等同 wave 无效 |
| histogram 权重 | 当前每个已知网格样点计一次，长区间权重更大；不是每 edge interval 计一次 | **保留现有明示权重，不能混称 edge-period 分布。** 旧 dense ui_ests 也可能按网格加权；不能只因是新 helper 就断言统计权重全部新造。更换权重本身须另行定义 |
| FFT 完整固定窗口 | 当前要求规定窗口内全为已知、均匀网格，再 FFT；不自行选一段“更好看”的窗口 | **保留计算前提；缺条件时 spectrum unavailable。** 已知 period histogram 或有效 decisions 不应因 FFT 无法成立而一起失效 |
| readiness 与 lock | 当前依 Ignore_Bits 做 readiness，保留模型返回／缺失标签；不再用经过若干 tick 直接构造锁定证明 | **保留区分。** status=1、时间足够、已处理 probes 都不能推导 lock；模型返回 history 被均匀 repeat 到网格只是宿主投影，不是模型返回了逐样点时间轴 |

这里有一个直接可定位的过强耦合：`consume_ami_clocks()` 已完成循环、取得真实 samples/decisions 后，仍将“至少 W decisions、至少规定数量 Eye traces、整个 FFT 内窗 known”三项并为 `full_analysis_eligible`；任一不满足便将 `consumption_status` 写成 partial，并抛 `insufficient_coverage`。[consume:128–159][clock-consume]

**建议最小缩窄：真实消费是否完成、BER 窗口是否成立、Eye 是否可展示、period FFT 是否可算应分别由各自的数据条件决定。** 保留所有不足与失败，不伪造完整；但不要因为缺一个可视化窗口就反推模型没完成 waveform 或采样循环。若用户请求的核心 BER 本身没有足够真实 decisions，仍需明确其不可得，不能将任务整体宣称数值合格。

此项不能只改 Web 层：原 gate 已在共享 Main 的 D1 helper 里，GUI 也受影响。时钟原点修复、Ignore_Bits 坐标变换和这些选窗是否放宽都可能改变最终 BER/分析集合；不能打包成一次“改显示”提交。

## F. D2：保留 reader，live 发布合同要与 D1 一起缩窄

来源：[live context][d2-live]、[period projection][period-projection]、[data 发布 gate][data-gate]、[stored validator][stored-validator]。

| 部分 | 建议与依赖 |
|---|---|
| producer freshness、实际 branch、raw copy、partial 保存 | **保留。** 请求开关不是执行证据，不能把 stale／partial producer 当完整结果；原始失败记录也不因建议变更而改成功 |
| 两个 timed Eye 必须全部 ready | **建议最小缩窄。** `collect.eye.dfe` 与 `analysis.eye.dfe` 的展示能力分别报告；不是任一 Eye unavailable 都等同 Main wave／有效 BER 失败 |
| 所有 period analysis 必须 available 才发布 | **建议最小缩窄。** `period_projection()` 本身已有分离的 histogram／spectrum availability，却在 collect 末尾又统一拒绝；不应让可选 spectrum 的前提变成所有结果的前提 |
| D1 与 live context 的联合 gate | **必须配套。** D1 先要求 full coverage，`clock_context()` 又要求 full_analysis_eligible；只删除 `data.py` 最后几个 raise 不能真正解除耦合。也不能把所有 status 人工改为 available |
| raw6 / clock_contract2 / `ami-clock-grid-v2` reader | **保留旧合同与 validator。** 现存档声明了 complete C1/D1 producer、实际 indices、mask 和最终窗口，读时仍须验证；不能为接受一种新不完整结果而放宽旧档解释 |
| 新来源或部分分析结果的保存 | **如将来接受，再显式表达新合同。** 不假写 `c1_fresh_main`，不降为 raw4 来绕过校验，不用旧 full 标识覆盖缺失。无需本轮设计新框架／编号，也不更改旧文件 bytes |

这不意味着所有异常都降为 warning。输入矛盾、数组错位、mask 欺骗、真正的执行失败或必需数值依赖缺失仍应阻止相关结果被当作有效；可选图不成立与这些情况不同。可以保留“Main 已完成，某分析不可用”的事实，不把它宣传为完整 qualification。

现有三文件恢复方案仍可独立先做：clocks 未请求／合法空 clocks 的实际 Native 分支不需要新的 D2 合同；恢复后非空且未映射的 clocks 明确停止消费、保留 partial。因此**这轮对 D2 的收窄建议不是恢复原初始化的前置条件**。

## G. PR #34 与非 AMI 的简短边界

- **PR #34 保留。** `0a7a036` 修复 Traits Dict 的 update 写法；只要现有 producer 状态字段还在写，就不应撤回。它没有改变采样公式，也不代表 D1 全部新合同都必要。
- **S8P/S12P through/FEXT 映射修复建议保留并独立标注。** `b87c80c` 修正送入原差分公式的物理端口组合；已有具体 oracle／外部模型证据，不能为了与旧错误结果相等而恢复错误接线，也不外推为全部硬件资格。
- **worker 隔离与输入冻结保留。** 它们控制作业间 NumPy 全局 RNG／可变对象影响；不要求同一 AMI helper 内把 probes 与 Main 分成不同模型。
- **显示投影、坐标与显示噪声保持来源可辨。** 图形点数、窗口或随机 realization 不同不自动是物理算法回归；额外观察不能宣称 GUI 已有 producer，也不借本轮重做全部显示。
- Native DFE/CDR/Viterbi、本体优化评分及 COM 不重新审查或执行；已有范围与 UNKNOWN 保留。

## 修订决策表

以下拆开原九行中混合的结论；“建议修改”仍只是本轮建议。

| 独立项目 | 修订结论 |
|---|---|
| Web 输入、资源绑定、worker 隔离、真实证据保存 | 保留 |
| tuple／无效字符串方法修复 | 保留 |
| 完整 path、缺失／非数值不造零 | 保留 |
| root／声明必需参数／语法检查 | 保留识别；按实际依赖决定哪些结果不能使用 |
| 全 numeric key set 作为 Main 硬门槛 | 最小缩窄，不能冒充类型与 Usage 验证 |
| 所有 tap 名叶节点必须等长 | 最小缩窄为同组矩阵要求；否则该观察 unavailable |
| Init/GetWave status、有效 Init guard | 保留 |
| Close 所有权、幂等、失败清理 | 保留 |
| Close 返回状态遗漏 | 建议补齐窄修复；不重试、不声称释放已证明 |
| 参数输出指针每 call 未清空 | 建议补齐窄接口修复，防旧值冒充本次返回 |
| sentinel 有效 prefix | 保留 |
| 合法空 clocks | 保留并维持真实 fallback |
| NaN 预填 | 保留合理诊断，撤回默认回退建议 |
| raw finite／非负、绝对时间、跨 call 严格递增 | 保留适用规范检查 |
| 因 Tx／probe／未消费而一概跳过 clocks 检查 | 不建议；没有这种普遍放行依据 |
| 所有捕获异常统一暗示模型状态坏了 | 缩窄错误分类；保留无法安全续跑时的保护 |
| 可选 RNG API | 保留 |
| 自动 seed 绑定 | 按用户决定取消，尚未实施 |
| C1 fresh Main | 按用户决定恢复原流程，尚未实施 |
| D1 标量迭代修复、原半 UI 选点、真实末 tick | 保留；依赖独立原点映射，不恢复坏循环 |
| D1 重复网格、未声明 PAM4 profile | 暂保留支持边界，不说成模型必错或已验证 |
| 实际 decisions、无伪造 padding、producer 索引 | 保留；不足的指标如实不可得 |
| period NaN+mask、明确的网格加权／窗口 | 保留有来源的观察，不当未变统计或模型 lock |
| D1 Eye/FFT 完整性阻断全部消费／Main | 建议最小缩窄，结果能力分开 |
| D2 全 Eye／period ready 才发布 | 建议与 D1 成组缩窄 |
| 历史 raw6 reader／validator／archive bytes | 保留不动 |
| PR #34 | 保留 |
| S8P/S12P 物理映射修复 | 建议保留为独立 native 修复 |

## 只需另外收束的三组决定

不为每个分支再提一个实施请求。能确定的保留项直接按上表建议；尚需决定何时实施的额外工作压缩为三组：

1. **窄接口与诊断修正。** 建议补 Close status、参数输出指针初始化；按 `.ami` 类型／真正消费者缩窄历史矩阵硬失败，并区分宿主诊断错误与 DLL 执行失败。与恢复原训练顺序独立；若修改 PyAMI，单独固定新对象，不整体重写 fork。
2. **独立 clock origin 与 timed 支持。** 继续以实际已处理 samples、ts 和同一 epoch 为映射证据，保留 raw clocks；不固定减常数、不再 Init、不取消绝对单调检查。保留 D1 的正确采样部分，NRZ/PAM4／分辨率边界在证据不足时明确 unsupported。真实模型验收仍暂缓。
3. **分析 availability 与发布合同。** 建议将 Main／真实采样、BER、Eye、histogram、spectrum 的条件分开；修改时 D1 producer、D2 live gates 与新结果保存含义必须一起处理。旧 raw6 validator 不放宽。这组不是三文件恢复的必要依赖，可在独立 timed 工作中再决定。

本轮没有给未执行的结果补 pass，也没有证明所有合规模型与当前 wrapper 逐值相等。确定的是源码与适用接口规则支持哪些保留、哪些失败域被宿主额外扩大，以及哪些窄缺口尚未补齐；具体 DLL 数值与适应行为仍 UNKNOWN。

<!-- Source references bind to fixed reviewed objects. -->
[params]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L85-L146
[params-consumer]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L452-L490
[parser]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/parser.py#L95-L143
[prefix]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L311-L324
[lifecycle]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L375-L460
[init]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L463-L535
[getwave]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L537-L626
[param-property]: https://github.com/yx520143-G/PyAMI/blob/d6d1f7fe7e58536546a1cfb9430c750cc2cb103e/src/pyibisami/ami/model.py#L809-L817
[old-lifecycle]: https://github.com/yx520143-G/PyAMI/blob/5270d713e40bac2be5747bef09b92df79df9085b/src/pyibisami/ami/model.py#L334-L395
[old-param-init]: https://github.com/yx520143-G/PyAMI/blob/5270d713e40bac2be5747bef09b92df79df9085b/src/pyibisami/ami/model.py#L405-L430
[old-getwave]: https://github.com/yx520143-G/PyAMI/blob/5270d713e40bac2be5747bef09b92df79df9085b/src/pyibisami/ami/model.py#L481-L528
[clock-plan]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/ami_clock.py#L18-L83
[clock-consume]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/ami_clock.py#L86-L159
[clock-analysis]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/utility/ami_clock.py#L163-L253
[main-decisions]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/models/bert.py#L633-L778
[d2-live]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/clocks.py#L42-L118
[period-projection]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/clocks.py#L144-L224
[data-gate]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/data.py#L426-L460
[stored-validator]: https://github.com/yx520143-G/PyBERT/blob/ab36b656a61cb6866da98105d72f6cacfb118031/src/pybert/web/clocks.py#L284-L368
