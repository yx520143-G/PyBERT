## 状态与执行边界

**PLAN_CLOSED / 已由PM派发实施，issue保持OPEN。** 父#1计划门槛已满足；#8经[PR #18](https://github.com/yx520143-G/PyBERT/pull/18)验收并普通merge，当前集成基线为 `3807bd2f54647a491f350cbda7ab61c0752b06f0`，tree `61089b8058acaf08ee2c9b9c643959ded5e21a54`。#8原owner已停写返权，PM已派发唯一owner chat `01a16c77-9624-79a2-9d55-75e715f6e2fd`（local，gpt-6.1-sol/xhigh），从上述固定基线建立独立worktree，开工ACK与实际路径待核验；尚无本票计算/验收证据；下方验收项均保持未完成。PM负责调度、集成和最终验收，owner自主处理常规实现/验证并定期汇报，不逐步骤增加审批。

#4默认COM139756144外层仍OPEN/BLOCKED_BUDGET/NOT_EXECUTED，不能以Viterbi/优化结果替代或启动不可控搜索。#16外部S8P/S12P补验保持开发后计划，不在本票提前执行。只写Fork，保留原GUI/CLI/MCP与全部旧原件；#9之后才派#10。

采用 PR #7 信号链基础，最低集成提交 `8542f10f4c137f79b3200638f5ee59d36202526a`；原生语义基线 `1bc905d577d2f3bd9471421cfbf3d422d4e6080e`。沿用 #1 的原型集成前置与实际执行 SHA 记录。PR #6 是 GUI 功能/语义证据，既有草稿 Chrome QA 不是本票的解码/数值验收。只要求桌面 Chrome 1280×720。

## 目标、范围与不含项

把原 GUI 的 **Use Viterbi / Trellis Depth、Results / Viterbi、Position / Error** 及两路误码信息接入信号链。用户能在 DFE/Slicer 之后启用原生 ISI/MLSD 解码，Run 后查看 trellis、获选路径、前三个状态的概率、错误定位，以及同一 Run 的 DFE 与 Viterbi 误码结果。此分支是对恢复符号的可选解码/分析，不能被画成影响前面 Channel/CTLE/RxFFE 的线性滤波级。

本票覆盖 Native NRZ 与 PAM4 的完整 ISI 路径，并保留原生 Duo-binary 的明确能力状态与一个有界对照，不因原型页面缺位而默默删除原 GUI 功能。包括必要的原始解码数据/索引上下文暴露、视图操作、取消/失败和导出记录集成。

不含：新 MLSD 算法、人工重新计算概率或纠错率、RS-FEC 或其他标准 FEC、AMI 模型内部 trellis、优化器评分与 trellis 混用。**API-only 的 `rx_viterbi_fec=True` 在此版本保持明确 blocked**，不能因同名 Viterbi 控件而暴露成可用 FEC。GUI 不含这一 FEC 开关、PyBertCfg 也未持久化该字段；原生 FEC 分支有未初始化变量路径，须另行修复与验收后才能承诺支持。

## 依赖

- **技术依赖 #2、#3**：真实 Native Run、单 worker、不可变 run 记录、DFE/CDR 原始输出与完整分析/字段身份。
- 不技术依赖 Native EQ 优化，不技术依赖完整存档系统。与 #5 的保存协议集成可沿用已交付的数据包 schema；不能为完整旧格式兼容延后 trellis。
- Duo-binary 输入能力沿用 #4 的模式契约（队列中 #4 在本票之前）。若原生该模式存在失败，保存复现与原因，不能把它显示为已验证 NRZ/PAM4 的别名。
- 在 #1 的串行队列中位于 #8 Native EQ 之后、#10 IBIS-AMI 之前；这是单 owner 排期，不把前一专项伪装为所有计算的技术前置。

## GUI 功能 → 信号链落点

