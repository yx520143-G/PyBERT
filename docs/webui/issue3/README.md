# WebUI #3：全链路原生分析与比较

owner 已完成实现、限定数值验证、fresh review 修复和桌面 Chrome 检查，等待 PM 验收；本文件不关闭 GitHub #3。只在本 Fork 的独立 worktree 开发，未改主工作区或 #2 的原始材料。

## 交付行为

- Channel 三种频响并列：raw/perfect termination、actual termination、trimmed impulse FFT；继续保留所有 h/s/p/H 单级与累计响应，DFE 始终注明最终权重等效 FIR。
- 原四点 Channel-only/Rx input/CTLE/DFE 与新增 Rx FFE 的 eye、Total/independent PDF、TIE amplitude spectrum/threshold、Info、crossing-jitter bathtub。Rx FFE 对真实 `ffe_out`、source `x`、局部 decision_scaler、原窗口和 PAM4 mask 独立调用 native helpers。
- Channel clean eye 与单独冻结的 GUI-compatible σ=1mV 显示噪声视图；物理 waveform、global RNG、原四点及 bits/noise 均不受影响。
- CDR 完整 `ui_ests` 的 100-bin histogram 和 legacy log10 spectrum；原 ps、f*UI、无 ×10/20 约定保留，零分母或归一化溢出明确不可用。
- 同 run 多点图表、两成功 run 的所选图表比较，使用各自物理 x 坐标，不按 index 叠加；eye 面板保留独立坐标并共用 count 色标。Expand viewer 提供完整图轴/图例；原 GUI 反查直接进入对应分析。
- schema3 在发布前一次构建全部分析与 availability/reason。schema2 已有 Rx input/DFE eye、DFE Dist/Spec/Info 和 Channel actual-termination H 继续可读；旧 Info 的拟合有效性为 unknown，旧 Channel 的三源视图缺失在单图与比较图图例中均明确标注。缺少新分析明确提示版本/数据不可用，切图不计算。

服务仍由 `uv sync --extra web`、`uv run --extra web pybert web` 启动。API schema1/raw schema3；`analysis_version=1`。原 worker/normalize 的单槽 spawn、合作取消与父进程 join/退出规则沿用 #2。完整档案/Load Results 仍属于 #5。

## 固定来源与联合冻结契约

| 项目 | 固定值/材料 |
| --- | --- |
| base/master | `35a3b60351836431e4f96136b61708515ec5f77c` |
| 原生语义 | `1bc905d577d2f3bd9471421cfbf3d422d4e6080e` |
| 产品代码提交 | `e9c73c5fa2de2e23b4f2b3c5a7a6e1b1a6825779`；后续交付提交只增加工具/证据/文档 |
| 本票初始冻结 | [frozen-manifest](fixtures/frozen-manifest.json)，SHA256 `457a66a4af98087eb5ad6ac4dfcfa103787d1bcb3cd035eab0133b272da12c5a` |
| 计算前窗口更正 | [window-correction-v2](fixtures/window-correction-v2.json)，SHA256 `5d06cc3b4ad6f2ef6cd7aea5d7723ce81b679c588551b764aa3a4403064a681e` |
| 控制仿真前 effective 冻结 | [identity-effective-v3](fixtures/identity-effective-v3.json)，SHA256 `ca18eb3234b414bb3cc05b9a055270de972805cc0c55ab4f42dba2fea54edd73` |
| 来源/执行版本适用表 | [delivery-applicability](evidence/delivery-applicability.json)，包含逐源码 hash、解释器/模块路径、原十文件与 commit blob 检查 |

初始补充表误把 PAM4 `ignore_until_s` 写为 2.42e-7；在任何新增 helper 计算前保留原件并追加 v2。原 raw 的 NRZ UI=100ps、Ts=3.125ps；PAM4 UI=200ps、Ts=6.25ps。两者 `ignore_until_s=4.84e-7`，sample window 分别为 154880/77440。builder 直接消费 raw context/window，不使用该错误常量。

