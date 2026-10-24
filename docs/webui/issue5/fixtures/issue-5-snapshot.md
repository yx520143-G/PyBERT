## PM 派发准备与实际依赖（2026-10-24）

#1已PLAN_CLOSED。#2/#3已验收关闭；#4经PR #15已集成资源/完整配置/不可变结果及真实XLS COM代码，基线master为 `f1d0ea80f9db8ab31e25963496875a44fe4a19d9`。#4原owner已停写返权，PM现按已记录预算处置v2正式重排进入本票，随后仍为#8→#9→#10，单活动开发owner。

**#4继续OPEN：原默认COM为BLOCKED_BUDGET/NOT_EXECUTED。** 本票使用已验证代码契约开展archive/比较，不依赖该默认full-sweep标量；不删除/勾选其矩阵行、不启动默认搜索、不换参数。本票“核心验收”不能意味着#4默认gate或父#1总验收完成，TIME/CTLE File/impulse_length等原生边界继续可见。

优先复用#2/#3/#4已有版本与hash的真实raw进行精确存档往返；新主计算只为本票确需的跨功能行为，在输入/资源/窗口/容差事先冻结后执行。结果读取/查看不跑引擎，archive数组dtype/shape/原始字节必须exact；legacy缺轴不得借当前run轴。未完成checkbox全部保留。

## 状态、授权与执行边界

- 状态：**PLAN_CLOSED / PM正在派发，issue 保持 OPEN**。尚未完成本票实现或数值验收；当前调度以顶部为准。
- “计划 close”仅指规格、依赖、范围和验收的评审闭环；只有**本会话协调者明确 `PLAN_CLOSED`**后，唯一 **Astra / xhigh PM** 才可派发 **6.1 sol / xhigh issue owner** 串行实施。该门槛已由父票的PLAN_CLOSED满足；本票依顶部实际依赖和PM调度实施。
- 单活动开发 owner；PM 负责队列、集成、风险和阻塞协调，不重复替 owner 实现。是否采用 fresh plan/final review 由 PM 按风险决定，不对每个小步骤增加审批。owner 在开工、关键契约/阻塞、验证完成和交付时汇报，长任务至少每 30 分钟一次实质更新；PM 回应阻塞并维护交接。
- 只在 `yx520143-G/PyBERT` Fork 工作；保留原生算法及 GUI/CLI/MCP 兼容。默认本机 `127.0.0.1`、桌面 Chrome 1280×720，不考虑窄屏、云部署、多用户或任意连线编辑器。
- 原生语义基线：`1bc905d577d2f3bd9471421cfbf3d422d4e6080e`；信号链原型来源：PR #7 `8542f10f4c137f79b3200638f5ee59d36202526a`。PR #6 是已完成的历史功能/语义证据，不再规定新 WebUI 的七页签位置。历史 Chrome 草稿测试不等于本票运行验收。
- 未完成 checkbox 不勾选；本票的任何 `passed` 必须链接本票实际提交、输入/资源 manifest 和验证结果。

## 目标、范围与依赖

父任务 #1；技术依赖 **#2、#3、#4**。在这些票已经可运行、可看 Responses / Results / Jitter、可用真实通道资源的基础上，交付可重开、可追溯的结果文件与比较工作流，完成核心 Native 信号链的跨功能验收。不得把本票变成所有图表/交互问题的首次验收：各前置票应已完成自身交付。

本期包括：完整 Web run archive、原生结果文件兼容入口、加载/保存/清除参考、两次或多次已保存结果的选择比较、配置/资源与结果归属、旧草稿兼容、桌面端到端验收。#2 的至少两次成功 run 临时缓存和基本比较不能延期到本票。

不含：重写原生结果格式、改物理算法、云端存储/多人项目、任意次数的无界内存历史、批量重跑/大规模速率矩阵。Native EQ、Viterbi、IBIS-AMI 专项在后续分别补各自记录与验收；本票的“核心验收”不表示它们或整个 #1 已完成。

## GUI 功能落点与文件语义

