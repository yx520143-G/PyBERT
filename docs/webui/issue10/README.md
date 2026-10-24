# #10 IBIS-AMI 实施交付（Draft，保留未完成验收）

本票接入了两侧独立的 IBIS 电气选择、动态 AMI Configure、worker 内模型检查/Run/Tune、真实执行观察、显式 AMI Use EQ，以及版本化配置与结果保存。**实现交给 PM 固定提交复核；有效 AMI clocks 验收仍 BLOCKED，不能关闭 #10 或父 #1。** 不包含 COM、BER 或任意厂商/平台资格认证。

基线为 `f3e94fa220c4bf39931ec7db343f2512a8441617`，tree `8bef34bfa12ad6a5a052576b6628a50e1a33299b`；PyAMI `5270d713e40bac2be5747bef09b92df79df9085b`、PyChOpMarg `ca905e793fcf6330929471317ca32e7611578e5d` 未变。唯一 writer 位于 `codex/pybert-issue10-ami` 独立 managed worktree；主 checkout 的 `b9c56fe` 和原未跟踪目录未改动。

## 实现与使用

- `IBIS / AMI` 或节点原 Select/View/Configure 入口打开同一面板。登记本机完整模型目录或上传保持相对路径的目录；内容 hash 覆盖 bundle 及每个依赖。Select 包含真实 component/pin/model 联动，View 显示原解析信息；valid 来自子进程预检，不可手工勾选。
- 电气 Native/IBIS 与 EQ Native/IBIS-AMI 分离；Init/GetWave、TS4 和 Rx clocks 按实际能力检查。模型变化需要显式 rebind；side、bundle、selected model、AMI/binary hash 与完整参数路径共同绑定 Configure/候选身份。缺文件可恢复草稿，执行需重新绑定原内容。
- Configure 使用原 parser 的完整参数树、类型、usage、Range/List/Corner/标签/单位；可写字段经原 setter 和回读校验。搜索仅接原生支持的 Range tuner；原 Configure 树不等同于搜索表。
- 模型预检、Run、Tune 共用一个活动槽，每 task fresh `spawn`。HTTP 父进程只处理字节、纯 JSON 和状态；binary 在子进程加载。合作取消区分 requested/observed，实际退出/join 后才发布终态；不承诺中断正在执行的 DLL 调用。
- Tune 复用原 `coopt`/Optuna TPE，只增加只读 candidate 观察钩子；无公式修改。成功候选不自动应用。Use EQ 先按 input/revision/model/path 校验，再显式确认 dynamic patch 与适用的 Native patch。Native Reset 只做适用 Native 侧 current→search，不提供 AMI Reset。
- YAML 的 `pybert-web-runtime-v1` 注释保存完整模型树、选择、资源绑定、clocks 请求、搜索设置和预算。原生 PyBertCfg 不表达这些扩展，导出有 loss list。`.pybert_run`/`.pybert_opt` 保存 raw 与源记录，资源 bytes 仍需原内容重新绑定。
- Rx AMI 的 `ctle_out` 图标为 Rx AMI output，RxFFE 标 bypass；模型未明示的内部 taps/lock 状态不以 Native 零值冒充。raw 保存实际 helper 输入/输出、复数 H、返回参数和 clocks；时间轴为 s、频率为 Hz，显示变换另列。

## 实际覆盖与阻塞

以下是 Windows x64 官方 example 模型、冻结非零 seed/noise 的实际范围；不是任意模型支持矩阵。NRZ 3×3 每格均尝试了 direct 与 worker。

| Tx \ Rx | Native | Init | GetWave |
|---|---|---|---|
| Native | validated，444 raw arrays exact | validated，440 exact | validated，440 exact；无模型 clocks，Native CDR fallback |
| Init | validated，450 exact | validated，446 exact | validated，446 exact；fallback |
| GetWave | native limitation：原生 params_out ParseError | 同一原生 ParseError | 同一原生 ParseError；双 GW 原生丢弃 clocks 的限制保留 |

