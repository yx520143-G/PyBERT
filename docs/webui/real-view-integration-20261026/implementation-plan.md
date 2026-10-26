# WebUI 真实计算与视图实施计划

日期：2026-10-26。目标：用户修改参数后手动点击 **Run**，由现有 PyBERT 原生引擎完成计算，新 WebUI 显示该次运行的真实结果，并能追溯输入、数据来源和分析窗口。本轮仅形成计划，没有新增仿真或修改产品代码。

推荐从“固定同一版本的前后端并完成真实 Run 验收”开始。当前已经有计算接口、独立 worker、结果存档和绘图读取链路；新 Run 的闭环可能不需要新增产品代码。仅对验收中确认的缺口做局部修改。

## 当前状态与实施基线

源码基线为 [PR #35](https://github.com/yx520143-G/PyBERT/pull/35) 的 `16ee4f406146a2d92fd1190b65913e24a8730b8b`，其基分支提交为 `108b4d5d4fa7f8fad69dbc0d263608011f98b0cf`。PR #35 的产品差异为五个静态文件，已经包含新双图调用和手动 Run 入口。[PR 交付说明](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/docs/webui/webui-design-20261026/README.md#L5-L25)

2026-10-26 的[只读现场记录](runtime-readonly.json)显示：本机 `127.0.0.1:8797` 在线，五个静态文件与上述提交的内容在换行规范化后相同；当前有 **0 个新 Run、2 个历史 archive reference、无活动任务**。最近任务为成功的 normalize，不是失败的 Run。两份 reference 的原始 producer 都是 `108b4d5`，Native NRZ、10 Gbps、15000 bits、32 samples/UI、EyeBits 10160、seed 1；Channel length 分别为 2 m / 1 m，CTLE boost 都为 10.7 dB。已读取的 Channel / DFE impulse 和 Eye 均 available，包含真实数据数组。因此当前图表已有真实历史结果，下一步要验证的是“当前草稿产生新结果”的完整流程。此次现场检查为 HTTP/API 只读检查，没有进行新的浏览器视觉验收。

`/api/version` 的 `native_sha` 是历史来源常量，`adapter_sha()` 从当前磁盘仓库读取 Git HEAD；它们单独不足以证明已运行进程加载的全部模块来源。实施时应固定 checkout、核对实际模块路径和源码 hash，再启动新的验收进程。[来源常量](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/__init__.py#L3-L9)、[实际源码身份](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/data.py#L71-L91)

## 已有真实计算链路

```mermaid
flowchart LR
  A[编辑草稿] --> B[原生 normalize 校验]
  B --> C[用户点击 Run]
  C --> D[冻结完整配置及输入身份]
  D --> E[独立 worker 调用原生仿真]
  E --> F[采集原始数组与分析结果]
  F --> G[manifest 与 arrays.npz]
  G --> H[绘图接口读取所选记录]
  H --> I[Eye / Impulse 与其他视图]
```

1. **输入与启动已实现。** 前端 Run 再次等待 normalize，提交完整 config、input hash、identity hash、资源绑定与 draft revision；后端 normalize 复用原生配置加载和 observer，Run 路由调用 `Tasks.start("run", request)`。[前端提交](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/static/workbench.js#L394-L403)、[原生校验](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/config.py#L378-L487)、[路由](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/server.py#L63-L77)
2. **原生执行已实现。** `Tasks` 使用 spawn；worker 创建 fresh PyBERT，核验 requested/effective input 后调用 `my_run_simulation`。结果必须经过实际完成检查及采集，父进程在 worker 退出、join 并确认 manifest 后才发布成功。[任务启动](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/tasks.py#L28-L128)、[真实计算](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/worker.py#L94-L180)、[成功发布](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/tasks.py#L170-L214)
3. **数据采集与绘图已实现。** `collect` 保存原始数组、原生分析结果、物理轴和 metadata，生成 `arrays.npz` / `manifest.json`。绘图 GET 从这些文件读取，不调用仿真。新双图请求同一所选记录的 impulse 与 Eye，直接把服务器的 `chart.data` 交给 Plotly。[保存](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/data.py#L424-L490)、[只读投影](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/data.py#L494-L542)、[新双图](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/static/workbench.js#L193-L217)

## 各视图应显示什么

| WebUI 入口 | 已有绘图 ID / 原始来源 | 实施中要保持的含义 |
| --- | --- | --- |
| 通道参考双图 | `chnl_h`、`eye.chnl`；`chnl_out` | 理想激励经 Channel 的独立参考；默认 clean eye |
| 接收端输入双图 | `tx_out_h`、`eye.tx`；`rx_in` | 累计响应及实际 Rx input，包含当前链路适用的 Tx / noise |
| CTLE 输出双图 | `ctle_out_h`、`eye.ctle`；`ctle_out` | 当前 Run 的 CTLE 输出；关闭 CTLE 时保留真实旁路结果 |
| FFE 输出双图 | `ffe_out_h`、`eye.ffe`；`ffe_out` | 实际 Rx FFE 输出；独立测点仍可访问 |
| 判决前信号双图 | `dfe_out_h`、`eye.dfe`；`dfe_out` | DFE 求和节点；impulse 是最终权重等效 FIR，不是实时非线性自适应过程 |
| Source / Noise | `wave.x` / `noise`；`context.source.x`、base noise、适用的 FEXT 分量 | 来自所选 Run 的实际激励和噪声；不以当前草稿重新生成示意波形 |
| Jitter / DFE / CDR | `jitter.*`、`adaptation`、`cdr`、`cdr.histogram`、`cdr.spectrum` | 使用各自保存的窗口、轴、单位和 availability；CDR spectrum 保留原 legacy log10 ratio |

上述映射来自 [observation 定义](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/analysis.py#L15-L23)、[响应及波形采集](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/data.py#L167-L265)、[Eye 生成](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/analysis.py#L235-L290)、[CDR 分析](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/analysis.py#L292-L362)。

“真实”不要求浏览器与原 GUI 像素相同。原始波形保持完整；Web 波形采用末 20 UI 的原样本投影，Native CDR 曲线最多取 4096 个索引。Impulse 单位为 `V/sample`、横轴 ns；Eye 横轴 ps、纵轴 V、矩阵为 count。不得由前端再次除以 Ts、重采样或按数组索引强行对齐。[显示投影](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/data.py#L180-L224)、[CDR 取点](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/data.py#L390-L397)、[Eye 坐标](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/analysis.py#L265-L282)

## 实施顺序与成功标准

| 步骤 | 具体工作与可能涉及的文件 | 通过标准 |
| --- | --- | --- |
| 1. 固定可复现运行入口 | 使用包含 PR #35 及其完整基线的 checkout；核对 Python / PyBERT / PyAMI / PyChOpMarg 实际模块路径、提交与 hash、依赖版本。复用已有环境与 `pybert web --port`，在独立端口和独立结果目录验收，先保存当前 reference | 静态文件、已加载后端和 worker 源码来自同一声明版本；原服务及两份 reference 保留。此步优先补启动说明和验证脚本，不新增计算 API |
| 2. 真实 Run 到新双图 | 在新页面加载明确的 Native 配置，点击 Run，等待任务完成；依次选择五个测点及 Source / Noise。必要修改集中在 `workbench.js`、`layout.js` 的事件/记录绑定 | 真正新增 run ID；worker 已退出、task succeeded；双图共享该记录的 run ID / input hash；物理轴与返回数据一致；未使用旧 reference 冒充本次结果 |
| 3. 参数变化与数据来源 | 固定 seed，改变一项实际生效参数；Run 前保留旧图并提示输入已变化，Run 后显示新记录。比对 Native NRZ/PAM4 原始数组与直接原生调用；核查 API → Plotly 的坐标和值 | 相同完整输入的配对结果 dtype、shape、数组 bytes 一致；参数变化后的 requested/effective input 和相关结果可追溯。发现差异先定位，不以放宽容差、裁剪数据或截图相似替代 |
| 4. 状态、竞态与归档 | 扩展 `tests/web_workbench.test.cjs`，覆盖切换记录/测点的迟到响应、单图 unavailable、无记录、当前任务失败；复用 API/归档测试。真实结果保存后重新打开 | 迟到响应不能把 A Run 的 Eye 与 B Run 的 impulse 混在一起；不可用项显示原因，其他有效图保留；只读切图与重开不新增 Main，存档数组身份保持 |
| 5. 收敛与交付 | 只修复前四步证明存在的问题；收集浏览器操作、网络请求、运行记录和数值比对报告。验收后单独处理最终集成选择 | 有可复现启动步骤、至少一组 NRZ 和 PAM4 新 Run、参数变化闭环、归档重开证据；报告明确已通过与未执行范围。产品改动保持可独立审查 |

CLI 已提供本机绑定的 `pybert web --port`，`web` extra 已声明 FastAPI / Uvicorn / Plotly，静态文件也已配置 package-data，故无需先重写 launcher 或更换前端框架。[CLI](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/cli.py#L61-L70)、[依赖与打包](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/pyproject.toml#L67-L75)。现有 CLI 默认使用临时结果目录；若验收需要固定目录，可复用 `create_app(Tasks(directory))` 的现有接口编写最小本地启动脚本，无需扩展产品配置面。[现有接口](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/server.py#L22-L25)、[目录管理](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/tasks.py#L28-L44)

先在固定 PR #35 head 上验收；最终合入是独立的集成决策。当前 base `108b4d5` 相对核查时的 master `ab36b65` 多 7 个提交，涉及先前 AMI 与依赖修改；这些不计入本次 UI 接线工作量，也不要求为显示 Native 结果先恢复真实 AMI 验收。[固定提交比较](https://github.com/yx520143-G/PyBERT/compare/ab36b656a61cb6866da98105d72f6cacfb118031...108b4d5d4fa7f8fad69dbc0d263608011f98b0cf)。实施命令必须显式指定此固定源码目录或其隔离 checkout，不能依赖当前终端默认工作目录。

## 首轮有限验证矩阵

先执行输入、结果读取和前端状态测试，再进行有界的真实运行。以下是建议执行范围，不表示已经完成。

| 用例 | 真实计算次数 | 验收重点 |
| --- | --- | --- |
| A：Native NRZ 基线 | 浏览器点击 Run，Web Main 1 次 | 固定非零 seed、完整 normalize 快照；五测点双图和其他已开放分析读取同一结果 |
| B：A 只改一项实际生效参数 | 浏览器点击 Run，Web Main 1 次 | 建议 CTLE boost；保持 Tx/Rx Native、CTLE 已启用；Run 前 stale，Run 后新身份与相关结果变化 |
| C：Native PAM4 基线 | 浏览器点击 Run，Web Main 1 次 | 使用原生 normalize 得到合法完整输入，选取 EyeBits < Nbits、偶数 bit counts / NspUI；保留 PAM4 四电平及三眼区的含义和实际物理轴，不要求眼睛一定张开，也不由前端补画 |
| A / C 对照 | 直接原生 Main 各 1 次 | 同源码、同环境、同配置和 seed，调用原生加载/仿真/结果更新；逐数组比较，不重写参考算法 |
| 记录切换、视图切换、放大、归档重开 | Main 0 次 | 五测点、四信号比较、Source / Noise、Jitter / DFE / CDR、保存重开；核对数组和来源身份 |
| 校验拒绝与不可用分析 | 通过定向测试和已保存数据覆盖；不追加常规 Main | 无效输入不发布成功 Run；缺图有原因；当前失败不覆盖已有成功记录 |

首轮建议最多 **3 次 Web Main + 2 次直接原生 Main**。输入使用已确认的小型 Native 场景并在运行前冻结；不把这个预算扩展为扫参。具体耗时和峰值内存以实际记录为准。失败即停止后续矩阵并定位，保留失败与成本，不自动扩大执行范围。

A/B/C 必须由新 WebUI 的真实浏览器 Run 按钮触发，捕获实际 POST 的 config / input identity、返回 task ID、完成后的所选记录更新和 Plotly 数据；不能只以脚本调用 `Tasks.start` 代替前端验收。A/C 的直接原生调用仅作为数值对照。运行测试前应检查所选测试是否实际调用 Main；若会调用，计入同一预算并调整矩阵。软件替身的错误/取消测试单列，不冒充真实数值运行；不直接运行未经计数的完整集成套件。

现有测试可复用：`tests/test_web.py`（原生 observer、spawn、生命周期）、`tests/test_web_analysis.py`（轴/来源、Eye unavailable、CDR window）、`tests/test_web_archive.py`（dtype/shape/bytes、损坏拒绝、reference 不变）以及 `tests/web_workbench.test.cjs`（草稿校验竞态）。新增测试针对新双图和记录绑定，不复制计算公式。[输入与任务测试](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/tests/test_web.py#L39-L187)、[分析测试](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/tests/test_web_analysis.py#L40-L120)、[归档测试](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/tests/test_web_archive.py#L61-L86)、[前端测试](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/tests/web_workbench.test.cjs#L76-L123)

此前已有 Native NRZ/PAM4 GUI producer / Web worker 数值一致性证据，可复用其输入冻结和比较方法；它不是本次新前端的完整运行验收。Channel display noise realization、波形投影和 Eye 坐标的既有显示差异应按原有合同解释。[历史数值与显示报告](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/docs/webui/final-numerical-review-20261025/README.md)

## 结果保存与范围边界

每个成功 Run 完成后，立即保存完整 `.pybert_run`、manifest、raw arrays、输入 YAML/JSON、任务日志、源码/依赖身份和测试报告，再开始下一次运行。当前服务只缓存最近两个成功 Run；第三次成功会移除最早的临时结果目录。不能等三次运行结束后再统一取证。[两记录缓存](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/tasks.py#L194-L213)、[完整归档与 raw 导出](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/server.py#L271-L297)

保留现有 4 reference / 总 1 GiB 数组限制，不为验收扩大缓存；保存与重开不等于重新计算。归档来源、原 run ID 与当前 reference ID 分别记录。[reference 限制](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/records.py#L14-L46)

本次实施先覆盖 Native 的真实运行与新视图。真实 AMI 模型验证继续暂缓；默认 COM 的 139,756,144 候选搜索不恢复；Viterbi 视图维持已收起的范围，旧配置值不静默改写。验收专用输入显式设为 Native、COM 关闭、Viterbi 关闭，不改变用户已有草稿。需要外部 Touchstone、package 或优化结果的后续用例，按已支持能力单独追加，不能把默认 Native 跑通外推到全部模型和通道。

现有后端明确拒绝 nonzero `impulse_length`、启用的 CTLE File、package + FEXT 等未支持执行组合；真实视图应展示拒绝原因，不以默认值或示意曲线替代。[运行预检](https://github.com/yx520143-G/PyBERT/blob/16ee4f406146a2d92fd1190b65913e24a8730b8b/src/pybert/web/config.py#L173-L191)

实施完成的判据是：用户能在固定版本的新 WebUI 中修改参数并点击 Run，获得具有完整来源身份的新真实结果；所有开放视图按原生数组、物理轴和可用性显示；改变显示方式不重算或改变原数据。此判据不包含真实 AMI、默认 COM 大搜索或硬件/标准资格认证。
