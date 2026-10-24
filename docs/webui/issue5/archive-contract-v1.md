# #5 存档、legacy 与迁移冻结 v1

实施基线 `f1d0ea80f9db8ab31e25963496875a44fe4a19d9`。本冻结先于实现和本票新主计算；存档验证优先只读复用 #2/#3/#4 原件。原生计算、单位、窗口与容差继承原冻结；存档精确比较不使用浮点容差。

1. `.pybert_run` 为 ZIP，恰含 `manifest.json`、`arrays.npz`。外层 `format=pybert-web-run`、`archive_schema=1`、创建时间、保存工具 SHA、原文件校验值、逐数组 dtype.str/shape/nbytes/C-order 字节 SHA256，以及完整 primitive `run` manifest。NPZ 原文件逐字节复制，不重新计算/降精度/对象序列化。读数组一律 `allow_pickle=False`；只允许有限 bool/int/uint/float/complex。
2. 原 manifest 内 requested/effective 输入、runtime extensions、资源原名称/内容 hash/有序身份、版本、全部 raw/axes/masks/indices、display、producer/point/kind/unit/window/clock/noise/availability、summary/warnings/logs/cancellation/子功能计划完整归档。保存时间与原运行时间分开；旧文件缺失信息标 unknown，不事后冒充已知。保存 provenance 是另一个对象。资源 bytes 不默认附带；路径仅为定位提示。
3. archive v1 原样读取；未知外层版本/必需特性拒绝且不替换现有状态。raw schema 2/3/4 保留原 manifest，不补算缺项；图缺失就不可用。未知命名扩展保留，恢复输入执行前仍通过现有完整 normalize/执行 gate；未知必需输入拒绝。打开不加载模型/资源或启动 worker。
4. 外部记录独立 `record_id`，保留原 `run_id`。参考与当前两次临时成功 run 分开。参考最多 4 条，总解包数组 1 GiB；每文件最多 256 MiB、解包数组最多 768 MiB。预算超出明确拒绝并列出移除方式，不静默淘汰参考。临时成功缓存维持两条并显示其字节与淘汰语义。
5. 输入恢复是显式动作：使用原 requested 输入和 runtime 扩展，不使用最终 AGC/DFE 状态。资源需用户显式重新绑定且逐 field/index/hash 校核；缺失/变化拒绝 Run。查看保存图不依赖原资源。
6. legacy `.pybert_data` 只有用户显式选择并勾选可信 pickle 才进入服务端分支，验证 exact PyBertData/ArrayPlotData、原 `_item_names` 23项、有限数值一维数组；缺项和零维 None 明确 absent。未知项/对象/版本不伪造原始物理数据。缺轴只显示 sample index/frequency-bin index 诊断，不借当前 run 轴，禁止混入物理图叠加。
7. legacy 导出复用原 PyBertData 类及 producer 的实际 plotdata 语义；先检验23项。`tx_out` 原 producer 未生成时拒绝并返回损失清单，不能填零/用 rx_in 冒名。可导出的完整子集保持原读取格式，独立 sidecar 保存轴/来源/单位和缺失能力。完整保存使用 Web archive。
8. 草稿 schema v2 使用稳定字段 ID 与完整 adapter/native/prototype SHA。PR7 schema1 显式按字段迁移，未知/不合法字段单列保留并禁止默默执行；catalog 顺序不作为 schema。非法 JSON/读取/写入失败有独立草稿状态。localStorage 只存轻量草稿和选择，不存数组。
9. 导入先在独立暂存目录校验全部，再发布记录；生成文件临时写入并 replace。失败、未知版本、预算拒绝均不变更草稿/已选 run/参考。下载只报告交付浏览器；服务重启临时结果不可用，已保存 archive 可重新打开。重连按后端 task ID/退出状态继续，不把取消请求当退出。

验证顺序：旧真实 run 精确往返 → 损坏/未知版本/预算/legacy 类型与缺轴/输入资源 gate → UI 比较/文件原子语义 → 冻结后 Chrome 1280×720 新 Run 及原 raw 对照 → GUI/CLI/MCP 受影响检查。所有早期尝试、失败和新增计算成本保留。#4默认COM仍 BLOCKED_BUDGET/NOT_EXECUTED，#8/#9/#10与父#1不在本票完成范围。
