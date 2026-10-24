## 当前实施进度（2026-10-24 PM更新）

- **#2 已验收关闭**：[PR #11](https://github.com/yx520143-G/PyBERT/pull/11)交付 `c3958b1`，代码 `f67f07d`；PM固定终审通过，owner停止写入并返还ownership。前置PR #7先merge为`69f3d3063f0b6de326b01925f74a31264e0db6f7`，#11再merge为`35a3b60351836431e4f96136b61708515ec5f77c`。master树与验收交付完全一致，两来源祖先均确认。[固定验收记录](https://github.com/yx520143-G/PyBERT/pull/11#pullrequestreview-5634825596)。
- **#3 已验收关闭**：[PR #12](https://github.com/yx520143-G/PyBERT/pull/12)交付`1a6378f2`、产品`83b75154`，普通merge为`9a33d08458aa00782e90169c699857b8b19455a2`；master与交付tree相同。两项metadata P2闭环；保留非阻断P3及所有原始/失败证据。owner停止写入和服务并返还ownership。[固定终审](https://github.com/yx520143-G/PyBERT/pull/12#pullrequestreview-5635369402)。
- **#4 代码已集成、默认COM gate继续OPEN**：[PR #15](https://github.com/yx520143-G/PyBERT/pull/15)固定交付`50570116`，普通merge `f1d0ea80f9db8ab31e25963496875a44fe4a19d9`；master tree与交付一致。[固定终审](https://github.com/yx520143-G/PyBERT/pull/15#pullrequestreview-5636373094)关闭COM历史P2，增量Standards 0/Spec 0，保留原非阻断P3；PM468项增量核验通过。owner已停止写入/服务返权；本票无活动writer，52份raw等原件保留。
- **#13 原生端口修复已验收合并，返回 #4**：[PR #14](https://github.com/yx520143-G/PyBERT/pull/14)固定交付`92c31740`，普通merge为`e29f87c177ac89fabdec2d5a34d8e6ea7e7cce7c`；master与验收tree一致。[终审](https://github.com/yx520143-G/PyBERT/pull/14#pullrequestreview-5635615740) Standards 0 / Spec 0，49项相关回归通过。同一owner已正常集成回#4 WIP（`c89cbd7`），追加corrected-native v2 `a8144879…`；PM104项材料核验通过，#13完成关闭。四个M及另外5个新资源case现已完成direct/worker数值对照，PM核验原始报告/输入/源码/资源与退出状态；真实原xls独立COM已核验direct/worker均−15.4199841033 dB、差0；TIME保留Tab解析原生阻塞。默认COM139756144外层组合继续`BLOCKED_BUDGET / NOT_EXECUTED`；#4不关闭，不缩参数或以XLS替代。
- **#5 已验收关闭**：[PR #17](https://github.com/yx520143-G/PyBERT/pull/17)固定交付`6cb8b8b7`、产品`fb97265b`，普通merge为`5fcf8285b042fe1fe92c068b1c3311fa87a50de0`；master tree与交付`c06164a0b87c4577073477c71a9ec05aee5125ee`相同。[固定终审](https://github.com/yx520143-G/PyBERT/pull/17#pullrequestreview-5636772734) Standards 0 / Spec 0，所有阻断finding闭环。2053 archive数组精确往返、879新Run raw一致性、112字段迁移、历史COM快照和实际Chrome证据已核验；最后91项PM核验通过。owner停写/停服返权，旧失败/raw/费用保留；本票验收不关闭默认COM或后续专项。
- **#8 已验收关闭**：[PR #18](https://github.com/yx520143-G/PyBERT/pull/18)固定交付`837d4f6a`、生产修复`e55819a`，普通merge为`3807bd2f54647a491f350cbda7ab61c0752b06f0`，master tree与交付`61089b8058acaf08ee2c9b9c643959ded5e21a54`一致。[固定终审](https://github.com/yx520143-G/PyBERT/pull/18#pullrequestreview-5637061905) Standards0/Spec0，两P2闭环；37定向契约、211原件与34封存检查通过。保留252优化数组/434数组RLM Run对照、23coopt/3Main/0数值COM、errors0/0/7及全部失败/成本。原owner已停写停服返权，无第二writer。
- **依预算处置v2继续 #9 → #10。** 已派发#9唯一owner：chat `01a16c77-9624-79a2-9d55-75e715f6e2fd`（local，gpt-6.1-sol/xhigh），从上述3807bd2建立独立worktree，开工ACK与实际路径待核验；暂无#9计算或验收。#4默认数值gate仍归PM/#4，不开full sweep、不改参数或用FOM/Viterbi替代；#16仍开发后补验，父票保持OPEN。
- **开发后新增补验 #16，尚未执行**：[外部S8P/S12P修复前后与下游回归](https://github.com/yx520143-G/PyBERT/issues/16)排在#5→#8→#9→#10开发交付之后，由main统筹并反馈。寻找有端口依据的外部8/12-port文件，优先硬件实测；模型与实测分列，缺口保留。固定fix前9a33d084/fix后92c31740及最终集成版本，独立差分参考核对完整复数lane/FEXT，并做必要下游回归。当前开发不受打断，不新增并行writer；本项未完成时不宣称父票总体验收完成。
- PM仍为Astra/xhigh chat `01a16a69-8a11-71a0-8620-5d157b897926`；30分钟heartbeat随当前owner推进，正常推进静默。
- 保留#2/#3/#4/#5/#13工作区中的ignored raw及原失败/过早截图；主工作区仍为b9c56fe及原docs/research、source未跟踪内容。原生GUI既有异常等范围限制延续，不能把有界接入验收外推为标准/硬件资格。

