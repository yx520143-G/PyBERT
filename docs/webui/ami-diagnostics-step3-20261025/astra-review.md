# 第 3 步 F3/F4：Astra 独立审查

2026-10-25。**本轮发现 3 个 P2，均已修复并独立复核；最终剩余 findings 为 0。** 最终候选可形成本地 checkpoint。本结论只覆盖 F3/F4，不包含 F5/F6、真实 AMI 验收或完整参数符合性认证。

## 固定对象与方法

- 工作树：`C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator`；父基线 `23c72c512a3ef2068dfa268b192df12799d42bc7`，审查其工作树 diff 与新增测试。
- PyAMI：基线 `86f9d92de7b7ba8ad9a76d32337acdf2975a8111` → 候选 `207bd902ee1e344c9f9053e8150ced8ac143b14d`，tree `ef9f093881259a8e3f1955524804142094de5593`。
- Spec 为 [最终清单 F3/F4](../fresh-algorithm-review-20261025/final-modification-checklist.md)；Standards 为用户精准修改要求及父子仓库 `CLAUDE.md`。沿用同一 Astra，按 `code-review` 两条线审查，未派生其他审查者。
- 独立读取产品和测试差异，使用真实 `AMIParamConfigurator` 复现边界，静态追查实际 Rx、DFE/CDR、反馈 taps 和绘图输入，然后对冻结候选做一次父／子定向复跑。未运行完整 Main 或真实 DLL。

## Standards

**发现 0 项，剩余 0 项。** 产品代码仅修改父 `models/bert.py` 和子 `ami/model.py`，版本固定与测试配套；未修改 native DFE/CDR/Viterbi 算法、GUI、Web/raw6 reader 或既有证据。删除的 `numpy.typing` 导入只服务于本次移除的历史数组投影。

参数声明、辅助历史和当前 helper 的观察记录保持在原消费位置；F4 复用原错误对象和生命周期，没有引入通用状态框架。已读取保存的定向 mypy 与 Ruff 对照：mypy 通过，Ruff 仅保留基线诊断；本审查未重复运行这两项，不据此宣称全库 lint/type-check 通过。父子差异检查无 whitespace 错误。

## Spec：发现与关闭

**本轮发现 3 项 P2，关闭 3 项，剩余 0 项。** 下列问题都先用实际配置／生产 helper 复现，再由实施者修复；审查者未修改产品或测试。

| Finding | 原行为与影响 | 最终关闭证据 |
|---|---|---|
| P2-1：必需非 Table 叶被误当成辅助 Table | 声明 `gain` 为 Usage Out、Type Float、Format Value，返回 `(rx (gain (1 2)))` 时原候选不抛错，而将 `gain` 标为 unavailable。这放过了必需叶的错误结构。 | `bert.py:136–137` 在投影前拒绝已声明非 Table 叶的 rows/branches；真实 configurator 的 row／branch 负例均通过。缺失、空值及不可转换的必需数值仍失败。 |
| P2-2：合法数字 Tap 与普通 sibling 被误判 mixed | 同组声明数字命名 Tap `1`、`2` 和普通 Float `gain`；合法返回 `(rx (dfe (1 1) (2 2) (gain 3)))` 被 parser 表示为 list＋tuple，原候选因此抛 mixed。 | `bert.py:138–145` 按声明识别数字子叶，允许与普通命名 sibling 共存。正例保留三个独立历史并形成两列 Tap 矩阵；加入未声明 row `(99 9)` 的负例仍拒绝。 |
| P2-3：必需 Table 的空／非叶 payload 绕过检查 | Table 的提前 return 使 `(table)`、`(table (child 2))` 等进入 unavailable，未满足必需输出的叶结构。原 Table 正例还使用了嵌套行的参数串。 | `bert.py:131–133` 拒绝空 payload、child branch 和 nested row。正例改为 wire 形式 `(table 1 2)` → `(table 1 2 3 4)`，允许返回行数变化，仍不投影为浮点 Tap 列。 |

