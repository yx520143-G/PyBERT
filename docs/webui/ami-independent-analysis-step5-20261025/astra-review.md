# 第 5 步 F6：Astra 两轴最终审查

审查日期：2026-10-25。结论：**Standards 0 项，Spec 0 项；本轮新增发现 0、关闭 0、剩余 0。** 固定候选的独立定向验证为 **151 tests + 15 subtests passed，12.67 秒，退出码 0**。该结论覆盖宿主软件的同 epoch NRZ 采样、独立分析状态和新保存合同；真实 AMI 模型验收没有执行，`model_qualification` 仍为 `UNKNOWN`。

## 范围与固定点

- 工作树：`C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator`；父基线 HEAD 为 `27a75c5368c04034ba5b4f24cc70714e8895361b`，tree 为 `d05b50fa671b45979fd79611d66a52e0725bd4f6`。本报告审查相对此基线的未提交候选，包含显式列出的新增文件，不把空的 commit-to-commit diff 当作审查内容。
- PyAMI 保持 `dfae46033f490c9d19f2684454b6fe9bd90d9a72`，tree 为 `ea0b79aaef18cd436b92d139741842a91b63fa90`，子工作树干净。
- Spec 为[最终修改清单 F6](../fresh-algorithm-review-20261025/final-modification-checklist.md)及本步已确认的[软件合同](README.md)：分别表达 Main、采样、BER、Eye、histogram、spectrum；保留原 W、W−2 和固定 FFT 窗口；失败或取消仍保留 partial；旧 reader 不放宽。
- Standards 为用户的精准修改、高内聚低耦合、UTF-8 without BOM 要求，以及父仓 `CLAUDE.md` 的复用原生算法与运行约定。沿用同一 Astra，按 `code-review` 技能分别审查 Standards / Spec；用户明确限制单一审查者，因此未派生 agent。
- 审查者只写本报告，未修改产品、测试、旧报告或 Git 状态，未安装依赖、启动真实 DLL、COM、优化搜索或重矩阵，也未操作浏览器。

## Standards

**未发现需要修改的标准违例或可执行的结构问题。**

新 `web/clock_v3.py` 集中保存和校验新合同；`clocks.py`、`archive.py`、`viterbi.py` 按显式版本接入，旧 version 2 / raw6 仍沿原严格路径。底层 epoch 映射和窗口选择复用 `utility/ami_clock.py`，Web 不另写采样、BER、Eye 或频谱物理模型。重复检查用于 live 与存档的不同信任边界，未发现需要扩大本步范围的抽象或重构。

改动与 F6 的生产、consumer、持久化及显示路径对应。Python 和 native GUI 状态/辅助绘图有窄修改；Native DFE/CDR/Viterbi 算法、PyAMI、依赖声明和 `uv.lock` 未修改。新英文提示保留 unavailable / UNKNOWN 语义。格式检查没有发现新问题；实施方保存的 Ruff 差分为当前 49 项、基线 49 项、零新增，未将既有告警算作本步修复。

## Spec

**未发现固定候选遗漏、越界或实现错误；本轮没有需要关闭的新增发现。** 代码审查与定向测试分别提供以下证据，未用测试全绿代替来源和发布条件检查。

