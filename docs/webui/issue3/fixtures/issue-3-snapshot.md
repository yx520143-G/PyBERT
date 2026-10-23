Source: https://github.com/yx520143-G/PyBERT/issues/3 · updated 2026-10-23T20:02:51Z

## 状态、目标与依赖

**计划评审中，尚未实施。** 仅在 `yx520143-G/PyBERT` Fork 工作。只有本会话协调者明确记录 `PLAN_CLOSED` 后，由唯一 **Astra xhigh PM** 派发 **6.1 sol xhigh owner** 串行实施；本票继续 OPEN，未完成验收不勾选。PM 管理队列、依赖、风险和交付，owner 负责实现；是否 fresh plan/final review 由 PM 按风险决定，不给每个小步骤加审批。owner 与 PM 在开工、实质里程碑、阻塞及交付时沟通，长任务期间定期更新；本次计划更新不启动 owner。

父任务 #1；技术前置是 #2 已交付的真实 Native Run、冻结输入、不可变 run 结果、原始数组和最小图表。串行队列位于 #2 之后、#4 之前；不等待文件通道、优化或 AMI。#2 已有的 Responses、Outputs、Rx 输入/DFE 眼图与 DFE Jitter 必须继续可用，本票不能再次退回参数说明或图表占位。

产品使用 PR #7 的信号链基础：固定原型 `8542f10f4c137f79b3200638f5ee59d36202526a`，原生语义基线 `1bc905d577d2f3bd9471421cfbf3d422d4e6080e`。实施基线继承 #2 已记录的 PR #7 合并或集成来源，不能从不含原型及其四项修复的 master 重新起步。PR #6 的真实截图/交互记录保留为历史功能和语义证据；不要求七页签位置或固定四格。桌面 Chrome 1280×720；不做窄屏。

**本票用户可见结果：** 用户能在同次 run 内沿接收链检查全部既有响应、眼图、jitter、bathtub 和 CDR 统计，并通过真正独立的 Rx FFE 观察点区分 CTLE、FFE、DFE 的效果。

## 范围与不含项

包含：

- 补齐 Channel 三种频响及各节点单级/累计/DFE 最终权重等效响应的选择与比较；四种响应类型延续 #2。
- Channel-only、Rx 输入、CTLE、DFE 四个原生观察点的全部 Eyes、Jitter Dist./Spec./Info、Bathtubs。
- `ffe_out` 的独立眼图和新增 jitter 分析；沿用原 helper，明确这是新观察点，不假称原生已有 `jitter_ffe` 或同名旧 GUI 图。
- CDR clock-period histogram/spectrum；保留已有 UI estimate 和 DFE adaptation。
- 同次 run 多观察点比较、已有两次成功 run 的所选图表比较、轴/窗口/单位/来源说明。
- 有效性和不可用原因，以及必要的最小分析上下文暴露。

不含：

- 任意连线图编辑器、前端重写物理算法、MATLAB/IEEE COM correlation 或标准资格认证。
- 文件通道/封装/COM、真实 AMI、自动优化、Viterbi 的专项实施；它们按 #1 队列推进。
- 完整磁盘 run archive 与 legacy results 导入导出（#5）；本票仍使用 #2 的不可变 run 数据存储。
- 独立 Native Tx 引脚波形、AGC 时间趋势、独立 TIE 轨迹 UI、垂直 bathtub/额外 BER margin 算法；保留可扩展数据身份，不以这些非原 GUI 能力阻塞本票。

## GUI 功能落点与观察点

节点设置保持可见，右侧选择 Responses / Waveform & Eye / Jitter / Adaptation；全链路比较入口共享同一观察点目录。原 GUI 反查仅作辅助导航。没有数据时显示状态与原因，不显示假曲线。