## 状态、授权与执行边界

- 状态：**PLAN_CLOSED / 实施中：#2/#3/#5/#8已验收，#4代码已集成但默认COM gate仍OPEN，#9已派发，父issue保持OPEN**。协调者已独立复核 #1–#5、#8–#10 的实际正文及关键源码；此状态不表示产品实现或数值验收完成。
- “计划 close”仅指规格、依赖、范围和验收的评审闭环。**本会话协调者现已明确 `PLAN_CLOSED`，开发启动门槛已满足**：按用户最新授权，由唯一 **Astra / xhigh PM** 派发 **6.1 sol / xhigh issue owner**，从 #2 开始串行实施。旧“#2 无限期暂停”已被本次授权替代。
- 单活动开发 owner；PM 负责队列、集成、风险和阻塞协调，不重复替 owner 实现。是否采用 fresh plan/final review 由 PM 按风险决定，不对每个小步骤增加审批。owner 在开工、关键契约/阻塞、验证完成和交付时汇报，长任务至少每 30 分钟一次实质更新；PM 回应阻塞并维护交接。
- 只在 `yx520143-G/PyBERT` Fork 工作；保留原生算法及 GUI/CLI/MCP 兼容。默认本机 `127.0.0.1`、桌面 Chrome 1280×720，不考虑窄屏、云部署、多用户或任意连线编辑器。
- 原生语义基线：`1bc905d577d2f3bd9471421cfbf3d422d4e6080e`；信号链原型来源：PR #7 `8542f10f4c137f79b3200638f5ee59d36202526a`。PR #6 是已完成的历史功能/语义证据，不再规定新 WebUI 的七页签位置。历史 Chrome 草稿测试不等于本票运行验收。
- 未完成 checkbox 不勾选；本票的任何 `passed` 必须链接本票实际提交、输入/资源 manifest 和验证结果。

## 协调者计划评审闭环记录

**结论：PLAN_CLOSED。记录时间：2026-10-23 20:17:22 UTC。** 用户在 2026-10-24（Asia/Shanghai）授权“6-Pro 更新 issues → 协调者 review 闭环 → Astra xhigh PM → 6.1 sol xhigh owner 串行开发”。协调者已逐票读取实际 GitHub 正文，核对功能矩阵、首期真实 Responses/Results/Jitter、PR #7 集成前置、数据/输入/资源/取消契约、阶段依赖和计算前冻结的验收程序；当前未发现阻断实施的计划冲突。

评审中已与 Pro 闭环的修订包括：旧总票目标与子票同步、当前任务日志与旧成功结果 ID 分离、CTLE File 按实际调用分支判断 inactive/blocked、Viterbi 未计算状态不覆盖 DFE 实际误码。关键调用点已独立对照固定源码核查。评审采纳的 Pro 发布版本：#1: 2026-10-23T20:15:02Z；#2: 2026-10-23T20:14:54Z；#3: 2026-10-23T20:02:51Z；#4: 2026-10-23T20:14:56Z；#5: 2026-10-23T20:02:55Z；#8: 2026-10-23T20:11:04Z；#9: 2026-10-23T20:14:58Z；#10: 2026-10-23T20:15:00Z。

