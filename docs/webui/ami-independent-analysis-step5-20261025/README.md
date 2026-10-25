# 第 5 步：F6 AMI 独立分析与保存合同

状态：F6 软件实现与验证完成。同一位 Astra 的 [Standards / Spec 最终审查](astra-review.md)均为0项待修问题；独立复跑151项测试和15项子检查通过，15个候选文件身份匹配。真实 AMI 验收继续暂缓。本步仅本地提交，不提交远端、不运行真实模型 DLL。

## 范围与语义

本步实现最终修改清单 F6：Main 波形、真实采样、BER、Eye、period histogram、period spectrum 各自报告可用性。某个可选分析不足，不再自动否定其他有效结果。执行错误、取消、损坏来源、未知进度仍失败并保存 partial 原件。

新实际 NRZ Rx GetWave 时钟路径明确使用 producer 3：一次 Init、原两次 probes、原 Main、最终 Close 的流程不变；具备完整 F5 receipt 和 NRZ profile 时启用同 epoch 映射采样。这替代 F5 的临时 `unsupported_pending_contract` 消费门槛。`available` 只表示本次执行和该项数据条件满足，**模型资格仍为 UNKNOWN**，不是独立数值验收或硬件 PASS。PAM4 未声明 profile、AMI+Viterbi、缺失或失败 receipt 不开放；all-epoch-empty 保留原 Native fallback，非空但全部落在 Main 之外不 fallback。

| 对象 | 新合同 | 保留的限制 |
|---|---|---|
| Main | 原流程确实完成后才 completed | 不能由采样器代替 Main 宣告完成 |
| 采样 | 保存每个实际 sample / decision / bit；循环结束可 completed，0 点为 unavailable | decide 异常或取消仍 partial；不补点、不补 bit |
| BER | 不足时内部 Int 为 −1、Web count 为 null，并保存原因；清除旧 auto_corr / errors | 原 W、最后 W 决策和原 calc_ber 对齐算法不变 |
| Eye | 两处 Web consumer 及 native helper 分别核对自身实际 crop | 保留原 W−2（至少1）trace 门槛和单条2 UI宽度；没有改为少量 trace 即通过 |
| Histogram | 冻结窗口内已知 grid period 可用即计算 | 原100 bins、每 grid sample 一票，不冒充每 edge 一票 |
| Spectrum | 固定窗口内 period 全已知且网格条件满足才可用 | 不缩窗、不挑连续片段、不填未知值 |

Native CDR 绕过时保留空 lock 数据并标 unavailable，不用 readiness 或零值冒充模型锁定。真实计算异常不会被统一吞成正常 unavailable。

## 时钟坐标

F5 的 epoch target、epoch sample、一次舍入 readiness 阈值贯穿消费和读回；Main-local target 供展示，不能重新用其差值决定 ceil 或 readiness。冻结窗口若精确等于一个原 Main grid timestamp，使用该样点的 `(N_pre + index) * ts` epoch 坐标；非网格边界使用一次舍入的实际前置时长加原边界。保存实际 epoch bounds 和规则，不使用 epsilon、近似吸附或改写原 ticks。

定向回归发现并修复：`N_pre=344, ts=.1, Main=166, raw tick=50.7, UI=.4` 的末样点本来被 F5 正确保留，但把 Main stop=16.5 独立换算成50.9会再次排除 epoch sample=50.900000000000006。新规则保留 index165 和零量化延迟；首边界、readiness、消费和保存读回均有测试。

## 保存与旧档

新结果必须同时具备 raw7、`ami-clock-independent-v3`、clock contract3、producer3 和 same-Init NRZ 来源；decoding schema3 独立表达 BER unavailable。旧 raw6 / contract2 / decoding1–2 继续由原严格 reader 解释，不重标历史失败，不降到 raw4。

原始 ticks、每 tick 来源、epoch/local 坐标、实际样本、decisions、bits、mask、分析索引与边界存放于 primitive NPZ。调用账中的 clock 区段指向固定原数组；不序列化模型或可执行对象。读取验证 receipt、映射、waveform 采样身份、固定窗口、metric 状态及数组引用，不调用模型、slicer、Eye、histogram 或 FFT 重建结果。NaN 仅允许 `ui_ests` 的严格 bool mask 例外，其他数组仍要求有限值。

