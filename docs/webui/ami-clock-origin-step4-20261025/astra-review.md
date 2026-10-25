# 第 4 步 F5：Astra 独立审查

审查日期：2026-10-25。结论：**Standards 未发现待修问题；Spec 发现 1 个 P2，已由实现方修复并独立复核关闭，当前剩余 0 项。** 最终定向验证共 **203 tests + 15 subtests** 通过。本结论覆盖实际调用账与时钟映射观察；同 epoch timed consumption、F6 发布合同及真实 AMI 资格仍未开放。

## 范围和固定来源

- 父仓 worktree：`C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator`，分支 `codex/restore-ami-single-init`。审查 base / 当时 HEAD 为 `8cd173b81484554a21293e838d49b1b1abe4038e`，base tree 为 `a4db62cbb893b98dcceb19a5da3914da0aa7245c`。父候选尚未提交，因此审查采用相对此固定 base 的工作区差异，并单独读取新增测试；不能用空的三点 HEAD 差异代表候选。
- PyAMI base：`207bd902ee1e344c9f9053e8150ced8ac143b14d`；本地候选提交：`dfae46033f490c9d19f2684454b6fe9bd90d9a72`，tree：`ea0b79aaef18cd436b92d139741842a91b63fa90`，子仓工作区干净。
- Spec 为 [最终修改清单 F5 及坐标边界](../fresh-algorithm-review-20261025/final-modification-checklist.md)，并采用用户本步明确接受的“映射观察，F6 与真实 AMI 暂缓”范围。Standards 为用户精准修改要求及父子仓 `CLAUDE.md`。沿用同一 Astra，依 `code-review` 技能分别审查两条轴，未派生其他审查者。
- 独立读取产品差异、测试及生产 caller/consumer。审查者仅新增本报告，未修改产品、测试、依赖或旧报告，未执行 Git 写操作，未运行真实 DLL、完整 Main、GUI、Web 或 COM。

## Standards

**发现 0 项，未解决 0 项。**

变更集中在已有责任边界：PyAMI 保存实际 Init/GetWave 坐标账；父 wrapper 收集阶段快照；`ami_clock.py` 验证并映射；实际 Rx caller 接入旁路记录。六元组返回 API 保持不变，新增参数为 keyword-only。没有为本步建立通用事件框架，也没有重构相邻算法。

浮点修复的 `Fraction` 仅计算一次标量 readiness 阈值，逐 tick 仍为 float64；它处理本次已复现的边界问题，未添加外部依赖。子仓修改仅 `model.py` 与 lifecycle 测试；父仓生产修改仅三个既有文件，附对应测试、gitlink / 直接 URL pin 和本步记录。GUI、Web、其余依赖和 `uv.lock` 未修改。文本保持 UTF-8 without BOM。

读取实现方的检查记录：父 21、子 29 个 Ruff 诊断与各自 base 的 code/message/source-line 一致，新 origin 测试无诊断；子 `model.py` 定向 mypy 通过。这些是已读取的交付证据，不声明审查者另行执行了全仓 lint/type-check；本次独立执行范围见下文。

## Spec

**发现 1 个 P2，已修复 1 个，未解决 0 个。**

### P2：先平移再比较浮点网格会错移边界，已关闭

初始候选 `ami_clock.py`（SHA256 `a20afc3a6a84e60a9e98c84cc662593038977e76003423813b3f112b3e86950b`）第 60、64–66、76 行先计算 `(edge + UI/2) - T_pre`，再与独立舍入的 Main-local grid 比较。审查者直接调用生产映射函数，复现三种表现，归为同一个坐标比较问题：

| 输入与独立 epoch 关系 | 初始结果 | 修复后结果 |
|---|---|---|
| `ts=1e-12, UI=4e-12, N_pre=11, edge=1.1e-11`；epoch target 与第 2 个 Main 样点同为 `1.3e-11` | local target 为 `2.000000000000001e-12`，误选 index 3 | index 2，量化延迟 0 |
| `ts=.1, UI=.4, N_pre=344, N_main=166, edge=50.7`；epoch target 精确命中末样点 165 | local target 为 `16.500000000000007`，误标 `future` | 保留 index 165 |
| `ts=.1, UI=.4, N_pre=11, edge=1.3, Ignore_UI=1`；epoch target 为 readiness 边界 `1.5` | local target 为 `.3999999999999999`，误判未 ready | ready |

