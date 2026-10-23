# 从原 GUI 反查 WebUI 的覆盖核对

核对日期：2026-10-24。结论：上一版有遗漏，也有把计算生效条件误当成 GUI 编辑条件的地方。本次已补齐主窗口命名控件的映射登记，并修复下表中的编辑器差异。当前页面仍是本地配置草稿工具，没有仿真后端。

## 依据与范围

- PyBERT 11.1.0，固定源码 `1bc905d577d2f3bd9471421cfbf3d422d4e6080e`：`src/pybert/gui/view.py` 的实际 Item、ObjectColumn、enabled_when、visible_when；结合 `pybert.py` 中默认值和回调。
- [PR #6](https://github.com/yx520143-G/PyBERT/pull/6)，本次读取的 head 为 `b9c56fe76bafb901d58dd53cda54e2ad5093fe6c`，与当前检出的文档提交一致。产品源码相对上述固定版本没有变化。
- 其[控件审计](../../webui/baseline/control-audit.md)、[Config. 截图](../../webui/baseline/screenshots/01-config-default.png)、[Equalization 截图](../../webui/baseline/screenshots/02-equalization-default.png)、[Optimizer 截图](../../webui/baseline/screenshots/03-optimizer-default.png)、[CTLE 关闭截图](../../webui/baseline/screenshots/30-ctle-disabled.png)以及对应 UIA 记录。截图是 PR 的既有采集证据，不是本次实时采集。
- 本次 Computer Use 找到了正在运行的 PyBERT 窗口，但两次窗口捕获超时，未获取新的截图。没有修改原生 GUI 参数、执行仿真或保存原生配置。

主窗口有 **129 个实际命名 Item**。已注释的 `com_info` 页面不计入。表格的列另外核对；不能把一张表算成一项后忽略其中的列。模型动态生成的 IBIS/AMI 子对话框不属于这个固定清单。

| 本次 WebUI 状态 | 主窗口条目数 | 含义 |
| --- | ---: | --- |
| 可编辑草稿字段 | 82 | 包括按模式禁用的字段；不代表每项当前都启用 |
| tap 表 | 5 | Native Tx、Native Rx、Tx tuner、Rx FFE tuner、DFE tuner；列名、顺序和只读性已比对 |
| 本地批量动作 | 2 | DFE Disable All / Enable All |
| 需要模型或运行数据 | 24 | 路径/Valid 状态、模型操作、AMI 参数表入口、只读优化结果、Viterbi 图表控制；明确不可用 |
| 图表与信息页参考 | 16 | 登记 GUI 位置与源码，没有制造图表、性能、日志或运行结果 |
| 合计 | **129** | 所有条目均可在页面“按原 GUI 查找设置”中找到 |

另登记 **16 个菜单入口**及状态栏的字段类别。登记不等于迁移功能；例如原生 Load/Save、Run/Abort、Tune/Use/Reset EQ 目前均未接入。

## 修复清单

| 原 GUI 项目 | 上一版问题 | 本次处理 |
| --- | --- | --- |
| Rate & Modulation / RLM | 放在 Optimizer，且额外要求 MMSE 开启 | 回到 Source 的调制组；只按 PAM-4 控制能否编辑，另说明计算用途 |
| Samps. per UI、Nbits、EyeBits、Noise、AGC 等 | 按信号链重组后不容易从原 GUI 找到 | 增加原 GUI 分组索引，直达对应字段；保留信号链组织方式 |
| Rx_Cac | 因 Native 计算未使用而被错误设为只读 | 恢复草稿输入，继续注明当前主链未读取 |
| CTLE Enable=false | 错误禁用频率、带宽和 boost 数字框 | 仅禁用模式选择；已有 Native 参数仍可编辑，与截图一致 |
| Native Tx/Rx tap 的 Value | 禁用 tap 后同时锁定 Value | 保留可编辑权重；Enabled 与是否能修改数值分开 |
| Rx FFE 表 | 仅显示 Ntaps 指定的前若干行 | 显示全部 100 槽位；Ntaps 更新启用前缀，表内滚动 |
| Tx Optimizer 表 | 遗漏可编辑 Value 列 | 补齐 Name / Enabled / Min / Max / Step / Value |
| Rx FFE Optimizer 表 | 遗漏只读 Enabled、Value 列，入口只在 Rx FFE | 补齐列；Enabled 随 Ntaps，Value 标明未提供；Optimizer 也可进入同一草稿表 |
| DFE 表 | 遗漏只读 Value 和两个批量按钮；曾强制自动补齐启用前缀 | 补齐列与按钮；按原 GUI 逐行编辑 Enabled，明确引擎只使用首个禁用 tap 之前的前缀 |
| Optimizer / CTLE Result | 只存在于说明 | 设置页增加只读“未执行优化”状态；默认 1.7 dB 留在参考说明，不冒充结果 |
| IBIS / AMI | 缺少独立 Valid、只读路径和 Select/View/Configure 入口 | 各侧分别显示；依赖有效模型的操作禁用并说明原因 |
| AMI Params | 只有概括文字 | 增加 Tx/Rx 独立入口状态与完整列说明；没有加载模型时不造参数行 |
| Viterbi Error / Position / of | 部分只在说明，遗漏误码总数显示 | 设置页补上控件或只读状态；无图表数据时禁用 |
| Responses / Results / Jitter / Info、菜单、状态栏 | 没有逐项登记 | 补全参考映射与未接入状态；保留原生 Console 可编辑等差异说明 |

## 保留的差异与未实现部分

1. 按信号链组织模块，不复刻桌面的像素布局。GUI 中隐藏的部分设置在 WebUI 中仍可见，但禁用并解释条件。
2. 输入立即进入本地草稿。Nbits/EyeBits 不自动照搬原 GUI 的裁剪回调，而是保留输入并显示关系错误；Npre 只更新位置标签，不执行原生 tap 移位；fMax 没有调用引擎做 Nyquist 裁剪。这些都不构成原生可运行性验证。
3. GetWave 和模型时钟在本页是调用方案草稿，允许查看分支；原 GUI 的实际可用性还依赖模型解析得到的能力。文件选择只记录名称/路径，不加载模型，不产生 Valid。
4. IBIS component/pin/model 选择器、I/V 查看器、动态 Model_Specific 配置对话框和 AMI 优化参数行尚未实现。随附 `example_rx.ami` 的参数仅作为参考示例，不能代表任意模型。
5. DFE Level 使用源码初始化值 0.5 V。PR 截图中的约 0.300 V 是运行实例状态，不能覆盖初始化默认值，也不能作为当前草稿的自动优化结果。
6. 原生配置/结果导入导出、仿真、优化、真实绘图、日志与性能统计均未接入。本页的“恢复默认”与原生 Optimization / Reset EQ 不是同一个动作。

## 验证

`node verify-gui-coverage.cjs` 从真实 `view.py` 反查：129 项无遗漏、来源行匹配、5 类表格的所有列及只读性一致；另检查已修复的编辑条件与旧草稿新增列兼容。该检查不导入或运行 PyBERT。

浏览器验证通过：

- 129 个索引条目均有跳转入口；实际验证 Samps. per UI 直达编辑器、Rx AMI Valid 直达只读状态。
- 打开全部 16 个模块，没有重复 DOM id 或控制台 warning/error。
- RLM 在 NRZ 禁用、PAM-4 启用；Rx_Cac 可编辑；CTLE 关闭后仅模式选择禁用，fp/BW/boost 仍可编辑。
- Tx tuner 的 Value 可编辑且刷新后保留；DFE 批量禁用为 0 行、批量启用为 20 行；单独关闭 Tap3 不修改 Tap4，禁用行的边界仍可编辑。
- Rx FFE 两张表均保留 100 行；Ntaps=9 时 Native 表与只读 tuner Enabled 均为前 9 行启用。
- 六个 IBIS/AMI 模型操作按钮禁用且说明原因，路径/Valid 没有伪造加载结果；Viterbi Error/Position 无数据时禁用，总数显示未提供。
- 1280×720 桌面、390×844 窄屏检查通过；窄屏文档宽度 375 CSS px，没有横向页面溢出。

未执行 PyBERT 仿真。所有运行数据相关结果保持 unavailable，不以空白或零代替成功。