| 原 GUI 功能 | 新落点 | 本票输出 |
| --- | --- | --- |
| Responses / Impulses、Steps、Pulses、Frequency | Channel、Tx EQ、CTLE、Rx FFE、DFE 节点；全链路比较 | 延续四类型；补齐 Channel raw/terminated/trimmed 曲线、单级/累计/等效选择与来源 |
| Results / Outputs | 对应实际观察点 | 延续原始波形，尤其保留独立 `ffe_out`；节点 input/output 使用真实字段 |
| Results / Eyes | Channel-only、Rx input、CTLE、Rx FFE、DFE | 四原生观察点＋新增 Rx FFE；窗口/时钟/显示噪声可见 |
| Results / DFE / Adaptation | DFE 节点 | 延续逐 tap 权重与索引语义 |
| Results / DFE / CDR Adaptation、Clock Period Histogram、Clock Period Spectrum | CDR 控制支路 | 补齐周期分布和频谱，不能把 CDR 画成串行滤波器 |
| Jitter / Dist. | 每个有效观察点 Jitter / Distribution | Total 与 Data-independent PDF |
| Jitter / Spec. | 每个有效观察点 Jitter / Spectrum | Total、Data-independent、Pj threshold |
| Jitter / Info | 节点摘要＋全链路区段比较 | ISI/DCD/Pj/Rj、dual-Dirac 参考、原生 rejection 表；新增 FFE 区段单独标识 |
| Results / Bathtubs | 节点 Jitter / Bathtub | 原 helper 生成的 crossing-jitter bathtub，非完整电压/BER 资格证明 |

| 观察点 ID（Web 稳定身份） | 原始波形 | 原生字段后缀 | 类型与有效条件 |
| --- | --- | --- | --- |
| `channel_only` | `chnl_out` | `chnl` | 仅 Channel 的诊断对照，不是真实 Tx EQ 后输出 |
| `rx_input` | `rx_in` | `tx` | Native Tx＋Channel＋显式噪声后的实际 Rx 输入；旧 `eye_tx`/`jitter_tx` 的真实来源 |
| `ctle_output` | `ctle_out` | `ctle` | Native CTLE 输出；旁路时仍保留旁路状态和相同波形 |
| `rx_ffe_output` | `ffe_out` | 原生不存在独立 eye/jitter 套件 | 新增观察分析；Native 下有效，不能复制 CTLE 图改名 |
| `dfe_output` | `dfe_out` | `dfe` | 实际求和节点输出；不同于最终权重等效 FIR 响应或判决 bit 流 |

上述来源见 [原生 jitter 四点调用](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L833-L1022)、[Rx FFE 原始响应与波形](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L476-L497)。

## 数据契约：producer、轴、单位和类型

所有 dataset 带 `run_id`、input hash、engine SHA、schema/producer 版本、observation ID、原始字段、dtype/shape、轴引用、单位、有效窗口、availability 和 reason。原始数组不可被显示截窗/降采样覆盖。每个观察点保存自己的 bin/frequency/TIE 轴及成功状态；不能仅因旧 GUI 共用轴就假定它们总是相同。

### 响应与过程统计

- Channel：`chnl_h/s/p`；`chnl_H_raw`、`chnl_H`、`chnl_trimmed_H`。Tx：`tx_*` 与 `tx_out_*`。CTLE：`ctle_*` 与 `ctle_out_*`。RxFFE：`ffe_*` 与 `ffe_out_*`。DFE：`dfe_*` 与 `dfe_out_*`。`*` 为 h/s/p/H；DFE 后两组始终标“最终权重等效”。
- 保存 `t_ns_chnl`、`start_ix` 和响应采样原点；不可将所有响应默认为 `t[:N]` 或从零生成的索引。响应 impulse 使用原生离散 V/sample 约定及归一化元数据；step/pulse 为 V。
- H 原始为复数线性系数，频轴来自原生 `f`（Hz）；显示 GHz、`20*safe_log10(abs(H))`，DC 不进入 log-x。不得读取已转 dB 的同名 plotdata 当原始 H。
- `ui_ests` 实例已经为 ps；其时间轴来自 `t`（s→ns）。Clock histogram 沿用 100-bin histogram，返回 bin edges/centers（ps）和 counts；使用完整原始 `ui_ests`。
- Clock spectrum 保留现有 `rfft(ui_ests)`、去 DC、相对 fundamental 的 `safe_log10` 比值，频轴为 `f_clock*ui`（相对符号率）。原 GUI 的 `dB norm.` 标签与当前无 10/20 系数的 producer 不一致；Web 明示 legacy log10 约定，不擅自乘 10/20。若归一化分母为零或结果非有限，显示 unavailable/原因，不加未声明 epsilon。
- `adaptation` 的 x 是权重记录索引（含初始项），不是 waveform 时间或仅实际更新次数。`dfe_scalar_values` 没有逐样本时间轴，本票不据此生成 AGC 时间曲线。