八个成功配对（上述六格加 PAM4 两格）共 **3548** 个原 raw 数组 dtype/shape/C bytes exact。PAM4 的 Native Tx + Rx Init、Rx GetWave 分别 441 个数组 exact；其他 PAM4 组合未测试。三个 Tx GetWave 配对都失败，保留 18 个失败 helper raw 的一致性证据，不能算成功。Tx 模型输出参数缺右括号触发原生 `bert.py` ParseError；未改 parser 或算法绕开。

新增 NRZ adaptive-clock 探针两路均在原生 `tuple.name` 解析失败。返回 clocks 长 15000、首项 4 ns、有限，仅满足原生 len/first 入口条件；有 2184 个零间隔与 312 个负间隔，且解析失败发生在后续 clocks 消费之前。**不记物理有效或实际采用的 AMI clocks。** PAM4 有效 clocks fixture 也缺失。需要模型维护者提供合法、可分发/可按 hash 绑定且原生能解析的 NRZ/PAM4 clocks fixture 后，另行冻结窗口/预算再补验。

Tx GetWave 的 `rx_in` 是 noisy diagnostic，当前原生下游另用数组；双 GetWave 丢弃 Rx clocks。界面和结果保留警告，没有重新接线。disabled File CTLE 按原生实际调用分支：Native/Init Tx + Native Rx 可旁路，Tx GetWave + Native Rx 会阻止 File FIXME，Rx AMI 按替代分支判断。

Linux/SO、其他架构、其他厂商、GetWave-only Init 评分、多 component 模型的数值矩阵、原生桌面 GUI 端到端未新验收。GUI/CLI/MCP 入口文件未改；原生 core 仅 `threads/optimization.py` 五行可选只读观察钩子，兼容性证明限于源码审查与本批相关回归。#9 Native ISI Viterbi 与 FEC 拒绝边界保留；#4 默认 COM gate/#16 不在本次计算范围。

## 冻结、数值与 Chrome 证据

| 冻结/批次 | 可核查结果 |
|---|---|
| `fixtures/v1/manifest.json`，SHA `18806cc1bc9ee1eb2cb77d37e7001911e0c47836cbad90d2a08776a3c56174f6` | 首次探索前冻结；1 Main、3.0234 s、peak UNKNOWN。Rx GetWave 无效 clocks fallback，仅探索观察。 |
| `fixtures/v2/` | TraitsList 跨 IPC 失败的不完整冻结，原件保留，不算验收。 |
| `fixtures/v2-executable/manifest.json`，SHA `adae77854ac91abab460dafe60145fb87cf96b71328762821a1b6fbb50b5fe05` | 完整 13 requests、模型/参数/环境/窗口/零 raw 容差。154831 首次 worker 在目录 digest 处 0 Main 失败；154940 只补 worker、复用旧 direct；155041 完成余下矩阵及最初优化。 |
| `fixtures/v3-closeout/manifest.json`，SHA `864005ae164f71eb865bbcc7db737adb618f0b3eeaee13dc7590e2f9390cdab3` | 加 model parameter identity、clocks 探针与有界补证预算。160343 两 Main 均原生失败；160818 仅新增 direct fixed1/TPE4 共五评估，复用 155041 worker。完整 83 worker raw 数组 exact，另验新增 25 helper 轴；83 已包含原先 50，不相加。 |
| `fixtures/v4-final/manifest.json`，SHA `bb9a85d6d511059cf1095b1c19d4861cedd3f1663ce336e00f1a81ed2f046955` | 同物理输入，补 List 合法值/tips/Corner/label metadata。Chrome Run/Tune 前 config/runtime/bindings 逐字段相等。 |
| `evidence/chrome-v3` | NRZ GetWave `823bfdbb-bc37-40b6-ae56-12e3bf6b3476` succeeded；真实目录检查、TS4/模式拒绝、YAML 保存。 |
| `evidence/chrome-v4` | PAM4 Init `f4d00fbb-54d1-47cb-a95f-0cf0945b5aee` succeeded；真实 Abort `730e3f10-2a3f-4345-b6cf-e78762b2cc48` 在 Running DFE/CDR 被观察，退出后 cancelled，旧成功保留。 |
| `evidence/chrome-v4` | fixed `58d83a53-d409-447d-b0a6-31c55a469005` / TPE4 `3de6652f-4bf3-42b0-b337-5783194aa2db` 成功，1/4 trials。完整 30+78=108 raw 与 160818 direct exact，全部 trial FOM/AMI 值一致；不把它与旧 83 重复计为新增独立覆盖。 |
| `evidence/chrome-v4/closeout-checks.json` | Chrome NRZ/PAM4 的 440+441=881 旧 raw exact，新增 5+5 秒轴另验 exact；Run 重开重存的 arrays.npz 与 source_manifest_utf8 原 bytes 相同，允许保存 envelope 时间/adapter 变化。优化重存整个 manifest/raw bytes 相同。验证器本身 0 模型/引擎调用。 |