| 合同 | 审查结果 |
|---|---|
| 实际路径与资格 | `bert.py:247` 为实际 Rx GetWave 时钟路径选择 producer 3；`ami_clock.py:136` 起先检查 same-Init 来源和完整 F5 receipt。合法 NRZ profile 可进行软件采样，资格保持 `UNKNOWN`。缺失 receipt 即使 clocks 为空也拒绝；PAM4 未声明 profile、AMI+Viterbi 仍不开放。 |
| 空时钟与窗口外时钟 | 只有整个 epoch 的原始 clocks 全空才使用原 Native fallback。非空 clocks 即使无 in-record tick，也保留 AMI 路径与 Main，采样 count 为 0 / unavailable；没有伪造 Native 锁定观测或补样点。probe 边界 tick 也按其原来源参与映射。 |
| 浮点坐标 | `epoch_analysis_bounds` / `analysis_sample_mask` 贯穿 plan、consume、live 和 stored 校验。精确 Main grid timestamp 对应该样点的 epoch 坐标，非网格边界采用一次舍入的前置时长加原边界；readiness 与量化延迟复用 F5 epoch 依据。保存规则与 bounds，不用 local 展示差值再次决定 ceil。 |
| 消费与失败 | `consume_ami_clocks` 保存实际 sample / decision / bit，循环完成与完整分析覆盖分离。真实判决异常、取消、来源损坏仍失败；已完成的 prefix 保留为 diagnostic partial，正常 manifest / arrays 不发布。Main completion 在实际主流程末尾设置。 |
| BER | 覆盖不足时不调用 `calc_ber`，内部 Int 使用 −1、Web count 使用 null 并附原因，清空上一运行的 auto_corr / errors。实际 bits 保留，但不伪造参考、对齐或误码数组。覆盖足够时继续使用原 W、最后 W 个决策与原 `calc_ber`。 |
| Eye | native helper 与两个 Web consumer 依据各自 crop 和实际样点独立判断。保留 W−2（至少 1）条完整 trace 及每条 2 UI 宽度；不足显示 unavailable，不把少量 trace 当作满足既定门槛。Web 对不可用电压尺度先判 unavailable；实际计算异常仍抛出。 |
| 周期图 | histogram 仅使用冻结窗口内已知 period，每个 grid sample 一票，保留 100 bins。spectrum 继续使用原固定 slice，未知 period 导致自身 unavailable，不缩窗、不挑片段、不填补缺口。单点和无 in-record tick 可合法保留全未知 period mask。 |
| 新保存合同 | raw7、`ami-clock-independent-v3`、clock contract3、producer3、same-Init NRZ 和 decoding3 必须匹配。`clock_v3.validate_info` / `validate_publication` 重新核对来源账、epoch 映射、实际 waveform 样点、决策、bits、mask、固定窗口、索引及各项状态；模型资格不能改成 PASS。 |
| 字节与历史档 | 原始 ticks、调用来源及实际采样数据存为 primitive NPZ。读回不运行模型、slicer、Eye、histogram 或 FFT；原 manifest / NPZ 字节及每个数组的 dtype / shape / bytes / hash 保持一致。NaN 例外仍仅属于有严格 bool mask 的 `ui_ests`。raw6 completeness=false 仍拒绝，未降级成 raw4 或重标历史失败。 |
| 产品显示 | summary、比较与 trellis 读取显式 BER availability / reason，未把 null / −1 显示成零误码。Run overview 单独列出各分析状态和 UNKNOWN 资格。native CDR 绕过时空 lock 数据保持 unavailable。 |

候选的窗口回归保留 `N_pre=344, ts=.1, Main=166, tick=50.7, UI=.4` 的末样点 index 165；其 epoch target 与 sample 均为 `50.900000000000006`，不会因独立舍入的 Main stop 转换而再次丢失。首窗口边界、readiness 和保存读回也有定向回归。另以生产 helper 对四种 ts、四种 N_pre、每组 999 个网格值及两侧 `nextafter` 检查转换单调性，未复现边界顺序反转；这是一项有限浮点检查，并非所有浮点输入的证明。

## 独立验证与证据边界

审查者执行且仅执行一轮最终定向软件测试：

```text
tests/test_ami_single_init.py
tests/test_ami_getwave_params.py
tests/test_ami_parameter_projection.py
tests/test_ami_clock_origin.py
tests/test_ami_clock_traits.py
tests/test_ami_partial_analysis.py
tests/test_ami_partial_main.py
tests/test_ami_partial_legacy.py
151 passed, 15 subtests passed in 12.67s
exit code: 0
```

使用既有 `uv run --no-project`、资源环境 Python 3.13.15、NumPy 2.5.1、pytest 9.1.1；`PYTHONPATH` 指向本工作树 `src`、`PyAMI/src` 和既有资源工作树 `PyChOpMarg/src`，关闭 bytecode / pytest cache，Qt 使用 offscreen。测试前实际导入 `pybert.models.bert`、`pybert.utility.ami_clock`、`pybert.web.clock_v3`、`pyibisami.ami.model`，断言其文件路径与 SHA；没有误用已安装副本。测试前后 15 个候选文件 SHA 均匹配。

新集成用例运行真实 `my_run_simulation → collect → archive.save/load` 软件链，AMI helper 是明确标识的合成替身，规模为 2048 NRZ bits、1024 eye bits、8 samples/UI、固定 seed，COM 关闭。覆盖 full、BER 不足但 histogram 可用、BER 可用但 FFT 有缺口、单点、全 future、全空 Native fallback、判决异常、取消、重复运行清旧 BER、GUI 辅助绘图和八类存档矛盾拒绝。历史 D2 mask / producer / archive 用例由保留文件直接调用，没有改历史 fixture。

