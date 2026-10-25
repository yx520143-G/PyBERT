# PyBERT WebUI 迁移最终修改清单

2026-10-25。状态：**方案已汇总，产品修改尚未实施。**

本清单合并前述审查及其修订结论：恢复原 AMI 初始化和自适应历程，保留明确的接口与计算缺陷修复；时钟原点、诊断失败及分析发布条件分别处理。真实 AMI 验收仍按用户决定暂缓。本清单不启动代码修改、数值实验、提交或发布。

## 1 恢复原行为

| 编号 | 最终修改项 | 目标行为与边界 |
|---|---|---|
| R1 | 撤销 C1 probe 后 fresh Main 的重新初始化 | **一个模型、一次 Init、原两次 response probe、同一 handle 继续 Main、最后统一 Close。** probe 与 Main 之间不 Close、不重新 Init、不构造第二个模型、不迁移隐藏状态。保留原 probe 的适应输入与调用顺序 |
| R2 | 取消自动把仿真 seed 绑定到 probe | 移除目标 caller 的 `_probe_seed=self.seed` 策略；不传新增 `rng=` 时继续使用原私有 entropy RNG。保留可选 RNG API，Main 原全局 seed 政策不改；不把 probe 改用全局 RNG |

目标调用顺序：

```text
构造一个 initializer 和模型
→ Init 一次
→ probe 1：GetWave(u)
→ probe 2：GetWave(convolve(u, channel)[:len(u)])
→ 同一 handle 上 Main：GetWave(x)
→ 取得宿主拥有的返回数据
→ finally Close
```

两次 probe 复用同一个生成的 `u`，第二次是它经过 channel 后的波形。保留原 `Ignore_Bits` 前缀、limited-run 序列、convolution、输入长度和分块；不补训练、不删训练，也不把训练后的状态装入一个新模型。Main 的 `bits_per_call=0` 沿用 probe 后的有效值 40，非零请求保持原覆盖规则。恢复的是初始化和适应历程，不承诺随机重复运行逐值相同。

**最小生产改动集仍为 3 个 PyBERT 文件：**

| 文件 | 必须调整的部分 |
|---|---|
| `src/pybert/utility/ibisami.py` | 使用现存单模型 legacy 主体，移除 C1 selector 和因此孤立的代码；把返回数据所有权保护及最终清理放在整个 probe→Main 生命周期末尾。原 initializer 准备函数可保留，不需要重新内联 |
| `src/pybert/models/bert.py` | 移除自动 `_probe_seed` 传入；停止将恢复后的流程标为 `c1_fresh_main`，记录实际来源；保存原始返回 clocks |
| `src/pybert/utility/ami_clock.py` | 区分观察 invocation 与模型 Init epoch；让合法空 clocks 走原 fallback，不被 fresh-origin 条件误拦；未完成原点映射的非空 clocks 明确不消费 |

这一步不要求先修改 PyAMI pin 或 D2/archive reader。只删除本次恢复产生的孤立代码，不做无关重构。显式未请求 AMI clocks 的既有分支继续运行；合法空 clocks 保留原 fallback；**请求非空 AMI clocks 时，在独立映射完成前明确 unsupported／partial，不能静默忽略请求。**

## 2 保留现有改动