| 原功能/本期能力 | 信号链 WebUI 落点 | 明确行为与边界 |
| --- | --- | --- |
| File / Load Results | 顶栏“结果 → 打开结果/加入比较”；Run 概览的参考记录列表 | 识别 Web archive 与原生 .pybert_data。加载参考不替换编辑草稿，不自动 Run；外部记录有自己的 source ID/版本/可用范围 |
| File / Save Results | 所选成功 Run 的“保存结果” | 保存选定 run 的冻结输入和结果，不把当前已编辑草稿套到旧数组；当前没有成功结果时不可用并说明 |
| View / Clear Loaded Waveforms | 比较区“清除加载的参考” | 只清除参考叠加/选择，不删除当前 run、配置或磁盘源文件；不是清空全部项目 |
| File / Load Config. / Save Config. / Save Config. As... | 配置工具栏 | 沿用 #2/#4 的当前草稿语义；与保存结果严格区分。Save 沿用逻辑文件名，无名转 Save As；浏览器下载不承诺覆盖原路径 |
| 历史结果比较 | 全链路比较工作区；节点保留同类图选择 | 每条曲线/热图摘要显示 run/reference ID、输入差异、单位、窗口、观察点和算法来源；不同轴不能按索引盲目叠加 |
| Info / Performance、Console、Help/About、状态栏 | Run 概览、日志抽屉和帮助入口 | 读取所选记录的原始状态/版本/日志；性能来自对应运行且不作逐值数值一致性结论 |
| 草稿恢复默认/撤销/刷新 | 草稿工具栏与恢复状态提示 | 只改草稿；成功结果标 stale，未应用的输入中间态/存储错误与运行错误分开 |

