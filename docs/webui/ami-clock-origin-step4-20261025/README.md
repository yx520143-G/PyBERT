# 第 4 步：F5 同一 Init epoch 的时钟原点观察

状态：实现与定向验证完成，同一位 Astra 的 Standards / Spec 审查已通过。Standards 0 项；Spec 发现 1 个 P2，已修复并独立复核关闭，剩余 0 项。仅本地交付，真实 AMI 验收继续暂缓。详见 [Astra 独立审查报告](astra-review.md)。

## 交付边界

本步实现 [最终修改清单的 F5](../fresh-algorithm-review-20261025/final-modification-checklist.md)：同一实例、同一 Init 的两个 response probes 和 Main 的实际调用账，以及 absolute epoch ticks 到现有 Main-local grid 的可核验映射。

这是一项 **映射观察能力**。当前运行仍标为 `same_init_after_probes`，模型 clock 资格仍为 `UNKNOWN`。新来源的 timed consumption、完整／部分分析状态和 Web／归档合同留给 F6；本步不将其标为 `c1_fresh_main`，不放宽旧 version 2 / raw6 reader，不以 raw4 绕过检查。尚未确认真实模型的 origin 与 profile，也没有运行真实 DLL、完整 Main、GUI、Web 或 COM 验收。

## 实际调用账

PyAMI 每次成功 Init 生成独立的 epoch ID；同一模型再次 Init 或不同模型实例的 ID 不同。实际 Init 记录中的 `sample_interval` 是时间依据，analysis invocation ID 不再被当作模型身份。

每次 Python GetWave 完成或失败后，保留该调用的输入样本长度、完成状态及各 C chunk 的真实 `wave_size`、连续调用编号、epoch、返回 status、阶段和 valid clock prefix。这份轻量历史不会被第二次 probe / Main 覆盖；不再次保存所有输入／输出 waveform。原来的 `last_getwave_calls` 完整快照接口保持不变。Close 后历史保留；重新成功 Init 后重置历史。失败调用和被拒绝的重试不能拼成完整执行账。

父 wrapper 通过可选 keyword-only `clock_observations` 返回旁路记录，既有六元组 API 不变。在 Main 入场前保存阶段边界，在最终 Close 之前复制历史；只有主体成功、观察复制成功且 Close 成功后才将 receipt 标为 complete。观察读取失败保留 incomplete，不额外调用／重新初始化模型，也不改变已授权的原波形运行。

原流程保持一次 Init → 原两次 probes → 同一 handle Main → 最终 Close；probe 输入、40 bits_per_call、Main block override、私有熵 RNG 和 F1–F4 的状态／参数检查不变。

## 映射与消费者边界

`map_same_epoch_clocks()` 验证两次 probes 完整成功、Main 是第三次 Python GetWave、C call 编号连续、同 epoch、sample interval 一致、每阶段的实际 chunk 总数与输入长度一致。Main grid 必须与真实 Main 样本数以及当前生产者的 `index * ts` 网格精确一致；缺失、失败或不一致的来源不映射。

固定 sample interval 下：

```text
N_pre       = 两次 probes 实际成功 C chunks 的 wave_size 总和
T_pre       = N_pre * Init sample_interval
target_epoch = raw_epoch_edge + symbol_UI / 2
sample_epoch[index] = (N_pre + index) * Init sample_interval
index        = epoch grid 中第一个不早于 target_epoch 的 Main 样点
target_main  = target_epoch - T_pre（派生坐标展示）
```

先在 raw epoch 坐标检查有限、非负、严格递增，再建立派生 local edge 和 target。两次 probes 与 Main 的 ticks 全部按原返回次序保留，不排序、不去重、不改写 raw clocks。每个 tick 保留 Python / C call 来源；早于 Main 的目标标为 before_record，晚于最后样点标为 future。索引碰撞继续拒绝，不复制／外推样点。

probe 返回的 edge 平移后可以为负，但其半 UI target 仍可落入 Main。首尾包含判定、ceil 选点、deferred 和 quantization 在同一 epoch 坐标比较；不先减掉前置时间再与独立舍入的 local grid 比较，避免恰好命中样点的 tick 错后移一个样点。派生 local target 仅作观察，不能用其独立舍入误差重新判断索引。

readiness 的语义仍为 Main-local `Ignore_Bits * symbol_UI` 门槛，在 epoch 坐标比较其平移阈值。这个单一标量用标准库 Fraction 对输入的二进制精确值组合 `N_pre * ts + Ignore_Bits * symbol_UI`，最后只舍入一次，避免预先舍入 T_pre 引入另一个边界偏移；不是每 tick 高精度重算。probe 训练不抵扣 Main 门槛，BER／Eye／FFT 窗口不变。不使用 epsilon、snapping、排序或改写 raw ticks。