| 编号 | 保留项 | 保留理由及限制 |
|---|---|---|
| K1 | Web 参数传递、资源绑定与身份、配置冻结、worker 隔离、取消、结果观察和归档 | 属于 GUI→Web 运行适配。作业之间的隔离不要求在同一 AMI helper 内把 probe 与 Main 拆成两个模型 |
| K2 | tuple/string 兼容、完整参数 path、缺失和非数值不造零 | 修复实际 parser 类型／字符串方法问题，避免同名叶节点混合和伪造历史；额外的统一 key/tap 矩阵限制另见 F3 |
| K3 | Init/GetWave 返回 status 检查、有效 Init guard | 显式执行失败不能当成功；status=1 不等于模型收敛、CDR lock 或 BER 合格 |
| K4 | handle 所有权、幂等 Close、Init 失败清理、原始错误与 cleanup 错误分别保存 | 保留明确生命周期修复；恢复流程把 Close 放到 Main 之后。调用返回不能单独证明资源已释放；Close 返回码缺口另见 F1 |
| K5 | sentinel 有效 prefix 提取和合法空 clocks | 不把 padding/sentinel 当有效 tick；首槽 −1 表示合法无 clocks，不强求每次都有 tick |
| K6 | 每次 C call 前 NaN 预填 clocks 输出缓冲区 | 保留合理的未写检测。合规有效 prefix 和 sentinel 会覆盖初值，尾部不参与结果；撤回早期仅凭“初值改变”就建议回退的判断 |
| K7 | raw clocks 有限、非负、同一模拟内绝对时间及跨调用严格递增检查 | 保留适用规范检查。不能在 Main 开始清空 `_last_clock`、重新 Init 或因 Tx/probe 不消费 clocks 就一概跳过；Main-local 派生坐标与 raw epoch 坐标分开 |
| K8 | 无法安全续跑时停止当前 epoch、不自动重试已消费 chunk | 保留保护及 partial 原件。宿主诊断异常与模型失败的分类、非必要耦合另见 F4 |
| K9 | 可选 `get_responses(rng=...)` API | 保留兼容的依赖注入入口；生产默认不再自动绑定 run seed，见 R2 |
| K10 | D1 标量循环修复、原半 UI／向上选点、真实末 tick、真实 decisions 与 producer indices | 不恢复旧数组 pairwise 缺陷；不丢掉可采样的末 tick，不用 padding 伪造实际 decisions。半 UI、`dfe.decide` 与绕过 native run_dfe 原本已有。使用仍依赖正确时钟原点 |
| K11 | 重复采样索引和未明确 PAM4 timed profile 的支持边界 | 不能悄悄去重、插值或猜门限。明确为分辨率／模式不支持，不宣称 raw clock 必错；不扩大为所有 PAM4 或 clocks 关闭模式都不可用 |
| K12 | period 的 NaN+mask、真实索引、明确的网格权重与固定分析窗口 | 保留有来源的派生观察，不伪造未知头尾；网格加权 histogram 不冒称逐 edge 分布，readiness 不冒称 lock。它们不证明统计语义与旧实现完全相同 |
| K13 | PR #34 Traits Dict 兼容写法 | 相关状态字段仍在写，撤回会重新造成入口失败；本身没有改变采样公式 |
| K14 | 旧 raw6／clock contract reader、validator、原始 NPZ、manifest 和失败证据 | 旧档按原合同解释，不降 schema、不重算覆盖、不重标历史失败。未来新来源或部分分析结果不能伪装成旧完整合同 |
| K15 | S8P/S12P through/FEXT 物理端口映射修复 | 保留有具体错误依据的独立 native 修复；正确接线可能改变下游数值，不为追求旧结果相等恢复错误接线 |
| K16 | 明确来源的显示投影、坐标、显示噪声及显式候选应用 | 保留原始结果与展示之间的区别；不宣称 GUI 像素完全一致，也不把显示噪声反馈为物理链路计算 |