证据：[Channel 响应轴](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/pybert.py#L1554-L1600)、[DFE 等效响应](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L644-L654)、[过程图 producer](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L1155-L1192)。

### Jitter 与 Bathtub

`S` 表示 `chnl/tx/ctle/dfe`。新增 Rx FFE 使用相同 typed result 结构，但 origin 明确为 Web adapter 对既有 helper 的新增调用。

| 数据 | 现有 producer / 字段 | 原始单位及显示 |
| --- | --- | --- |
| Total PDF | `calc_jitter` → `jitter_S` | bin centers s、PDF `/s`；显示 ps、`/ps` |
| Data-independent PDF | `jitter_ext_S` | 同上；`ext` 不是 tail extrapolation curve |
| Total / independent spectrum | `jitter_spectrum_S` / `jitter_ind_spectrum_S` | TIE FFT 幅值；原频轴 Hz；显示 MHz，`10*(safe_log10(raw)-safe_log10(ui))` dBui |
| Pj threshold | `thresh_S` | 原算法生成；和该点频谱用同一轴/单位变换 |
| ISI/DCD/Pj/Rj | `isi_S/dcd_S/pj_S/rj_S` | s→ps；前三者 pp，Rj 为标准差 |
| Dual-Dirac reference | `pjDD_S/rjDD_S/mu_pos_S/mu_neg_S` | s→ps；独立参考拟合及有效性 |
| TIE 与时间轴（保留数据） | `tie_S/tie_ind_S` 与对应 `t_jitter` | s；本票不要求新增 TIE UI，但不能丢轴或借其他点的轴 |
| Bathtub | `make_bathtub(bins, jitter_S, min_val=0.1*MIN_BATHTUB_VAL, rj=rj_S, mu_r=dj_pos_S, mu_l=dj_neg_S, extrap=True)` | 原始 probability；x s→ps；log10 仅显示层；保存 floor、参数、实际外推条件 |

不使用前端公式替代 native helper。`MIN_BATHTUB_VAL` 当前为 `1e-12`，实际传入 floor 参数为 `1e-13`；版本变更需记录来源而非前端写死。Dual-Dirac 拟合值不是原生 bathtub 的构造参数。见 [jitter 返回含义](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/utility/jitter.py#L212-L273)、[显示换算与 bathtub](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L1263-L1314)。

Jitter Info 保留原来的输入来源：Tx 的 Pj/Rj rejection 为 n/a；TOTAL 的 ISI/DCD 从 Channel-only 对照开始，Pj/Rj 从 Rx input 开始；旧“DFE rejection”实际为 `ctle_output→dfe_output`，包括 Rx FFE。Web 用真实区段名，并在新增 FFE 分析成功后另给 `ctle→ffe`、`ffe→dfe` 对比，明确是新观察能力。原生零分母 sentinel 不作为有效抑制值；保存 raw 值并显示不可计算原因。[原表输入来源](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/pybert.py#L776-L836)

### Eye 矩阵与窗口

1. 使用同 run 的 `ui/nspui/nui/eye_uis`；`ignore_samps=(nui-eye_uis)*nspui`、`ignore_until=(nui-eye_uis)*ui`，切取末段真实 waveform。PAM4 的 `eye_uis` 由原模型产生，不把 bit 数误当 UI 数。
2. 复用 `calc_eye`，height=1000、width=`2*nspui`，color=count。保存生成时 `y_max`、实际像素→V 映射（含 y_scale/y_offset）、x/extent、sample window、source waveform 和 helper version；不能只保存热图图片。
3. Channel-only、Rx input、CTLE、Rx FFE 采用原 helper 的无显式 clock 路径（从 waveform crossing 对齐并按 nominal UI fold）。Rx FFE 不默认借用 DFE recovered clocks。
4. DFE 使用窗口内原生 `clock_times` 减 `ignore_until`；不足时沿用原有 nominal fallback，并记录 clock source/fallback reason。无有效 waveform/crossing/scale 时显示 unavailable，不生成假零眼图。
5. Channel 默认用干净 `chnl_out`。另提供明确标“GUI-compatible display noise：σ=1mV”的兼容显示；给该 run 单独冻结 display-noise realization/seed 并缓存，不污染原生物理噪声 RNG、raw waveform 或数值指标。两种眼图分别验收，不能比较不同随机噪声实现后要求逐像素相等。
6. 原 GUI 后续 `update_eyes()` 使用的轴/height 与矩阵 producer 存在差异，CTLE 还复用 DFE ys。Web 使用生成时数据元信息；这是显示契约修正，不改 `calc_eye` 物理/计数算法。

证据：[原眼图生成](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L1316-L1343)、[calc_eye](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/utility/sigproc.py#L395-L446)、[旧 GUI 坐标更新](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L1446-L1491)。

## Rx FFE 新分析的最小上下文暴露

#2「为新增观察点保全的局部上下文」是交接前置；本票核查并消费这份不可变上下文，不要求 #2 提前交付新增眼图/jitter。以下区分已保存字段与最小捕获/重建：

- `t`、真实源序列采样 `x`（Duo-binary 时不能由 `ideal_signal` 直接冒充）、`ideal_signal`、UI、nspui、nui、eye_uis。
- `pattern_len=(2**max(pattern)-1)*2`、`rel_thresh`、原主流程使用的 modulation enum 和局部 `decision_scaler`；后者是 jitter 调用使用的输入参考，不能换成 AGC 写回后的值。
- `ideal_xings`、windowed ideal crossings、`xing_min_t`、PAM4 symmetric-transition mask；保留生成参数及来源。
- 每观察点的互相关 offset、actual/windowed crossings、返回 bin centers/spectrum frequencies/TIE timestamps、成功或失败原因。

`self.ideal_xings`、各点部分结果及 `ofst_chnl` 已保存；其他 offset、CTLE/DFE 独立轴、局部输入等按 #2 从 producer 捕获，不能假称原实例原本全部提供。`xing_min_t` 由冻结窗口公式重建；若 #2 未保存 actual/windowed crossings，本票对同一 raw waveform/参考上下文直接调用既有 `find_crossings` 与窗口函数重建并记录 provenance，不以这一额外诊断要求倒逼 #2 增加图表范围。

对 `ffe_out` 使用原 `find_crossings`；offset 采用与既有点相同的 `(argmax(correlate(ffe_out,x))-(len(x)-1))*Ts` 对齐规则；依照原 window/mask 调 `calc_jitter`。返回完整 typed result 后，eye/bathtub/display 不再重跑主仿真。现有四点的计算值与调用次序保持兼容；新增分析不能改变 bits、noise 或原四点结果。新增派生项的预期不可用/分析失败以该 dataset 的状态及原因进入本次冻结 manifest，完成后统一原子发布；不得边算边向已成功发布的 run 追加半成品或修改旧 run。旧 schema 的成功结果缺少新分析时显示版本/数据不可用，切图不隐式发起新分析任务。若主引擎原有 jitter 阶段直接失败、任务异常退出或未形成有效 terminal envelope，则遵守 #2 的 failed run/保留旧成功结果规则。

## 输入、资源与运行约束

本票执行域为 #2 已支持的 Native NRZ/PAM4，使用同一完整有效输入及固定非零 seed/noise；不新增外部文件资源要求。任何配置启用未支持的 AMI/文件模型/优化/Viterbi 时，保留草稿并明确不支持运行，不能清字段、改模式或回退默认值后声称成功。

草稿、requested/effective input、run 原始数据、派生图和显示投影分开；所有图绑定选定成功 run。编辑草稿后提示旧结果；切图/缩放/比较不触发 Run。当前两次成功 run 的保留/释放遵守 #2；没有完整磁盘存档不妨碍本票比较。

继承 #2 每任务独立 spawn 子进程且同一时刻最多一个活动引擎 worker 的模型；主仿真合作取消使用同一共享 Event 与原生阶段检查，新增派生分析在观察点或图组边界检查请求，不另起第二个分析 worker。不承诺中断 `calc_jitter`/SciPy 单次调用。收到请求进入 #2 的 `cancel_requested`；只有可确认 callback/任务观察到取消，且父进程确认任务结束、子进程 join/退出后才 `cancelled` 并释放槽位。自然完成早于观察到取消时按 #2 记成功及晚到请求；不能仅凭 Event 已置位或任意 RuntimeError 记取消。失败/取消保留上一成功结果，不仅凭原生 Ready 字符串或无异常就标成功。

## 冻结 fixture、窗口与容差：计算前完成

本票不声称已有结果通过。实施开始引用 #2 已冻结的 `F-NRZ-01`、`F-PAM4-01` 完整 fixture 和 manifest；记录 SHA/hash、非零 seed/noise、模式、完整 taps、依赖版本。两者均为 10 Gb/s、seed=1、nspui=32、nbits=15000、eye_bits=10160；NRZ 的 nui/eye_uis/ignore_samps 为 15000/10160/154880，PAM4 为 7500/5080/77440。其余输入以 #2 完整 fixture 为唯一来源，不在本票重建另一套隐含默认；记录 `ignore_until=(nui-eye_uis)*ui`、实际 t/axis 范围及 crossing 有效 mask。若需新 fixture，先写完整有效输入、窗口和容差再计算；不可看结果后换 seed、缩窗口或放宽误差。

有界新增检查只包括：

- 对两份基准 run 新增 Rx FFE helper 分析；分别比较 adapter 与对同一完整数组/上下文直接调用既有 helper 的结果。
- 一个 Native identity-FFE 控制：以 NRZ fixture 为基底，冻结 `rx_n_taps=1`、`rx_n_pre=0`、实际 index0 tap=1 且其余禁用，其他输入保持。若 #2 现有 fixture 已覆盖此配置，复用而不重跑额外矩阵。验证 FFE 波形/派生分析与 CTLE 对应点在同一上下文下相符。
- 少量函数级无 crossing、窗口不足、clock fallback、非有限值/zero normalization 检查。不得写成浏览器实测或扩为重型速率/随机矩阵。

完整继承 #2 共同冻结规范，不对同类原始或显示数据放宽容差；以下明列本票比较及新增类型。共同规范后续若调整，本票须同步且在计算前版本化，不事后放宽：

| 比较项 | 门槛 |
| --- | --- |
| dataset identity、shape、units、window、clock mode、availability、离散 mask/indices | 精确一致 |
| 原始 waveform/response 与 complex real/imag | `rtol=1e-10`；V/系数绝对容差 `1e-12`，沿用 #2 更严格已冻结值时不得放宽 |
| crossing/TIE/bin/timestamp/jitter 时间标量 | `rtol=1e-10, atol=1e-18 s`；ps 字段按单位换算 |
| 频轴 | 校验生成来源和长度；沿 #2 `rtol=1e-12, atol=1e-6 Hz`；原始 `f_clock` 先按该门槛验收，再对相对符号率轴 `f_clock*ui` 使用 `rtol=1e-12, atol=(1e-6 Hz)*UI` |
| PDF（原始 `/s`） | `rtol=1e-10, atol=1e-12/UI`；记录原始单位最大误差；固定 UI 仅作量纲尺度，不使用显示数组 |
| Jitter raw spectrum/threshold | `rtol=1e-10, atol=1e-18 s` |
| Eye counts、histogram counts | 同输入/窗口/clock/y mapping/display-noise realization 时精确一致 |
| Bathtub probability | 有效正值 `rtol=1e-8, atol=0`；零值、floor 命中和不可用状态分别精确核对；禁止大绝对容差吞掉低概率尾部 |
| 显示变换 | 原始比较通过后另查单位变换、DC 排除、log/clip/mask；沿 #2 finite 显示量 `rtol=1e-10, atol=1e-10`（显示单位），不得用显示近似替代原始验收 |

对于原生返回 NaN/Inf、拟合失败或样本不足，比较有效性与明确原因，不将其填零或通过删点使测试通过。记录每项 max abs/rel error 与失败位置；性能、耗时和日志时间戳不作逐值数值一致要求。

## 实施步骤

1. 接收 #2 的 schema、run manifest、fixtures 和观察点目录；核查本票上下文是否齐备，在增加计算前冻结缺项暴露与容差 manifest。
2. 建立原四点与新增 RxFFE 的 typed analysis builder，复用原 helper；保留原始值和 per-point 轴/metadata，隔离 display transforms。
3. 接入四点 Eyes/Jitter/Bathtubs、RxFFE 新观察、Channel 三频响及 CDR 统计；先完成通用 viewer 再拓展观察点，不复制五套算法。
4. 增加全链路与两次 run 的对比，保持同 run/同点/同窗来源可见；不兼容轴禁止按 index 强行叠加。
5. 完成上述有界原始/helper 一致性与失败状态检查；再做真实 Chrome 1280×720 验收，分别保存数值报告和 UI 证据。
6. owner 向 PM 交付改动范围、原生边界、原始报告、UI 证据及剩余阻塞；PM 审核后推进下一串行票。GUI/CLI/MCP 受影响入口按风险做有限回归，不扩成无界测试矩阵。

## 可核查验收（全部待完成）

- [ ] 四种 Responses、Channel 三频响和单级/累计/DFE 等效标签准确，原始 `ffe_*`/`ffe_out_*` 未因旧 GUI 无图位丢失。
- [ ] 四原生观察点 Eyes、Dist./Spec./Info、Bathtubs 均接真实 producer；图表、菜单反查与节点跳转可用。
- [ ] Rx FFE 眼图/jitter 使用独立观察点、原始 `ffe_out` 和冻结上下文；直接 helper 对照及 identity 控制通过并留证。
- [ ] 原生四点 raw jitter/轴、CDR 原始值、DFE adaptation 与基准一致；无二次单位换算或把 PDF 当计数/把 spectrum 当 PSD。
- [ ] Eye 矩阵和轴/窗口/clock metadata 配对；Channel 1mV 显示噪声单独标记并缓存；clean 与兼容视图各自对照通过。
- [ ] Jitter Info 区段命名与实际输入输出一致；dual-Dirac 参考与 bathtub 生成参数分开；PAM4 crossing 限制可见。
- [ ] 同次 run/跨 run 比较不重跑、不混数据，编辑后旧结果标识准确；失败/取消及新增分析失败状态符合本票规则。
- [ ] 真实桌面 Chrome 1280×720 完成选择/缩放/对比/不可用状态验收；不把历史 PR #7 Chrome 草稿证据当作本票完成证据。
- [ ] 原始数值报告与显示投影报告分开，fixtures/窗口/容差在计算前冻结；未改原生物理算法，GUI/CLI/MCP 兼容。

## 原生边界与不确定性

- PAM4 jitter 主要是 0V crossing，相关统计有 symmetric-transition mask；不代表三眼完整 BER。缺 crossing 的 TIE 有边缘占位处理，不能当成每点都实测有效 transition。
- 原生 short-window jitter、拟合、clock coverage 可失败；保留失败原因，不为 UI 漂亮而改变窗口或统计算法。
- `jitter_ext_*` 不是外推尾部；DD 拟合不构造当前 bathtub；原生 rejection sentinel、CDR log 标度与旧 eye 显示轴问题不隐藏。
- `update_plots=False` 不产生原有全部 eye/bathtub 数据；允许薄数据 builder，但不以全库剥离 Traits/Chaco 为前提。
- 本票证明的是输入/数据适配与原 helper 一致，不证明独立物理准确性、MATLAB COM correlation 或 IEEE 资格。

