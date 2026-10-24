# D1：Native AMI clocks 采样与分析消费

2026-10-25。当前仅实施 #10 的 D1 阶段；[PM 完整合同](D1-contract-comment.json) 覆盖固定设计 §5/§6 的旧排程和执行限制。起点为 `9343cdb7a2eee1762a60ae284d1e3a48772729d4` / tree `486768d95e04717f3726e8fd98cf1e36dd59fc98`，PyAMI F2 及其他依赖不改。startup 原件在 [startup.json](startup.json)，此前 clean、独立 Git metadata；子模块未初始化。

采用实际 grid times 为 AMI canonical，producer absolute indices 供 Viterbi/Eye 复用；edge/target/量化延迟另留。全记录逐 tick 消费与冻结的双边界分析窗分开；format-valid、eligible、实际完成/partial 分开。period 保留 mask/NaN，histogram 只用窗内 known 值，FFT 只用预冻连续全 known 原 grid 子窗。Native 默认规则、C1 与 A 不扩改；D2/E 不提前。

当前生产配置缺少 PAM4 提供方对 Ignore 单位、zero nominal eye offset 及 native slicer mapping 的确认和输入承载合同；不添加模型白名单或默认认证。生产 PAM4 timed clocks 将明确 unsupported/UNKNOWN，软件矩阵可使用明确声明的 symbol-UI/零 offset profile。NRZ bit/UI 无歧义。该缺口已报告 PM，真实模型资格仍待后续。

既有 CDR period 线共享 waveform 的降采样 `t_ns` 轴；为避免 masked full-grid 数据与该轴长度不符，D1 必要图消费接线包含 `gui/plot.py` 的一个独立 period 时间键，Native 仍填原降采样轴，不改图布局/控件。

先按 [NumPy 安装计划](numpy-install-plan.json) 在新 `.venv` / cache 只安装 lock 对应的 NumPy 2.5.1 wheel，使用 frozen URL/hash、no-deps、copy 模式。实际 NumPy 模块 import/小数组执行待 source/test/runner/cases/guards/逐函数预算冻结并 commit 后开始，不以隐藏 version check 消费预算。runner 专用测试从一开始位于 evidence 下，不进入默认 pytest 收集树。

累计执行上限：planner/consumer/pure 投影 helper 合计 1000 次，calc_eye（含 baseline）128 次，histogram/rfft 各 64 次，动态批次 12 次，每批 timeout60s；单输入/FFT 长度≤4096、Eye height≤64、nspui≤32。实际 NumPy 活动及其 C 扩展加载与模型 DLL 分开记录，不称“0数值”。完整 Main/引擎/DFE/decode/PyAMI/grammar/模型/C DLL/COM/coopt/Web/GUI/服务/root pytest/fullsuite 均不执行。

启动与依赖准备成本保留；clone/switch 内部 elapsed `50.4921535999747 s`，整任务 wall/peak RSS UNKNOWN。首次较宽源码/lock 展示被工具截断，已用限定源码范围和目标 wheel 的新只读观察补足，不冒称恢复完整首次输出。全部旧 #30 原件、v1/v2、617339 B 本地原日志、环境及历史失败/费用保留。D1 完成后仅本人 fork 的一个 Draft PR，Refs #10，不关闭 #10；独立两轴自审、固定停写后交 PM fresh review。

## 第10批冻结前状态

01–09 共9批（含5个red）已实际执行，累计pure169、calc_eye15、histogram0、rfft0；NumPy import9。第10批冻结完整6个test methods，预计pure141、calc_eye15、histogram8、rfft5。所有实际source/test/runner及三份新增baseline快照由test-plan绑定，先commit再执行；完整Main/DFE/GUI等仍0。

第10批开始保存actual return-or-exception状态及lossless dtype/shape/C-order数组原bytes（每块≤65536B），不把return event当作正常完成。01–09没有该完整数组观察，不事后补造。静态AST检查单独记在bootstrap/05-binding-static，无NumPy或产品定义执行。一次只读git diff展示因subprocess默认GBK解码失败，工具转录保留该UnicodeDecodeError；后续限定源码读取和UTF-8 bytes decode完成核对，未触发动态批次。

## D1 实现与交付边界

AMI producer 保存 edge/target/实际 indices、grid times、量化延迟、Ignore readiness、实际消费与partial、known period及窗口；consumer逐tick消费，包括可用末tick。AMI Viterbi使用窗内最后W个实际索引，Eye使用当前裁剪后的相对索引；Native旧W+1规则与calc_eye旧入口保持。Main每run新建Traits producer状态，读取真实Rx Ignore_Bits，异常保留当前实际部分；合法empty才能Native fallback。实际Native fallback/整链返回由接线状态区分，但本阶段没有执行该引擎。

period原秒值/known mask及实际grid在producer中保留，self.ui_ests仍为ps。AMI图线成对发布full-grid ns与同长ps/NaN，histogram仅使用冻结双边窗known值，FFT限定预冻连续全known窗，轴为k/(n_fft*ts)。零fundamental保留raw FFT并明确display unavailable。Native写原t_ns_plot/ui_ests_plot，不改变共享波形轴、其他图线/布局/控件。Chaco6.1.1的update_data单事件API仅做源码核对，实际PlotData由普通stub替代，不称像素验收。

