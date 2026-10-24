# WebUI #4：真实资源、完整配置与独立 COM

当前状态为 **实现已固定，提交 PM 终审；default COM 数值验收仍待预算处置**。本报告不关闭 [#4](https://github.com/yx520143-G/PyBERT/issues/4)，不将 blocked 或未执行项计为数值通过。

实现 cut：`5fff0412b4cde14591ef0b9c1986be7505ac0e2b`（主体实现 cut 为 `6a3a323d89952d5807b852e517d1653a6f7e289c`）。PR 以 master 为 base，已正常集成 [#13 / PR #14](https://github.com/yx520143-G/PyBERT/pull/14) 的原生端口修复 `e29f87c177ac89fabdec2d5a34d8e6ea7e7cce7c`。数值 producer 的历史参考为 `1bc905d577d2f3bd9471421cfbf3d422d4e6080e`；multi-lane 使用已验收的 corrected importer，旧错误配对产生的数值不作为 expected。

## 功能与证据矩阵

| 功能 | 本轮状态 / 证据 | 实际边界 |
|---|---|---|
| 浏览器上传、显式绝对路径登记 | Chrome 实际上传 A/B，路径登记 C；内容寻址、外部修改隔离及重复位置契约测试通过 | YAML 和浏览器文件名不充当后端路径；相对路径不按 cwd/同名资源猜测 |
| Single A，NRZ / PAM4 | 两种完整 fixture 的 direct/current worker raw、复数分量、独立分析及显示通过 | 同一真实 .s4p，原 seed/noise/采样/窗口/容差 |
| Ordered cascade A→B / B→A | 两个原顺序/反序数值 case 通过；Chrome 实际重排并分别 Run，输入身份等于计算前冻结 | 保留顺序和重复项；不声称存在每段独立 waveform |
| Victim / FEXT | 原 M 两个 victim，各自 OFF/ON 四 case 全部通过；每路贡献及总干扰源数据保留 | 实际数值覆盖 .s8p 的 2 lanes；.s12p/其它端口约定不据此获全部物理资格 |
| 端口识别/自动置换 | 直接使用已验收 #13 helper；manifest 记录实际端口、输入/输出 pair、aggressor 路径 | 不是任意 pin-map 编辑器；不以 single-ended 跨 lane 非零替代差分证据 |
| Package / 普通端接 | KR/A1 + partial host 的代表性数值 case 对比 A 普通端接通过 | 其它 13 个合法 group/case 的 26 个 Tx/Rx model 仅预检；未做物理大矩阵 |
| Raised-cosine window | 同一冻结 A、`use_window=True`，原类/current helper 的 h/H/s/p/时间轴/trim 起点/延迟 7 项 exact | helper-only，不冒充新增完整 Run；GUI 仅文件模式可编辑，engine 的消费条件照原代码 |
| Duo-binary | 完整 NRZ 长度/采样及原窗口下 direct/worker 对照通过 | 展示真实 source x；ideal_signal 是另一个参考，不替换实际驱动 |
| 基础 noise / FEXT / 总干扰 | `self.noise` 只标基础 noise；各路和局部最终 noise 在原 producer 收集，raw/display/window/path 检查通过 | 每 aggressor 与 victim 使用同一 x；Rs/Rin 独立端接，原 trim 后从离散 index0 卷积；无新增幅度/延迟补偿 |
| FEXT 显示状态 | OFF 明确显示 `FEXT disabled`；ON 展示基础、各贡献和总干扰 | 最终两张 Noise 图来自已有真实 raw 的只读显示复验，不是新仿真 |
| 完整 Load/Save/Save As | 原生 95 字段、完整 100 tap 槽/约束、DFE 连续前缀及 patch/load 区别有契约与 Chrome 往返证据 | 导出当前输入，非 AGC 训练 Level 或 DFE 训练权重；资源 bytes 不打包 |
| 历史配置 / runtime extensions | 已知 PyBertCfg pickle、受限 YAML、aliases、旧 delta_t、缺失字段报告及版本化注释通过 | 未知对象拒绝；rlm/rx_use_clocks/ami_opt_trials/动态 AMI 参数作为 Native inactive 扩展保留 |
| Inactive 文件 | 缺失 IBIS/AMI/DLL 旧路径不触发模型 observer；disabled CTLE File 可保存/规范化且执行 gate 允许 | 当前激活的 IBIS/AMI、Viterbi 等明确拒绝，交给各专项；不静默退回 Native |
| 启用 CTLE File | **NATIVE_BLOCKED**，Chrome 实际 Run 明确失败、旧 core 保留 | 原 helper FIXME；未修算法。disabled Native bypass 的原生调用语义保留 |
| 非零 impulse_length | **NATIVE_BLOCKED**，完整配置可往返，执行 gate 拒绝 | GUI ns 与主仿真局部长度的原生单位疑点未修正 |
| Rx_Cac / package+FEXT | Cac 保留 µF 值并注明未消费；package+FEXT 执行拒绝 | 不增加 AC 耦合或完整 package aggressor 模型 |
| 原时间响应 T | **NATIVE_BLOCKED**，真实 import_channel traceback 保留 | 原文件 Tab 分隔；原分隔器读到 0 行。未换资源或修 parser/H→S/step-impulse 启发式 |
| 独立 real spreadsheet COM | 原 calc_com 与 fresh worker 均 **−15.419984103278814 dB**，差0；Chrome 实际独立计算相同 | 同一 A + 原 C .xls；独立参数，不注入当前时域 EQ/bitrate/noise/FEXT/package；负值有效，不是 IEEE pass |
| Run 后 COM | Chrome 真正 core→exit/join→新 COM child，19 次转换记录，父 manifest 前后 bytes 相同 | parent 保存 requested enable_com 和 deferred plan；子状态独立关联，父结果不回写 |
| COM / core 取消、失败 | helper 内取消、DFE/CDR 内取消、无效 XLS、CTLE File 拒绝均有实际 Chrome/task/退出证据；原成功结果保留 | helper 内无取消 checkpoint；request/observe/exit 分开。异常、ERROR、−999、非有限值不能成为新成功 |
| 默认 COM 数值 case | **BLOCKED_BUDGET / NOT_EXECUTED**，原参数及矩阵行保留 | 794069×16×11 = 139756144 outer candidates，local_search=0；依 PM v1 不启动，不缩网格，不以 XLS 替代 |
| Native GUI / CLI / MCP | 原生 CLI 同一完整 A case 成功保存；22 个 native response exact；MCP 全字段及 GUI view import 通过 | GUI/CLI/MCP 源码未改；未重新宣称完整桌面 GUI 资格，旧 #2 GUI 错误证据保留 |

## 计算冻结与资源适用性

入口为 [fixtures/frozen-manifest.json](fixtures/frozen-manifest.json)，SHA-256 `8d953b64ccc1e9afd57ac336679bf4e47156258e4cec4d4d023ce4c6d08ce381`。继承 #2 的 11 个文件、完整 NRZ/PAM4 输入、非零 seed1、rn/pn 0.01、100 tap 槽、窗口和容差；COM 标量门槛在计算前固定为 `rtol=1e-10, atol=1e-9 dB`。预算初版的 Python sum/精确零计数错误原件保留，以 budget-correction-v2 为更正。

5 个原资源及本机副本共 3,954,828 bytes，来源/权限/hash 见 [fixtures/resources.json](fixtures/resources.json)：

- A：PyChOpMarg 原 `example2_THRU.s4p`，0–40 GHz，BSD-3-Clause。
- B：课程材料原 `002_peters_01_0605_B1_thru.s4p`，50 MHz–15 GHz；只记录本机研究使用，没有再分发许可声明。请求为 0–40 GHz；原 helper 在覆盖外对 transmission 补0、reflection 极坐标外推并限幅、z0 外推。DC/高频补值不称为测量覆盖。
- M：SignalIntegrity 原 `TwoLaneModel.s8p`，0–80 GHz，GPL-3.0 模型；不是硬件测量。端口物理解释及 #13 修正见 corrected-native-precheck-v2。
- T：PyAMI 原 `impulse_response_8ma.txt`，表头给 s / V/s；保留原 Tab 字节及失败，不替换为方便解析的新文件。
- C：PyChOpMarg 原 `.xls`，不改原参数。原 reader 忽略 N-g/N-max 的警告完整保留。

资源 bytes/cache 不进入 PR。早期误跟踪的一个 A 副本仅移出 Git index，原文件仍在盘且 hash 匹配。全部 ignored raw、失败/旧冻结及 #2/#3/#13 worktree 均保留，没有 cleanup/archive。

## 数值、显示与 Chrome 的复核入口

| 层 | 原始报告 / 后续有效证据 |
|---|---|
| Single NRZ | `numeric-20261024-073225/report.json` 保留初次验证器错误；`saved-resource-check-20261024-073439/report.json` 首次只读更正，最终 metadata/window 检查为 `090813/report.json` |
| 其余 9 case | `numeric-20261024-075721/report.json`、`numeric-20261024-075832/report.json`；[numeric-corrected-baseline-links-v2.json](evidence/numeric-corrected-baseline-links-v2.json) 连接 corrected freeze、原输入/资源/实际执行源码和 raw |
| 最终 FEXT/path/window | `saved-resource-check-20261024-090825/report.json` 的 7 个非 ON case；`090903` 的 L0-ON、`090909` 的 L1-ON。`090819/090825` 中 lane_ix 验证器错误保留，改用真实字段 lane_sel 后仅重查两个 ON，无主仿真 |
| 原 COM / TIME | [native-tools-20261024-082936/report.json](evidence/native-tools-20261024-082936/report.json)，包含 pre-call freeze、完整参数、实际 source hash、原标量及 TIME traceback |
| 实际 Chrome | [browser-audit-v1.json](evidence/chrome-20261024/browser-audit-v1.json)：30 项通过，3 个真实 Run 各 439 个 raw 数组对旧独立 worker exact；ui/ 保留原 PNG、快照和控制脚本 |
| 串行退出与不变父记录 | [run-child-transitions.json](evidence/chrome-20261024/run-child-transitions.json)，核心退出后才创建子任务，父文件 before/after 完全一致 |
| 有限兼容性 | `light-compat-20261024-091034/report.json` 原报告保留；[saved-cli-check-v2.json](evidence/light-compat-20261024-091034/saved-cli-check-v2.json) 只读更正验证器后 11 项通过，22 native response exact。原 CLI 保存后状态为 Saved results，非 Ready；原 tx_out 为零维 None，非可用 waveform |
| 契约测试 | [final-resource-com-contracts-v4.xml](evidence/final-resource-com-contracts-v4.xml)：41 passed、1 deselected、40 warnings，43.86s。未重跑既有整套缓存历史测试；原证据和本轮实际 Chrome 缓存行为保留。定向 Ruff E4/E7/E9/F、compileall、JS syntax 通过 |
| 最终 Noise 展示 | `chrome-20261024/saved-noise-display-v2/`：已有 A 与 M raw，只读服务拒绝计算提交，实际 Chrome/稳定 Plotly/像素检查；无新 main/COM |

主仿真比较沿用 #2/#3：raw 与显示转换分别核对，复数实部/虚部分别检查，raw/data/analysis windows 和非性能摘要独立验证。原 FEXT ON 的 NPZ 整体 hash 差异仅 ZIP entry 排序不同，解包 NPY 原字节逐项相同，不是数值差异。analysis_version 仍为2，新增 raw schema 为4。

Chrome 实际执行上传、修改/恢复 Vod、A/B 顺序调整、Run、frequency/impulse/wave/eye/jitter、独立 COM、Run 后 COM、Save/Save As/Escape/下载重载、UNBOUND/显式基目录、旧格式/危险对象、失败/取消及 B/B/A 重复项恢复。所有关键 PNG 都经过 view_image 像素检查。

必须保留的尝试与范围：第一次 COM Abort 在预检阶段；第二次才捕获 helper 内区间。第一次 DFE Abort 监控错误地把 Run 前 normalize 终态当 Run 终态，错过区间，该次额外 single Run 和 COM 均真实成功并保留成本；随后重试成功取消 DFE。默认双 core 临时缓存已正常淘汰 AB/BA，最终双 run overlay 是两次 single A，不能声称是 AB/BA 叠图；AB/BA 的原 raw/manifest 已在淘汰前分别下载保全，并各自 exact 对照原 worker。

## 源码、成本与未完成项

[delivery-source-and-cost-v1.json](evidence/delivery-source-and-cost-v1.json) 的 SHA-256 为 `3fd573724604ddd055446a7c308f6775ce0f1dc3cab4d5cae4ceee25b3a66ecf`。它固定 implementation cut、23 个最终源码的 raw/LF hash、52 个保留 raw 文件的路径/hash/大小（2,198,132,299 bytes）、原四份 raw 的保全、12 个 Chrome 数值任务的实际时间及关闭端口检查。

原生 `pybert.py/models/bert.py/sparam.py/models/com.py` 与 corrected execution freeze 的执行字节相同；CLI/MCP/configuration/GUI source 与已验收 master 相同。原类/bert 的 direct frame 实际绑定 corrected importer，不能将旧错误 multi-lane 结果叫作标准 reference。

实际 Chrome 冻结后，主体 cut 中仅有两处展示变化：resources.js 保留展开的 COM 历史详情；data.py 的 `plot_payload` 增加 Noise 的 disabled 标题/已有 interference metadata。seal 反向移除这两个精确 hunk 后能重现 Chrome v3 冻结 source SHA；均未改 collect、数组或数值 producer。前者实际 reload 后跨轮询复验，后者用保存 raw 做只读 Chrome 复验。其余晚期 metadata decorator 修改已由全部 10 case 的 saved-only 检查覆盖，未为版本标签重复主仿真。

成本应按原件阅读：9 个新 case 的 direct 合计约66.76s，worker created→finished 间隔合计约89.53s；两者是各串行阶段之和，不是全部开发/验证 wall-clock 成本。原 spreadsheet COM direct 4.1219716s 含只读计数 profile，worker 7.05232096s 含 spawn/退出；实际 38 次 FOM、1 个 Tx 组合、local_search=2。CLI 7.7321305s。Chrome 包含一次额外完成的 single+COM 取消监控尝试；其逐任务时间均保留，不隐去或归入新物理资格。所有 metadata-only 检查也保留独立报告和 raw 副本。

默认 COM 仍是原参数的 **BLOCKED_BUDGET / NOT_EXECUTED**，不拿真实 XLS 的耗时线性推算 full-sweep，也不加入产品硬编码阈值或审批。TIME、CTLE File、非零 impulse length、package+FEXT 的原生边界如上；不存在 IEEE/Matlab correlation、硬件或 BER/电压裕量资格结论。后续默认 case 执行安排或显式范围修订由 PM 处置。

本轮生产服务 8767 与只读显示服务 8768 均已停止，Chrome 独立 session 已关闭；最后生产 index 的 active_task_id=null。主 checkout 仍为 `codex/webui-gui-baseline` / `b9c56fe76bafb901d58dd53cda54e2ad5093fe6c`，其 docs/research/、source/ 未触碰。固定交付后的后续工作为 PM fresh review / 预算处置；本票不派发 #5/#8/#9/#10。

最终追加 [delivery-final-source-v2.json](evidence/delivery-final-source-v2.json)，SHA-256 `1dd7ee7878a80f0896787b935f2abaa8cb27c038430b71542378cdf76ef4a8e3`。它连接上面的 v1 seal，固定最终 implementation cut `5fff0412b4cde14591ef0b9c1986be7505ac0e2b`：相对主体 cut 只改 app.js 的 inactive 文件选择/提示（3 行加入、2 行删除）。Channel/cascade/COM 三字段继续上传内容，其余未消费文件字段只明确保留文件名。实际 Chrome 用 disabled CTLE File 选择一个明确标作 inactive-reference-only 的 CSV 并 Save：全95字段匹配，resource_bindings 为空，真实下载一致，0 Run / 0 COM / 0 resource upload，slot idle；不是新物理 fixture。截图/原件位于 `chrome-20261024/inactive-file-picker-v5/`，另有原 storage 故障/恢复脚本及 syntax 检查通过。其它 v1 source hash 全部相同。最终 12 个 Chrome 数值任务间隔之和为84.99642396s；最后一次 filename-only 与只读 Noise 复验均无新增数值任务。
