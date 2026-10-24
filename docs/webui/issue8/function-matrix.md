# #8 功能落点与边界

| 原 GUI 功能 | 落点 / 生产者 | 验证 |
| --- | --- | --- |
| Tx tuner enabled/min/max/step、cursor constraint | Tx 节点 + Optimizer；独立于实际 `tx_taps`，原枚举过滤 cursor | 冻结顺序 / 数值 / Chrome grid |
| CTLE enable/fp/BW/min/max/step/selected boost | CTLE 节点 + Optimizer；GHz/dB，候选输出只读 | 两种评分 / 节点检查 |
| RxFFE 100槽/Ntaps/Npre/min/max/step | RxFFE 节点；enable 由原 observer 映射、只读；原 grid/MMSE | Chrome 100槽/只读；契约完整载入 |
| DFE enabled/min/max/Enable/Disable All | DFE 节点；普通 Run 共用，优化要求连续前缀 | gap拒绝 / 既有批量控件 |
| tuner value / selected boost | 所选获选 opt ID 的只读输出，实际 EQ 与训练状态另列 | Native handler 字段测试 / Chrome |
| Use MMSE / RLM | Optimizer；RLM可从 Source 反查，仅 PAM4 MMSE可编辑 | 两RLM MMSE输入hash、普通Run原数组exact |
| Tune / Abort | Native EQ 工作区，共用 fresh-spawn worker；`CancelBridge(OptThread)` 不 start | 互斥 / 原检查点 / requested-observed-exit |
| Candidate/channel pulse | 每个数组自己的实际 ns 轴；cursor 两 ns 值；clocks 是辅助显示线 | 全数组 exact / 不截断 / 视图不 Run |
| Candidate FOM/ID/weights | 原 `coopt` 每外层候选及首个严格更优 winner；dB复用safe_log10 | 顺序/ID/hash精确；哨兵/非有限/空winner拒绝 |
| Use EQ | 冲突差异→明确应用；调用原 handler 的字段集合，保留无关草稿 | 预览取消/确认、DFE不写初值、新Run |
| Reset EQ | 原 handler 同步实际EQ初值/enable；范围、DFE、Run保留 | 契约exact / Chrome / YAML扩展 |
| 优化保存恢复 | primitive JSON+NPZ `.pybert_opt`；独立于run archive与当前草稿 | 无损往返/版本/预算/失败原子性 |
| 原 GUI 反查与节点跳入 | 原稳定 field ID；Tx/CTLE/RxFFE/DFE/Source/Optimizer均可进入候选工作区 | 最终 Chrome 节点检查 |
| AMI trial/动态参数/TPE | #10 未接入，Native不能冒充AMI搜索 | 有效AMI输入明确拒绝 |

候选从不自动产生真实 Run/BER/CDR/COM；#1 父矩阵的 Viterbi、AMI 和 #16 仍由对应后续票负责。
