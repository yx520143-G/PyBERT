# PyBERT 真实桌面 GUI 基线

本记录服务于 [Issue #1](https://github.com/yx520143-G/PyBERT/issues/1) 开始 Web 页面实现前的设计基线。**五项设计基线采集已完成，提交 PM 终审；#2 由 PM 复核后派发。** 数字框和活动表格的人工鼠标 Run 均有事后证据，前者采用新值后失败，后者有正常返回记录，两者分别保留。没有实施 #2–#5、修改数值算法或完成 Web 验收。

## 身份与环境

- 源码固定为 `1bc905d577d2f3bd9471421cfbf3d422d4e6080e`，仓库 `yx520143-G/PyBERT`，工作目录 `E:\serial-bus-simulator`。采集分支 `codex/webui-gui-baseline`。
- 2026-10-23 在 Windows 10 build 19045 实际运行 `uv run --no-sync pybert`。使用项目 `.venv\Scripts\python.exe`，Python 3.12.10、PyBERT 11.1.0、PySide6 6.10.2、Traits 7.1.0、TraitsUI 8.0.0、Chaco 6.1.1；完整路径、版本和环境变量见 [environment.json](evidence/environment.json)。
- 原窗口外框 **1378×971 px**，客户区 1362×932 px，窗口 DPI 96（100%），主屏 2560×1440 px。图像保留真实窗口尺寸，不用示意图替代。
- 截图来自 screenshot skill 的 `take_screenshot.ps1 -WindowHandle 2558336`，即实际可见窗口的屏幕捕获。操作使用公开 `@oai/sky` Windows 接口；UIA 用于辅助读取，图位由真实 PNG 核对。`focused_element` 在本 Qt 窗口中多次滞后，输入焦点以可见蓝框/编辑器复核，不能只凭该字段判断。
- GUI 启动时已执行初始计算并生成图表。`01`–`18` 是启动后、人工改变参数前的可见状态，**不是构造前的纯输入默认值**。例如 Level 显示 `0.300`，后续原生保存值为 `0.30014859348604045`；不得将运行后实例值冒充运行前输入。
- 后续 Web 验收固定 **Google Chrome 155.0.8059.85、1280×720 CSS px、100% 浏览器缩放**。浏览器实际运行路径与 FileVersion/ProductVersion 已独立读取，见 [browser-version.json](evidence/browser-version.json)。这只是验收环境约定，尚未执行 Web 页面验收。

## 五项设计基线检查

| #1 检查项 | 本次结论 | 证据与边界 |
| --- | --- | --- |
| 实际启动全部顶层页、子页及菜单/状态栏截图 | 已采集 | 01–18、menu-*；均为实际窗口图像 |
| 环境、默认/灰态/只读、表格和图位布局 | 已记录 | 本期 CTLE、CDR、Ideal 条件已切换；只读外观与固定源码定义交叉记录，Console 差异已实测；延期条件保留初态和 S 标记 |
| 数字框/表格 Enter、失焦、直接点击 Run | 已核对代表样本 | Enter、Tab/焦点转移及 GUI 配置保存已留证；两类直接 Run 由用户鼠标操作、代理事后采集；数字样本提交成立但失败，表格样本正常返回且另存值为 .05 |
| 控件、菜单、图表清单与允许差异 | 已逐项登记，非全项交互通过 | 50 控件、5 菜单、18 本期图位均有状态；隐藏/只读定义的静态依据与实测分开 |
| Web 浏览器及相对位置约定 | 已固定 | 实际浏览器版本已读；1280×720 是未来验收目标 |

第二项是本期控件状态的记录门槛：默认值、表格列和图位有真实截图；CTLE/CDR/Ideal 的条件变化有交互证据；表格 Name、Optimizer / Rx DFE Value、Performance、Guide 的只读定义与实际展示对应登记，并明确只读拒写未逐项测试。封装、Viterbi 和非 native 隐藏组属于延期边界，只记录初态与源码条件，不把静态依据标成实测通过。此门槛不要求穷举非法值或验收延期功能。

直接鼠标样本没有用键盘 Run 代替。原 GUI 的线程异常与陈旧状态属于真实观察，不被改写为成功；表格样本的正常返回也不证明 Web 数值一致。Issue #1 父票还依赖 #2–#5 完整验收，本记录不等于父票完成。

## 页签与主要相对位置

| 顶层顺序 | 子页顺序 | 真实布局依据 |
| --- | --- | --- |
| Config. | — | [01](screenshots/01-config-default.png)：Simulation Control 左上、Analysis Parameters 右上；Channel 下部 Tx 左、Interconnect 中、Rx 右 |
| Equalization | — | [02](screenshots/02-equalization-default.png)：Tx 在左；Rx 在右，CTLE 左上、CDR 右上、FFE 左下、DFE 右下 |
| Optimizer | — | [03](screenshots/03-optimizer-default.png)：上部从左至右 Tx FFE、Rx CTLE、Rx FFE、Rx DFE；结果图在下部横跨全宽 |
| Responses | Impulses / Steps / Pulses / Frequency | [04](screenshots/04-responses-impulses.png)、[05](screenshots/05-responses-steps.png)、[06](screenshots/06-responses-pulses.png)、[07](screenshots/07-responses-frequency.png) |
| Results | DFE / Outputs / Eyes / Bathtubs / Viterbi | [08](screenshots/08-results-dfe.png)、[09](screenshots/09-results-outputs.png)、[10](screenshots/10-results-eyes.png)、[11](screenshots/11-results-bathtubs.png)、[12](screenshots/12-results-viterbi.png) |
| Jitter | Jitter Dist. / Jitter Spec. / Jitter Info | [13](screenshots/13-jitter-dist.png)、[14](screenshots/14-jitter-spec.png)、[15](screenshots/15-jitter-info.png) |
| Info | Performance / User's Guide / Console | [16](screenshots/16-info-performance.png)、[17](screenshots/17-info-guide.png)、[18](screenshots/18-info-console.png)；没有 COM 子页 |

普通四格的固定位置为 **Channel 左上、+Tx 右上、+CTLE 左下、+Native DFE 右下**。Results / DFE 的上排是 CDR Adaptation 左、DFE Adaptation 右，下排是 Clock Period Histogram 左、Clock Period Spectrum 右。本期只迁移前两格，后两格留原位延期占位。

1280×720 Web 页面应保持上述顺序、相邻关系和分组，可使用页面/表格滚动；桌面截图不要求按比例缩小到浏览器后逐像素一致。

## 真实观察与已批准的平台差异

1. **RLM**：NRZ 灰态；PAM-4 实际启用（[25](screenshots/25-pam4-rlm.png)）。Web 首版仍始终禁用、标明随优化迁移；不保存、不接受 RLM 设置，不改 PAM4 算法。
2. **输入提交**：数字 Nbits 的 Enter、Tab 失焦会提交并裁剪 EyeBits；用户直接鼠标 Run 后4000也进入本次引擎调用，但运行以异常结束。表格 Enter/Tab/焦点转移三种方式均保留值并进入 GUI 导出配置；直接鼠标 Run 独立样本中 .05 编辑器关闭、显示 +0.050，运行后导出首个 rx_taps tuple 为 .05。Web 使用 #1 明确的 N/T 规则，Run/Save 必须验证当前编辑器；不能据桌面样本断言编辑期间模型完全未变，详见 [interactions.md](interactions.md)。
3. **CTLE/CDR/Ideal**：CTLE Enable 关闭只使模式入口灰态，三个 Native 数字框仍可编辑；MM 使五个 CDR 数字框灰态；Ideal=false 启用 Bandwidth。Web 应保留这些“已实现但条件禁用”的语义，不能与 Not migrated 混淆。
4. **Console**：真实桌面 Console 可编辑（[19](screenshots/19-console-edit-probe.png)，探针文字随后 Ctrl+Z 移除）。Web 按 #1 只读。Performance、Guide 的只读要求不由 Console 行为推导。
5. **菜单**：实际顺序以截图为准，File 的 Quit 位于末尾；Optimization 为 Tune EQ → Abort → Use EQ → Reset EQ，与源码声明顺序不同。桌面 Ready 时 Simulation/Optimization 的 Abort 仍显示可用；Web Simulation Abort 仅 Running 可用，Optimization 全部延期。Web 不注册或展示未实现的桌面快捷键。
6. **输入和结果分离**：桌面启动后 Level 已是可变实例输出。先前 GUI 导出为 0.30014859348604045，表格样本运行后导出为 0.3019818488973055；这不是每次 Run 的冻结输入。Optimizer / Rx DFE 的 Value 初始全部显示 0，而 Results / DFE 适应曲线非零；前者绑定 tuner value，不能用后者最后一行冒充。Web 保留用户草稿、运行输入快照、AGC/适应结果的分离。
7. **标签与图义**：桌面 Rdc/R0 标签为 Ohms，Web 采用 #1 指定的模型 Ω/m 并解释差异；Rx Cac 保留输入兼容但不承诺 native 波形变化。桌面 +Tx 标题包含 De-emphasis & Noise，Web pulse 的实际语义仍为无附加随机噪声的累计响应。Channel 波形/眼图、去掉旧 Channel eye 1 mV 显示噪声、恢复时钟和 DFE 等效响应等差异以 #1 数据约定为准，截图本身不证明数值来源。
8. **未迁移入口**：本次 native 下未展开的 C22/C27/E05/E14/O07 子面板记录为隐藏，定义据固定源码；Web 不为展示延期项强行展开这些面板。独立 RxFFE 图延期，不删除 `ffe_out` 原始数据比较。

## 已知警告与证据限制

[launch-stderr.txt](evidence/launch-stderr.txt) 保留两处 jitter `OptimizeWarning: Covariance of the parameters could not be estimated`，及 Chaco `len(value) 960 - len(index) 640 = 320` 警告。没有为了截图消除这些警告或扩大范围修复模型。

数字框人工鼠标Run样本还保留了真实失败：[numeric-mouse-run-failure.txt](evidence/numeric-mouse-run-failure.txt) 的 `calc_ber()` 报参考序列3994、判决序列4000、bit_dly=6、bits=4000；线程异常后GUI仍显示 `Running DFE/CDR...`（[47](screenshots/47-user-numeric-run-after.png)）。这证明新Nbits输入被采用，也暴露终态显示不可信；不把用户口述“已结束”解释为引擎成功。完整输入身份采用先前GUI导出加观察到的两字段变化记录，见 [numeric-mouse-run-identity.json](evidence/numeric-mouse-run-identity.json)，明确没有原GUI冻结快照或run ID。失败样本不被后续独立的4000/3000表格样本覆盖。

表格鼠标样本见 [52 后态](screenshots/52-user-table-run-after.png)、[53 Console](screenshots/53-user-table-run-console.png) 及 [stderr 比对](evidence/table-mouse-run-stderr-check.json)。Console 有 `2026-10-23 16:01:27.975318+00:00` 和 `16:01:50.456489+00:00` 两条完成记录，stderr 没有新增内容；结合实际后态可记录为普通运行正常返回，不能声称只有一次 Run。原 GUI 没有 run ID 或不可变输入快照；[table-mouse-run-post.yaml](evidence/table-mouse-run-post.yaml) 是事后原生导出，确认 4000/3000 和 .05，但不能倒推每次运行前的全部输入或 AGC 值。

本记录证明窗口、控件与部分交互观察，不证明 BER、物理准确性、MATLAB COM correlation、IEEE 资格或 Web/引擎数值一致。状态栏 Ready 和初始 BitErrs 数字也不构成成功判据。

完整清单见 [control-audit.md](control-audit.md)，操作证据与适用边界见 [interactions.md](interactions.md)，文件清单见 [manifest.json](manifest.json)，完整性见 [checksums.sha256](checksums.sha256)。原始 PNG 与 UIA 文本均作为本基线的版本化证据；本目录的 [.gitattributes](.gitattributes) 禁止 Git 换行转换，校验针对实际保存字节。UIA 中不可见部分、绘图轴和颜色不由树文本替代实际截图核对。