Chrome 目标为真实 Chrome 1280×720。`*-eye-verified.png` 及 `views-*.log` 同时匹配 source run、观察点、标题、ps/V 轴、heatmap 和 metadata run ID，并已目视核验。NRZ/PAM4 frequency 与 jitter 也以同一 run 切换，不计算。Use 预览不改草稿，确认后 ctle_mag 0→12；Native Reset 保留完整 AMI 树/范围/预算。失败优化记录、取消与旧成功共存，archive 重开不执行。

## 失败、勘误与 source 适用性

1. `chrome-v3/nrz-eye.png` 下拉虽为 Eye，像素仍旧频响，**不能算 Eye pass**；`nrz-response.png` 也拍得过早。原文件/脚本保留，后以 `chrome-v4/nrz-eye-verified.png` 和严格等待补证；不以 PAM4 图替 NRZ。
2. 最初 PAM4 Load 的模型 bindings 仅在 YAML 注释、parent 未 freeze，导致 15 个 FFE search enabled 与冻结不同。旧 `before-main-pam4.json` 保留，未对该错误输入 Run；修复后才启动 PAM4。显式及省略 load mode 均有回归。
3. Chrome fixed Tune 的 `283457ea...` 在 prepare 因 json_bytes 的纯 key order 比较误拒。后一次 `aa6406d9...` 的实际 traceback 是 **`name 'json' is not defined`**；owner 随后使用 `import copy` + `deepcopy` 修复。两次均 0 coopt/0 eval/Main0，仍计 outer 5.618/5.806 s 及存储。原 budget amendment 的“copy import”措辞不精确，本段勘误，不覆写原件。四个 submitted task 的预算 amendment 在两失败之后、两成功之前追加，不能说四次提交从首次就已冻结；实际 producer 两次/五评估上限未扩大。
4. 旧 Run manifest 的 `runtime_extension_status` 全写 inactive、`inactive_model_paths` 旧文字不准确；以同期 `ami.models/actual_branch` 和 raw 为实际消费证据。最终代码已按 AMI/clocks/Tune 分支纠正；旧 manifest 不回写。
5. 早批 `library_calls` 是 Python wrapper 次数，**Init34/GetWave80 不能当 C 分块调用总数**；旧 C 次数 UNKNOWN。Tune 早批 AMI raw unit/producer 字段也有旧泛化值；最终代码及新 Chrome artifact 使用真实 producer、V/sample/s，旧 raw 不变，错误 metadata 不追溯冒充正确。
6. 每批 source 与 fixture 版本单独适用。154831 未预存 harness；154940/155041/160343/160818 有实际 Python source/harness。37 项 source identity 通常是 23 Python 原 bytes + 14 static hash，不能称 37 个都预存原 bytes；114 个 package hash 也不是 114 份源文件封存。
7. Chrome v3 启动 source 与 NRZ 实际 task 的 `web/ami.py` 有一项差异；其余 36 项相同。实际 NRZ 源与运行前 Git `7b623f4` 原 bytes exact，不能把全部 v3 启动副本称为 NRZ 执行源。PAM4 v4 启动 37 项与 manifest 一致。
8. Followup 56 Python 副本及 23 Python identity 在取消/Tune 前保存，14 static 仅 hash。成功 Tune 的 optimization.py 另与调用前保存的 `pre-tune-final-optimization.py` 和 Git `130e85c` exact；不能扩大其他副本的预存范围。最后 Git renormalize 只恢复产品文件原有 LF 存储、无语义变更；本票 docs 的 `-text` 禁止换行转换，以保留冻结 hash/source 原 bytes。请按实际 task source identity 而不是仅 HEAD 判断数值适用性。

