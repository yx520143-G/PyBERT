# #30：目标 Rx GetWave 的独立 probe/main 协调

2026-10-25（Asia/Shanghai）。[live #30](https://github.com/yx520143-G/PyBERT/issues/30) 完整合同保存在 [issue-30.json](issue-30.json)；固定设计为 `e0e6424f606ef28ebd217ac8c14098b1962a9ea4` 的 §4/§6，原文 Git bytes 在 [inputs/fixed-contract-README.txt](inputs/fixed-contract-README.txt)。本票交付 C1 软件协调，不是有效 clocks、模型 ABI 或 NRZ/PAM4 数值资格。

## 来源和选择范围

全新独立 clone `E:/serial-bus-simulator-dependencies/pybert-issue30-probe-main`，branch `codex/pybert-issue30-probe-main`。起点 `3d942f30d892e038a2b52b5e876d11d94c511820` / tree `c5c0b8b4828ebf666eb571aa5fde7cc409c651a3`，写证据前 clean。独立 .git、无 alternates、objects link1；两个新子模块的 metadata 仅在本 clone 的 .git/modules 下。见 [startup.json](startup.json) 和 [bootstrap-plan.json](bootstrap-plan.json)。

PyAMI 仍为 F2 `d6d1f7fe7e58536546a1cfb9430c750cc2cb103e` / tree `1a74ae9844f657e5567c435345fdd561a1f747fe`；PyChOpMarg、gitlinks、.gitmodules、direct URL、uv.lock、许可证及 hooks 均不变。没有重复安装矩阵或修改依赖。只在新 clone 的本地 config 使用 PyChOpMarg HTTPS 传输 URL。

六个 helper 调用点中，仅 `models/bert.py` 的 Native/AMI_Init Tx + Rx GetWave 调用传入内部 keyword-only `_probe_seed=self.seed`。选择条件不依赖 rx_use_clocks，两值均覆盖；Tx GetWave、Rx Init、Native Rx 和其他五个 helper 调用点不附带改变调度。没有新 UI 开关。

helper 原九个 positional 参数、默认值与六元返回结构保留。`_probe_seed=None` 保持旧路径；仅 GetWave 且 seed selector 非 None 进入新 seam，所以 0 仍明确选择隔离。main 的既有全局 RNG 政策与 A 参数解析完全保留。initializer 准备抽为共用 adapter；原 channel/FEXT 公式、setter 顺序和分支内容经 AST 逐项等价核对。默认路径归一化内联后与原 helper AST 相同；config 的两个值在准备矩阵前取出，没有宣称完整 helper 已执行。

## 顺序、输入和数据归属

实际生产使用 `utility/ibisami.py::_run_probe_main`：

1. 先将原始 Init 值及 x 冻结为 host 副本；P/W 分别从冻结内容重新 deepcopy 并构造 initializer。
2. 新 P 构造、Init、原 get_responses、复制响应与 Init 诊断、finally Close。
3. P Close 返回且必要复制成功后才新建 W；新 Init 后首次 main GetWave 从冻结原 x 的首样本开始。
4. 复制 W wave/clocks/params 与诊断，再 finally Close，返回原六元结构。

h/out_h 来自 P；wave/clocks/GetWave params 和主要 Init 消息来自 W。消息追加明确的 C1 角色诊断；F2 last_init_call 的实际输入/输出矩阵、params、message、epoch 分别保存，两个模型即使 epoch 都为 1 也由角色区分。所有返回结果、Close 后消息和异常中保留的诊断均为 host 数据，未扩展 Web/archive schema。

AMI 参数、info、channel/FEXT、ts/UI 从同一冻结输入独立重建；P 的可变输入/输出不会成为 W 输入。没有补训练、添加/删除输入、预消费 wave 或减固定时钟偏移。P responses 继续由 F2 原实现计算：Bp40、nbits20、max_run_length10、两次 probe 顺序及 ±0.5 两电平算法保持；本票不复制该算法。

主请求 B 非零原样传递；仅隔离路径将 B0 显式传为 40，保留旧有效分块，不改 PyAMI 的 0 语义或全局默认。正 seed 直接传给私有 default_rng 工厂；0 传 None 请求 fresh entropy，诊断写 probe RNG replayability UNKNOWN。没有抽取或推进 main 全局 RNG。正 seed 的 seeded 只描述 probe RNG 输入政策，不保证模型内部随机性或完整链路重放。

## 失败和清理

构造、准备、Init、RNG、probe、输入/响应/诊断复制、main、消息解码或 Close 失败即停止，不重试、不进入下一角色。已经取得的模型都在 finally 尝试 Close；构造尚未返回的对象没有可供 host 清理的实例。

内部 `_AMIProbeMainError` 分别保留原 primary_error、cleanup_error、diagnostic_errors、role/phase 及已取得的 host 诊断，exception cause 保留原执行错误。包括中断类 BaseException 与 Close 同时失败的情况。Init 失败时尽量在 Close 前复制部分 Init 记录；复制本身失败也单独保留，不能覆盖主失败，失败的复制不重试。

close_attempted、close_returned 与 release_confirmation 分开；失败不能冒称释放已确认，也不承诺 OS DLL 映像或全局静态变量重置。P 清理或清理证据复制失败都不进入 W。生产 PyAMI Init/析构自身的幂等 Close 行为沿用 F2；纯 stub 计数不冒充完整真实生命周期调用账。

## 授权纯 seam 与定向矩阵

TDD 所需 seam 已由 live 合同明确授权：从实际生产文件 AST 提取 `_run_probe_main` 和内部 error class，使用普通 Python factory/initializer/model stubs、手工 buffers、受控 RNG token；没有在测试中另写协调算法。NumPy/AMI adapter、默认分支与 caller 用实际 source/AST 核验。

[run_guarded.py](run_guarded.py) 在任何产品执行前设置 import/audit/profile guards，只执行上述真实纯定义和测试；真实 response-key 常量用明确标注的受控字符串 key 替代，未导入 model 模块体，也没有 fake constructor 冒充真实导入。完整 run_ami_model 从未执行。stdlib preload 与平台/系统库动态活动没有完整 trace，不能把列明入口的 0 扩大为全系统活动 0。

新 bare `.venv` 使用 Python `3.13.15`，只有 stdlib，没有 pip/test dependency 安装。实际 executable/prefix/sys.path 和 venv.cfg 绑定在 receipt；guards 拒绝预加载的产品/NumPy/ctypes 模块，任何 blocked attempt 都使批次失败。每批执行前冻结 source、caller、test、runner、plan；最后批次同时验证它们执行后字节未变。

最后 [10-contract-green](runs/10-contract-green/receipt.json) **9 个测试方法通过、35 次实际纯协调器执行**：26 个 failure points、4 个 seed/B 组合、成功路径、双错误、primary/Close/双诊断错误、可变 Init/FEXT/params/info/ts/UI 与 x alias、以及中断双异常。另有两个静态测试方法，核对真实 initializer、默认路径、旧 positional/6元返回、唯一目标 caller、rx_use_clocks 两值与旧 main RNG/A 接线。动态与静态证据分别陈述，不把它们称为完整数值 helper 通过。

fake Close 会破坏其 buffers/记录；测试确认已复制响应、main 结果、Init 诊断仍完整。事件账确认 P Close 后才 W，实际 fake handle 不重叠；所有失败点停止前进，Close/失败点不重试。clocks/wave/params 为固定手工值，不是 golden 或 DSP 结果。

## 原件、red/green 和费用

| 批次 | 实际结果 |
|---|---|
| 01-tracer-red / 02-tracer-green | baseline 没有 seam 的真实 red；最小成功路径 green |
| 03-dual-red / 04-dual-green | probe 错误被 cleanup 覆盖的 red；双错误保留 green |
| 05-failure-matrix-red / 06-failure-matrix-green | 失败矩阵 red（8 failures、10 errors）；26点与复合异常 green |
| 07-wiring-red / 08-wiring-green | 缺实际 caller/adapter selector 的静态 red；接线及当前矩阵 green |
| 09-interrupt-red / 10-contract-green | 中断+Close 信息丢失的 red；最终完整当前矩阵 green |

首次 line119 静态 preflight 因 runner 一行 123 列停止，测试尚未执行；[preflight-static.json](preflight-static.json) 与 [原 runner](inputs/runner-preflight-v1.py.txt) 保留该失败，修正后才开始 01。所有 red/green、原始 stdout/stderr、每批 input/receipt/hash 及原版本均保留；文件名 green 不代替实际 exit。最后文件必须与 10 receipt hash 一致。

[cost-ledger.json](cost-ledger.json) 记录十批全部成本：累计实际纯协调器 **130** 次、内部 error constructor **106** 次；selected stub entries 为 model factory193、initializer177、initialize169、private RNG factory102、get_responses98、main getWave40、Close183；copy/message 辅助计数另列。06起补充完整 observed test Python entry histogram，旧批次未冒称此观察范围。以上均为非零 Python 软件活动，不能写为模型 C 调用。

十批内部 elapsed 合计 `2.624448799979291 s`；三个 Git/venv bootstrap 合计 `18.391242700003204 s`；clone/switch `51.39330739999423 s`。首次静态 preflight 内部 elapsed UNKNOWN，tool wall 单列；整任务 wall/peak RSS UNKNOWN。没有将历史失败或花费归零，也没有重复 #24/#27/fullsuite/安装矩阵。

全部批次真实完整 helper、PyAMI 生产 initialize/getWave/get_responses/close、AMIModel/Initializer 实例、model 模块体/response-key 构造、NumPy/SciPy DSP、grammar、engine/Main/COM/coopt、C/模型 DLL、模型资源获取/编译、CLI/GUI/服务/浏览器均 **0**。Git 依赖传输可能包含仓库既有示例 binary，未将其加载或当作合法 fixture。完整 lint/type-check/hooks 未运行；新私有定义/测试/runner 的 AST3.10、119列及 raw UTF-8/EOF/mixed/large 静态检查通过，两个既有超长能力错误字符串不作无关改动。原件无 hook 冲突，未改 hook 配置。

[startup.json](startup.json) 保护旧 12 个仓库 HEAD/tree/status、169 项 Git 元数据、4,874 项原件及 784 项后续材料/安装源码，保留 12 个旧 env/cache 目录。没有修改或清理旧 #24/#25/#27/#28、主 checkout、子模块或 cache。新环境与原件亦保留。

## 资格界限与交付

这是生产纯协调 seam 的软件证据。完整 adapter、实际 AMIParameter 对象复制、模型时序/随机性、容量与数值行为未动态验收；40 不保证所有模型合法，非整数采样比和短末块的模型资格留 E。I>0 时固定私有 probe seed 与 fresh W 可能改变响应、wave、params、clocks，方向/幅度 UNKNOWN；前 Ignore_UI 输出仍是真实适应期。两电平 probes 不声称 PAM4 golden。

D1 Native 采样、D2 Web 消费/保存、E1/E2 合法 fixture 与真实配对均属后续票；#10 有效 clocks/E SOURCE_BLOCKED、#4 COM BLOCKED_BUDGET/NOT_EXECUTED、#1 最终 fresh 数值 review gate 不变。

交付只向本人 PyBERT master 创建唯一 Draft PR（Refs #30）；双轴审查与最终 hash 封存另记。固定 HEAD/tree/clean 后停写停测，交 PM fresh review，不自行 merge/close。开发期公开 push/PR 已授权，私有化由 PM 在全项目最终验收后统筹。