identity 请求只改 NRZ 的 Ntaps=1/Npre=0、index0=1 与其余 tap disabled。原生 `PyBertCfg.load_from_file` 会按 Ntaps 强制同步 optimizer `ffe_tap_tuners.enabled`，因此 v3 在控制仿真前固定完整 effective 输入：index1..14 的 enabled 从 true 变 false，其余 bounds/pos 不变。Z0/rs/rin/min_mag_tune/max_mag_tune/step_mag_tune 的整数变为等值 float 属 JSON 表示变化；不是物理值变化。原 requested 文件、失败预检与 canonical hash 规则均保留。

#2 原 freeze SHA256 `f2bf44622304222455d0501235c230e11100e0cf2d6b0294b0b8284e33c51de9` 和十文件逐一匹配；两份 source NPZ/manifest hash 也匹配。完整 YAML、100 槽 taps、seed=1、非零噪声、窗口和原容差均未替换。单独的 display-noise 使用 `default_rng/PCG64` seed34003、σ=1mV、完整 waveform 长度 realization，缓存为 display dataset，不消费原生 global RNG。

## 数值与契约证据

[最终数值报告](evidence/numeric-20261024-061108/report.json) 的八项 execution source hash（7 个 `src/pybert/web/*.py` 文件及 `tools/verify_web_analysis.py`）与当前源码全部匹配。期望直接对完整保存数组调用 native `find_crossings/calc_jitter/calc_eye/make_bathtub`，没有调用 adapter 的 FFE/eye/CDR builder 生成期望。CDR FFT real/imag 分别比较；原数组的期望使用独立副本，能检查 in-place 修改。

| case | raw 数值＋typed metadata 检查 | display 检查 | 结果 |
| --- | ---: | ---: | --- |
| F-NRZ-01，保存 raw 派生 | 824 | 71 | 全过；max abs/rel=0 |
| F-PAM4-01，保存 raw 派生 | 827 | 71 | 全过；max abs/rel=0 |
| F-NRZ-IDENTITY，复用控制 raw | 513 | 71 | 全过；max abs/rel=0，28项 CTLE/FFE/上下文/物理 RNG 相等 |

raw 一栏包含逐字段身份/shape/dtype/window/版本检查，不表示有 824 个独立数值数组。PDF、时间/频轴、complex、eye/histogram counts、bathtub 正值相对误差/零值/floor 等仍按计算前冻结的分类门槛检查，未放宽容差。PAM4 的 native DD covariance 警告保留；新增 FFE 的 rjDD/mu_pos/mu_neg 单独显示 unavailable/raw reference，pjDD 与 bounded dj_pos/dj_neg 不连带失效。原四点旧 raw 缺拟合诊断，明确标 unknown，不反推成功。

唯一新增主仿真是 [060157 报告](evidence/numeric-20261024-060157/report.json) 的 identity task `80ecab74-7bd7-4cf9-8871-71752657ab2f`，succeeded、worker_exited=true、exitcode=0。后续 060425/061108 复用其保存 raw，仅补受影响的分析/显示/独立期望核验，没有再次运行主仿真。

- [contracts.xml](evidence/contracts.xml)：35 passed（25项原 Web 契约＋当时10项 analysis 边界），含真实 spawn/退出/忙状态。
- [analysis-boundaries.xml](evidence/analysis-boundaries.xml)：11 passed（原10项复测＋finite input 的 CDR normalization overflow）；无 crossing、短窗口、非有限/零 scale、nominal fold、零分母明确拒绝。
- [function-boundaries](evidence/function-boundaries.json)：9项通过；保存 raw 的函数级副本上检验 FFE 无 crossing、可用的原四点、CDR zero、DFE nominal fallback/counts 和分析组 callback 取消。它不是浏览器或进程取消证据。
- [MCP compatibility](evidence/mcp-compatibility.xml)：4 passed；配置 round-trip/未知字段/工具注册。[entrypoint smoke](evidence/entrypoint-smoke.json)：原 GUI view 可导入、无仿真构造 Ready、CLI sim --help 退出0。原 GUI/CLI/MCP/物理 producer 源码相对 base 未改；本票没有重新做完整原生 GUI 交互或 CLI 数值矩阵。
- 目标文件 `ruff --select E4,E7,E9,F`、compileall 通过；[最终静态检查](evidence/final-static-checks.json) 记录具体命令。证据目录的 `-text` 保留原始 CRLF bytes，暂存 diff 检查使用 `cr-at-eol` 识别行尾并通过，没有改写冻结原件。完整风格规则的 C408（dict literal 偏好）仍会报告现有 dict(...) 风格；没有把此检查写成完整 style lint 通过，也未为其重排相邻代码。