生产PAM4非空timed请求仍unsupported/UNKNOWN：缺提供方Ignore_UI单位、零nominal eye offset、Native slicer mapping三项声明及其生产输入合同。软件手工profile只证明软件约定，不认证真实模型。D2 Web/两个Eye/CDR/finite/raw/archive/metadata与E真实资源配对仍待串行阶段。#10保持开放；默认COM大搜索及最终数值review边界不变。

## 实际执行与成本

10批全部原件保留；5个red是功能TDD失败，未重标为通过。第10批冻结commit为418d72bcd63932dd7e456c9fd3c77525d0a4cf42；其实际source/test/runner与当前逐字节绑定见verification.json。最终green6 methods，0 failures/errors，128个lossless array blob及return-or-exception观察记录；Python return event单独不证明正常完成。

| 批次 | exit | pure | calc_eye | hist | rfft | child elapsed(s) | launcher elapsed(s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 01-planner-red | 1 | 0 | 0 | 0 | 0 | 2.024823200 | 2.249740400 |
| 02-planner-green | 0 | 2 | 0 | 0 | 0 | 2.018043800 | 2.223991800 |
| 03-planner-contract-red | 1 | 50 | 0 | 0 | 0 | 2.200430600 | 2.418558200 |
| 04-planner-contract-green | 0 | 70 | 0 | 0 | 0 | 2.268094500 | 2.495333000 |
| 05-consumer-red | 1 | 0 | 0 | 0 | 0 | 2.164925500 | 2.409367300 |
| 06-consumer-green | 0 | 43 | 0 | 0 | 0 | 2.305052400 | 2.535803500 |
| 07-eye-red | 1 | 0 | 0 | 0 | 0 | 2.267005300 | 2.479350500 |
| 08-eye-green | 0 | 4 | 15 | 0 | 0 | 2.402356600 | 2.619473600 |
| 09-period-red | 1 | 0 | 0 | 0 | 0 | 2.380742600 | 2.640221200 |
| 10-integration-green | 0 | 141 | 15 | 8 | 5 | 34.802327800 | 35.045675000 |

累计实际 pure **310/1000**、calc_eye **30/128**（baseline8、candidate22）、histogram **8/64**、rfft **5/64**；动态批次 **10/12**，单批timeout60s，全部正常返回，无guard/timeout失败。NumPy普通import10次，每批实际记录3个NumPy .pyd及import阶段ctypes事件；这些是实际软件数值和平台加载，不能称0数值或完整系统trace。单输入/FFT≤4096、Eye height≤64、nspui≤32，RNG draw/seed0；普通Python decide/cancel/PlotData stub逐批单列。

child内部elapsed合计 `54.83380230006878` s；launcher合计 `57.117514500016114` s，二者包含关系，不能相加。clone/switch50.4921535999747s，venv0.30824099999153987s，NumPy安装5.7882642000040505s；静态失败/重观察和audit费用另见各receipt。整任务wall、peak RSS及完整系统library trace **UNKNOWN**。

完整PyBERT构造/Main/my_run_simulation/update_results、DFE/run_dfe、Viterbi/FEC decode、完整run_ami_model/PyAMI/model module、grammar/SciPy/其他DSP、model C/DLL/COM/coopt、Web/GUI/CLI/服务/浏览器/资源下载编译均未执行；未运行pytest/root collect/fullsuite/旧安装矩阵。AST接线比较不升级为真实整链或模型资格。

## Standards

独立只读审查固定68bbd56129e4999273bce3fabd694dec3d8cf79f/tree57be400d41272e6f104d6c8b2298fbfdc3d87298：hard0、actionable heuristic0，无阻断项。完整轻度排版报告见review.json；一次read-only StopIteration展示失败保留工具转录，限定源读取完成后无数值入口。审查未写源码。

## Spec

独立只读审查同一固定候选：missing/partial0、scope creep0、implemented wrong0，无可复现合同违背。结论限于源码和有界软件证据，不证明Main/DFE/GUI/模型验收。两轴各0项、各轴均无最严重未解问题；source/test/runner审查后未改，不为耗尽预算重跑。

## 原件保护与最终封存

verification.json核验15个旧repo HEAD/tree/default status、252项metadata、4874项旧raw、1008项材料/安装源码、14个旧env/cache目录及#30 v2 seal保持，失败0；新NumPy安装950文件hash保持。所有失败、raw、环境、cache均保留。verify_evidence.py只用stdlib/Git读源，不执行产品/NumPy定义。完整manifest和最终HEAD/tree/clean/raw与Git blob关系将由本阶段新cache下的final-seal.json固定并交PM；seal在最终commit之外，避免自引用。

最终文档staging发生一次静态check失败：将bootstrap stdout原bytes复制为派生verification.json时保留了CRLF，被Git判trailing whitespace。bootstrap/07保存同一staged输入修复前的新只读完整再观察（exit2），首次完整输出缺口如实保留；原bootstrap raw不变，仅派生JSON按同一对象重新写LF，不扩大whitespace豁免。无数值/测试复跑。
