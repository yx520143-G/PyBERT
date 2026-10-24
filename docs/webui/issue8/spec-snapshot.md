# Live #8 规格快照

来源：https://github.com/yx520143-G/PyBERT/issues/8

GitHub updated_at: 2026-10-24T04:27:59Z

## 状态与执行边界

**PLAN_CLOSED / 已由PM派发实施，issue 保持OPEN。** 父#1的计划闭环已满足启动门槛，#5已验收并通过PR #17合并；当前集成基线为 `5fcf8285b042fe1fe92c068b1c3311fa87a50de0`，tree `c06164a0b87c4577073477c71a9ec05aee5125ee`。当前唯一owner：本机chat `01a16c1d-73a2-7532-bdf5-e8c8d1683103`，gpt-6.1-sol/xhigh。已开工ACK并创建独立worktree `C:/Users/yx/.codex/worktrees/pybert-issue8-optimizer/serial-bus-simulator`，分支`codex/pybert-issue8-optimizer`。PM已核验HEAD/tree与基线一致、工作树干净，PyAMI `5270d713e40bac2be5747bef09b92df79df9085b` / PyChOpMarg `ca905e793fcf6330929471317ca32e7611578e5d`固定gitlinks正确。owner报告实际module路径均指向本票工作树；首次优化前fixtures已冻结于`06dc89f`；首轮4 direct+4 adapter有界对照完成，PM已核对136个数组原字节及候选/输入/退出状态，详见[里程碑与证据边界](https://github.com/yx520143-G/PyBERT/issues/8#issuecomment-6379847871)。当前继续取消/失败/冲突/Chrome/兼容验证，尚未最终验收。前任#5已停写返权，无第二writer。未交付项不勾选。

#4资源/完整配置/不可变结果契约已集成，默认COM仍OPEN / BLOCKED_BUDGET / NOT_EXECUTED，不是本票优化计算的前置标量；不启动该搜索、不以优化FOM替代。后续仍串行 #8→#9→#10，开发完成后由main统筹#16外部S8P/S12P补验；本票不提前执行#16。

产品基线是 PR #7 的信号链 WebUI（最低集成版本 `8542f10f4c137f79b3200638f5ee59d36202526a`），原生语义基线为 `1bc905d577d2f3bd9471421cfbf3d422d4e6080e`。沿用 #1 的 PR #7 集成前置、字段身份、实际执行 SHA 记录和原生兼容约束。PR #6 的真实 GUI 材料用于功能/语义核对，不要求复制页面布局。历史草稿 Chrome 验证不构成本 issue 的优化或数值验收。

## 目标、范围与不含项

让用户在已有真实 Run、Responses / Results / Jitter 之上，配置 **Native Tx FFE + Native CTLE + Native Rx FFE + bounded ideal DFE** 优化约束，执行原生 `coopt`，查看候选 pulse 与评分，明确选择 Use EQ 应用候选，再运行真实时域仿真评估变化。

本期包括：Tx/Rx 搜索表，CTLE 优化范围，DFE 连续启用前缀及约束，`use_mmse`，MMSE 使用的 RLM，Tune EQ、合作取消、候选展示、Use EQ、Reset EQ、候选/输入与当前 Run 的来源关系。原生非 MMSE 网格搜索与 MMSE 均需接入，不以只展示表格视为完成。

不含：IBIS-AMI/TPE 优化、改写 MMSE/DFE/通道算法、自动修改普通 Run 的 PAM4 电平、把 FOM 当 COM 标准资格结论、自动运行大规模参数矩阵。AMI 优化由 #10 承接；其控件在本期明确标记“未接入 AMI 优化”，不能退回 Native 运行。优化完成不自动替用户执行 Use EQ，也不自动覆盖成功 Run 的数据。

## 依赖与排期

- **技术依赖：#2、#3。** 复用单 worker、输入快照、事件/结果包、真实状态、图表能力和字段映射。
- 使用文件通道的优化验收依赖 #4 的资源契约；使用内建 Native 通道可先完成核心功能，不把完整结果存档作为计算前置。
- 与其他任务共用 #1 的单活动 owner/worker。总队列中的 `#2 → #3 → #4 → #5 → #8（本票）→ #9 → #10` 是串行交付安排；Viterbi 不技术依赖本 issue。

## GUI 功能在信号链中的落点