早期 [060028](evidence/numeric-20261024-060028/report.json) 为比较工具对 bool 减法的 TypeError；[060045](evidence/numeric-20261024-060045/report.json) 在 identity effective hash 预检停止，未运行该控制主仿真。原报告、其已写 raw、后续完整轮和源码适用关系均保留；不把早期失败重命名成通过。

## 实际任务生命周期与 Chrome

- [真实失败](evidence/lifecycle-failure-20261024-062215/report.json)：`193d929b-22ff-46bd-aaa1-6fcf0aa693b7`，错误 hash，failed；退出后释放槽。
- [真实取消](evidence/lifecycle-cancel-20261024-062247/report.json)：`cec1177a-0f8d-45a1-ad6a-47e88c7df4f0`，在 validation 前请求并被 worker 观察，随后真实退出/join；退出前 normalize/Run 均409。没有新增数值仿真，也不据此宣称中断了单次 SciPy helper。
- 两项均逐字节核对两成功结果的 raw hash 和完整 manifest 不变，旧所选结果仍保留。请求、task ID、日志、取消请求/观察/退出及原失败均有独立记录。

[Chrome INDEX](evidence/chrome/INDEX.md) 逐图限定支持范围与采集版本。测试使用真实桌面 Chrome、CSS viewport 1280×720；工具原帧为 JPEG、图像1265×712，原 bytes 保存并以 `view_image` 回读检查，未转成 PNG 冒充原帧。控件选择、稳定 run/标题核对、采集分别进行。早期图轴裁切、全局 SVG 描边、过小比较面板和旧 table 高度的原帧都保留并排除在相应最终通过证据之外。

为遵守“已有 raw 能派生则不重跑”，Chrome 的两个 case 通过 [test-only hydration 工具](../../../tools/serve_web_analysis_evidence.py) 放入独立临时 `Tasks` 缓存：`F-NRZ-01`/`F-PAM4-01` 是固定 case 的显示身份，不是假称本票新点击 Run 的 task ID。正例来自完整 #2 原生成功 raw，经本票 helper 统一派生；legacy 检查另外消费未扩展的真实 schema2 raw。此工具不是产品 Load Results/磁盘档案功能。生产启动仍使用 `pybert web`，不自动载入这些测试材料。

## 复核与边界

[fresh review](evidence/review.md) 的 DD 有效性、GUI 反查 route 和 CDR 除法后 finite 三项已修复；route fall-through 又经同一只读 reviewer 确认闭环。最终兼容性自查补回旧 schema2 Info/Channel H，reviewer 提出的比较图限制说明丢失也已通过图例与 metadata 修复并确认。Chrome 另外发现的 SVG 描边/图例、eye count 色标/面板尺寸、表格高度问题由 owner 修复。

不改原四点顺序或物理算法，不扩至文件/AMI/COM/优化/Viterbi 等后续票。PAM4 jitter 仍是 symmetric 0V crossing 边界；DD 是参考拟合，bathtub 使用 separated Rj 与 bounded jitter，不是完整电压裕量/BER、MATLAB COM correlation 或 IEEE 资格结论。

本票 raw 仅保留在本机 ignored NPZ，逐项 hash/bytes 见 [raw-files-local](evidence/raw-files-local.json)。此时18份共587,927,522 bytes，包含失败、旧投影和服务测试缓存；未清理 #2 或本票原件，不把临时结果称为完整档案。