| GUI 功能 | 落点/操作 | 输入、状态与单位 |
|---|---|---|
| Config / Native Rx / Use Viterbi | DFE/Slicer 下游的“Viterbi / MLSD”分支设置 | `rx_use_viterbi`；Native 模式可启用，Trellis Depth 随 enable 生效；不是 AMI 内部解码的控制开关 |
| Trellis Depth | 同分支设置 | `rx_viterbi_symbols` 为符号数 N，非 bit 数；状态数来自原模型 L^N。默认以真实构造后值为准，不从 DOM 猜 |
| Results / Viterbi | 节点的“结果 / Trellis” | 展示原 producer 的路径、转换连线、前三个状态及概率，不声称画出全部状态概率 |
| Position | trellis 工具栏 | 符号索引 viewport；初始窗口沿用 10 symbols 的可理解语义，边界按真实数组长度裁定，移动视窗不 Run |
| Error / of | trellis 工具栏与错误清单 | 0 表示未选择错误；其余按原 1-based 错误条目跳转，条目本身保存 bit index 与映射 symbol index |
| BitErrs / 两路结果 | 同一 run 概览与节点结果摘要 | `n_errs_dfe`、`n_errs_viterbi` 与各自错误索引；显示有效 bit window / 对齐信息。Viterbi 未启用时仅 n_errs_viterbi=-1 表示未计算；DFE 误码计数仍显示该 run 的实际结果，不能把未计算显示为零误码 |
| 原 GUI 反查 | 辅助搜索入口 | 能从原字段/菜单定位上面对应位置，不要求复制 Results 页签或原布局 |