上述 Table 边界依据已重新核对：[IBIS 6.1 第 197–198 页](https://ibis.org/ver6.1/ver6_1.pdf#page=197)要求 Out/InOut Table 至少返回一行，参数串使用 flattened values；[第 202 页](https://ibis.org/ver6.1/ver6_1.pdf#page=202)规定声明的 Out/InOut 参数以叶形式返回。本步没有扩展为完整列数、列类型、范围或所有 Type/Format 的验证器。

## 最终行为核对

| 范围 | 结论 |
|---|---|
| F3 必需输出与辅助投影 | 目标 Rx caller 传入实际声明；root、重复路径、真正混合结构和语法错误继续失败。必需输出与 numeric projection 分开；辅助 path 不完整只使该历史 unavailable，独立完整历史保留，不 padding、截断或造零。合法空 Model_Specific 的既有 parser warning 有精确例外，真正被跳过的声明仍阻止完整必需集合声明。 |
| Tap 分组 | 仅单个父路径下声明为 Type Tap 的整数位置列形成矩阵；多组不拼接、同次列不齐只禁用矩阵，不猜测包含 tap 字样的名称。String／Boolean／Table 不强制转换为浮点 Tap。 |
| 实际下游 | Rx 历史观察保存在 `ami_clock_info.parameter_history`。Native 路径由 `dfe.run_dfe()` 返回 `tap_weightss`、`ui_ests`、`lockeds`；AMI-clock 路径使用实际时钟结果并清空反馈 taps。之后计算 DFE response、保存 adaptation/UI/lock 和绘图读取这些消费者结果。删除的 repeat／zero-pad 历史投影没有作为数值配置输入；非空同 epoch clocks 仍在 F5 边界拒绝。 |
| 字符串与 raw | `parameter_strings` 是 GetWave API 的字符串，可能含既有 NULL／空内容 fallback；没有将它称为 DLL 原始 bytes。PyAMI observation 继续保留各次调用的 `params_raw`。 |
| F4 阶段与安全续跑 | 首 chunk 的普通 C 前准备错误允许调用者修正输入后显式再调用；本次 invocation 已消费部分 chunk、调用进度未知、失败码、非法 clocks、必需输出捕获／解码／组装失败均阻止续跑。没有自动重发 chunk 或重新 Init。取消仍传播并停止。 |
| F4 证据与主因 | 成功返回后 UTF-8／捕获错误标为 host post-return，不能据此断言 DLL 内部已坏。分项捕获保留已取得的 wave／clocks；原生异常或失败码与 capture 异常并存时保留主因及附加错误。`completed_samples` 只计本次 Python invocation 中明确成功的样点，未被用作 F5 跨 probes/Main 的 epoch 账本。 |

## 独立复跑与固定来源

既有环境：Python 3.13.15、NumPy 2.5.1、pytest 9.1.1；通过离线 `uv run --no-project` 执行，未安装依赖。实际导入已核对为本工作树的 `src/pybert/models/bert.py` 与 `PyAMI/src/pyibisami/ami/model.py`，并在运行前校验冻结 SHA。

| 定向范围 | 独立结果 |
|---|---|
| 父：parameter_projection、getwave_params、single_init、clock_traits 四个文件 | **69 passed + 15 subtests passed**，0.73 s，exit 0 |
| 子：clock_lifecycle、response_rng 两个文件 | **83 passed**，0.27 s，exit 0 |

合计 **152 passed + 15 subtests**，包含三个 P2 的最终正反例。生产包装代码和 Python callbacks 被实际执行，真实 AMI DLL 调用为 0。父 gitlink、direct URL 与子 HEAD 对应 `207bd902…`；`uv.lock` 仍为 editable `PyAMI`／10.0.0，未改字节。其他验证记录及复跑命令见 [README](README.md) 与 [validation.log](validation.log)。

未执行真实 AMI、完整 Main、COM、GUI/Web 端到端或远端安装。本地未推送的依赖候选不构成远端可安装或真实模型资格；不推导训练收敛、BER、ABI 容量或物理资源释放。F5/F6 仍未开始。最终没有未关闭的本步 findings。

本审查只新增本文件，未修改产品、测试或旧报告，未执行 Git 写操作。

| 最终文件 | SHA-256 |
|---|---|
| `src/pybert/models/bert.py` | `e99b7b68495581d3da8c55aa7af30136c5960672456f69a02fa45e72b1206e5a` |
| `tests/test_ami_getwave_params.py` | `b70241e27652b4bf1164db9f4cb7ba4bcbb2482c5ebc6df29beb773b8813c50f` |
| `tests/test_ami_parameter_projection.py` | `e8aaf12c3750879451f1f0b3029169f6cb59f422519fe4e183b399141c1ce148` |
| `PyAMI/src/pyibisami/ami/model.py` | `0defb0bfea016a5bf9d29e1b77643cc43c87d2cfb2b2c5a9681b350abd6863ed` |
| `PyAMI/tests/ami/test_clock_lifecycle.py` | `c12ddbacb4ae7309541ab5d058a117c3976943aed41d34b461d3b14e5c8f2380` |
| `pyproject.toml` | `215daf0d03dacbcd94dc3ebef822aa19e1904432d9bd66625734a876e6655248` |
| `uv.lock`（未改） | `cc21cb7dd84c9729a6a2fedfda297af9fb195c0dd7e05a24f89fb7db87be4b12` |
