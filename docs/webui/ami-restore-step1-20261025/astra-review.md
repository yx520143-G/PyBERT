# AMI 原流程恢复第 1 步：Astra 独立审查

2026-10-25。审查范围为 R1/R2，以及恢复后必需的来源标签和合法空 clocks 分流。结论：**本步未发现需要修复的缺陷，可以形成独立本地 checkpoint。** 此结论只适用于下面固定的候选，不代表 F1–F6 已完成，也不解除真实 AMI 验收的暂缓状态。

## 审查对象与方法

- 工作树：`C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator`。
- 分支：`codex/restore-ami-single-init`；base/HEAD：`ab36b656a61cb6866da98105d72f6cacfb118031`；tree：`8412b639f4dd6f51c227e19d649a333fbad9d6a2`。
- 检查该固定 base 到当前工作树的三个产品文件和已跟踪测试差异，另完整读取新增测试。候选尚未提交，因此没有把空的提交间 diff 当作审查对象。
- Spec 为先前的 [最终修改清单](../fresh-algorithm-review-20261025/final-modification-checklist.md) 与 [原流程恢复方案](../fresh-algorithm-review-20261025/restore-original-ami-flow-plan.md)。旧文档中的“尚未实施”是当时状态；本轮实施授权与本候选是当前审查对象。
- Standards 为用户的精准修改／简洁／验证要求和仓库 `CLAUDE.md`。按 `code-review` 技能的 Standards、Spec 两条线独立判断；本次未派生其他审查者。
- 静态追查固定 PyAMI 的 initializer、Init/GetWave/Close 包装、两次 response probes，以及现有 D1 caller、D2 native 分支和 raw6 reader。未修改产品、测试、依赖或历史报告，未执行 Git 写操作；本审查只新增本文件。

## Standards

**可执行 findings：0。**

产品改动严格限于三个已计划文件。现存 `get_responses()`、initializer、convolution 和分块算法继续复用，没有另造信号处理公式。删除 C1 分支、私有 selector 及仅为该分支服务的 helper，保留共享 initializer；未顺带重构其他路径。双错误对象仅保留 `primary_error` 和 `cleanup_error`，未引入额外状态框架。

新增测试使用真正的 PyAMI 包装代码和 Python `FakeDLL`，通过调用、输入、chunk 和 handle 状态验证宿主合同；caller 测试执行实际目标分支的两条 AST 语句。它们不声称替身等同真实 DLL。`git diff --check` 无错误；Ruff/flake8 未运行，现成环境缺少这两项工具，未安装依赖，因此本结论不包含完整 lint 通过声明。

## Spec

**可执行 findings：0。**

| 检查点 | 审查结果与证据 |
|---|---|
| 单次 Init 与原适应历程 | `utility/ibisami.py:160–193` 只构造一个 initializer 和模型，执行一次 `initialize()`，随后原 `get_responses(bits_per_call=40)` 与 Main `getWave()` 使用同一对象。固定 PyAMI 的 `model.py:725–743` 继续生成一个 `u`，第二 probe 为 `convolve(u, chnl_imp)[:len(u)]`。中间没有 Close、重新 Init 或状态迁移。 |
| 原输入和 B 语义 | 独立复跑确认 Ignore_Bits=23、4 samples/UI 时两个 probe 各 172 samples，C chunks 为 160+12；Main 开始前替身累计处理 344 samples。Main 166 samples，B=0 继承 40，得到 160+6；B=7 得到 28×5+26。输入、尾块及 FEXT 行的既有缩放、padding／截断均保留。 |
| 取消自动 seed 接线 | `models/bert.py:453–457` 已移除 `_probe_seed=self.seed`。代码搜索未发现残留 selector/helper 调用。固定 PyAMI 可选 `rng=` API 未改；默认仍是无参数 `default_rng()`，测试捕获其调用并确认全局 RNG 状态未变。Main 的既有全局 seed 政策未改。 |
| 返回值与最终清理 | `utility/ibisami.py:193–211` 在 Close 前复制返回 tuple，并在整个初始化、probe、Main、复制过程外层执行 `finally`。原始异常单独发生时原样传播；同时出现 cleanup 异常时分别保留两者，并以原始异常为 cause。固定 PyAMI 在 Close 前放弃 handle 所有权，重复 Close 是 no-op。 |
| 失败与中断 | 替身分别覆盖 Init、第一 probe、第二 probe、Main 失败、仅 cleanup 异常、双异常、复制异常和中断。未出现重试、第二模型或重新 Init。Close 前副本测试通过破坏原缓冲验证返回数组独立性。Init-only 与 FEXT 共享路径的专项测试通过。 |
| 来源与空 clocks | `models/bert.py:456` 使用 `same_init_after_probes`；`ami_clock.py:11` 不再把 invocation 标识称为 fresh Main/Init epoch。`ami_clock.py:53–59` 先允许合法空 clocks 进入 Native，再对非空同 epoch clocks 抛出 `unsupported_origin_mapping`。普通 dict 和真实 Traits Dict 的测试均通过；非空未映射 clocks 没有被消费或静默回退。 |
| D1→D2 fallback 可达性 | 静态追踪 `models/bert.py:586–590,649–672`：合法空 clocks 设置 `use_native=True` 后走既有 Native DFE/CDR 分支。`web/clocks.py:59–66` 在 AMI fresh-origin guard 之前处理并返回合法 Native 结果，因此新来源标签本身不会阻断这条 fallback。完整 Main 和 Web 发布未运行，此处是控制流审查结论。 |
| 已有保护与历史合同 | PyAMI 文件内容与固定 HEAD 一致，status、prefix/sentinel、NaN 预填、absolute/跨调用严格单调和不可安全续跑保护未改。参数历史回归测试通过；D2/raw6 reader 无差异，仍严格要求其既有 C1 来源及完整性合同。旧七份报告未改。 |