计划闭环发布时，本记录满足全部实施票中“等待协调者明确 PLAN_CLOSED”的条件；子票原有 PLAN_REVIEW 文字是发布时的条件状态，以本记录为当前统一调度依据。#1 和所有开发 tickets 继续 OPEN，产品验收 checkbox 均未完成；原生缺陷、真实资源/AMI 模型与后续数值/Chrome 验收仍按各票实际结果处理。唯一队列为 **#2 → #3 → #4 → #5 → #8 → #9 → #10**。PM 管调度和交接，唯一 owner 完成当前票后返还 ownership，再推进下一票。

## 产品目标与本次需求替换

以 PR #7 的信号链交互为基础进行 PyBERT 二次开发：用户能理解参数参与哪一处理环节，修改后真实 Run，并查看各级 Responses / Results / Jitter、比较和保存。**首个实施阶段就必须同时交付真实 Run 和这三类分析能力。**

本正文替代旧 #1–#5 的布局/分期要求：不再要求七页签作为主导航、按原控件相对位置复制、固定四格或先做几轮纯设置框架。Jitter 从 #2 起提供真实展示，#3 补齐；独立 Rx FFE 的真实波形/响应在 #2，独立眼图/jitter 在 #3 验证接入。原 GUI 反查是辅助入口，不重新决定主布局。

迁移对象是**功能、输入/执行语义、观察与分析能力**。16 模块、129 个 GUI 命名 Item 与 5 类 tap 表是原型的控件映射起点，不是仿真/分析功能完成证明。未支持的功能保留明确落点、原因、交付票和状态，不能静默缩水。

## 已有证据与实施版本