这里的“精确命中”指传入 binary64 epoch target 与 epoch sample 数值相等，不是把十进制写法视为无限精度物理真值。当前功能只记录观察，因此没有据此声称真实模型 BER 已受影响。

实现方改为在同一 epoch 坐标比较 `edge + UI/2` 和 `(N_pre + sample_index) * Init ts`，统一首尾包含判定、ceil 选点、deferred 与量化延迟；派生 local 值只作观察。readiness 仍保留 Main-local 门槛语义：用输入 binary64 的精确值组合 `N_pre * ts + Ignore_UI * UI`，最后仅舍入一次，避免先舍入 `T_pre` 造成另一个边界偏移。没有 epsilon、snapping 或改写 raw ticks。

新增 11 项回归覆盖 ps 网格、以上末样点/readiness 反例及首尾两侧真正跨界的 `nextafter`。独立最终测试全部通过；候选保存 `comparison_basis`、epoch targets、选中 epoch sample times 和 readiness threshold，可核查实际判断依据。F6 后续不得以 independently-rounded local 展示值重新作一次索引判定。

## 已核实的实现边界

| 核查项 | 代码及验证结论 |
|---|---|
| 实际调用账 | PyAMI 每个成功 Init 生成独立 epoch ID，每次 Python GetWave 记录真实输入长度、完成状态及实际 C `wave_size`、连续调用编号、epoch、status、阶段与有效 clock prefix。两次 probes 不再被最后一次记录覆盖；未额外复制整段输入/输出 waveform。 |
| 阶段与原点 | wrapper 在 Main 入场前取得 epoch / Python / C call / Init ts 快照，最终 Close 前复制全阶段历史。映射要求两 probes 加 Main 共三次成功 Python 调用，每阶段 chunk 总样本数等于实际输入长度，C 调用连续、同 epoch、ts 一致。缺失或失败证据拒绝映射。 |
| 执行保持 | 一次 Init → 原两次 probes → 同一 handle Main → 最终 Close。新增观察不额外调用模型，不改变 probe 输入、40 bits-per-call、Main override、私有 RNG、seed 或初始化时序。 |
| 短末块 | 生产 wrapper + Python ABI stand-in 实际记录两个 probes 各 172 样本，分块 `160+12`；Main 前合计 344。Main 默认分块 `160+6`，override 则为 `28×5+26`。这些是该测试的执行记录，不是产品偏移常量。 |
| raw 与边界 | raw clocks 在 epoch 坐标检查有限、非负及严格递增，按原返回次序保留来源。probe 的负 local edge 仍可通过半 UI target 落入 Main；保留 before-record/future 标记，重复采样索引继续报 `unsupported_resolution`。Main grid 与真实 Main 样本数和生产 `index * ts` 形式精确匹配。 |
| 失败与原件 | 失败调用、被拒绝的重试不能拼成完整账；receipt 仅在主体、观察读取与 Close 都成功后标 complete。原 F4 的 C 前/C 中/C 后阶段、失败类别和 unsafe-continuation 保护保留；Close 后可读取历史，重新成功 Init 才开始新历史。 |
| 实际 consumer | Rx caller 写入真实 Traits Dict；`plan_ami_clocks()` 保存 `origin_mapping`，并精确比较独立返回的 Main clocks 与 receipt 中的 Main clocks。对于携带新 receipt 的生产路径，任何非空 epoch clocks 仍拒绝 timed consumption；Main 空而 probe 有 boundary tick 也不能走“全空” fallback。 |
| F6 gate | 只有整个新 receipt 的 epoch clocks 全空才允许原 native fallback。非空映射不进入采样 consumer；`same_init_after_probes` 不改成 `c1_fresh_main`，`model_qualification` 为 `UNKNOWN`，`consumption_permission` 为 `unsupported_pending_contract`。旧 version 2 / raw6 reader、Web 完整结果判断及 BER/Eye/FFT 窗口均未放宽。 |