原菜单/handler 的实际行为依据：[菜单](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/view.py#L1021-L1068)、[配置/结果/清除 handler](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/handler.py#L48-L124)。

## 两种结果格式的契约

### A. 完整 Web run archive（本票新增记录格式）

使用版本化 manifest + primitive metadata + 数值数组文件（例如 JSON 与 NPZ，加载数组时不允许 object/pickle）。不序列化整个活 PyBERT、Traits/Chaco、decoder 或模型 DLL 对象。格式必须包含：

- archive schema、run ID、状态、创建时间、实际 engine/adapter/prototype SHA 与依赖版本；
- 原运行 requested/effective 输入、input hash、资源 identity/原名称/内容 hash、模式与有效条件；扩展输入按版本保留；
- #2/#3/#4 导出的全部原始数据和轴、dtype/shape、producer、观察点、single/cumulative/equivalent/diagnostic 类型、window/clock basis、valid masks、availability/reason；
- 完成该 run 时使用的 eye/jitter/bathtub/适应过程元数据和真实派生结果。显示噪声、时钟回退、显示用裁剪/降采样与原始数组分离；
- 错误/警告/日志和子功能状态，含原生已知边界；无数据明确 absent，不能补零；
- 允许保存配置/结果文件的来源说明与文件校验值；resource bytes 可作为显式可选附带内容，不默认复制模型库或所有绝对路径。

**重新打开看图不依赖原资源仍在磁盘上。** 重新 Run 则必须恢复完整输入并重新解析/校验所需资源内容 hash；缺失或已改变时报出受影响字段，不默默换文件或以默认通道运行。绝对路径只是资源定位提示，不作为内容一致的证据。

旧 archive schema 采用明确转换或只读降级；无法识别的必需字段/版本不得当已验证配置执行。未来专项的命名扩展可原样保存并标记“当前版本不能执行”；不得丢字段后恢复默认。运行状态/最终 AGC Level/DFE weights 不覆盖原输入。

### B. 原生 .pybert_data 兼容范围

原生 PyBertData 只保存 **23 个 plotdata 项**与版本/日期，其中频响已是显示数据；没有完整配置、时间/频率轴、Rx FFE 全套数据、眼图、jitter 或 run ID。其 load 直接把数组作为 _ref，并借当前模型的轴画图，不能据此宣称恢复了原运行。[results.py L32–73](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/results.py#L32-L73)、[L86–145](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/results.py#L86-L145)。

本票须接入 Load / Save / Clear 三个原功能，做到：

1. 导入走服务端显式 legacy 分支，仅接受本机用户选择的可信旧结果；遵守原格式的 pickle 属性，不把它当通用无代码数据格式或从页面自动反序列化未知文件。
2. 验证实际对象/已知数组清单、shape/有限性/缺项。已知版本的单位、是否为显示变换应从对应 producer 记录，不能把已转换的 dB 再转换一次。
3. 外部 legacy 文件没有轴时，**禁止用当前 run 的物理轴猜配**。显示缺少轴/输入的原因；可提供明确标注 sample index / frequency-bin index 的诊断预览，但不能显示伪造 ns/GHz 或做物理域数值比较。只有用户同时提供可核查的原配置/轴证据且校验匹配时才开放物理叠加。
4. 从新 Web run 导出原生兼容文件，仅导出原生清单可表示的 subset，并附可选独立 sidecar 记录轴/来源/单位；不改变原生读取要求。不能表示的能力给出损失清单，完整保真保存应选 Web archive。
5. tx_out 等原生清单项可能未由当前 producer 生成；导出前验证，不以零数组顶替。若直接原生导出也因缺项失败，明确原生边界与可用的 Web archive，不捏造成功的 legacy 文件。
6. 清除加载的参考只移除所选记录及图层绑定；不会把旧 _ref 残留进其他 run。

## 输入、资源、数据和运行一致性

- 本票沿用 #2 的单 worker：保存/读取已完成的 primitive 数值数据无需重跑引擎；任何需要原生配置 observer 的校验必须走同一个串行数值槽位。Run/优化/COM 不因打开 archive 而被隐式启动。
- 运行输入快照、编辑草稿、成功结果、显示投影分别存放。保存按钮明确对象；一边编辑一边保存旧 run 时，其 archive 仍保存旧 run 的冻结输入。
- run/reference 每个 dataset 使用自身轴、窗口、producer 和单位；对齐/插值如仅为显示必须显式标注，原始数值比较不经过该变换。DFE 最终权重等效响应不能标作真实 DFE 线性传函；Channel-only 与 Rx input、Rx FFE 与 DFE 不混淆。
- eye 对比明确各自 clock basis/window/电压网格/显示噪声；网格不同可并排显示，不能仅凭颜色相同判数值相同。jitter 比较使用原始 PDF/TIE/spectrum 与正确统计单位，缺数据/原生失败有原因。
- 至少两个成功 run 的现有缓存维持不变；增加明确条数/字节预算和可移除记录，不无限保存所有数组。超过预算显示可执行处理方式，不静默覆盖用户选定参考。服务重启后以已保存 archive 恢复；浏览器 localStorage 只存轻量草稿/选择状态，不塞全波形。
- 文件读写失败/损坏/版本不支持时原草稿、选定 run 和已加载参考保持不变。服务端文件写入采用临时文件后原子发布；浏览器下载只报告生成/交付状态，不能在未确认时宣称已覆盖本地文件。
- 刷新/断线不会取消后端任务；重连查询 task ID/最终状态。后端已重启且临时 run 不存在时显示“结果未保存/当前不可用”，不得从 localStorage 标记伪造成功。
- 草稿 schema 独立于 catalog 显示顺序，记录完整源码 SHA 与稳定 field IDs。接入 PR #7 v1 localStorage 草稿时执行显式迁移/校验；非法 JSON、旧字段或本地存储失败可恢复且不被误标为输入/仿真错误。未支持的有效字段保留并说明，不能默默丢弃。

原生 Responses / Results / Jitter producer 与单位沿用 #2/#3/#4；本票不得把 Chaco 的 1000 点显示数据作为原始时域结果，也不得在前端实现新的 eye/jitter/BER 公式。[原显示构建](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L1116-L1343)。

## 实施步骤

1. 冻结 archive/legacy manifest、schema 与迁移表；逐项对照 #1 功能矩阵和已交付数据契约，列出可保存字段与原生 legacy 缺项。
2. 实现完整 archive 序列化/校验/重开及清除参考；先用已完成的实际 run 数据走往返，图层绑定保持 run ID。
3. 接入原生 Load/Save Results 子集和 sidecar；缺轴/未知来源明确降级，不套用当前配置。旧配置/草稿迁移以相同原则处理。
4. 完成比较入口、输入/资源差异、stale/失败/取消提示及文件操作语义；完善 1280×720 路径。
5. 用已冻结的 #2/#3/#4 有界 fixtures 做本票所需的跨功能和往返验证；复用有版本的原始基准，不以重新挑选“看起来更好”的输入代替修复。
6. 交付真实证据、未通过项及 native blockers；后续专项只扩展自己的 schema/验证，不再次重建核心结果系统。

## 计算前冻结与验收

沿用 #2 完整 NRZ/PAM4 fixture、非零 seed/noise、资源 hashes、全部有效窗口、raw 数值分类容差及 #3/#4 已冻结附加 fixture。实际计算前提交 manifest；若输入/依赖/窗口变化，应新建显式版本并在计算前记录原因，不在看到差异后调宽容差。

本票的**存档往返**要求数值数组的 dtype、shape、原始字节/数组 hash 精确一致，valid masks、indices、axes 和元数据语义精确一致；存档不是浮点重算，不能以 allclose 允许丢精度。直接原引擎 vs adapter 仍按 #2/#3 的分单位容差，不能用存档一致代替引擎一致。display projection 另验轴转换、降采样及 raw 数据未被修改，截图只验证界面语义/可操作性。

- [ ] #1 的核心功能矩阵逐项有实现/未支持原因和本票证据链接；Responses 四类、Results/DFE/Outputs/Eyes/Bathtubs、Jitter 三类及菜单/文件动作都有落点，Viterbi/优化/AMI 仍指向其专项，未虚报全功能完成。
- [ ] 所选成功 run 可保存为完整 archive、重开并在无需原通道文件的情况下查看全部已采集图；再 Run 时缺资源/资源变动明确阻止且不回退默认。
- [ ] 全部 raw arrays/axes/窗口/有效性与输入 snapshot 往返精确；最终 AGC/DFE 状态未覆盖用户原输入，当前草稿不污染旧 run archive。
- [ ] 原生 .pybert_data 的 Load/Save/Clear 有可核查结果；缺轴/缺项/旧版本/非法文件不伪造完整运行或物理轴，已知显示单位不二次转换。
- [ ] 比较至少两次具有输入差异的真实成功 run，节点/全链路/摘要/参考图都绑定正确 ID；不同轴/窗口/时钟明确显示，切图/缩放/加载/清除不重跑。
- [ ] Run 失败、原生预检返回、合作取消尚未完成、任务实际结束、重连/后端重启分别有正确状态；旧成功结果保留且不会冒充新结果。
- [ ] 当前配置 Save/Save As、结果 Save、Load、取消选择、损坏文件、下载/写入失败均不破坏原草稿和成功记录；本地草稿旧版本/存储失败有独立状态。
- [ ] 在真实桌面 Chrome 1280×720 走通“修改 → Run → 各级响应/波形/eye/jitter → 比较 → 保存 → 重新打开”；当前数值/浏览器证据与 PR #6/#7 历史证据明确区分，不做窄屏验收。
- [ ] 同一完整输入的 NRZ/PAM4 直接原引擎对照、raw 与 display 分离证据、原 GUI/CLI/MCP 必要兼容检查和剩余原生限制可追溯；没有把接入一致性称为 MATLAB COM correlation、完整 BER 资格或标准认证。

## 原生缺陷与不可用边界

原 .pybert_data 信息不完整、原 eye 显示轴/附加噪声、部分 jitter/BER 短窗口与优化/AMI 分支限制不会因文件保存消失。保留 producer 的原行为、availability 和真实限制；#2/#3/#4 已记录的 native blocker 在本票仍可见。若某项只能记录阻塞，必须保留未完成状态并由 PM 管理后续修复范围，不能删除矩阵行来关闭总任务。


