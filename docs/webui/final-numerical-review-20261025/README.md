# GUI → WebUI 最终数值改动影响审查

日期：2026-10-25（Asia/Shanghai）。范围：已交付 GUI 功能迁移的计算、结果和显示一致性。没有恢复默认 COM 大搜索、真实 AMI 验收或控制层扩展。

## 结论

修复本轮发现的 Traits 字典兼容性回归后，固定 Native NRZ/PAM4 输入的 GUI producer 与实际 Web worker **数值一致**：889 个原始及派生数组的 dtype、shape、C-order bytes 完全相同，108 项共有 GUI 显示数据完全相同；误码数、延迟、功率、jitter、初始/最终 Level 与有效输入一致。与迁移前保留的原生参考结果比较，原有 623 个数组也全部逐字节相同。

这不等于所有图形逐像素一致：波形显示窗口/采样方式、Channel eye 显示噪声和眼图电压坐标映射有明确差异。S8P/S12P 导入与 AMI 路径还存在双方共享的原生修复，不能概括为“相对开发前完全没有数值行为改动”。

## 固定版本和证据边界

- 开发前原生语义：`1bc905d577d2f3bd9471421cfbf3d422d4e6080e`。
- 本轮初审集成版本：`0c4424a67f93c9f6a9ae4ffe2a274f9ac65cc1f3`，tree `93f18abc94bd63e582c988526c349a5a8028e6e1`。原执行 checkout `6e4fcf5` 与该 tree 完全相同。
- 本轮最小产品修复及实际通过版本：`0a7a03652a0f75f8032bf88cb588ca01fb751892`。后续报告提交不修改产品源。
- [完整提交清单](commits.txt)、[原生及依赖差异](native-diff.patch)、[11 个未变核心文件的 Git blob/AST 比较](unchanged-core.json)。DFE、CDR、Viterbi、COM、math、jitter、channel、configuration、GUI handler/view 和 sim thread 均与开发前逐字节一致。
- 使用既有 Python 3.13.15 运行环境；NumPy 2.5.1、SciPy 1.18.0、Traits 7.1.0。执行前冻结实际源码和输入 hash，运行时断言模块来自审查 checkout。PyAMI 使用已固定的 `d6d1f7fe…`，PyChOpMarg 为 `ca905e79…`。未安装或改动环境。
- fresh GUI 对照调用原生 `load_configuration` 读取原 YAML，并实际执行 `my_run_simulation(update_plots=True)` / `update_results`；没有打开桌面窗口或把此次测试称为 GUI 全交互验收。Web 侧使用真实 `Tasks.start`、spawn worker、terminal 和 join。

## 本轮发现并修复的 P1

初审版本将 `clock_info` 存入 `PyBERT.ami_clock_info = Dict()` 后重新读取，得到 `TraitDictObject`。随后 `update(ignore_ui_requested=...)` 使用了 Traits 7.1.0 不支持的关键字形式，Native NRZ 在 `models/bert.py:392` 即抛出 TypeError；Native PAM4 和 AMI 也使用这一无条件入口。

本轮只把 `models/bert.py` 的 6 处、`utility/ami_clock.py` 的 10 处相关写入改为 `update(dict(...))`。没有改变 trait 类型、字段值、公式、采样窗口、状态判断或调用顺序。[AST 核验](correction-source-audit.json)确认：去掉这 16 个 dict 参数包装后，两份完整文件与修复前 AST 相同。

新测试使用真实 `HasTraits + Dict`，同时保留普通 dict 对照，覆盖无 clocks 回退、非法输入、实际采样和 `calc_eye`、部分失败保留首个 decision。旧源 [4 failed / 4 passed](traits-red.xml)；修复后连同配置、显示、归档、优化动作、Viterbi 映射、多端口/4-port/VITA 检查，共 [195 passed](targeted-green.xml)，248 个既有 warnings 保留。没有将软件 clock 样例称为真实 AMI 模型验收。

## 实际数值改动、原因和影响