GUI 语义：[view.py L439–451](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/view.py#L439-L451)、[Results Viterbi L969–983](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/view.py#L969-L983)、[Position/Error handler L1373–1382](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/pybert.py#L1373-L1382)。

## 数据生产者、观察点、轴与有效条件

| 数据/图 | 原生 producer / 实际字段 | 观察位置、单位、有效条件 |
|---|---|---|
| 解码输入采样 | `models.bert` 在 recovered `clock_times` 对 `dfe_out` 取样；`dbg_dict_viterbi["sig_samps"]` | 真实 DFE 输出，V；窗口取最后 `eye_uis` 有效时钟，每次按 t 中首个不早于该时钟的样本取值，不能替换为前端插值 |
| 解码 pulse 样本 | `dbg_dict_viterbi["pulse_resp_samps"]` | `vod * dfe_out_p` 在恢复时钟相位取样，V；不是波形峰值时刻直接代替恢复相位 |
| 解码噪声上下文 | 原生 `sigma=max(rn, std(sig_samps-decided_levels))` | V；残余 ISI + 决策分散的实际上下文，`rn` 为下限。禁止在前端只用 rn 重算概率 |
| 路径与决策 | `dbg_dict_viterbi["path"]`、`["symbols_viterbi"]`、`["symbols_dfe"]` | path 为状态索引；symbol 值来自原 decoder 的归一化电平。PAM4 最终 slicing 使用 `decision_scaler` 还原幅度，不能直接对归一化值套电压阈值 |
| 完整调试概率与回溯 | `dbg_dict_viterbi["probs"]`、`["prevs"]`、decoder 的 states/trans | 列为符号索引，状态/前驱为离散索引，概率无量纲。保留原始概率，不自行归一化或将其解释为 BER |
| Trellis 连线/获选路径 | `plotdata["trellis_x/y"]`、`trellis_path_xs/ys` | x 为本分析窗口内 symbol index，y 为 state index；原图连线来自保留的前三状态及其非零转移，不表示所有全图边均已展示 |
| 前三状态概率图层 | `trellis_state1/2/3_ys` 与 `trellis_state1/2/3_probs` | 状态编号与概率；颜色的 log/下限裁剪是显示变换，raw probability 保留原值 |
| 错误标记 | `bit_errs_viterbi` → `trellis_err_xs`；`trellis_err_ys` | NRZ/Duo-binary 沿用 bit index；PAM4 是 bit index // 2。y=-0.25 仅为显示标记。一个 PAM4 symbol 的两个 bit 错误可映射到相同 x，不能默默去重或把条目数称为 symbol errors |
| 两路误码结果 | `n_errs_dfe / bit_errs_dfe`，`n_errs_viterbi / bit_errs_viterbi` | 误 bit 数及各自经 `calc_ber` 对齐后的窗口相对 bit index；窗口起点/长度/bit delay 必须随数据给出，不能由前端猜测完整波形绝对位置 |

计算依据：[models/bert.py L660–749](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L660-L749)、[两路共用 calc_ber L603–640](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L603-L640)、[trellis producer L1345–1443](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L1345-L1443)、[图层/轴 L169–222](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/gui/plot.py#L169-L222)。

### 最小后端暴露工作

`bits_out_viterbi`、实际 `_sample_times`、原始 sample indices、`sigma`、cursor/恢复相位上下文目前是函数局部数据；不要在接口文档中假称它们已有同名实例字段。新增只读结果元数据，将这些值与实际 `decision_scaler`、N/L、ui/ts、有效 sample/bit windows 一起绑定当前 run。`calc_ber` 两次调用会覆盖 `self.auto_corr`；若展示各路径的对齐，须在原调用时分别捕获对应 bit delay/窗口/相关信息，不能把最后一次 `auto_corr` 复制给两路。

复用原 decoder 与现有 trellis producer；允许做输出收集/纯数据视图适配，不能在 JavaScript 重写 Viterbi、概率、BER 或 slicing。打包 primitive/arrays/metadata，不能向浏览器或结果文件 pickle 整个 decoder。新增字段有 schema 版本，单位、axis ID、producer、有效性/不可用原因明确；现有结果未含这些字段时显示“该记录未采集”，不从其他图猜造。

## 输入、资源、运行与保存语义

1. 启用字段与 N 属于下次 Run 的冻结完整输入；沿用 #2 的同一数值 worker，不启动第二个解码 worker。预检支持模式、正整数 N、实际状态数/样本数与预算、原生资源；超预算显式拒绝，不能偷偷减 N、减 eye window 或切回 DFE-only。
2. `rx_use_viterbi` 与 N 由 PyBertCfg 原生保存；运行产生的适应状态、概率、路径、错误数组不写回用户输入。`rx_viterbi_fec=True` 导入/请求时返回明确 `unsupported_native_fec`，不能丢掉字段后默认 false 假装成功。[configuration.py L145–146](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/configuration.py#L145-L146)。
3. 解码是该 Run 的一个阶段。若原生 decoder/trellis 失败，则该 Run 状态须体现失败/分析失败与具体原因，不能发布全套“成功”零误码结果。既有成功 Run 保留且标注其 run ID；不让旧 trellis 冒充新 Run。Viterbi 被禁用时当前结果明确“未启用”，而不是沿用上次图/零数值。
4. 取消使用 #2 的合作取消与实际任务完成条件。现有 decoder 内无“即时终止”承诺；在可用检查点确认取消前保持 `cancelling` 和 worker 占用。用户切图、Position、Error、缩放只读取完成的数据，不再次 Run。
5. 数据包保留 raw samples、raw probabilities/indices/path、参考/测试 bit 窗口元数据及显示图层来源。可按视窗获取图层，原始数组不随 viewport 截断；颜色取对数、隐藏低概率点等显示变换不进入原始数值验收。通过 #5 的通用记录扩展保存该分支，不依赖可执行对象反序列化。

## 实施步骤

1. 登记全部功能和原生能力条件，冻结数据 schema 与最小 producer 暴露；先验证原有字段及局部上下文的位置，再增加只读收集，保留原算法/GUI/CLI/MCP 默认行为。
2. 完成 enable/N/资源预算预检与 Run 流程集成。关闭/开启/Viterbi 失败的状态必须可区分；实现两路误码的来源、窗口与有效性显示。
3. 接入真实 trellis、top-3 概率、path 与 Error/Position；用实际长度约束 viewport。原 GUI 以 `eye_bits-10` 设置位置上界，对 PAM4 不可直接视为正确 symbol 上界；新视图按实际 symbol 长度裁定并记录这个界面适配差异。
4. 完成原始数据导出/归档扩展与性能保护；仅视图分页/渲染降采样，不削减引擎输入或改变原始概率。
5. 执行以下冻结 fixture 验收，交付实际 Chrome 操作及 raw comparison 证据，并把任何原生失败留为显式 blocker。

## 冻结 fixtures、窗口与容差

首次计算前，继承 #2 完整 Native NRZ/PAM4 输入与固定非零 seed/noise；冻结 `V-NRZ-ISI`、`V-PAM4-ISI` 以及 #4 模式契约下的 `V-DUO-ISI` manifest。基础有界测试用 N=2，完整记录 L/N、nbits/eye_bits、ui/ts、DFE/CDR/AGC 配置、资源 hash、执行 SHA/依赖版本、允许状态/样本预算。按运行前约定的原生规则取全部有效末尾分析窗口，记录实际 `_sample_times`/bit delay；不看结果后手工找“容易通过”的局部窗口。原默认 N 的校验/预算行为另有参数验收，不把 N=2 的结果外推到任意大 trellis。正例/无误码/含错误/禁用/取消用例及其输入在计算前固定；若预设含错误用例没有产生错误，如实报告该路径尚缺证据，不能事后不断换 seed。

同环境直接原引擎与 adapter 用相同完整输入独立运行，比较整个有效输出：counts、bit/symbol/state indices、decoded bits、路径、shape、零概率位置、finite/valid masks **精确一致**；采样电压/pulse/sigma `rtol=1e-10, atol=1e-12 V`；归一化 symbols `rtol=1e-10, atol=1e-12`；原始 sample times（s）`rtol=0, atol=1e-18 s`；原始非零概率 `rtol=1e-10, atol=0`（不能用统一绝对容差吞掉小概率/下溢差异）；原始零值精确相同。离散路径/错误计数不能用“概率差很小”豁免。log 色标/裁剪阈值单独验收，不能替代 raw probability。报告最大差、首个差异位置与原生边界；失败后不自动放宽容差。

## 可核查验收

- [ ] NRZ/PAM4 的 Use Viterbi / Depth、trellis/path/top-3 probability、Position/Error、两路误码全部在信号链中可找到，未通过功能不会标记已实现；Duo-binary 有本票有界证据或明确原生阻塞记录。
- [ ] fixture/schema/容差/窗口 manifest 先于计算记录冻结；实际比较保留完整输入、资源和版本 hash，无历史草稿 Chrome 记录冒充新验收。
- [ ] 原生采样时钟、DFE output、pulse 相位、sigma 和 PAM4 decision scaling 被复用；新的只读元数据能追溯到同一 Run，不存在前端代算路径。
- [ ] 两路误码窗口/对齐独立记录；PAM4 的 bit→symbol 映射有可核查样本，重复 symbol 上的两个 bit 错误不静默合并；无错误时 Error=0/0 行为清楚。
- [ ] Chrome 1280×720 中启用→Run→查看 trellis→Position/Error 定位→切回 DFE/Responses/Jitter→比较旧 Run→保存/打开 的路径可操作；切图、拖动和错误定位不触发 Run。
- [ ] 浏览器显示区分 raw state probability、log 色标和 BER；图轴/有效窗口来自该 Run，原始数组与视图分页/降采样分别验证。
- [ ] Viterbi 禁用时返回“未启用”，其 -1 不显示零误码，DFE 计数继续显示当前实际结果；预检拒绝、decoder/图层失败、合作取消、旧 Run 保留与新输入 dirty 状态均有可核查证据，worker 未实际结束前不释放。
- [ ] `rx_viterbi_fec=True` / AMI 内部解码 / 超预算 N 等未支持请求有明确状态和原因，不静默忽略或改为默认；原生 GUI/CLI/MCP 行为兼容。
- [ ] 保存的结果具备 raw 数据/axes/producer/窗口、schema 版本与 unavailable 原因；旧记录缺字段显示“未采集”。owner 向 PM 交付证据、已知原生限制与下游 AMI 衔接说明。

## 原生缺陷及不能冒充完成的边界

基线 FEC 分支先创建 `decoder_fec`，但后续公共字典使用只在 ISI 分支定义的 `decoder`，且 `symbols_viterbi` 在 FEC 中依赖 debug 分支；这属于原生缺陷，不能包装成受支持 FEC。[bert.py L688–742](https://github.com/yx520143-G/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/src/pybert/models/bert.py#L688-L742)。原 trellis producer 对空路径等退化输入亦存在边界，概率下溢/少于三个有效状态/采样不足需记录实际行为。adapter 可以预检、暴露不可用与保留旧成功结果，不趁 WebUI 迁移改写 decoder 或伪造状态/概率。发生既定 Native fixture 的真实算法失败时，保存最小复现、受影响能力与错误，不删除该验收项；由 PM 协调独立算法修复，不把“接入一致”写成纠错性能或标准资格认证。

