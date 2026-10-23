# #13：原生 8/12-port lane / FEXT 端口修复

本交付等待 PM 固定版本审阅与集成；owner 不合并 PR、不关闭 #13/#4。base 为已验收 master `9a33d08458aa00782e90169c699857b8b19455a2`，物理修复提交 `b87c80ce2f8c32b0394651d0e7a11067c821af61`；后续仅修审计工具路径分隔符、补材料。

`import_freq` 原来把 plain lane 从 interleaved `(TX+, RX+, TX−, RX−)` 重排为 grouped，却继续调用使用 interleaved 配对的 `sdd_21`。`import_fext` 也把 grouped 的四导体传给该 helper，因而会把同 lane 的耦合/反射混进所谓跨 lane FEXT。

修复只改变这两个 caller 的端口选择及其相关说明。`se2mm/sdd_21` 公式、4-port、VITA、插值、端接、卷积、噪声、EQ、COM 均未改。源边界与原件适用性见 [source-applicability](evidence/source-applicability.json)。本票没有时域主仿真、COM 或 Chrome 运行，不代替 #4 的产品验收。

## 端口合同

所有编号以下均为 0-based。

| 路径 | 实际选择 |
| --- | --- |
| Plain lane k，renumber=false | 原四端口 `[4k,4k+1,4k+2,4k+3]`；输入差分 pair `(4k,4k+2)`，输出 `(4k+1,4k+3)` |
| renumber=true | 只在每个 lane 自身完整 through 四端口调用既有 `thru_is_1to3`，必要时交换中间两端口；仍只支持原有两种编号 |
| Aggressor j → victim k FEXT | 用已识别的各 lane 导体身份，按 `[aggressor TX+, victim RX+, aggressor TX−, victim RX−]` 组装；默认即 `[4j,4k+1,4j+2,4k+3]` |
| FEXT 编号检测 | 从 source lane 自身 through 得到身份；跨 lane 子网络不调用 through 启发式 |
| Aggressor 顺序 | lane 递增，跳过 victim；非法 victim、非 multi-lane 返回/报错边界保留 |

renumber=false 始终使用字面编号。grouped 文件若未选择 renumber，不保证符合其物理 pair；测试明确检查该字面语义，没有偷偷开启自动重排。

## 验证与真实资源

| 证据 | 结果与适用范围 |
| --- | --- |
| [旧基线 red](evidence/red-baseline.xml) | 实际 Touchstone → `import_freq/import_fext`；26 tests，19 failures、0 errors、0 skipped，7项本就通过；原失败保留 |
| [同一物理 oracle green](evidence/green-physical.xml) | 26 passed；2/3-lane、所有 victim/aggressor、默认/grouped/mixed 编号、复数完整 2×2 S、成对 z0、严格零隔离、符号/相位及顺序 |
| [相关回归](evidence/green-regression.xml) | 49 passed；上述26 + 更新后的10项原 multi-lane + 4项独立 4-port + 9项原 VITA；没有跳过 |
| [真实 M 修复前](evidence/real-M-before.json) / [修复后](evidence/real-M-after.json) | 相同原 bytes，两个 victim 的完整复数 thru/FEXT 均匹配独立物理差分公式；跨 lane 块清零后 native FEXT 严格为零 |
| [源码与证据适用性](evidence/source-applicability.json) | 未改函数及 4-port/VITA 分支 AST 相等；原 red 测试/诊断源码快照匹配执行 hash，格式化后 AST 相等；实际生产源码匹配 after 诊断 hash |

独立 fixture 根据真实导体的 near/far 身份构造两个同极性通路、反射及已知有符号/相位的跨 lane 耦合。期望值按 `+1/√2、−1/√2` 差分波激励与测量得到，未调用 importer 或 `sdd_21` 生成。每端两导体用相同参考阻抗，各端/lane 的阻抗不同，因而 z0 检查能区分错误 pair。

原 `test_multilane_sparam` 为适配错误重排，在单个 `S[-B,+A]` 写 `−2*T`；现改为两条对应导体的正常传输，原期望通道不换，并把幅度检查增强为完整复数矩阵。VITA 的固定偏移和既有测试保持原样，其固定元素回归不外推为本票的物理 VITA 资格。

真实资源为既有 SignalIntegrity `TwoLaneModel.s8p`，SHA256 `0f6cbb032432eadc8c1bee4f382ef25e3c06fe0718fae07fc835e495067d5abf`，330007 bytes，0–80GHz；来源与 GPL local-use 信息记录在报告。它是现有物理模型，不称为测量硬件。

| `max |S21|` | Victim 0 | Victim 1 |
| --- | ---: | ---: |
| 旧 victim thru | 0.0188637464 | 0.1488355607 |
| 修复后 / 独立物理 thru | 0.9866371803 | 0.9852244635 |
| 旧 FEXT | 0.0865081433 | 0.0795863114 |
| 修复后 / 独立物理 FEXT | 0.0375248047 | 0.0487050799 |
| 旧代码在跨 lane 全清零后仍返回 FEXT | 0.0863737599 | 0.0794775499 |
| 修复后跨 lane 全清零 | 0（精确） | 0（精确） |

表中最大值仅帮助解释差异；验收比较的是全部频点的复数矩阵和 z0。清零副本只用于隔离诊断，不替换 #4 冻结资源。原件、清零诊断副本、before/after raw NPZ 均保留在本 worktree ignored `local/`，逐文件 hash/长度见 JSON。

## 成本、工具与后续

测试 JUnit 记录的执行时间分别为 red 1.248s、green 0.641s、49项回归 0.994s，不包含 Python 启动和全部调查时间。原生库的现有 warnings 保留，未把 warnings 数量写成零。生产文件及三个新验证文件的 `ruff --select E4,E7,E9,F` 与 compileall 通过；没有声称全仓库风格/完整仿真套件通过。

复现：`uv run --extra web pytest tests/test_multilane_physical.py tests/test_multilane_sparam.py tests/test_singlelane_physical.py tests/test_vita_sparam.py`。`tools/diagnose_native_multilane.py` 读取原 M，并拒绝覆盖已有 before/after 报告；`tools/audit_native_multilane.py` 同样保留原审计。最初审计因 Windows 路径分隔符 KeyError 停止，见 [audit-attempt-v1-error](evidence/audit-attempt-v1-error.json)，修复后没有追加数值重算。

#4 原 WIP HEAD 为 `8a18333aaeafa59c5fdac156397cac6d709457a9`；其11个 case、原坏基线诊断、失败、4份 ignored NPZ（179017472 bytes）和 local 资源完整保留。四个 M 主仿真 case 仍为 `NATIVE_PORT_MAPPING_BLOCKED / NOT_EXECUTED`，等待本票 PM 合并后以追加 corrected-native 版本冻结再执行；默认 COM 仍单独为 `BLOCKED_BUDGET / NOT_EXECUTED`。本交付不把 helper 回归记成 #4 已通过。