集成用例走实际 `my_run_simulation → collect → archive.save/load`，AMI helper 为明确标识的合成替身。原 source manifest 和 NPZ 文件字节、逐数组 dtype / shape / bytes / hash 必须完全相同；不使用 allclose 替代。epoch、indices、mask、version、feature、资格、BER count、Eye count 篡改必须拒绝。

## 验证与浏览器

- 新用例覆盖完整结果、BER不足但histogram可用、BER可用但FFT窗口缺口、单点全未知period、无in-record tick、all-empty Native fallback、真实判决异常和取消、重复运行清除旧BER状态、native绘图helper、F5边界贯穿读回。
- 直接调用保留的 D2 raw6 mask / producer / archive 用例，历史文件不修改；raw6 completeness=false 仍拒绝。
- 最终候选 **151 passed、15 subtests passed、35 warnings**；[final-validation.log](final-validation.log) 为最后一次完整定向执行，耗时13.57秒。[validation.log](validation.log) 保留前次输出，包括一次测试文件名拼错导致的0项收集；0项不计为通过。保存的终端与浏览器文本仅清除行尾空白，未改动测试结论或页面文本。
- [lint-delta.json](lint-delta.json)：Ruff 0.17.2 对14份 Python 文件按 code / message / 源行与父基线比较，当前49项、基线49项、零新增；没有自动修复旧告警。两份 JavaScript 的 `node --check`、`git diff --check`、UTF-8 without BOM 检查通过。
- [software_browser_fixture.py](software_browser_fixture.py) 只生成四个明确 `SYNTHETIC-*` 的档案供本地浏览器检查；原始运行数据生成在临时目录，未加入产品仓库。
- 浏览器验证属于软件展示证据，不是实际模型数值证据。`full` 全部可用；`ber_short` 保留 Main / samples / histogram，但 BER / Eye / FFT 不可用；`fft_gap` 的 BER 可用而 FFT 不可用；`future` 无实际采样但保留 Main。Run overview 保留资格 UNKNOWN，比较和 trellis 均明确显示 BER 不可用原因，未显示为0。保存了[状态总览](browser-ber-unavailable.png)、[已知周期直方图](browser-histogram.png)、[比较视图文本](browser-comparison.txt)。本次没有在页面点击 Run；临时8769服务在验证后已停止并核实端口无监听。

定向测试集合：`test_ami_single_init.py`、`test_ami_getwave_params.py`、`test_ami_parameter_projection.py`、`test_ami_clock_origin.py`、`test_ami_clock_traits.py`、`test_ami_partial_analysis.py`、`test_ami_partial_main.py`、`test_ami_partial_legacy.py`；使用既有资源环境的 `uv run --no-project`，指定本工作树 `src` / `PyAMI/src` 和既有 `PyChOpMarg/src`，未新增依赖。最终产品/测试候选身份见 [candidate-sha256.json](candidate-sha256.json)。

## 文件与依赖

精确产品和测试文件清单（本目录另保存验证证据）：

```text
src/pybert/models/bert.py
src/pybert/pybert.py
src/pybert/utility/ami_clock.py
src/pybert/web/ami.py
src/pybert/web/analysis.py
src/pybert/web/archive.py
src/pybert/web/clocks.py
src/pybert/web/clock_v3.py
src/pybert/web/data.py
src/pybert/web/viterbi.py
src/pybert/web/static/viterbi.js
src/pybert/web/static/workbench.js
tests/test_ami_partial_analysis.py
tests/test_ami_partial_main.py
tests/test_ami_partial_legacy.py
```

Python 代码和 native GUI 状态/辅助绘图有窄修改；Native DFE/CDR/Viterbi 算法、PyAMI 子模块、依赖声明、lock 文件没有修改。父基线 `27a75c5368c04034ba5b4f24cc70714e8895361b`，PyAMI 保持 `dfae46033f490c9d19f2684454b6fe9bd90d9a72`。没有启动真实 DLL、COM、优化大搜索或安装依赖。