## 调用与费用账单

| 批次 | 新 Main | 新 coopt producer / objective eval | 状态/复用 |
|---|---:|---:|---|
| v1 探索 | 1 | 0 / 0 | success observation，非验收 |
| 154831 | 1 | 0 / 0 | direct success；worker pre-Main failed |
| 154940 | 1 | 0 / 0 | 仅 worker success；旧 direct 不重计 |
| 155041 | 20 | 4 / 10 | Main 14 success/6 native failed |
| 160343 | 2 | 0 / 0 | 2 native failed，clocks 未消费 |
| 160818 | 0 | 2 / 5 | 仅 direct 补证；旧 worker 不重计 |
| Chrome | 3 | 2 / 5 | Main 2 success/1 cancelled；另外 2 Tune preflight failed 为 0 producer/eval |
| **合计** | **28** | **8 / 20** | **Main 19 success（含探索）/8 failed/1 cancelled；submitted 优化 10 个（8 producer + 2 preflight failed）。** |

冻结库预检早期 18 次、v3 五次、v4 五次均为 0 Init/GetWave；Run/Tune/Chrome 后续模型检查另列 task 原件，不把加载当执行。已装 C 层计数批次：160343 Init2/GW754；160818 Init5/GW10；Chrome Main/取消/Tune Init8/GW391。可核查这部分为 Init15/GW1155，**不是含早批 UNKNOWN 的全局总数**。GW probe 与实际序列调用在 raw context 中区分。

每次 request/terminal、已可查询的 joined task 状态、worker raw、source、elapsed、峰值记录均在 `evidence/` 和 `evidence/logs/`。Chrome 内部优化 producer elapsed 为 0.678/0.885 s，outer task elapsed 另计；不能把二者混用。进程峰值采样记录按 PID 保留，无法唯一映射 task 的 peak 标 UNKNOWN，不凭全服务最大值代填。未记录的旧 peak/费用保留 UNKNOWN。全部失败、停止日志与原件保留，无清理覆盖。

## 验证与交接

最终相关回归 **170 passed / 35 warnings / 83.33 s**，原日志 `evidence/logs/issue10-final-regression-170.log`。旧 168-pass、早期 112-pass/1-fail、定向修复结果、键序测试 1-fail/2-pass 及修正 1-pass 均分别保留，不相加。完整 native GUI/跨平台验收不在此数字中。新 `test_web_ami.py` 覆盖 YAML 资源 freeze、原 parser metadata/setter、路径/hash、File CTLE 分支、预算、replay、Native Reset 与 key-order 回归。

只读独立审查确认 identity/replay/budget/metadata 六项旧发现及缺省 load、运行 metadata、结构比较三项新增 closure；最后静态复核基于 `130e85c`，没有额外模型/引擎调用。此自审不能替代 PM 对固定 Draft PR 的 fresh final review。

`chrome-v4/final-service-state.json` 显示活动槽空闲，`shutdown.json` 记录主动停服及 8785 端口关闭；monitor 已退出。固定提交推送并创建唯一 Draft PR 后 owner 停写返权，后续验收/合并/关闭由 PM 按原流程处理。有效 clocks 等未完成条目保持 BLOCKED/未勾选。

## PR #20 首轮 fresh review 的两项 P2 补修