| 原 GUI 功能 | WebUI 落点与行为 | 约束/读写语义 |
|---|---|---|
| Optimizer / Tx FFE 搜索表 | Tx FFE 节点的“优化约束”，全局优化工作区可聚合 | `tx_tap_tuners` 的 enabled/min/max/step 为输入；候选 value 为输出，与普通 `tx_taps` 分离 |
| Optimizer / Rx CTLE | CTLE 节点的“优化约束” | `ctle_enable_tune`；`rx_bw_tune`、`peak_freq_tune` 单位 GHz；min/max/step/候选 `peak_mag_tune` 单位 dB。候选 Boost 只读 |
| Optimizer / Rx FFE | Rx FFE 节点的“优化约束” | `ffe_tap_tuners` 按原生 tap 身份/位置绑定；GUI enabled 列只读、由实际 Ntaps/Npre 映射，不给 100 槽位虚构独立有效性；min/max/step 可编辑、value 为结果 |
| Optimizer / Rx DFE | DFE/Slicer 节点的约束区，与普通仿真共享 enabled/min/max | 从首 tap 开始的连续 enabled 前缀参与计算；gap 后的 enabled 项不能被静默认为有效。优化 value 是候选值，不能覆盖自适应运行状态 |
| Use MMSE / RLM | 全局优化策略；Source 的 RLM 位置可反查至此 | `use_mmse` 决定 Rx 原生求解方式。`rlm` 仅在原生 MMSE 优化路径生效；非 MMSE 时禁用并说明，普通 Run 不受该控件改变影响 |
| Tune EQ / Abort | 优化工作区操作栏，状态显示在全局任务区 | 与 Run / COM / AMI 共用同一计算资源；不会产生并行优化线程 |
| 候选 pulse / cursor / clocks | 优化工作区的候选响应图，可从 Tx/CTLE/RxFFE 节点跳入 | 明确“优化模型的 pulse，假设 bounded ideal DFE”；不能冒充 `dfe_out` 真实输出或已测 BER |
| Use EQ | 候选差异预览 → 将获选 Tx/CTLE/RxFFE 字段写入编辑草稿 | 仅按原 handler 所覆盖字段应用；不应用优化 DFE 权重为时域 DFE 初值；已有成功 Run 标为输入已变更 |
| Reset EQ | 将当前实际 EQ 草稿同步回优化器的初值/enable | 不是恢复应用默认值，不清空历史 Run，不重置搜索 min/max/step 等全部约束 |