K3、K5、K7 的接口依据见 [IBIS 6.1 §10.2.3，第 186–190 页](https://ibis.org/ver6.1/ver6_1.pdf#page=186)。本清单不将这些规则外推为所有 ABI 版本或实际模型均已验证。

## 3 单独修复和缩小限制

这些项目与 R1/R2 分开实施、分别验收。F1/F2 是**基线已有、当前仍未补齐的接口缺口**，不能记作迁移新增回归；目前没有真实 DLL 触发证据。

| 编号 | 单独处理项 | 最小目标 | 依赖与边界 |
|---|---|---|---|
| F1 | Close 返回状态未检查 | 保存 C `AMI_Close` 返回码，识别失败码与 Python 调用异常；不把“调用返回”当 cleanup 成功 | 保留先放弃所有权和幂等策略，不重试同一 handle。status=1 仍不等于物理释放已独立验证。修改 PyAMI 后同步必要版本固定 |
| F2 | 参数输出指针每次调用前未清空 | 按适用接口要求初始化 Init／每次 GetWave 的输出指针；区分本次 raw 返回、缺失和宿主标准化表示，防止旧值冒充新值 | 模型正确写入时不据此断言已有数值错误；不能用更严格 key set 代替正确调用边界。与 F1 可在同一窄依赖变更中处理 |
| F3 | 参数历史投影的硬失败过宽 | 根据实际声明及消费者，区分必需参数与辅助历史；只对真正同组 tap 矩阵要求列对齐。无法形成辅助图表时标 unavailable，保留 raw | 不是允许任意缺少必需 Out/InOut，也不删除 root／语法错误识别；缺失真正参与后续计算的数据仍阻止该计算。不 padding、截断或造零补历史 |
| F4 | 宿主辅助错误与模型执行失败混用 | 明确错误发生在 C 前、C 中还是成功返回后；能独立保留的有效数据与可选诊断分别报告 | 进度未知或无法安全续跑时继续停止；不删除 `_epoch_failed` 保护，不自动重发 chunk／重新 Init；不把辅助捕获失败一概说成 DLL 已坏 |
| F5 | 同一 epoch 下的 clock origin 映射 | 根据 Main 前实际成功处理的样本数和该 epoch 的 ts，建立绝对 ticks 到 Main-local grid 的映射；保留边界 ticks 与原始 clocks | 与恢复初始化分开。需要两个 probes 的真实调用账，当前仅最后一次 `last_getwave_calls` 不够；不固定减 4 ns／40 UI，不猜第一 tick 原点，不通过 reset 模型解决 |
| F6 | D1/D2 把所有分析完整性当作 Run 成功前提 | 分别报告 Main／真实采样、BER、Eye、histogram、spectrum 的可用性；某个可选图不可用不自动废弃不依赖它的有效数据 | 必须配套调整 D1 coverage、D2 live context 和发布 gate；不能只删除最后的 raise。必需指标不足仍不可得，旧 raw6 validator 不放宽，历史失败不改成功 |

F1/F2 的依据见 [IBIS 6.1 第 189–190 页](https://ibis.org/ver6.1/ver6_1.pdf#page=189)。F3/F4/F6 是缩小宿主附加限制，不是放行矛盾数据或把部分结果认定为完整资格。

## 4 时钟和分析的独立边界

对于固定采样间隔、同一 Init epoch 的成功调用，独立时钟修复采用：

```text
T_pre = Main 前实际成功处理的样本总数 × ts
目标 Main 时间 = raw_epoch_tick + symbol_UI/2 − T_pre
采样索引 = 第一个不早于目标 Main 时间的真实网格样点
```

实际样本账必须覆盖两次 probes 的 C chunks、短末块、阶段边界和同一 epoch 身份。不能用配置推算值代替已执行记录。最后一次 probe 返回的 tick 可能对应 Main 开头的采样点；派生 local edge 也可能为负、但加半 UI 后仍落在 Main 内。原始非负／单调检查应在 raw epoch 坐标中完成。

**坐标映射不改变模型的输入或适应状态，但错误或不同的采样选择会改变 BER。** 不自动将已经处理的 probe 训练折算为 Main 的 lock、readiness 或统计资格；调整 Ignore_Bits、最后 W decisions、Eye trace 数和 FFT 窗口须明确列出其数值影响。原点正确也不等于整个 timed 分析已经验收。

F6 应在新的来源和结果合同确定后接入。已有 raw6 声明完整 C1/D1 结果，继续严格读取；未来“Main 完成但某项分析不可用”的结果需要明确保存含义，不能冒用旧完整标识或降为 raw4 绕过检查。

## 5 实施顺序

以下是将来实施的顺序，不是本轮执行授权；每步只验证受影响的行为。

| 顺序 | 工作包 | 完成条件及对下一步的关系 |
|---|---|---|
| 0 | 固定实施基线和保存原件 | 固定 PyBERT/PyAMI 来源、现有归档和失败证据；不用整 PR revert 或依赖漂移版本实现恢复 |
| 1 | **R1＋R2 原流程恢复**，包含必要来源／空 clocks 接线 | 三个 PyBERT 文件形成同一逻辑变更；一次 Init、两 probes 后同 handle Main，原输入与分块不变，最终清理正确。未映射非空 clocks 仍明确不支持。此步可独立交付，不以 F1–F6 为前提 |
| 2 | **F1＋F2 窄接口补齐** | 单独修改 PyAMI 的 Close status／输出指针边界；核对返回值、异常和幂等清理。同步实际需要变化的 gitlink、direct URL 和 lock 来源，其他依赖不动 |
| 3 | **F3＋F4 参数诊断与错误分层** | 不让无关辅助历史阻断有效数据；必需参数与未知消费进度仍严格处理。只改实际依赖点，不创建通用事件／状态框架 |
| 4 | **F5 独立 clock origin** | 有实际样本账、epoch 与边界 tick 证据；raw clocks 不改写，转换与选点可核验。模型和 profile 条件未成立时继续 unsupported，不能仅凭合成样本开放真实资格 |
| 5 | **F6 timed 分析与发布条件** | D1、D2 live 和未来保存合同配套；各指标分别表达可用性，错误／partial 保留，旧 reader 不放宽。不得顺带改变未经列明的 BER／Eye／FFT 窗口 |
| 6 | 真实 AMI 对照及最终验收 | **继续暂缓，待用户恢复。** 此前的软件测试只证明相应宿主行为，不作为真实模型数值通过 |

顺序 2、3 与原流程恢复的目标独立，分别保留差异和验证结果。顺序 4、5 的来源、索引与保存合同相互关联，但与重新初始化无关。不得因后续时钟仍不支持而重新启用 C1。

## 6 验收清单

| 对象 | 有界成功标准 | 证据限制 |
|---|---|---|
| R1/R2 调用与输入 | 一个模型／initializer、C Init 一次；两个 probes 和 Main 同 handle；中途 C Close/Init 为零；成功末尾 C Close 一次。两 probes 复用原 u，尾块与原有效 B 保持，不自动注入 seed | Python GetWave 通常是三次，C GetWave 次数由 chunks 决定，不能混计。替身只能证明宿主编排 |
| 清理和接口 | Init／GetWave／Close 失败能区分；失败不自动重试；输出指针未写不会冒用上一返回；合法 prefix、空 clocks、未写槽与跨 call 连续性按合同处理 | status=1 不证明收敛或物理资源释放；测试替身不构成真实 ABI 资格 |
| 诊断与结果 | 辅助历史不可用时保留不依赖它的有效结果；必需数值依赖缺失时拒绝相关运算；不制造补零历史或虚假成功 | 不能将 malformed 接口输出自动降为无关 warning |
| 独立时钟映射 | 非零前置长度、短末块、跨 probe/Main tick、合法空 clocks、末尾 deferred 与坐标阈值均可核对；不依赖固定偏移 | 合成数学样本只证明映射实现；真实模型 origin 仍需实际记录 |
| D1/D2 与归档 | Main、decision、BER、Eye、histogram、spectrum 状态相互一致；旧 raw6 原件仍按原 validator 读取；新结果不伪装成旧完整合同 | 不重标任何历史失败，不把部分可用扩大为完整资格 |
| 真实数值恢复 | 恢复验收后，以独立表达的原单 handle 调用顺序作参考，使用同一固定 PyAMI／已保留修复及同一份实际训练输入，对照 h/out_h、wave、raw clocks、params | **目前不执行。** 不共享待测 helper，不以 C1 作原参考；DLL 内部状态或随机性不可比时不宣称 exact。夹具固定输入不改变产品 entropy 默认 |

## 7 不纳入本轮修改的事项

Native DFE/CDR/Viterbi 本体、既有优化评分、COM 算法和默认大搜索不变，不为这份清单重跑全矩阵。已有 GUI 对象 seed 缓存／操作历史差异维持原审查限制，不附带修复。模型 ABI 容量、真实 NRZ/PAM4 AMI 资格和硬件资格不由本清单补齐；真实 AMI 暂缓状态不解除。旧工作原件、失败和成本记录保留，不启动清理、备份私有化或定时监控。

## 8 来源和结论优先级

本清单采用最新复审结论，供未来实施使用；较早报告的原件保留。尤其不再沿用“NaN 预填或跨调用单调应默认回退”的旧建议。C1 恢复、取消自动 probe seed 绑定始终包含在修改范围中，尚未实施。

- [原算法审查](README.md)：固定源码差异与作用域。
- [迁移范围建议](migration-scope-recommendations.md)：早期拆分及依赖背景，修订处以上述最终决定为准。
- [原初始化流程最小恢复方案](restore-original-ami-flow-plan.md)：三文件范围、原调用输入与独立时钟方案。
- [其余改动复审](remaining-changes-review.md)：规范依据、修订保留项、两个历史接口缺口与分析限制。

固定对比为 PyBERT `1bc905d577d2f3bd9471421cfbf3d422d4e6080e` 到 `ab36b656a61cb6866da98105d72f6cacfb118031`；PyAMI `5270d713e40bac2be5747bef09b92df79df9085b` 到 `d6d1f7fe7e58536546a1cfb9430c750cc2cb103e`。实施前如来源变化，应先核对差异，不能把这份固定版本清单直接当成新版本已完成审查。