## 独立验证

本审查在现有离线环境独立运行以下三个文件，结果为 **40 passed、15 subtests passed、35 warnings，exit 0**。pytest 报告用时 0.60 s；warnings 为既有依赖弃用提示。复跑方式见同目录 [实施记录](README.md)；审查额外输出并核对了实际模块路径。

- `tests/test_ami_single_init.py`
- `tests/test_ami_clock_traits.py`
- `tests/test_ami_getwave_params.py`（未修改的回归测试，包括 750 条历史返回字符串）

运行身份：Python 3.13.15、NumPy 2.5.1、pytest 9.1.1；PyBERT 实际导入本工作树 `src/pybert/utility/ibisami.py`，PyAMI 实际导入 `E:/serial-bus-simulator-dependencies/pybert-issue30-probe-main/PyAMI/src/pyibisami/ami/model.py`。PyAMI HEAD 为 `d6d1f7fe7e58536546a1cfb9430c750cc2cb103e`，该文件 SHA-256 为 `0e5a18c6d3402f10e2fb85af147f6ee961e5c67ae21fec555b1842f51a870442`，与 HEAD 无差异。

## 留待后续的边界

以下都是最终清单已明确拆开的工作，未计入本步 findings：F1 Close 返回状态、F2 参数输出指针初始化、F3 参数历史投影限制、F4 宿主诊断与模型失败分层、F5 同 epoch clock origin 映射、F6 各项分析与发布可用性。

本步 cleanup 测试覆盖的是 Python 调用异常；它没有证明 Close 的非成功返回码会被识别，后者仍为 F1。非空同 epoch clocks 在请求消费时明确不支持，需 F5 才能建立实际样本账和映射。不能把该暂时限制解释为已恢复完整 AMI clocks 功能。

未加载真实 AMI DLL，未运行完整 Main、COM、GUI/Web 端到端或真实模型数值对照。替身证明宿主调用和状态传递结构，不能证明真实模型收敛、隐藏全局状态、缓冲容量、物理资源释放、BER 或模型资格；这些限制不阻止最终清单已允许独立完成的 R1/R2 结构步骤。

## 固定候选 SHA-256

| 文件 | SHA-256 |
|---|---|
| `src/pybert/utility/ibisami.py` | `6c919116d4e8d1736e53de7e1f573f003ba5c547aa46f69b9133998b08307402` |
| `src/pybert/models/bert.py` | `f56b4bf73853fd50d79c049053d66b839656a4d2ef899ba11c924bd162371e2c` |
| `src/pybert/utility/ami_clock.py` | `93dbda66f8dc8887847fb5062ff22c8b30fcee145b7213f059b437fe955064f6` |
| `tests/test_ami_single_init.py` | `8edc3ca11efe1af7bceca2a87a8b3dafa318e08ff1b43fc0a7723eac52c04cf9` |
| `tests/test_ami_clock_traits.py` | `f53474b20c2693c7144499d757329d4612d3912c121cbd375d89363e2c5ef49b` |