实际 Rx caller 已传入记录，原 `plan_ami_clocks()` 会计算并保存 `origin_mapping`，并逐值比对独立返回的 Main clocks 与账内 Main clocks。它仍拒绝非空 same-epoch timed 消费。只有整个 epoch 的 clocks 全空才走旧 native fallback；Main 自身空但 probe 有 boundary tick 时不能误判为无 clocks。故本步的映射成功不等于算法已消费、Web 可发布或模型合格。

## 验证

- 先运行新增契约测试，24 项因新能力尚不存在而失败；不是现有真实模型数值缺陷的重现。
- 最终父仓 117 tests + 15 subtests 通过；子仓 86 tests 通过，共 **203 tests + 15 subtests**。父仓 35 个第三方既有 deprecation warnings。
- 通过真实生产 wrapper 和 Python ABI stand-in 核对：两个 probes 实际各 172 样本、C chunks 为 160+12，Main 前真实 344 样本；默认 Main chunks 160+6，以及 override 的 28×5+26。这组特定值是测试实际记录，不是产品偏移常数。
- 纯映射测试以独立整数 epoch grid 为 oracle，覆盖非零前置长度、短末块、负 local edge、probe-only boundary、全空 clocks、末尾 deferred、ceil 选点、碰撞拒绝、readiness 不抵扣训练、来源破损和实际 Traits Dict。
- Astra 发现 1 个 P2：float64 坐标平移可能错移采样点、误丢末样点或误判 readiness。已先复现两个精确命中错误，再统一 epoch 比较，并补充 11 项 ps／非二进制 ts／首尾及 nextafter 真正跨界回归；一次中间修复还暴露单独舍入 readiness 阈值的问题，已用上述一次舍入标量处理。当前 41 项 origin 测试全部通过，Astra 已独立复核关闭，并复跑最终 203 tests + 15 subtests 全部通过。
- F1–F4 参数、生命周期、Close、输出 pointer、失败阶段、RNG 回归保持通过。PyAMI model.py 的定向 mypy 无问题。
- Ruff 父 21、子 29 项均与各自 base 的 code/message/source-line 相同，无新增；新映射测试无 lint 问题。这不是全仓 lint 通过声明。
- 两仓 diff --check 通过。没有安装／升级依赖、重新锁定环境、推送远端或创建 PR。静态检查比对脚本首次按 Windows locale 编码 stdin 失败，改为显式 UTF-8 后完成；代码测试无此问题。

测试使用现有 Python 3.13.15 环境，`uv run --no-project --python <issue4/.venv/Scripts/python.exe> python -B`，`PYTHONPATH` 指向本 worktree 的 src、本地 PyAMI/src 和 issue4/PyChOpMarg/src。已核对实际 import 路径。完整最终测试输出和定向检查见 [validation.log](validation.log)。

## 精确范围与候选身份

父 base：`8cd173b81484554a21293e838d49b1b1abe4038e`。PyAMI base：`207bd902ee1e344c9f9053e8150ced8ac143b14d`；本地候选提交：`dfae46033f490c9d19f2684454b6fe9bd90d9a72`。

父修改：`src/pybert/models/bert.py`、`src/pybert/utility/ibisami.py`、`src/pybert/utility/ami_clock.py`、`tests/test_ami_single_init.py`、新 `tests/test_ami_clock_origin.py`、PyAMI gitlink、pyproject 直接 URL pin，以及本目录的 README / validation.log / Astra 报告。

子修改仅 `src/pyibisami/ami/model.py` 和 `tests/ami/test_clock_lifecycle.py`。原 GUI、Web、其他依赖、uv.lock、前三步报告与旧七份审查材料不变。新的直接 URL pin 对应本地提交，远端尚未发布，因此不声称已验证从 GitHub 安装。

| 文件 | SHA256 |
|---|---|
| parent models/bert.py | `033251747b54ebc894ca952aa33b2141f91de2c74a2e4363b8451f9b71dd982d` |
| parent utility/ami_clock.py | `9cabfc411da9a58f2a25cc9b816c2f014c98195e30cebe4b500a99dc948419c8` |
| parent utility/ibisami.py | `183bc2b49faec2dbe84f714d6e4a23b74dd3971211eb0976cde58002069da99e` |
| tests/test_ami_single_init.py | `10fa7a25fc7656d7c0f2666541ad9f473b0c30da15eb4cd08dcf928370f8c872` |
| tests/test_ami_clock_origin.py | `e9475890be2ed33952716789885c9392732f65624165147346acf25c6cd68f85` |
| PyAMI model.py | `9afc229c6d4218d8fa5c6699489a1f8947ac3dad62313604744e36d0604ca8c9` |
| PyAMI test_clock_lifecycle.py | `50d70e312ce6dfd8804bbfbed946aa17448837520766b0c6d18cdae60b88cba0` |
| uv.lock（不变） | `cc21cb7dd84c9729a6a2fedfda297af9fb195c0dd7e05a24f89fb7db87be4b12` |

文本 UTF-8 without BOM。validation.log 仅统一换行为 LF 并去除行尾空白，测试结果不改写。