| 部分 | 相对开发前的改变及原因 | 影响及证据 |
|---|---|---|
| Native 通道、Tx、CTLE、Rx FFE、DFE/CDR、BER、jitter | `models/bert.py` / `pybert.py` 增加可选观察采集，保存实际中间量；不替换计算。核心 helper 文件未变 | 本轮原始 NRZ/PAM4 623 项历史对照、889 项当前 GUI/Web 对照全 exact；采集、保存和切图不反馈物理波形 |
| Native EQ 优化 | `threads/optimization.py` 记录候选和 MMSE 输入/输出，评分与优胜选择不变；后续新增 AMI 候选记录 | [#8 原数值审计](../issue8/evidence/delivery-audit-20261024-130843/report.json)有 252 个 direct/adapter 数组 exact；当前相对 #8 增量只在 AMI 分支记录结果。本轮检查 Native Use/Reset、拓扑与归档，未新跑 coopt |
| Native Viterbi | 原 trellis producer 抽取后共享；decoder 本体未变。Web 增加保存、定位和严格数据来源校验 | [#9 原审计](../issue9/evidence/delivery-audit-20261024-143549/report.json)有 2871 个数组 exact。当前额外 clock-source 分支仅用于 AMI；Native 保留原采样规则。当前定向测试覆盖 DFE 独立轴、decoder tail 和归档。未重跑完整 decoder 矩阵 |
| S8P/S12P through/FEXT（#13 / PR #14） | `utility/sparam.py` 修正 caller 端口次序和每 lane 的 renumber，原差分公式未改 | **确实改变受影响输入的通道及下游结果**，GUI/Web 同享修复。真实 M victim 0 的 max \|S21\| 从 0.018863746 变为 0.986637180，匹配物理 oracle；跨 lane 清零后 FEXT 从 0.086373760 变为严格 0。[前](../native13/evidence/real-M-before.json)/[后](../native13/evidence/real-M-after.json)。#16 外部模型 through 15/15、FEXT 24/24 已有证据。本轮相关 49 项回归通过；不外推硬件资格 |
| COM（#4 / PR #15） | Web 复用未变的 `models/com.py::calc_com`，独立 worker；Run 后 COM 等主 worker 退出。采用原 XLS 或明确 defaults，未注入时域 EQ | [真实原 XLS](../issue4/evidence/native-tools-20261024-082936/report.json) direct/worker 均 −15.419984103278814 dB，差值 0；原 Chrome 同值。当前 COM 两个产品文件相对已验收版本无差异。默认 139,756,144 候选仍未执行，按用户范围修订不再阻断 GUI 迁移 |
| AMI 参数/PyAMI 返回接口（PR #23/#26/#29） | `bert.py` 解读 GetWave tuple/full-path 参数；固定 PyAMI wrapper clock buffer/返回约定及私有 probe RNG | 影响 AMI 参数历史、clocks 和失败条件；共享原生修复。不能用旧接口历史运行宣称当前真实模型数值已验收 |
| AMI probe/Main 隔离及采样（PR #31/#32/#33） | `ibisami.py` 隔离响应 probe 与 fresh Main；`ami_clock.py`/`bert.py` 使用生产者实际 grid index、有效窗口、period mask，GUI/Web 消费相同来源 | **可能改变 AMI 实际波形、取样和 Eye/CDR 输出**；本轮只审查代码和修复 Traits 容器兼容性。真实 NRZ/PAM4 AMI 按用户决定暂缓，保留 UNKNOWN / PARTIAL / NOT_EXECUTED，不给数值一致性总通过结论 |
| Web 运行与配置 | 每次 Run 新实例和完整有效配置快照；复用 `PyBertCfg` 加载及 observer；COM 延后执行、结果与草稿隔离 | 同完整输入/同非零 seed 下配对一致。性能计时因进程启动和采集不同，不作为数值一致性指标。GUI 旧实例的编辑历史、seed=0 随机运行不在逐点相同保证内 |

## 计算结果和显示的一致性

| 项目 | 结论 |
|---|---|
| 共有 h/s/p/H、jitter PDF/Spec、bathtub、CDR histogram/Spec | 直接比较真实 GUI `plotdata` 与 Web 投影；每模式 54 项 exact，含 Rx input、CTLE、DFE 三个非显示噪声 eye count 矩阵。Web 前端使用服务器给定物理轴和单位，没有再次计算数值或按索引强行对齐 |
| waveform / CDR 曲线 | 原始数组一致。GUI 对长记录使用全记录 1000 点插值；Web waveform 显示末 20 UI 的原样本，CDR 使用全记录最多 4096 个索引。屏幕曲线取点不同，不影响 raw 或统计 |
| Channel eye | Web 保留无显示噪声版本，并另加固定 PCG64、σ=1mV 的显示版本；GUI 使用自己的 normal 显示噪声 realization。无需、也未宣称像素逐点相同；该噪声不进入物理链路 |
| Eye 电压坐标 | Web 按实际 `calc_eye` 的 `y_scale/y_offset` 还原 1000 行电压网格。原 GUI `update_eyes` 的既有线性端点/全记录幅度坐标存在差异。因此原生 count 一致不能扩写成全部绘制坐标一致；本轮没有修改原 GUI 显示 |
| Web 额外观察 | Rx FFE 分析、部分 single-stage pulse 等是已有迁移范围中的额外 helper 观察，不是 GUI 中存在的同名图。不可把缺少 GUI 对应项记成数值差异 |
| 无数据/非有限/旧档案 | 明确 unavailable / unknown，不用当前 run 的轴补旧资料、不把 sentinel 当测量。当前归档和显示契约测试通过 |

## 本轮验证记录

固定输入沿用 #2 原件：10 Gb/s、NRZ/PAM4、seed 1、15,000 bits、32 samples/UI、eye_bits 10,160、原噪声/FFE/全部 tap 配置，没有更换窗口或调整容差。

| 对照 | 结果 | 证据 |
|---|---|---|
| NRZ GUI producer vs Web worker | 444 个数组 exact；54 项共有 GUI display exact；摘要/输入/窗口相同 | [原报告](fixed-v2/numerical-report.json)、[不适用图项勘误](fixed-v2/display-check-correction.json) |
| PAM4 GUI producer vs Web worker | 445 个数组 exact；54 项共有 GUI display exact；摘要/输入/窗口相同 | [报告](pam4-v3/numerical-report.json) |
| 当前 vs 保存的开发前原生参考 | NRZ 311、PAM4 312 项，全部 dtype/shape/bytes exact；0 新仿真 | [输入 hash](saved-comparison-inputs.json)、[逐项报告](saved-baseline-comparison.json) |
| 两个真实 worker | 均 succeeded、worker_exited=true、exitcode=0 | NRZ `6f127f36-10a0-4bd7-8407-1889cb5d9850`；PAM4 `215ee1b2-45b4-4823-b6ec-2dc242d456bc` |
| 非性能摘要 | 两模式 DFE errors=0，Viterbi disabled=−1；延迟均 2.3812500000000002 ns；其余功率/jitter/Level 逐项相等 | 两报告的 summary 与 summary_equal_excluding_performance |

保留的失败和成本：初审版本 1 次 Main 部分执行后 TypeError；修复后 4 次完成 Main（2 GUI producer + 2 Web）。NRZ 首轮比较脚本把 GUI 不存在的 tx_p/ctle_p/dfe_p 当成共有字段，原报告保持 failed，另附勘误；NRZ 未重跑。没有产品数值差异被放宽门槛掩盖。真实数值 COM/coopt/AMI library 调用均为 0。两个通过批次的脚本 elapsed 为 17.9904s 和 10.6407s，包含采集/保存/worker，不是纯仿真耗时；195 项测试的 pytest 时间为 38.86s。RSS/CPU 峰值未采样，不推断。

原始数组保留在本机 `E:/serial-bus-simulator/docs/webui/final-numerical-review-20261025/` 下对应 `fixed-v2/local`、`pam4-v3/local`；Git 保存报告、输入 hash 和验证脚本，未提交或清理大数组。原有源材料和失败证据不改写。本目录禁用 Git 换行转换以保留证据字节；patch 上下文和原始测试日志/XML 的空白警告原样保留，产品源及新写报告/脚本/JSON 的 whitespace 检查通过。

## Standards

独立 reviewer 检查原生 helper 复用、配置/worker/显示映射和本轮最小修复：documented breaches 0，heuristic findings 0。确认没有替代算法、无关重构或新增环境。静态审查本身不能代替上述实际运行。

## Spec

初审静态 0 finding 在真实运行后撤回；实际发现 1 个 P1（Traits Dict API 不兼容）。16 处最小修复经独立 fresh 复审和真实配对闭环，当前未解决 finding 0。真实 AMI、默认 COM 未执行以及显示差异保持明确边界。

最终：Standards 0；Spec 1 个 P1 已修复，未解决 0。结论仅覆盖已声明 GUI 迁移范围与列明证据，不代表全部模型、参数组合、IEEE/MATLAB 或硬件资格。