保存读回对原 manifest / NPZ 文件字节和逐数组 identity 作精确比较；读回阶段将 Main 替换为失败哨兵，验证没有再次仿真。未更改的 PyAMI 子仓测试不在本轮重复执行，前一步结果不累加为本轮通过数。

实施方的[最终测试日志](final-validation.log)另记录 151 tests + 15 subtests、35 个既有 warnings、13.57 秒；此前[日志](validation.log)中一次文件名错误导致 0 项收集，没有计为通过。审查者的独立执行先导入模块核对身份，其 pytest 汇总未重复列出这些导入告警；不把该差异解释为告警修复。[Ruff 差分](lint-delta.json)、JavaScript syntax 和浏览器检查属于实施方证据；审查者另复核 `git diff --check`。四个合成状态的[浏览器截图](browser-ber-unavailable.png)、[histogram 截图](browser-histogram.png)及[比较视图文本](browser-comparison.txt)不构成真实 AMI 数值验收。

## 最终候选身份

[candidate-sha256.json](candidate-sha256.json) 的 SHA-256 为 `14c6c0cc03fad1ce27d5cf7416dff72adfb643e4633ab089196439267687efd5`。本报告对应以下 15 个产品 / 测试文件；本步证据目录不属于产品候选数量。

| 文件 | SHA-256 |
|---|---|
| `src/pybert/models/bert.py` | `3fc527ea158d9a2967b27eee094b0451f648062d8edc2620fe7b84aeb84249bb` |
| `src/pybert/pybert.py` | `33ac17329b7714255c0fd8dfb0b086a0e3a7e02706a3f31d20131fdce4f1d7b7` |
| `src/pybert/utility/ami_clock.py` | `327d12a6a9733c1c7ed66fbb20537294b86e4c8779b86ba81d66b6307b7e2bff` |
| `src/pybert/web/ami.py` | `a93e690674218f5c7bd7731ea35320eea71f60ecb8dfdab926623145304a32f2` |
| `src/pybert/web/analysis.py` | `35bfcd9380e3b8dd02b2a8e788bdfa3f91d71f936cd07ed4534e6f23bff86de4` |
| `src/pybert/web/archive.py` | `f4ad3b110ea4e63b8817a75aaa2f23bcf4368913b4fb820e63117867027e72a2` |
| `src/pybert/web/clocks.py` | `035d16584382f50bcfbe126722df07909500c4f1e8c2652b5b54c1a85f16e43f` |
| `src/pybert/web/clock_v3.py` | `3c5aca06b26f867b1dd5159535495f2e368381e66b55667ebd33e1e71ea98229` |
| `src/pybert/web/data.py` | `e94a69624876d81d36730f6cb5e5fa89385e19fcec841d2f00d152335457762d` |
| `src/pybert/web/viterbi.py` | `fd98f24562e8370d4f39a624a025c7e46d66b974e7bb7d9def37b3877db5f1ed` |
| `src/pybert/web/static/viterbi.js` | `4bade268606c84b851af5f11a8da02458b0b8fdc9f397c8a2fe1d1150f529b96` |
| `src/pybert/web/static/workbench.js` | `7731cea67b9a58c618e9f6fe1a25ea53794415c17890f2f7cefd8875eece7cc3` |
| `tests/test_ami_partial_analysis.py` | `0f2fda6c78b986ac368207b88eca99b8af1ef0d82096027cd4dda2fc413cab3f` |
| `tests/test_ami_partial_main.py` | `394406e956d1930e3c6772456c3b4124625b9f05d0ea1acad6b409bfc4da4ab5` |
| `tests/test_ami_partial_legacy.py` | `026acc27cc92471cb87d56d0669462eb293bfec1cc416e97c0cc216496d8f341` |

另核对 `pyproject.toml` 为 `df809204a0bd2511b721ab288d09179b84cfbeef5c47b560d1c1669bf65e702e`、`uv.lock` 为 `cc21cb7dd84c9729a6a2fedfda297af9fb195c0dd7e05a24f89fb7db87be4b12`，与前步一致；PyAMI `model.py` 为 `9afc229c6d4218d8fa5c6699489a1f8947ac3dad62313604744e36d0604ca8c9`。原七份 `fresh-algorithm-review-20261025` 文件和前四步 `astra-review.md` 全部与既有固定 SHA 匹配。

本步可按该固定候选完成本地交付。审查结束并归还实现所有权；真实模型数值正确性、模型/profile 资格和硬件资格仍未由本轮验证建立。

两轴结论：Standards 0 项；Spec 0 项；本轮新增 0、关闭 0、剩余 0。