| 证据/版本 | 用途 | 不能据此声称 |
| --- | --- | --- |
| 原生语义 SHA `1bc905d577d2f3bd9471421cfbf3d422d4e6080e` | 计算、字段、单位、GUI 条件和 producer 依据；实际实施 SHA 必须另记并复核差异 | 不表示任意输入/速率/模型都已数值验收 |
| 已合并 PR #6；base `457f444b0a6e705532579d4242596d60c9dfa153` | [baseline](https://github.com/yx520143-G/PyBERT/blob/457f444b0a6e705532579d4242596d60c9dfa153/docs/webui/baseline/baseline.md)、[control audit](https://github.com/yx520143-G/PyBERT/blob/457f444b0a6e705532579d4242596d60c9dfa153/docs/webui/baseline/control-audit.md)、[interactions](https://github.com/yx520143-G/PyBERT/blob/457f444b0a6e705532579d4242596d60c9dfa153/docs/webui/baseline/interactions.md) 及真实桌面截图是已完成的历史证据 | 其中原“本期/延期”和旧布局安排已由本正文替代；事后 AGC 状态/历史截图不等于本轮冻结输入 |
| PR #7，已普通merge为69f3d306；原head `8542f10f4c137f79b3200638f5ee59d36202526a` | [README](https://github.com/yx520143-G/PyBERT/blob/8542f10f4c137f79b3200638f5ee59d36202526a/docs/research/pybert-signal-chain-ui/README.md)、catalog/settings/gui-map/app 与信号链研究文档；包含四项复核修复 | 当前仍是参数草稿与说明，没有仿真后端和真实结果 |
| [8542f10 历史验证](https://github.com/yx520143-G/PyBERT/blob/8542f10f4c137f79b3200638f5ee59d36202526a/docs/research/pybert-signal-chain-ui/review-20261024/README.md) | 处理器回归及 1280×720 的索引、模式切换、草稿恢复/存储等已有证据 | 不代表真实文件选择、原生配置/模型加载、Run/响应/eye/jitter/数值验收已通过 |

**PR #7 集成前置（#2 必须执行）：** PLAN_CLOSED 后开工先记录实际 PR 状态。若仍未合并，从固定完整 head `8542f10f4c137f79b3200638f5ee59d36202526a` 接续原型及全部修复，未来实现基线不能只取旧 master；PM 管理叠加实现和最终集成顺序。若已普通合并，核对祖先；若 squash/rebase，核对全部文件及修复/测试的内容等价。若 head 变化，先记录差异后再冻结新基线。不重复 cherry-pick、不擅自遗漏修复。本轮不合并 #7、不创建实现分支。

## 桌面信息结构与用户路径

桌面 Chrome 1280×720。保留 PR #7 信号链节点/搜索基础，页面使用以下区域；不实现任意拖线/拓扑编辑器。

| 区域 | 内容与关系 |
| --- | --- |
| 顶栏 | 当前配置/dirty 状态、Run/Abort、任务阶段、所选成功 run、加载/保存/帮助 |
| 信号链导航 | Source、Tx EQ、Channel、Rx CTLE、Rx FFE、DFE/Slicer；AMI 为相应处理路径的替代，实际模式明确 |
| 注入与控制支路 | Noise/FEXT 是加法注入；Tx/Rx 端接与封装属于 Channel 电气边界；CDR/AGC 是采样/判决控制，不画作串行滤波级 |
| 节点工作区 | 左侧参数/条件/单位与未支持原因；右侧该级响应、输入/输出、眼图、jitter。切节点保留分析类型与所选 run |
| 全链路比较与 Run 概览 | 汇总观察点、输入/资源差异、两次结果、BER/性能/警告；Observe 是跨节点分析入口，不是主链末端的硬件 |
| 工具与日志 | Native/AMI 优化、COM、可选 Viterbi 分支各有独立任务/能力状态；日志/帮助/原 GUI 反查为辅助入口 |

典型路径：修改节点参数 → flush 表格/数字编辑 → 校验完整输入/资源并冻结 → Run → 同一 run 下看单级/累计响应、真实输出/eye/jitter → 选择旧成功 run 比较 → 保存当前配置或明确所选 run 的完整结果。失败/取消仍可查看旧成功结果，但不能把它标作新任务结果；编辑后显示旧结果所属输入。

## 全功能迁移矩阵（计划范围，不是已实现清单）

阶段：S1=#2；S2=#3；S3=#4；S4=#5；O=#8；V=#9；A=#10。每行交付后链接实际实现与验收证据；阶段进度见上方当前实施记录，未明确验收的阶段继续待完成。

### 设置、处理与工具

| 原 GUI 功能 | 信号链落点/功能身份 | 阶段与边界 |
| --- | --- | --- |
| Simulation：Rate/Modulation/Pattern/Seed/Nbits/nspui | Source + Simulation/Analysis 全局网格 | S1 NRZ/PAM4；S3 Duo-binary；完整输入/有效窗口明确 |
| EyeBits/Pj Threshold/fMax/fStep/Impulse length | 分析网格及 Channel/响应设置 | S1 采样/分析条件，自动 impulse length；S3 核对手动长度原生限制 |
| Tx Level/Noise：Vod/Rn/Pn/f(Pn) | Source 电平与 Noise 注入支路 | S1；电压噪声与时间 jitter 不混称 |
| Channel Native 损耗、Tx/Rx R/C、电气选择 | Channel 及两端电气分组 | S1 Native；S3 文件/封装，A IBIS；Rx_Cac 保留兼容但说明原生未消费 |
| Single/Multiple、renumber/window、lane/FEXT、文件顺序 | Channel 资源与 Noise/FEXT 注入 | S3；真实资源/端口/有序网络与 hash，原生实际启用条件 |
| Package group/cases/partial-host | Channel 封装电气区 | S3；不与 lumped/on-die 路径重复叠加 |
| Native Tx taps（实际 6 非主 tap） | Tx EQ 设置 | S1；与 Tx 搜索表分离，cursor 使用原生规则 |
| CTLE Enable/Native/File/fp/BW/boost | CTLE 节点 | S1 解析模式；S3 实际消费 File 时明确 native blocker；disabled 是否旁路以 Native/Init Tx 或 Tx GetWave 的真实分支判定 |
| Rx FFE Ntaps/Npre/100 槽位、actual tap enable/value | Rx FFE 节点 | S1；保留 observer 重排、真实构造后默认和全部槽位，不只改显示标签 |
| DFE Gain/Nave/Level/AGC、sum model/BW | DFE/Slicer + AGC 控制 | S1；输入 Level 与最终 AGC/DFE 状态分离 |
| Optimizer/Rx DFE enabled/min/max/Enable All/Disable All | DFE/Slicer 基本配置 | S1 普通 Run 已必需；连续前缀和实际有效 tap 数清楚；优化 value 为只读结果 |
| CDR Type/Delta/Alpha/Lock 控件 | CDR 控制支路 | S1；Bang-Bang 与原生固定 MM 锁定点语义，不宣传 MM 捕获动态 |
| Native Tx/CTLE/RxFFE 搜索表、Use MMSE/RLM | 各 EQ 节点优化约束与全局优化工作区 | O；RLM 首期禁用并说明仅 MMSE 使用，不改变普通 PAM4 符号 |
| Tune/Abort/Use/Reset、候选响应/评分 | 独立优化任务区 | O；候选与真实 Run 分开，显式 Use 才改草稿，Reset 按原 handler 语义 |
| Use Viterbi/Depth、解码分支 | DFE/Slicer 下游可选分析 | V；API-only FEC native blocker 明确，不冒充 GUI 支持 |
| Tx/Rx IBIS Select/View/TS4、模型路径/Valid | 两端电气与模型资源区 | A；Valid 只读真实解析/加载，Native 电气与 AMI EQ 开关分离 |
| AMI Configure/Init/GetWave/Use clocks | 相应 Tx/Rx 替代路径及 CDR | A；动态参数与实际能力/时钟来源，缺资源/模型能力明确拒绝或原生可见回退 |
| AMI 参数优化表/trial budget/TPE/候选应用 | 优化工具 + 模型参数身份 | A，复用 O 任务契约；无 Init response 的 GetWave-only 搜索不支持 |
| Compute COM/COM Config | 独立 COM 工具，按需绑定 Run | S3；真实单 .s4p + 独立配置，不自动继承普通 Run 的 EQ/noise/FEXT 设定 |

### Responses / Results / Jitter（不能由一个说明性 Observe 节点替代）

| 原 GUI 功能 | 落点与真实数据范围 | 阶段 |
| --- | --- | --- |
| Responses / Impulses | 节点响应：Channel、Tx、CTLE、Rx FFE、DFE；单级/累计及 DFE 等效标识 | S1 |
| Responses / Steps | 同节点 step response；保留单级/累计区别 | S1 |
| Responses / Pulses | 同节点 pulse response；tx_out 为 Tx+Channel，DFE 为最终权重等效 | S1 |
| Responses / Frequency | 原复数 H/各自 f → 显示幅频；Channel raw/perfect-term、actual-term、trimmed 三种来源 | S1 基本各级，S2 补齐 Channel 三种并列 |
| Results / DFE：DFE Adaptation | DFE 节点，adaptation 各 tap 随记录序号 | S1 |
| Results / DFE：CDR Adaptation | CDR 节点，ui_ests 与真实记录时间 | S1 |
| Results / DFE：Clock Period histogram | CDR 节点统计，由原 producer、窗口/单位生成 | S2 |
| Results / DFE：Clock Period spectrum | CDR 节点频谱，保留原 log10 比值语义，非擅改 dB | S2 |
| Results / Outputs：Channel / +Tx / +CTLE / +DFE | Channel-only 对照 chnl_out、实际 Native Rx input rx_in、ctle_out、dfe_out；增加 ffe_out | S1，独立 Rx FFE 波形不延期 |
| Results / Eyes：原四观察点 | 对应节点眼图；实际输入/window/clock basis/display noise 元数据 | S1 Rx input/DFE，S2 Channel-only/CTLE |
| 新 Rx FFE eye | Rx FFE 节点；原 calc_eye + 独立分析上下文验证 | S2；不把 CTLE 或 DFE 图改名 |
| Results / Bathtubs：原四点 | 节点 jitter/bathtub 与全链路比较；原 make_bathtub/真实分解参数 | S2；crossing-jitter 估计，非完整电压/BER 资格结论 |
| Results / Viterbi：trellis/path/top-3 probability | Viterbi 分支结果 | V；原 decoder/producer，非前端新概率算法 |
| Results / Viterbi：Position/Error/of | 分支视窗与错误定位 | V；bit 与 symbol index/PAM4 对齐明确，切窗不 Run |
| Jitter / Dist.：total / data-independent PDF | 各点真实 PDF/bins/统计来源，jitter_ext 不是尾部外推；dual-Dirac 参考属于 Info | S1 DFE；S2 原四点全覆盖 |
| Jitter / Spec.：total/independent/threshold | 各点真实 spectrum/频率轴/TIE 窗口 | S1 DFE；S2 原四点全覆盖 |
| Jitter / Info：ISI/DCD/PJ/RJ、DD 估计/拒斥比 | Run 概览与节点 jitter 信息，原 producer/分母/单位可见 | S1 DFE 摘要；S2 完整原生语义，含 CTLE→DFE 指标实际含 RxFFE |
| 新 Rx FFE jitter 与对应 bathtub | Rx FFE 节点独立 observer；复用原 crossing/jitter/bathtub helpers | S2；与 identity-FFE/原上下文有界核对，失败显式不可用 |
| 原状态栏 BitErrs/Jitter/ChnlDly/TxPwr/COM | 所选 run 概览及子工具结果 | S1 Native基础；S3 COM；V 两路错误；不把未计算 -1/-999 显示为有效值 |

### 菜单、文件、Info 与草稿动作

| 原菜单/动作 | 新落点与语义 | 阶段 |
| --- | --- | --- |
| File / Load Config. | 配置工具栏；解析/校验后原子替换草稿 | S1 Native YAML，S3 完整支持域/历史格式；A 模型扩展 |
| File / Save Config. | 当前有效草稿，沿用逻辑名/无名转 Save As | S1；S3 完整资源/不可表示字段说明 |
| File / Save Config. As... | 新名下载，取消不改名/草稿 | S1；不承诺浏览器覆盖原路径 |
| File / Load Results | 结果工具栏，载入参考不重跑/不替换草稿 | S4，legacy 子集与完整 Web archive 分开 |
| File / Save Results | 保存所选 run 的输入/原始数据/分析元数据 | S4；S1 已有临时两 run 缓存不是持久存档 |
| View / Clear Loaded Waveforms | 比较区清除加载参考 | S4，不删除当前成功 run/源文件 |
| Simulation / Run | 顶栏，flush→validate→freeze→唯一 worker | S1 |
| Simulation / Abort | 顶栏/任务状态，合作取消/实际结束 | S1，不承诺 DFE/AMI 即时停止 |
| Optimization / Tune EQ | 优化工作区，独立 opt ID | O；A 扩展 AMI |
| Optimization / Abort | 优化任务状态，真实检查点 | O；A 保留库调用边界 |
| Optimization / Use EQ | 显式应用候选 patch，旧 run 标 stale | O；A 动态参数候选 |
| Optimization / Reset EQ | 当前实际 Native EQ 同步到搜索初值/enable | O；不是恢复全应用默认值 |
| View / Debug Mode | 日志/调试设置，共用字段 | S1，运行日志绑定任务 |
| File / Quit | 断开 Web 会话/提示可关闭标签 | S1；不关闭 Chrome，不隐式取消后端任务 |
| Help / Getting Started | Web 操作说明与原帮助链接 | S1 |
| Help / About | 实际版本/SHA/原署名及 fork 身份 | S1 |
| Info / Performance | run 概览按原组件数据，单位 Msmpls/min | S1，缺数据 unavailable，不拿耗时做严格物理一致 |
| Info / User's Guide | 帮助区 | S1，布局可变但功能保留 |
| Info / Console | 任务日志抽屉，只读 Web 适配 | S1，原 GUI 可编辑不要求 Web 编辑日志 |
| statusbar | 当前任务状态和所选成功 run 摘要分离 | S1，Ready/正常 return 不单独证明成功 |
| 原型搜索/GUI 反查/恢复默认/撤销/localStorage | 辅助索引和草稿工具 | S1 保留修复，S4 版本迁移/故障恢复；不计为分析已实现 |

原始功能清单依据：[view.py 图表/Info/菜单](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/view.py#L919-L1068)、[plot.py](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/plot.py)、[handler.py](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/handler.py)。矩阵之外若发现真实 GUI 功能，必须登记交付票或具体 native blocker，不能仅因不在129 Item索引而忽略。

## 每票共用的输入与结果规则

1. 建立稳定 field ID/功能 ID，关联固定源码位置、GUI 反查路径、信号链位置、单位、构造后默认、编辑/只读、GUI 编辑条件、实际计算条件、提交时机、PyBertCfg/扩展持久化和测试证据。参数 ID、视图标题与数组 ID 分开；catalog 的说明不充当数值 schema。
2. 状态分两轴：实现状态（待实施/已接入/未验证/原生阻塞）与当前配置状态（active/inactive/bypass/unavailable及原因）。尚未接入不等于当前未启用；有效条件失败不能 silently fallback 或忽略字段。
3. 草稿与规范化输入、每次 frozen input、run/opt/COM ID、原始结果、显示投影分离。每个数据集包含 producer/point/类型/轴/单位/有效窗口/clock basis/显示噪声/可用性。AGC/DFE/AMI 输出不覆盖用户输入。
4. 真实主链、诊断和等效结果明确区分：chnl_out 是 Channel-only；Native rx_in 才是 Rx 输入；保留 ffe_out；DFE 最终权重等效响应不是非线性 DFE 的完整传函。AMI 各分支再按实际输入/噪声/时钟标记，不沿用 Native 名称误导。
5. 原 eye/jitter/bathtub helpers 在服务端复用；CTLE/DFE 缺失的逐点轴与局部上下文只做最小收集，不造公式。新 RxFFE helper 分析单独验证 decision_scaler、真实 x、PAM4 mask、crossing/window/offset/clock basis，不能“相似图”改名。
6. 眼图计数/电压网格/时钟及 Channel 显示附加噪声单列；原始数值不含显示降采样、dB floor、色标或临时渲染噪声。crossing-jitter bathtub 不宣称完整 PAM4 电压裕量/BER 认证。
7. #2 先定义完整 Native NRZ/PAM4、有非零 seed/noise 的 fixture，以及逐数据类型容差与有效窗口。**首次计算前**物化完整 YAML/扩展/资源/版本 manifest 并冻结 hash；各专项在计算前扩展自己的 bounded fixture，不能看完差异后更换 seed/窗口或调宽容差。历史截图不是数值基准。
8. Run 需 preflight + producer postconditions；原函数提前 return、status Ready、无异常、部分图可见不能单独判成功。失败/取消保留旧成功数据并清楚标所属输入；不把取消请求当任务结束。
9. API/原始 schema 有版本；不支持的有效输入明确 reject，原始数组与显示转换分别验收。保留原 GUI/CLI/MCP；不借 UI 接入修物理算法，不将接入一致性写成 MATLAB COM correlation 或标准认证。

关键 producer：[原运行/预检](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L84-L153)、[响应/FFE/DFE](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L429-L654)、[jitter](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L792-L1022)、[eye/bathtub/trellis](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L1297-L1443)。配置/MCP复用：[PyBertCfg](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/configuration.py)、[MCP](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/mcp/server.py)。

## 技术栈、进程模型与取消最低合同

沿用 PR #7 的 JavaScript 信号链；增加清晰分离的输入状态、API client、结果注册表和图表 renderer。薄 FastAPI/Uvicorn 本机服务 + 本地 Plotly 资源；Web 依赖保持可选。没有必须先迁移 React/TypeScript/Vite 或完全剥离 Traits/Chaco 的前置。

服务进程管理请求/状态/不可变结果索引；每个原生计算任务用跨平台 spawn 子进程和全新 PyBERT 上下文，**最多一个活动引擎 worker**。包含 Run/优化/COM、加载模型及需 observer 的校验；浏览器可继续编辑轻量草稿，忙时原生校验 pending。不在 HTTP 进程共享活 PyBERT，也不经 GUI handler 另起并行数值线程。现有 MCP 的规范化/调用 helpers 可复用，但同步 MCP handler 不是现成的 job/cancel/runID 服务。

任务状态经带 ID 的 IPC 上报；取消通过实际被原检查点读取的共享 Event。只有确认请求被观察且任务真实结束/子进程已 join 或退出才标 cancelled并释放槽位；晚到请求可能对应已自然完成的成功。普通异常不一律算取消；进程异常退出无完整终态判 failed。DFE 内环、优化内层、COM和AMI库调用无即时打断保证。具体桥接与 postcondition 以 #2 和各专项为准。

COM 可作为 core Run 后关联的独立子任务，复用同一串行槽位；请求自动 COM 与实际 deferred 策略均记录，core 图表与 COM 子结果分开保存，失败不伪造 margin。未来 AMI 优化同样使用私有 candidate；原 coopt 自动写回不能污染用户草稿。

## 交付队列与真实依赖

| 顺序/优先级 | Issue | 用户可见结果 | 技术前置 |
| --- | --- | --- | --- |
| 1 / 最高 | #2 — Run + Responses/Results/Jitter | Native NRZ/PAM4 真跑、全部响应类型、5个输出点、Rx input/DFE眼图、DFE jitter、两run最小比较 | 本票规格冻结与 PR #7 集成核对 |
| 2 / 高 | #3 — 完整观察与 RxFFE 分析 | 原四点图/完整jitter/bathtub、CDR统计、独立 RxFFE eye/jitter | #2 |
| 3 / 高 | #4 — 真实通道资源/完整配置/COM | 文件/多段/lane/FEXT/封装、完整 Native 语义和独立 COM | #2；排在 #3 后 |
| 4 / 高 | #5 — 存档/比较/核心验收 | 完整 run archive、原生结果子集、核心端到端证据 | #2、#3、#4 |
| 5 / 专项 | #8 — Native EQ | MMSE/非MMSE候选、Use/Reset/Abort、RLM边界 | #2、#3；文件通道另依赖 #4 |
| 6 / 专项 | #9 — Viterbi | ISI/MLSD trellis、概率、Position/Error及两路误码 | #2、#3；Duo-binary语义依 #4，不技术依赖优化 |
| 7 / 专项 | #10 — IBIS-AMI | 真实模型资源/Configure/Init/GetWave/观察/搜索及保存 | #2、#3、#4、#8；结果格式接 #5，不技术依赖 Viterbi |

**唯一串行开发队列：#2 → #3 → #4 → #5 → #8 → #9 → #10；开发交付后由main统筹新增补验#16。** 技术依赖和排队先后分开；不因某专项缺厂商模型就把缺证据项勾选完成。PM 在 blocker 发生时维护明确记录与重排理由，始终只有一个活动开发 owner。

## 实施组织、计划关闭与验收

本会话协调者独立 review GitHub 实际正文；发现规格/依赖/验收冲突在计划内修正，直到其明确说 **PLAN_CLOSED**。在该事件之前所有票为 PLAN_REVIEW，不启动 PM/开发 owner；本轮只写计划。PLAN_CLOSED 后 PM 在授权范围派发指定 6.1 sol xhigh owner，按风险安排 fresh plan/final review，不给常规步骤再设审批。owner 在开工、关键契约/阻塞、验证完成和交付时与 PM 沟通；长任务至少每30分钟实质更新，报告变更、证据、风险与下一步。PM负责队列、资源、集成和协调，不重复实现。

**PLAN_CLOSED 检查项只涉及可执行规格：**

- [x] 本票和所有实施票的范围/排期/技术依赖无冲突，PR #7 集成来源明确；旧暂停授权由本门槛替代。
- [x] 完整功能矩阵覆盖参数、图表、菜单、文件和动作，所有能力均有交付票或真实不可用原因。
- [x] 每票有数据/单位/有效条件、输入/资源/取消/失败协议、实施步骤和可核查验收；fixture/window/tolerance 的计算前冻结程序具体。
- [x] 协调者对实际 GitHub 正文复核后明确 PLAN_CLOSED；该事件不等于开发完成，不关闭这些实施 issues。

**产品交付完成定义（各票验收合起来）：**

- [ ] 首阶段已用真实引擎交付三类分析和 Native 端到端路径，各后续票独立验收自己的增量，不把所有问题留给 #5。
- [ ] Responses/Results/Jitter 与完整功能矩阵逐项有真实证据；#5 不提前宣布尚未完成的优化/Viterbi/AMI已覆盖。
- [ ] 所有 raw/axis/window/unit/availability 与直接原生调用按冻结容差核对；显示变换单独验收，NRZ/PAM4是有界案例，不外推所有速率/模型。
- [ ] 真实桌面 Chrome 1280×720 具备完整路径、条件提示、运行/失败/取消/旧结果状态及保存恢复；未实测项目仍未完成。
- [ ] 原生缺陷/未知平台/模型资源缺口有证据与责任归属；不改算法取得表面一致，不宣称 COM correlation/标准资格认证。

- [ ] 完成新增[#16](https://github.com/yx520143-G/PyBERT/issues/16)开发后补验：外部S8P/S12P来源/端口依据/原件hash、fix前后与最终集成版本、全部适用lane/FEXT的独立复数参考及必要下游回归可追溯；实测/仿真和剩余缺口明确，不能用构造样例冒充外部覆盖。

## 风险与保留的不可用边界

短窗口/BER分析、CTLE File/手动 impulse length、Rx_Cac 未消费、原 eye 显示轴/随机噪声、legacy结果缺轴、优化哨兵/硬编码噪声、FEC分支、AMI噪声/时钟/模型平台限制按对应票处理。可以增加预检、只读数据暴露和准确状态，不能用前端近似或默认回退掩盖。真正需要修算法时由PM分离范围/复现与后续协调；受影响验收仍未完成，开发issue继续OPEN。本轮未运行新仿真、未复做浏览器QA，也未将任何实施checkbox标成完成。


