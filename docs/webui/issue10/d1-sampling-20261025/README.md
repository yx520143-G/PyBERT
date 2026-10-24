# D1：Native AMI clocks 采样与分析消费

2026-10-25。当前仅实施 #10 的 D1 阶段；[PM 完整合同](D1-contract-comment.json) 覆盖固定设计 §5/§6 的旧排程和执行限制。起点为 `9343cdb7a2eee1762a60ae284d1e3a48772729d4` / tree `486768d95e04717f3726e8fd98cf1e36dd59fc98`，PyAMI F2 及其他依赖不改。startup 原件在 [startup.json](startup.json)，此前 clean、独立 Git metadata；子模块未初始化。

采用实际 grid times 为 AMI canonical，producer absolute indices 供 Viterbi/Eye 复用；edge/target/量化延迟另留。全记录逐 tick 消费与冻结的双边界分析窗分开；format-valid、eligible、实际完成/partial 分开。period 保留 mask/NaN，histogram 只用窗内 known 值，FFT 只用预冻连续全 known 原 grid 子窗。Native 默认规则、C1 与 A 不扩改；D2/E 不提前。

当前生产配置缺少 PAM4 提供方对 Ignore 单位、zero nominal eye offset 及 native slicer mapping 的确认和输入承载合同；不添加模型白名单或默认认证。生产 PAM4 timed clocks 将明确 unsupported/UNKNOWN，软件矩阵可使用明确声明的 symbol-UI/零 offset profile。NRZ bit/UI 无歧义。该缺口已报告 PM，真实模型资格仍待后续。

既有 CDR period 线共享 waveform 的降采样 `t_ns` 轴；为避免 masked full-grid 数据与该轴长度不符，D1 必要图消费接线包含 `gui/plot.py` 的一个独立 period 时间键，Native 仍填原降采样轴，不改图布局/控件。

先按 [NumPy 安装计划](numpy-install-plan.json) 在新 `.venv` / cache 只安装 lock 对应的 NumPy 2.5.1 wheel，使用 frozen URL/hash、no-deps、copy 模式。实际 NumPy 模块 import/小数组执行待 source/test/runner/cases/guards/逐函数预算冻结并 commit 后开始，不以隐藏 version check 消费预算。runner 专用测试从一开始位于 evidence 下，不进入默认 pytest 收集树。

累计执行上限：planner/consumer/pure 投影 helper 合计 1000 次，calc_eye（含 baseline）128 次，histogram/rfft 各 64 次，动态批次 12 次，每批 timeout60s；单输入/FFT 长度≤4096、Eye height≤64、nspui≤32。实际 NumPy 活动及其 C 扩展加载与模型 DLL 分开记录，不称“0数值”。完整 Main/引擎/DFE/decode/PyAMI/grammar/模型/C DLL/COM/coopt/Web/GUI/服务/root pytest/fullsuite 均不执行。

启动与依赖准备成本保留；clone/switch 内部 elapsed `50.4921535999747 s`，整任务 wall/peak RSS UNKNOWN。首次较宽源码/lock 展示被工具截断，已用限定源码范围和目标 wheel 的新只读观察补足，不冒称恢复完整首次输出。全部旧 #30 原件、v1/v2、617339 B 本地原日志、环境及历史失败/费用保留。D1 完成后仅本人 fork 的一个 Draft PR，Refs #10，不关闭 #10；独立两轴自审、固定停写后交 PM fresh review。

## 第10批冻结前状态

01–09 共9批（含5个red）已实际执行，累计pure169、calc_eye15、histogram0、rfft0；NumPy import9。第10批冻结完整6个test methods，预计pure141、calc_eye15、histogram8、rfft5。所有实际source/test/runner及三份新增baseline快照由test-plan绑定，先commit再执行；完整Main/DFE/GUI等仍0。

第10批开始保存actual return-or-exception状态及lossless dtype/shape/C-order数组原bytes（每块≤65536B），不把return event当作正常完成。01–09没有该完整数组观察，不事后补造。静态AST检查单独记在bootstrap/05-binding-static，无NumPy或产品定义执行。一次只读git diff展示因subprocess默认GBK解码失败，工具转录保留该UnicodeDecodeError；后续限定源码读取和UTF-8 bytes decode完成核对，未触发动态批次。