[IBIS 6.1 第 188 页](https://ibis.org/ver6.1/ver6_1.pdf#page=188)规定 clocks 以首次 GetWave 为时间起点、跨调用严格递增；加半 UI 后的采样点可落入下一段波形。本步据此保留跨 probe/Main 的原始时钟及边界来源；该标准依据本身不构成某个真实 DLL 的资格证明。

## 独立最终验证

审查者使用现有离线环境执行一次最终定向组合，未安装或升级依赖，未启动真实模型：

| 范围 | 独立结果 |
|---|---|
| 父仓 `test_ami_clock_origin.py`、`test_ami_single_init.py`、`test_ami_clock_traits.py`、`test_ami_getwave_params.py`、`test_ami_parameter_projection.py` | **117 passed + 15 subtests passed**，退出 0，0.82 s |
| 子仓 `tests/ami/test_clock_lifecycle.py`、`tests/ami/test_response_rng.py` | **86 passed**，退出 0，0.28 s |
| 合计 | **203 tests + 15 subtests** |

运行方式为现有 `uv run --no-project --python <issue4/.venv/Scripts/python.exe> python -B`；Python `3.13.15`、NumPy `2.5.1`、pytest `9.1.1`。设置 `UV_OFFLINE=1`、`PYTHONDONTWRITEBYTECODE=1`、`QT_QPA_PLATFORM=offscreen`，关闭 pytest cache；`PYTHONPATH` 指向本 worktree 的父 `src`、本地 `PyAMI/src` 与既有 issue4 `PyChOpMarg/src`。运行前断言实际导入的 `ami_clock`、`ibisami`、`bert`、PyAMI `model` 文件路径及 SHA256 均匹配下表，排除误用其他 checkout。

这些测试覆盖软件 stand-in、纯映射及既有 F1–F4/RNG 回归。实现方原测试日志中的 35 个第三方 deprecation warnings 不计为本次独立运行的输出；本次先导入模块核对身份，结果如上。实现方完整过程见 [validation.log](validation.log)。

## 最终候选文件身份

| 文件 | SHA256 |
|---|---|
| `src/pybert/models/bert.py` | `033251747b54ebc894ca952aa33b2141f91de2c74a2e4363b8451f9b71dd982d` |
| `src/pybert/utility/ami_clock.py` | `9cabfc411da9a58f2a25cc9b816c2f014c98195e30cebe4b500a99dc948419c8` |
| `src/pybert/utility/ibisami.py` | `183bc2b49faec2dbe84f714d6e4a23b74dd3971211eb0976cde58002069da99e` |
| `tests/test_ami_single_init.py` | `10fa7a25fc7656d7c0f2666541ad9f473b0c30da15eb4cd08dcf928370f8c872` |
| `tests/test_ami_clock_origin.py` | `e9475890be2ed33952716789885c9392732f65624165147346acf25c6cd68f85` |
| `PyAMI/src/pyibisami/ami/model.py` | `9afc229c6d4218d8fa5c6699489a1f8947ac3dad62313604744e36d0604ca8c9` |
| `PyAMI/tests/ami/test_clock_lifecycle.py` | `50d70e312ce6dfd8804bbfbed946aa17448837520766b0c6d18cdae60b88cba0` |
| `pyproject.toml` | `df809204a0bd2511b721ab288d09179b84cfbeef5c47b560d1c1669bf65e702e` |
| `uv.lock`，未修改 | `cc21cb7dd84c9729a6a2fedfda297af9fb195c0dd7e05a24f89fb7db87be4b12` |

最终校验同时确认前三步审查报告和旧七份审查材料字节未变；父子差异检查无空白错误。上述 PyAMI 提交及直接 URL pin 尚未发布远端，本报告不声称 GitHub 安装或依赖远端可用性已验证。

本步可按上述固定候选完成本地交付。真实 AMI 数值结果、模型/profile 资格、F6 每项分析可用性与新保存合同继续暂缓；没有将这些未授权事项记作 F5 的缺失项。

两轴结论：Standards 0 项；Spec 1 个 P2 已关闭、剩余 0 项。