上述 170-pass、数值/Chrome 批次属于首次固定提交 `13172a8`。PM 在该提交的 [formal review](https://github.com/yx520143-G/PyBERT/pull/20#pullrequestreview-5637676782) 提出以下两项 P2 后，将唯一写权交回原 owner；本节为独立补充批次，原件和冻结 manifest 不变。

1. **Rx clocks 两入口冲突。** 弹窗与主链重复使用 `ami-clocks`，全局查找命中主链，导致弹窗提交值错误、Tx render 误禁用 Rx 主链控件。弹窗改用独立 `ami-modal-clocks`，仅 Rx Apply 修改 `rx_use_clocks`，Tx 操作保留该请求。原 `ami.js` 的 first-match DOM 红灯为 4 fail/1 pass，修复后 5 pass。
2. **可选 AMI DLL 误阻止独立 IBIS 电气路径。** 仅实际请求 AMI EQ 时才加载执行 DLL；Native EQ 的电气/TS4 路径不构造可选 DLL。参数 parser 有效时仍严格验证完整树、setter 值、bundle/selected model/parameter hash；实际请求 AMI 时 parser/库加载错误仍明确失败，TS4 请求仍需有效 parser 和声明依赖。可选 parser 解析/UTF-8 错误另记 `ami_capability.invalid`，不冒充 AMI valid 或更改请求模式。只读自审另发现该容错分支需要消费显式 rebind；已先红灯复现再生成稳定 canonical 定义，后续 `discover=False` 不再误拒。

无真实库的分支红灯 3 fail/3 pass，首轮修复 6 pass；后补 UTF-8、身份/未知路径/非法值及 rebind 覆盖。身份测试曾把原 setter 的正确 `TraitError` 误写为 `ValueError`，留下 3 pass/1 fail，修正异常类型后 4 pass；这次失败不代表非法值被放行。该阶段相关回归 182 passed；随后加强必需 parser/库失败阶段的三项断言，并补 Native parser/TS4 不依赖可选 DLL 文件的两个用例。后两项先红灯；初次补修仍被 resolver 返回的不存在路径阻挡，二次修复后绿灯。最后完整相关回归 **184 passed / 35 warnings / 83.25 s**。旧 170、177、182、各定向与最终批次不相加。所有日志在 `evidence/p2-supplement/`；测试 stub 不加载真实 DLL，不执行 Touchstone 数值分析或原引擎。

最小真实 Chrome 为独立 `ami10p2` 会话、1280×720。`issue10-p2-chrome.log` 与三张新截图覆盖：主链 false → 弹窗显示 false → 弹窗编辑 true 但 Apply 前主链仍 false → Apply 后主链 true → 主链 false → 再开弹窗 false；Tx render 不禁用主链，Tx Apply 保留 Rx false；Save 后重新打开 Rx 面板仍为 false。已目视核验，旧图片不被重新标为此次覆盖。保存 YAML 的完整 config 与 v4 相同，runtime 仅 clocks 请求改为 false、bindings 相同；true 请求 identity 仍为原 `59863eea...`，false 为 `777119a3...`。这些只验证请求和持久化，**不证明有效 AMI clocks 被模型返回或消费**。

`before.json`、冻结输入、37 项 source 原 bytes 及 bounded server harness 均先于库预检保存。临时服务只接 normalize，禁止 Run/Tune/COM，拦截意外 Main/initialize/getWave；12 次库加载预算实际使用 **6 次**，来自 **8 个 fresh spawn normalize**，全部退出/join，outer elapsed 合计 **42.753805 s**。本轮新增 **Main/coopt/AMI_Init/AMI_GetWave/COM 均 0**；历史 Main28、coopt8/20eval 和 C 已知子集15/1155及 UNKNOWN 不变。未采样本轮 peak，保留 UNKNOWN。

Chrome 后仅 `web/ami.py` 的可选 parser 失败 rebind canonicalization、Native parser/TS4 与可选 executable 文件解耦又作小修，最后 184 项回归覆盖这些分支。可选 DLL 不存在时 binary identity 明确为 None；已冻结 bundle 自身缺文件仍先被 hash 校验拒绝，实际请求 AMI 没有该豁免。`source-delta.json` / `final-source/` 保留第一阶段，`final-source-delta.json` / `fixed-files-source/` 保存最后 Python bytes，不能将旧 Chrome task 源称为最后 Python 的再次预检。UI 文件与实际 Chrome 源一致。自审只读确认两项 P2 及两个边界闭环，没有额外模型调用，不替代 PM 对新固定 HEAD 的 fresh final review。

`checks.json` 保留全部 task 与 0 Main、保存往返和预检费用；`shutdown.json` 记录活动槽空闲后停服、8785 关闭，专用 Chrome 已关闭。exec 的 CtrlC 返回 1，server finally 未写总数文件；实际 6 次以各 task 的加载尝试原件逐项汇总，不伪称来自退出回调。原错误/停止证据保留。PR 仍为同一 Draft，待固定新提交推送后停写返权；#10/#1 和所有原生/fixture BLOCKED 边界不变。