GUI 搜索表/条件依据：[view.py L764–859](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/view.py#L764-L859)。Use/Reset 的字段集合依据：[handler.py L155–181](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/handler.py#L155-L181)。未提到的原 GUI 优化功能仍须在 #1 总矩阵定位；AMI 专属项归 AMI issue，不记作本期已实现。

## 数据生产者、单位与有效性

| 数据 | 真实生产者/字段 | 轴、单位、含义和有效条件 |
|---|---|---|
| 候选 Tx/RxFFE、CTLE、评分 | `threads.optimization.coopt` 返回 Tx weights / peak magnitude / Rx weights / FOM / valid；DFE weights 写入隔离实例的 `dfe_tap_tuners[].value` | taps 无量纲，CTLE dB；FOM 原始值与评分模式一并保存。GUI 的 `20*safe_log10(fom)` 仅为显示换算。候选有效性不能只看返回 `valid=True` |
| Channel pulse 对照 | `calc_chnl_h` → `calc_resps` → `plotdata["p_chnl"]` | 同一优化输入的通道 pulse；按实际数组长度提供自己的 `t_ns`，不得强行绑定较短候选数组的轴 |
| 优化候选 pulse | `_update_plotdata` 的 `ctle_out_h_tune` | **名字含 h，内容实际是 `p_tot` pulse**；x=`t_ns_opt`（ns）。保留原 GUI 的 pulse 电压标尺，同时注明模型激励/归一化；MMSE 使用 cursor=1 的等效响应，不是本次 Run 的真实电压波形 |
| Cursor / clocks 标记 | `curs_ix`、`curs_amp`、`clocks_tune` | `curs_ix` 实际为两个 ns 时间值，不是数组下标；`curs_amp` 是 [0, amplitude]；clocks 是显示取样位置的辅助曲线，不是 CDR 恢复时钟 |
| MMSE 过程上下文 | `NoiseCalc` / `mmse` 的实际参数与输入 hash | RLM、level count、Rx Ntaps/Npre、DFE 前缀、各范围与独立频率网格需可追溯。内部 `f_t` 单位 Hz，不能借用普通 Run 的频率轴 |
| 候选应用结果 | adapter 的显式 Use EQ patch | 包含来源 opt ID、候选 ID、原草稿 revision、应用字段及应用后的完整输入 hash；不是优化器擅自更改已冻结 Run 输入 |

生产者依据：[coopt 输入与通道 pulse L197–235](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/threads/optimization.py#L197-L235)、[MMSE / 非 MMSE 评分 L273–352](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/threads/optimization.py#L273-L352)、[返回与 plotdata L573–619](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/threads/optimization.py#L573-L619)、[原 GUI 图名/轴 L146–159](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/plot.py#L146-L159)。

**必须公开的模型边界：** 当前 MMSE 的 Tx level / SNR / DJ / RJ 使用原代码常量，`NoiseCalc` 使用空 aggressor 列表；不等价于普通 Run 的全部噪声设定，也不自动等价于 COM 工具的完整上下文。RLM 由 MMSE 实际读取，普通 PAM4 符号生成不读取它。保留原计算与约束，不能在前端补造新的噪声/波形/COM 公式。[常量 L41–45](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/threads/optimization.py#L41-L45)、[MMSE 调用 L287–318](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/threads/optimization.py#L287-L318)、[普通 PAM4 生成 L709–731](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/pybert.py#L709-L731)。

## 输入、资源、运行与持久化契约

1. 调度器提交 `kind=optimization` 工作给 #2 的唯一数值 worker 槽位；每个任务使用 fresh spawn 子进程及全新隔离 PyBERT 实例，以 `opt_id`（任务 ID）、冻结完整 Native 输入、搜索范围、资源内容 hash、引擎/依赖版本和源草稿 revision 建立记录。`opt_id` 与时域 `run_id` 明确区分。worker 同步调用原生 `coopt`；不要调用 GUI `do_tune_eq` 再启动第二个数值线程。
2. 预检按原算法枚举约束验证有限数字、min≤max、step>0、Tx cursor 约束、Rx Ntaps/Npre、DFE 连续前缀、CTLE enable、可用资源。显示预计外层 Tx×CTLE 候选数；非 MMSE 还须显示 Rx 内层组合数。设置显式资源预算，超预算返回原因，不静默减小搜索范围或回退默认。预算预检/原生预检提前返回均不是成功候选。
3. 原生取消位于 `_report_progress`，读取 `pybert.opt_thread.stopped()`，且只在其进度检查间隔发生。最低实现：将共享 cancellation Event 桥接到符合 `Instance(OptThread)` 的适配实例（如覆盖 `stopped()`；不调用 `.start()`），由同一 worker 同步调用 `coopt`。如选择给原 helper 增加可选取消回调，默认行为须兼容原 GUI/CLI/MCP，并验证检查位置未减少。不能只在服务端设一个永不被原 helper 读取的标记。
4. 请求 Abort 后进入 #2 的 `cancel_requested`（界面显示正在取消）。必须区分请求与检查点观察回执：只有本优化任务确认观察到取消且实际结束，父进程核对 terminal envelope 并确认子进程退出/join 后，才转 `cancelled` 并释放槽位。自然完成先于取消被观察可记录成功及晚到请求；异常退出/无完整终态为 failed。MMSE 求解和非 MMSE 内层循环不保证即时可中断；超时不假装取消完成。不把所有 RuntimeError 当取消；是否用户取消必须由该任务 Event 与检查回执判定。[原线程异常处理 L58–90](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/threads/optimization.py#L58-L90)、[真实检查点 L597–604](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/threads/optimization.py#L597-L604)。
5. 部分候选图标记“进行中，opt ID”；只有完成且通过后置检查的获选候选才启用 Use EQ。失败/取消保留旧成功 Run 与旧成功优化记录；未完成候选不能伪装完整结果。对 `-1000` 无效哨兵、非有限评分/数组、缺少选中候选、数组/轴不匹配返回明确不可用原因；不因 `coopt` 的 True 返回值就宣称成功。
6. Use EQ 按原 handler 字段集合更新草稿，保留无关设置；DFE 候选值仅为优化结果。若草稿在优化后发生冲突，展示差异并要求用户明确选择是否应用当前候选，不能静默覆盖新编辑。应用后旧 Run 标旧，只有新 Run 证明时域效果。Reset EQ 只执行原同步语义，不等价“恢复默认”。
7. `PyBertCfg` 复用现有优化字段；它未持久化 RLM、部分 tuner 的候选 value 和候选响应，必须在有版本号的 Web 扩展/优化记录保存。原生 YAML 导出明确列出不能表示的字段，不能默默丢 RLM；RLM 不反向改写普通波形算法。候选记录保存冻结输入、资源引用、评分模式、raw pulse/axes/weights 和失败/取消状态，不用 pickle 序列化整个活 PyBERT 实例。[configuration.py L140–186](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/configuration.py#L140-L186)。

## 实施步骤与有界验收

1. 接收 #2/#3 的输入、worker、结果 schema；对照原 handler 冻结搜索字段与 Use/Reset patch 清单，登记 candidate/opt ID 和持久化扩展。
2. 接入 Native 搜索表、RLM/MMSE 条件、枚举预算与预检，保持实际 taps 和搜索范围分离；先物化并冻结下面的完整 fixtures/窗口/容差。
3. 在单 spawn worker 内接原 coopt 与真实取消检查桥接，收集候选/评分/响应和后置有效性，保留失败与无候选状态。
4. 接候选 pulse/cursor/诊断与来源展示，再实现显式 Use EQ、原生 Reset EQ 和草稿冲突差异；候选不自动覆盖当前 Run。
5. 完成记录保存及下面的有界直接-helper对照、取消/失败和桌面 Chrome 验收，提交证据及 AMI 后续复用说明。

在第一次优化计算前，继承 #2 的 NRZ/PAM4 完整输入及非零 seed/noise，冻结 `O-NRZ-grid` 与 `O-PAM4-MMSE` 两个 fixture manifest（完整 tap 表、RLM、CTLE/DFE 约束、资源 hash、依赖版本、期望候选枚举顺序、原始数组与图轴窗口）。每个 fixture 的外层候选不超过 16；非 MMSE Rx 内层组合不超过 16。范围与预算须在运行前具体写入 fixture 并产生 hash，禁止看到输出后选 seed/窗口/容差来取得通过。RLM 行为用同一 PAM4 fixture 的两份预先冻结 RLM 输入验证；不要求两者必然选出不同 winner，也不要求 FOM 或 BER 改善。

数值对照在同一冻结环境中运行直接原 helper 与 worker adapter，各自独立实例。比较全部原始有效 pulse，不裁掉差异；图表 viewport/降采样独立验证。允许误差预先固定：tap/归一化系数 `rtol=1e-10, atol=1e-12`；原生 pulse/cursor 电压 `rtol=1e-10, atol=1e-12 V`；原始 FOM `rtol=1e-10, atol=1e-12`；ns 轴 `atol=1e-9 ns, rtol=0`；显示 dB 仅在有限正 FOM 上沿用共同规范 `rtol=1e-10, atol=1e-10 dB`。选择的 tap 身份、候选顺序/获选 ID、形状、有效掩码、输入及资源 hash 精确相同；离散选择不能以“分数差不多”代替。遇到数学退化/非有限输出须双方一致标为不可用，不能纳入浮点 allclose。报告最大误差与失败位置，禁止失败后自动放宽容差。

- [ ] 在 #1 功能矩阵登记本票所有优化控件、动作、图与禁用原因；信号链节点能定位参数与候选，原 GUI 反查正常。桌面 Chrome 1280×720 可操作，无窄屏任务。
- [ ] 先提交完整 fixture/window/tolerance manifest，再运行直接 helper 与 adapter 的两个有界 Native fixture；保留实际输入/版本/候选/数组差异证据，不能用历史草稿截图抵数值验收。
- [ ] 分别验证 MMSE 与非 MMSE 的输入真正进入对应 helper；RLM 对普通 Run 的 PAM4 symbols/raw 波形不产生伪效果，对 MMSE 的调用输入可追溯。
- [ ] 搜索表的 Ntaps/Npre/100 槽位、enabled/read-only、DFE 前缀与候选值区分正确；非法数字、零 step、空候选、超预算、失效资源有字段级原因且没有成功结果。
- [ ] 两套候选 pulse 与对照的原始轴/单位正确；cursor/clocks 不能标为恢复 CDR；切节点/缩放/查看既有候选不触发再次优化。
- [ ] Use EQ/Reset EQ 字段集合与原 handler 一致；优化 DFE 值不写入自适应 DFE 初值；应用前后草稿/冻结 Run/运行状态三者可区分。
- [ ] Run 与 Tune 互斥，真实取消桥接被执行，取消前 worker 不释放；失败/取消/没有有效 winner 保留旧成功结果，不把 RuntimeError 一律标用户取消。包含一个执行中的合作取消案例和一个原生失败案例。
- [ ] RLM 与候选记录可按明确格式保存/恢复；原生配置不能表达的内容有显式损失清单，不默默取默认。文件通道用 #4 的已冻结资源补一个有界对照。
- [ ] GUI/CLI/MCP 原接口兼容，前端未引入物理近似；owner 向 PM 交付剩余限制、实际证据和后续 AMI 衔接说明。

## 原生缺陷与不可用边界

原生优化存在有限进度检查、无效评分哨兵仍可返回 True、部分 MMSE/候选退化、RLM 未进入原生配置等边界。本票可以在 adapter 做显式校验、状态和数据暴露，不借 UI 迁移修改选择算法、DFE/AGC 物理行为或重算“更好”的 FOM。候选分数、理想 bounded DFE pulse 与真实 Run 的不同必须保留在界面与记录中。发现导致既定 fixture 无法执行的原生缺陷时，提交可复现证据并标记受影响能力 blocked；由 PM 协调单独算法修复范围，不能靠隐藏数据、换测试条件或把计划项勾选为已完成绕过。

