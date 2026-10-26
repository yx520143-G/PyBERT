# PyBERT WebUI 交互版验收

GitHub 最终交付（2026-10-26）：[范围、最终截图与检查附件](docs/webui/webui-design-20261026/README.md)。下方保留设计与验收过程，历史本机路径不作为 GitHub 附件链接。

final result: passed

日期：2026-10-25。此结论限于本次 WebUI 布局、交互和浏览器显示检查，不代表数值算法、模型或协议 qualification。

## 目标与范围

- 采用用户选定的第一版视觉方向：深蓝导航、青绿色选中态、浅色表单和清晰的分组。
- 同屏保留信号链、所选节点参数、Eye 与 Impulse；参数区独立滚动。
- 以 1920×1080 为主要设计基准，适配用户的 2560×1440 显示器，并兼容 1280×760 浏览器视口。
- 基线 `108b4d5`（`origin/codex/restore-ami-single-init`），工作分支 `codex/webui-design`。
- 代码修改仅位于 `src/pybert/web/static/`：`index.html`、`workbench.css`、`app.js`、`workbench.js` 和新增 `layout.js`。没有修改 Python、数值算法、参数来源或后端接口。
- 交互地址：[本机工作台](http://127.0.0.1:8797/#dfe)。

## 视觉依据与比较方法

源设计：[第一版设计图](C:/Users/yx/.codex/generated_images/01a17215-cd9d-76d3-9784-1bdf40b49f73/exec-dbadf3d5-d253-48b8-8921-feb441567ab6.png)。原图为 1487×1058 像素。

等尺寸实现：[1487×1058 浏览器截图](C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/interactive-evidence/reference-size-1487x1058.png)。CSS 视口和截图均为 1487×1058，截图实际编码为 JPEG。两图在同一次比较输入中打开，直接检查整体构图与可读细节，没有缩放或裁切后再作判断。浏览器的原始 deviceScaleFactor 未独立读取；截图像素与 CSS 尺寸的有效比值为 1:1。

比较状态为浅色主题、DFE / Slicer、设置面板。源图为静态表单设计，未包含真实 Run；实现右侧加入用户另行要求的真实 Eye/Impulse 同屏区。因此表单宽度、字号层级、可见 tap 行数以及新增结果内容是有意的布局适配，不声称逐像素复刻。CDR、AGC 保留独立控制支路，避免把它们误画成串行滤波级。

原尺寸输入中的导航、字段标签、输入值、表格和坐标轴均可直接阅读；本轮没有需要额外放大才能判断的资产或装饰细节，因此不再另取局部裁切。另以 1280×760 实际截图检查紧凑布局的边界与坐标轴。

## 最终响应式证据

以下均为 Chrome 实际浏览器渲染，所选记录相同，图表加载完成。截图像素尺寸与表列 CSS 视口一致；没有对图像做密度归一化。

| CSS 视口 | 截图 | 页面横向溢出 | Eye/Impulse 同屏 |
| --- | --- | --- | --- |
| 1280×760 | [紧凑视口](C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/interactive-evidence/final-1280x760.jpg) | 无 | 两图完整，含物理轴 |
| 1920×960 | [含浏览器栏高度余量](C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/interactive-evidence/final-1920x960.jpg) | 无 | 两图完整 |
| 1920×1080 | [主设计视口](C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/interactive-evidence/final-1920x1080.jpg) | 无 | 两图完整 |
| 2560×1279 | [当前 Chrome 原始视口](C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/interactive-evidence/final-chrome-native.jpg) | 无 | 两图完整 |

用户显示器为 2560×1440，恢复浏览器视口覆盖后实际文档区为 2560×1279；物理屏幕尺寸与浏览器内容区分别记录。最终已恢复该原始视口。

[DOM 布局检查](C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/interactive-evidence/final-layout-checks.json)记录各视口均为两个图表、无加载提示、无横向溢出；图表容器的 scrollHeight 与 clientHeight 相等。参数区允许独立垂直滚动。

## 五项视觉检查

| 检查面 | 结论与边界 |
| --- | --- |
| 字体与排版 | 保留系统无衬线字体及中文回退。主导航与输入采用清晰的 13–14px 层级，说明与图轴使用较小字号。相较参考图缩小标题和留白以支持同屏调试；数值、单位、禁用说明均可读。参考图未提供字体元数据，不宣称使用完全相同字体。 |
| 间距与布局 | 对齐配置栏、紧凑信号链和左右工作区。参数与结果各自分区，操作菜单折叠，状态与普通提示收纳到页脚；错误保留可见。1280×760 下按钮、图轴和页脚无裁切。 |
| 颜色与视觉样式 | 深蓝导航 `#142d3e`、青绿强调 `#087f79`、浅色画布与白色分组延续参考方向。已选、禁用、错误、草稿与旧结果提示保持各自语义。 |
| 图像与资产 | 沿用产品已有标识与图标；没有用新绘制资产代替参考素材。图表由现有 Plotly 数据直接渲染，未把生成图中的曲线用作结果，也未重采样或补造数据。截图中曲线、热图和文字清楚。 |
| 文案与内容 | 配置、运行、节点和结果动作明确，中文说明配合无歧义的英文术语。保留原参数来源、不可用原因、模型资格边界和结果身份。无测点、无 Run、旧结果和输入错误各有对应提示。 |

## 发现、修复与比较历史

1. 首次准备阶段因浏览器工具无法可靠确认当前 URL 而停止该轮 UI 操作，报告曾为 `blocked`；当时没有完成实现或视觉检查。后续用户回合恢复 Chrome 操作后才继续，未用其他浏览器控制机制绕过限制。
2. **[P2，已修复] 紧凑视口的图表下边界被裁切。** 初次 1280×760 布局中固定图高与过高工具栏挤占空间。修复为按剩余高度分配两张图、压缩顶部层级、收纳普通状态说明。修复后重新捕获同一 DFE 状态；`final-1280x760.jpg` 显示 Eye 与 Impulse 的轴、单位和底边完整，图表区高度与滚动高度均为 304px。
3. **[P2，已修复] 切换节点保留旧参数区滚动位置。** 这会让新节点的首组参数不可见。仅在节点变化时重置参数面板滚动位置；Channel、CTLE、DFE 切换后参数与图表标题同步，未触发新的 Run。
4. **采集修正，不计为界面缺陷。** 视口切换后立即截图曾得到尚未重绘的尺寸；将调整视口与最终捕获分开，通过图像实际尺寸和 DOM 尺寸共同确认。早期带加载状态的截图不作为最终通过依据。
5. 最终再次将源设计、1487×1058 实现和 1920×1080 实现置于同一比较输入，并检查修复后的 1280×760 与原始 Chrome 视口。没有剩余可执行的 P0/P1/P2 发现。

## 交互与数据边界验证

- Channel、CTLE、DFE 的导航和链路节点联动参数、测点标题与真实图表。
- CTLE 参数由 1.7 改为 2 时显示旧结果提示，所选 Run 保留；恢复原值后显示与已验证输入一致。
- 搜索 `nspui` 定位到 Simulation；输入 1 时字段显示最小值错误及 `aria-invalid`，恢复 32 后解除错误。
- 配置菜单、保存命名对话框及取消、结果存档菜单、参数说明页与实现映射入口可用。菜单互斥关闭。
- Native EQ 优化面板打开、Escape 关闭及“返回工作台”按钮均验证；返回按钮恢复焦点。未执行优化计算。
- 结果放大和返回同屏正常；Eye 多测点视图保持原有可滚动分析行为，Run overview 可查看来源信息。
- Source 无自动对应测点时显示明确空状态，不伪装成 DFE 数据。切换回 DFE 后两张图恢复。
- Chrome 控制台最终检查：无捕获到的 error 或 warn。
- 三个修改/新增 JavaScript 文件的 `node --check` 通过；`git diff --check` 通过。既有 DOM 控制入口保留，新增代码未修改后端调用契约。

本轮只执行一次默认 Native NRZ 仿真，15000 bits，Run ID `0b4cd795-a7d0-4520-b62f-74f3a0ba1c5f`，运行成功。两图读取该记录已保存的响应与眼图，保留其物理轴与数据。最终 API 状态为 1 条 Run、0 条参考记录、无活动任务。

未执行完整数值回归、COM、AMI 或 EQ 优化验收；本次成功运行仅证明前端能够调用既有引擎并显示结果。输入变动后的新结果仍需用户显式 Run。

## 实施检查表

- [x] 选定视觉方向与同屏调试布局落地。
- [x] 指定尺寸、当前 Chrome 视口与关键交互验证。
- [x] P2 问题修复后重新捕获和比较。
- [x] 数值代码、后端接口与参数来源保持不变。
- [x] 浏览器标签保留为可交互交付物；代码位于独立本地分支。

开放问题：无阻塞问题。未覆盖的数值与模型验收维持上述边界。

## 后续修复：NRZ / PAM-4 连续切换

用户在 Source 面板报告切换不流畅。于用户标注的 1200×1199 视口复现：先点 PAM-4，再点 NRZ，第二次点击被忽略。四次交替选择中两次未到达所选值。

根因是 `workbench.js` 在后台 `/api/normalize` 期间把整个参数面板设为 `inert`，阻断了点击；这不是数值仿真耗时。修复只调整前端校验调度：后台校验不锁参数面板、不强制移走焦点；输入版本变化后不应用旧响应，并在当前请求结束后校验最新已提交草稿。原有 base 和有序 patches 保留至最新校验成功；过期失败响应也不覆盖当前状态。显式运行、保存等操作仍保留锁定与原生校验。

验证结果：

- 同一浏览器场景连续交替选择 10 次，10/10 均即时反映所选值；待校验结束后仍停留在最后选择 NRZ，并恢复可运行状态。
- 新增 `tests/web_workbench.test.cjs`，直接执行实际 workbench 脚本的事件/API 边界，使用延迟响应验证并发编辑。修复前 2/4 失败；修复后 4/4 通过，覆盖过期成功、过期失败、当前失败保留和显式保存校验。
- 测试命令：`uv run --no-project node --test tests/web_workbench.test.cjs`。语法检查与 `git diff --check` 通过，无遗留调试日志。
- 浏览器控制台无捕获到的 error 或 warn。未新增 Run，服务仍只有此前的 1 条结果记录，无活动任务；数值代码和后端接口未修改。

[交互检查记录](C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/modulation-switch/interaction-checks.json)中的 `elapsedMs` 包含浏览器自动化开销，不作为浏览器绘制延迟指标。[修复后截图](C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/modulation-switch/after.jpg)为 1200×1199 像素，与 CSS 视口一致。

## 后续调整：按配置显示适用参数

按用户对 RLM、Channel 文件输入、FEXT 和 CTLE 文件输入的标注，统一处理现有条件禁用的设置。仅修改 `app.js` 的展示与导航：沿用 `settings.disabledReason`，条件不满足时隐藏字段或 tap 表，整组都无适用字段时隐藏组标题；不清空草稿，也不改变原有启用规则、校验或后端输入。只读输出、模型能力状态及适用路径的限制说明仍保留。

隐藏项仍可通过搜索和原 GUI 索引查找；目标当前隐藏时跳到“参数说明”。无适用设置的模块显示简短提示。链路顶部的“请求模型时钟”沿用现有 Rx GetWave 条件显示。

浏览器检查使用用户当前的 1200×1199 视口：

- 遍历全部 16 个模块，未发现仅剩标题的空参数分组。
- NRZ 隐藏 RLM，PAM-4 显示；将 RLM 临时改为 0.94，隐藏再显示后仍为 0.94，最后恢复原值 0.95 与原 NRZ 选择。
- Native / Single / Multiple 分别显示对应通道参数；Single `.s8p` 文件名条件显示 lane 与 FEXT，恢复原通道后隐藏。这里只检查文件名条件，没有上传或运行通道文件，临时文件名已恢复为空。
- CTLE Native / File 互斥显示对应参数；关闭 CTLE 搜索时隐藏约束字段，保留只读优化结果。
- 非理想 DFE 求和显示带宽；Mueller-Muller 隐藏 Bang-Bang 动态环路字段；启用 Viterbi 和封装模型后显示对应设置。各开关均恢复原状态。
- 搜索隐藏的 RLM 正确打开并定位到“参数说明”；COM 无适用参数时显示说明提示。
- 既有草稿迁移、reset/undo 和四项后台校验回归测试通过；语法检查通过。没有新增 Run 或修改数值代码。

[条件显示检查数据](C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/conditional-settings/checks.json)记录各模块的可见/隐藏字段及切换状态。[Channel 调整后截图](C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/conditional-settings/channel.jpg)展示 Native 模式下收起不适用文件项后的布局。


## 后续调整：暂缓展示 Viterbi（2026-10-26）

按用户决定，Viterbi 暂不在本版 WebUI 开放，待后续 MLSE 工作再恢复入口。已移除导航和信号链按钮、图表菜单选项、参数搜索和原 GUI 索引入口、Observe 中的相关条目，以及输入比较表中的专用结果行。完整 catalog、配置字段、底层算法、结果存档和原始审计元数据保留。

验证通过：页面为 15 个模块；Viterbi / Trellis / MLSD 搜索均无入口；旧 `#viterbi` 地址回退到 Source；Observe 和帮助说明不再展示相关入口；Channel Eye + Impulse 正常显示，无横向溢出、无控制台错误或警告。最后恢复用户的 Channel 页面，保留当前配置和所选 Run。

Node 语法检查、4 项异步输入验证回归、现有草稿迁移及 reset/undo 检查通过。此次仅修改前端展示，没有修改数值计算代码或启动新的仿真。

证据：`C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/viterbi-deferred/checks.json` 和同目录 `channel.jpg`。

## 后续调整：A–D 测点交互预览（2026-10-26）

用户要求查看测点标记选择结果的交互效果。沿用当前已选定的工作台样式，仅修改前端：模块选择负责参数编辑，测点选择负责已保存结果。A 是独立的 Channel-only 诊断参考支路；B 是 Tx、Channel、Noise 后的 Rx input；C 是 CTLE output；D 在 DFE 求和后、Slicer 硬判决前。Rx FFE 保留为明确标注的 Web 扩展测点，未加入原 GUI 的 A–D 四组比较。Viterbi 仍不在 UI 开放。

### 视觉证据与状态

证据目录：`C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/measurement-preview/`。

- source visual truth：`before-1200x1199.jpg`，当前已接受的 Channel 参数与 Channel-only Eye + Impulse 工作台。
- implementation screenshot：`after-1200x1199.jpg`，同一 Channel 模块、同一 Run、同一输入、同一测点与双图状态，增加 A–D 标记。两图在同一个比较输入中检查。
- 两张比较图都是 1200×1199 像素，对应 1200×1199 CSS 视口，密度 1:1，无裁切或缩放归一化。完整视图中模块、标记、表单、轴与标签可直接辨认，因此无需额外区域裁切。
- 最终当前工作台：`ctle-edit-d-observe-1200x1199.jpg`。左侧 CTLE，右侧 D 点；所选 Run 为 `b1bcc6af-733b-4225-9b0e-b81e4eead9e9`，输入一致提示可见。用户的 Channel length 1 m 与 CTLE boost 10.7 dB 两项草稿修改保留。
- Chrome 视口证据：`ctle-edit-d-observe-1920x1080.jpg`、`ctle-edit-d-observe-1280x760.jpg`、`ctle-edit-d-observe-2560x1440.jpg`，均为对应 CSS 尺寸的 1:1 截图。三个尺寸无页面横向溢出，默认双图与参数同屏。Chrome 自身保存的草稿为默认输入，与所选 Run 不同，截图中的“输入已变化”提示准确保留；没有为截图更改输入。
- Chrome 视口覆盖已恢复，当前实际窗口为 1236×615；该高度下图表区允许滚动，见 `short-window-fixed-1236x615.jpg`。这不是声称显示器原生浏览器视口为 2560×1440。

### 五项视觉检查

- 字体：延续现有 Segoe UI / Microsoft YaHei 与字号层级；测点字母用 11–12 px 粗体，右侧标题与测点名称一致。
- 间距：保留左右工作区与顶栏；参考支路让信号链区域增加约 9 px。1280×760 的两图轴和持久操作均可见；更矮窗口采用图表区滚动，不再把绘图区压成零高度。
- 颜色：沿用深蓝侧栏、青绿强调色。模块使用轮廓选中态，测点使用实心选中态，二者可同时存在。
- 图像与资源：复用原图标与真实 Plotly 数据，没有新增装饰性图像或示例曲线。图表沿用保存的原始数据、轴、窗口及可用性。
- 文案：明确“点击模块编辑参数 · 点击测点选择结果”；A 的参考支路与 D 的判决前位置直接可见。专用/全局结果不高亮任何 A–D 标记；原 GUI 四点与 Rx FFE 扩展分组明确。

### 交互与修复记录

- Eye 模式依次点击 A/B/C/D，CTLE 参数页不变、视图种类不变、Run 不变，实际图标题分别对应四份已保存数据。
- D 点下切换到 Noise 参数模块，仍显示 D 点 Eye；Jitter Spec 模式点击 B，仍显示 Jitter Spec。
- CDR 专用结果清除测点高亮并禁用测点下拉；再点击 C 时进入 C 的 Eye + Impulse。Source waveform 与 Injected noise 有独立入口。
- A–D 四眼比较只读取 `eye.chnl`、`eye.tx`、`eye.ctle`、`eye.dfe`；Rx FFE 单独选择时标为“扩展”，没有 A–D 高亮。原 GUI Outputs 索引仍可打开四点波形。
- 键盘 Enter 可选择 B；较矮窗口中连续 B→C→D 后最终图和说明均为 D，没有遗留加载态。
- [P2，已修复] 窄结果栏四眼图标题重复 Run ID 导致重叠，见 `four-points.jpg`。删除同一 Run 的重复标签后只显示测点名称，见 `four-points-fixed.jpg`；Run 身份仍在记录选择器与数据来源中。
- [P2，已修复] 恢复到 1236×615 的实际 Chrome 窗口后，双图高度过小导致 Plotly axis scaling 错误。高度低于 700 px 时保留图表最小高度并允许滚动；同尺寸重新加载及快速切换通过。历史错误 `2026-10-25T17:34:04.393Z` 保留在检查文件中，修复后无新增控制台错误。当前 IAB 控制台无错误或警告。
- 静态资源加版本查询，避免部分缓存脚本与新 HTML 混用。没有修改后端缓存策略。

`interaction-checks.json` 保存上述 UI 状态、尺寸检查和控制台记录。Node 语法检查、4 项输入异步校验测试、既有 draft 迁移与 reset/undo 检查通过，`git diff --check` 通过。检查前后仍是同样两条 Run（`6da9e632-90f5-4945-863c-ad64cd1f27fc`、`b1bcc6af-733b-4225-9b0e-b81e4eead9e9`）及相同 input hash，无活动任务。此次没有启动仿真、COM、优化或 AMI 验证，没有修改数值计算代码。

无待处理 P0/P1/P2。宽屏四点比较、单测点与最小视口双图均可操作；较小结果栏的四眼比较允许在图表区滚动，属于预期布局。当前验收是前端交互与显示检查，不增加数值资格结论。

final result: passed

## 后续调整：信号名称优先（2026-10-26）

按用户批准的方案，将四组结果命名为“通道参考 / 接收端输入 / CTLE 输出 / 判决前信号”。A–D 保留为辅助标记，结果标题先显示名称，再显示浅色字母标签。宽屏常显链路测点名称；窄屏在选中、悬停或键盘聚焦时显示。通道参考仍是独立入口，说明其不含 Tx 均衡与显式噪声。四图比较采用完整信号名称。

证据目录：`C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/signal-name-preview/`。

- source visual truth 为前一版已接受的 `measurement-preview/ctle-edit-d-observe-1200x1199.jpg`；与本次 `ctle-d-1200x1199.jpg` 在同一个比较输入中核对。两图均为 1200×1199 CSS 视口及 1:1 像素，无裁切或密度归一化。名称、参数、坐标轴可在完整截图辨认，无需额外局部裁切。
- 字体保留原工作台层级；信号名称为主，字母缩为 10 px 辅助文本。颜色继续使用深蓝侧栏和青绿选中态，测点选中背景改为浅色。名称下方留出固定空间，不覆盖模块或参考入口。
- 图标与 Plotly 图形沿用现有资源，没有新增示例图或曲线；名称与悬停说明明确对应现有保存结果。
- `ctle-d-1920x1080.jpg`、`ctle-d-2560x1440.jpg` 验证宽屏常显名称；`ctle-d-1280x760.jpg` 验证紧凑屏幕的两个图及其坐标轴可见，无页面横向溢出。1280×760 的图表区有 1 px 取整溢出，不遮挡图形或坐标轴。
- 四个入口逐一点击后，右侧名称、字母、图注与高亮一致；左侧始终保持 CTLE、所选参考记录不变、视图保持 Eye + Impulse。四眼比较的标题依次为四个信号名，见 `four-signals-1920x1080.jpg`。用户的两项草稿修改保留，包括 CTLE boost 10.7 dB。
- [P2，已修复] 在 1280×720 且存在恢复提示时，旧的按窗口高度限定的最小图高规则未覆盖实际剩余高度，导致 Plotly axis scaling 错误。改为始终保留双图最小高度；紧凑高度减少结果标题和说明栏间距，过矮窗口允许图表区滚动。1280×720 重新切换 B→D 后两图均存在、状态无错误。控制台只保留修复前 `2026-10-26T06:17:27.070Z` 的历史错误，修复后没有新增错误。

本次预览服务恢复后，通过原有存档接口加载此前的两条结果作为 reference，未运行新的仿真。`restored-records.json` 保留原 run ID 与 input hash：`6da9e632-90f5-4945-863c-ad64cd1f27fc` / `f754f338475be34a07243cfa1cad82adbdaf5c908fa42b0580a7c53dfd67e204`，以及 `b1bcc6af-733b-4225-9b0e-b81e4eead9e9` / `3f39868b580e8ad6100ab8eff859b339f2bcb1e0c04e7d55f2c977f25d2ce43f`。最终服务为 0 条新 Run、2 条 reference、无活动任务。

修改仅涉及 WebUI 静态文件及本检查记录；Python、数值计算、依赖与子模块未修改。JS 语法检查、4 项既有异步输入测试与 reset 检查通过；最终 `git diff --check` 与 UTF-8 without BOM 检查通过。临时视口覆盖已恢复，交互预览已显示在右侧，当前左侧 CTLE、右侧判决前信号双图。

无待处理 P0/P1/P2。`interaction-checks.json` 记录交互、尺寸和控制台证据。

final result: passed

## 后续调整：DFE 专用视图按测点筛选（2026-10-26）

用户指出 DFE 结果只适用于 D 点。当前菜单对应项为 `DFE Adaptation`（权重收敛过程）。该选项现在只在 D 点加入菜单，在 A、B、C 和 Rx FFE 扩展点直接移出菜单；从 DFE Adaptation 切到其他测点时回到该点的 Eye + Impulse。DFE Adaptation 保持 D 点高亮及信号标题，不允许四点比较；原 GUI 的 DFE 结果快捷入口先同步 D 点可用选项，再选择该视图。

浏览器逐一验证 A/B/C 隐藏、D 可选，以及 DFE Adaptation → A/B/C/FFE 的回退；均保持所选参考记录和参数草稿。原 GUI DFE 结果入口验证通过，最终恢复用户的 Rx FFE 参数页、B 点双图、原参考记录及两项草稿修改。证据保存在 `C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/dfe-view-filter/`。

本次仅修改 `layout.js`、`workbench.js` 的视图导航、`index.html` 资源版本与本记录。语法检查和 4 项既有输入异步回归通过；未修改数值计算代码，未启动新仿真。

final result: passed

### 补充：将 CDR 专用项纳入 D 点筛选

用户截图中 DFE Adaptation 已隐藏，但三项 CDR 结果仍可见。将接收端专用集合明确为 DFE Adaptation、CDR Adaptation、CDR Histogram、CDR Spectrum；四项都只在 D 点加入菜单。A/B/C 均无这四项，从任一专用视图切到 C 点均回到 C 的 Eye + Impulse。专用视图保持 D 点标记，不提供四点比较。

浏览器验证四个测点的实际菜单选项及四种专用视图的回退通过，最终停在 C 点；原参考记录和两项草稿修改保留，控制台无错误或警告。证据目录为 `C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/receiver-view-filter/`。本次仅修改 `layout.js`、静态资源版本和本记录；语法与 diff 检查通过，数值代码未改，未启动仿真。

final result: passed

## 后续调整：将参考 A 放入 Channel 卡片右上角（2026-10-26）

用户批准将左下角的独立参考入口移到 Channel 卡片右上角，以较轻的“参考 A”文字呈现。入口与 Channel 参数按钮是相邻的独立按钮，避免嵌套按钮和点击行为混淆；仍使用原有 `chnl` 结果标识。AMI 模式的既有说明保持原逻辑。

证据目录：`output/playwright/channel-reference/`。本轮 IAB 自动化工具不可用，使用 Playwright CLI 的 Chrome 完成实际页面检查；已向 Codex 右侧提交交互预览打开请求，未将排队状态当作右侧已显示的证据。

- source visual truth 为 `before-1920x1080.png`；与 `after-1920x1080.png` 在同一比较输入中检查，均为 1920×1080 CSS 视口、1:1 像素。两图保持相同 CTLE 参数、参考记录、A 点和双图；重新加载后出现正常的“草稿恢复与迁移详情”折叠行，不属于本次视觉修改。
- 字体：入口使用 11 px 常规文字，A 延续已有辅助标记；Channel 标题保持原字号。间距：入口位于卡片右上角，主链区域减少 8 px，原左下角参考支路已移除。颜色：默认灰蓝，选中为青绿，悬停下划线，键盘聚焦有轮廓。
- 图像与资源：沿用原图标和存档 Plotly 曲线，没有新增图像或示例曲线。文案：显示“参考 A”，完整名称、独立通道含义及不包含 Tx 均衡与显式噪声的说明保留在无障碍标签和悬停提示中。
- `after-1280x760.png` 和 `final-1920x1080.png` 分别验证紧凑与宽屏。入口在 Channel 卡片内，未覆盖标题；无页面横向溢出，参数与双图可同时查看。`channel-detail.png` 是直接从页面捕获的信号链局部截图，1646×122 像素，未缩放。
- [P2，已修复] 首次包装 Channel 节点后 flex 基准宽度不一致，标题与入口间距过小。使包装层采用与其他节点相同的基准宽度后复查通过；宽屏与紧凑视口均无重叠。

实际点击 C→参考 A 保持 CTLE 参数页和参考记录；点击 Channel 主卡片打开 Channel 参数并保持 A；参考入口通过键盘 Enter 可选中。最后恢复 CTLE 参数页、A 点、Eye + Impulse。Chrome 的独立默认草稿与所选存档输入不同，“输入已变化”提示准确保留，未为截图修改参数。最终控制台无错误或警告。

本次实现修改仅为 `app.js`、`workbench.css`、`index.html`。JS 语法、UTF-8 without BOM 和 `git diff --check` 检查通过；Python、数值计算、依赖和子模块均未修改。预览服务恢复后加载此前两份存档，最终为 0 条新 Run、2 条 reference、无活动任务，没有重新计算结果。

无待处理 P0/P1/P2。

final result: passed

## 后续调整：通道参考移到结果工具栏（2026-10-26）

按用户进一步批准的方案，Channel 卡片恢复为参数入口，主链仅保留 B/C/D。结果区工具栏增加常驻的“通道参考”文字按钮；参考标题下显示“理想激励 → Channel · 独立参考”。移除该参考在链路、下拉项、标题徽标和比较图中的 A 标记，内部 `chnl` 标识、数据请求和原始数据保持原逻辑。

证据目录：`output/playwright/channel-reference-toolbar/`。source visual truth 为 `before-1920x1080.png`；最新实现为 `final-1920x1080.png`，两图在同一比较输入中检查。均为 1920×1080 CSS 视口与 1:1 像素，保留相同 CTLE 页面、参数、参考记录和双图。服务状态行的 normalize 任务标识随正常页面加载变化，不是新仿真。完整截图中的入口、标题、下拉项和主链标记可辨认，不需要额外的成对裁切；`reference-detail-1920.png` 提供结果区局部实拍。

- 字体：延续 Segoe UI / Microsoft YaHei；参考按钮为 11 px 常规文字，选中加粗，简短说明为 10 px。主链 B/C/D 字号与含义不变。
- 间距与布局：工具栏入口右对齐，不增加默认双图的工具栏行数；说明放在既有结果标题区域。1280×760、1920×1080、2560×1440 和 1200×1199 均无页面横向溢出，参考说明完整，参数与双图可同时查看。
- 颜色：默认参考入口使用现有 muted 色，选中使用 accent 色；键盘聚焦保留清晰轮廓。查看通道参考时 B/C/D 均无选中态，切回主链时仅对应信号选中。
- 图像与资源：沿用原图标和已保存的 Plotly 结果。截图在两个 Plotly SVG 与各自画布尺寸一致后捕获，避免将窗口切换中的暂态尺寸当作最终效果；没有新增图像或合成曲线。
- 文案：观察信号下拉分为“通道参考分析 / 主链观察点 / Web 扩展”；四图比较明确为“通道参考 + B/C/D”，参考图标题不带字母。参考双图的 Impulse 注释为“通道响应”，数据来源说明同步解释理想激励的含义。

浏览器验证通过：

- 参考与 B/C/D 连续点击切换，保留 CTLE 模块、全部已渲染参数值和所选 reference；参考入口 Enter、Space 与 B 点 Enter 均可使用。
- 下拉选择通道参考、B、C、Rx FFE 时没有 DFE/CDR 专用项。D 点具备 DFE Adaptation、CDR Adaptation、CDR Histogram、CDR Spectrum；从任一项点击参考入口，回到通道参考 Eye + Impulse 并清除主链高亮。
- 四图比较实际标题为“通道参考 / 接收端输入 B / CTLE 输出 C / 判决前信号 D”。既有四组数据保留，较小结果栏的比较图仍按既有方式滚动。
- 最终控制台无错误或警告。`interaction-checks.json`、`receiver-checks.json`、`comparison-checks.json`、`responsive-checks.json` 和 `plot-size-checks.json` 保存检查结果。

实际实现范围为 `app.js`、`index.html`、`layout.js`、`workbench.js`、`workbench.css` 及本 QA 记录。JS 语法检查、4 项既有输入异步测试、diff 与 UTF-8 without BOM 检查通过。Python、数值计算、依赖、子模块均未修改；没有启动新仿真。`service-checks.json` 确认 0 条新 Run、2 条 reference、无活动任务，两条原始 run ID 与 input hash 均与已有存档一致。

预览使用 Chrome / Playwright CLI 验证；IAB 自动化工具当前不可用。向主聊天右侧提交的交互预览打开请求已排队，未将该状态表述为已验证的 IAB 显示。

无待处理 P0/P1/P2。

final result: passed

## 后续调整：紧凑测点与结果导航，保留 Slicer（2026-10-26）

用户批准将交互预览中的紧凑测点、信号标题选择和结果入口应用到实际 WebUI，并明确要求保留已有 Slicer、不得修改数值计算代码。四个主链测点现在以小圆点呈现，悬停或键盘聚焦时仅显示“接收端输入 / CTLE 输出 / FFE 输出 / 判决前信号”。DFE 后、Slicer 前的判决前测点和原有 Slicer 设置入口均保留。

本轮实现文件为 `src/pybert/web/static/app.js`、`index.html`、`layout.js`、`workbench.js`、`workbench.css`，另更新本检查记录。没有修改 Python、数值计算、依赖、子模块或原生 GUI。工作区原有的 `tests/web_workbench.test.cjs` 本轮未改动。未创建提交或 PR。

### 视觉比较与允许的差异

- source visual truth：`C:/Users/yx/.codex/visualizations/2026/10/25/01a17215-cd9d-76d3-9784-1bdf40b49f73/pybert-navigation-preview.html` 的“提议布局”，叠加用户明确要求的 Slicer 保留约束。
- 实际页面：`http://127.0.0.1:8797/`。证据目录：`output/playwright/compact-navigation/`。
- 同状态完整比较：`source-1280x760.png` 与 `tooltip-1280.png`，均为 1280×760 CSS 视口、1280×760 像素、deviceScaleFactor=1；左侧 Channel，右侧接收端输入，所选记录均为 b1bcc6af，接收端测点提示可见。两图在同一比较输入中打开检查，没有缩放后宣称像素一致。
- 局部比较：`source-chain.png`（1085×86 像素）与 `implemented-chain-hover.png`（1066×109 像素）在同一比较输入中检查，均为页面元素的直接 1:1 截图。区域宽度差异来自既有产品侧栏与预览外框；未拉伸截图。
- 预览省略的 Slicer、完整参数表单、真实记录选择、状态提示和运行控制均保留。预览的说明序号、外框、轮播器与示例草稿不会写入产品。产品继续显示当前默认草稿（例如 Channel 0.5 m）和真实的“输入已变化”状态，没有为匹配预览示例的 1 m 修改输入。这些属于已明确的范围差异，不属于视觉回归。

五项视觉检查：

- 字体：沿用既有 Segoe UI / Microsoft YaHei，信号名称与菜单保持原产品的字号层级。测点提示为 11 px，仅显示短名称；标题中的信号选择器清晰且未截断。
- 间距与布局：测点占用 28 px 的交互宽度，不将名称常驻插入主链。1280×760 下 Source 至 Slicer 八个模块处于同一行，参数、Eye 与 Impulse 同屏。信号名称选择器移入结果标题，独立分析按上下文隐藏不适用的选择器。
- 颜色：延续深蓝侧栏、青绿选择态与浅色面板；选中测点为实心青绿，未选中为空心，悬停和键盘聚焦有可辨认反馈。Source、Noise 或通道参考被观察时使用对应模块的观察高亮。
- 图像与资源：产品继续通过既有接口显示所选存档的 Plotly 图形；没有添加生成图像、示例曲线或重算图形数据。预览中的存档截图与产品中的实际图表使用各自原有渲染方式。
- 文案：移除 B/C/D 与 FFE 混用的显示编号，四个测点使用一致的信号名称；提示不包含“Noise 之后 / Rx CTLE 之前”等位置解释。当前 Run 的结果概览、Jitter 汇总、Run 输入比较放入“结果与存档”，Source 和 Noise 波形由模块入口打开。

### 实际交互与回归检查

- 四个测点的点击、悬停、标题反向选择和键盘 Enter 通过。切换测点保留参数模块、完整草稿与所选 reference；测点导航未发出 POST 请求。
- Slicer 仍位于 DFE 后，点击进入原有 DFE / Slicer 设置，Level 参数存在；该操作不会切换当前观察信号或修改草稿。
- Source、Noise、Channel 的模块入口分别打开原有 Source waveform、Injected noise、独立通道参考；其余模块继续用于参数编辑。
- 七种信号视图在普通测点可用；DFE Adaptation 和三个 CDR 视图仅在判决前信号加入菜单。从任一接收机专用视图切到 FFE 输出时回到 Eye + Impulse。
- 原 GUI 索引的 DFE / CDR statistics、Jitter Info 入口在上下文菜单重组后仍正确跳转。四信号比较保持原有通道参考、接收端输入、CTLE 输出、判决前信号四组数据，图标题不带字母编号，新增 FFE 测点不会误显示为参与比较。
- 结果菜单三个新入口均显示所选记录的原有内容并自动收起；1280×760 下菜单完整处于视口内，存档操作可滚动访问，Escape 可关闭。
- 1280×760、2545×1223 和 2560×1440 CSS 视口检查通过，均为 density=1，没有页面横向或纵向溢出，Slicer 与两张图完整可见，短提示未被信号链滚动区域裁切。截图在 Plotly SVG 与画布尺寸一致后捕获。当前物理屏幕为 2560×1440；2545×1223 延续此前实测最大化 Chrome 的内容区域。
- 最终 Chrome 控制台为 0 error、0 warning。JS 语法检查、4 项既有异步输入回归与 `git diff --check` 通过；实现文件和本记录为 UTF-8 without BOM。
- 服务核对为 0 条新 Run、2 条 reference、无活动任务。两条记录的 record ID、原始 run ID、input hash、source SHA-256 和 array byte count 与本轮开始时逐字段一致；没有重新仿真。

证据包括 `interaction-checks.json`、`legacy-comparison-checks.json`、`responsive-checks.json`、`service-checks.json`、`four-signal-comparison.png`、`results-menu-1280x760.png`、`implemented-2545x1223.png` 与 `implemented-2560x1440.png`。最终截图为 `final-1280x760.png`，左侧 Rx FFE、右侧 FFE 输出双图，Slicer 可见。

本轮视觉比较没有发现需要修复的 P0/P1/P2。IAB 自动化仍不可用，实际视觉与交互证据来自 Chrome / Playwright CLI；没有把打开请求的排队状态当作 IAB 验证结果。

final result: passed
