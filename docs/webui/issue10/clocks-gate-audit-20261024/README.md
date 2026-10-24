# #10 AMI clocks gate：零引擎只读调查

日期：2026-10-24（Asia/Shanghai）。状态：**调查完成，产品未修复，有效 NRZ/PAM4 AMI clocks 资格仍 BLOCKED**。

本调查在独立 worktree `codex/pybert-clocks-gate-audit` 中进行，基线 HEAD 为 `b96977a34ec5122bef9f6b4457a035535215ac8a`，tree 为 `499d039af87c652410452520adc999bdd49e3f13`。所有新材料只写本目录；未修改产品源码、依赖、gitlink、旧证据或模型。最终交付 HEAD/tree 由本次提交及交接消息固定，避免在报告内自引用提交 hash。

## 结论与边界

这不是一个已经定位为“DLL 返回坏 clocks”的单点问题。已保存 NRZ probe 首先在 PyBERT 参数树访问处失败；纯解析/AST 复现还确认后续 tap 筛选、clocks 消费存在独立错误。PyAMI 的整块 buffer 拼接即使接收符合 sentinel 契约的输入，也能产生错误 aggregate。response probes 与真实 waveform 共用模型状态，另有时间原点及适应状态的行为问题。

现存 raw clocks 不是有效资格证据：虽然满足原生入口的弱谓词，但含零间隔和倒退；该失败任务没有走到 clocks 消费完成。作者当前 C++ 源码还显示缺少尾 sentinel，不过**本地 DLL 到该源码提交的构建映射 UNKNOWN**，没有逐调用原 buffer，不能据此判定旧 DLL 实际写入行为。

本轮没有找到许可、Windows ABI、调制支持及 clocks 契约均已核验的新的现成 fixture。现有 `example_rx` 没有 PAM4 声明；输入 PAM4 波形或 DFE mode 为 Adaptive 均不能证明 PAM4 CDR。下一阶段应分开处理接口缺陷、模型状态语义及资源获取，不能过滤、排序、补 tick、改时基或用 Native CDR 代跑来补资格。

本调查不触发 COM、优化、原生数值 helper、模型预检或主仿真，不改变任何 issue 的状态，也不代替 #4、#16 或父 #1 的独立验收。

## 输入、方法与复现

已有失败数据位于 `../evidence/numerics-20261024-160343/A-NRZ-ADAPT-GetWave/`。direct/worker 的 `ami-execution.npz` SHA256 均为：

`0899f82f17d9a6511f2b9f8596bfcaea4a4530828d72b59b622231ad2f27660b`

该 probe 的请求为 NRZ、UI `1e-10 s`、sample interval `3.125e-12 s`、15000 UI、32 samples/UI、`dfe_mode=2`、5 taps、`ctle_mode=1`、`ctle_mag=0`、请求 Rx clocks。direct/worker 均在 `bert.py:394 → 381` 因 tuple 没有 `.name` 失败；helper 返回不等于引擎成功。

[inspect_saved_probe.py](inspect_saved_probe.py) 仅做以下工作，结果见 [diagnostics.json](diagnostics.json) 和 [diagnostics.log](diagnostics.log)：

1. 读取既有 NPZ/JSON，核对 11 个 direct/worker 数组的 dtype、shape、C-order bytes 完全相同。
2. 从 pinned PyAMI `parser.py:85–143` 抽取纯 parsec grammar，解析已保存的 750 个返回字符串；不导入 PyAMI 模块或构造 Configurator。
3. 从 `bert.py` AST 抽取 visitor、tap lambda、入口谓词及 pairwise 表达式，用已保存数据和普通 Python 类型复现错误；不执行仿真函数。
4. 仅复放 wrapper 的 `extend` 与 slice 表达式到两个普通 Python list；不是 C ABI stub、模型或可用 fixture。
5. 对 7 个源码/数据输入计算运行前后 SHA256，断言未变；断言未导入 `pybert`、`pyibisami`。当前 `bert.py` 与旧实际 execution-source 的完整 AST 相同。

只读引用的 PyAMI 来自封存 worktree `C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/PyAMI`，固定提交 `5270d713e40bac2be5747bef09b92df79df9085b`。本 worktree 未初始化或更新 submodule。工具的一次性绝对路径刻意保留，重放前应核对该只读来源，不自动安装环境或寻找其他版本。

本次工具使用已有 Python 3.13.15 环境、NumPy 2.5.1 和 parsec，经 `uv run --no-project --python <既有解释器> python <本工具>` 执行。它复现缺陷，不是产品修复测试；不能据 exit 0 记 clocks 通过。

## 分层责任与最小证据

| 层 | 固定源码与触发 | 证据／影响 | 本轮判定 |
|---|---|---|---|
| 返回参数解析 | PyAMI `parser.py:114–143` 返回 `(label, values)`；PyBERT `bert.py:378–400` 按 `node.name/.values/.children` 访问 | 全部 750 个字符串可解析为 tuple；保存的非空 tap leaf 经原 visitor 抛 `AttributeError` | 已复现接口不匹配；是旧 probe 的实际首个失败 |
| tap 名称筛选 | `bert.py:403` 对运行时 str 调 `.tolower().contains()` | 原 lambda 在真实保存的 tap 名上抛 `AttributeError`；str 也没有 `contains` | 已复现独立后续错误；只修 visitor 仍不足 |
| clocks wrapper | PyAMI `model.py:488,491,519,523` 分配 `B+8`，整块 append，最后按 waveform UI 数截断 | 两个合法有效前缀 `[0,1]`、`[2,3]`、各自有尾 `-1` 的 list，经原表达式变为 `[0,1,-1,0]` | 已证明 wrapper 可损坏合规输入；不能删安全余量 `+8` 来掩盖 |
| probes 与模型状态 | `utility/ibisami.py:145–171` 初始化一次，先 `get_responses(bits_per_call=40)` 再真实 `getWave`；PyAMI `model.py:626,635` 两次 probe | fixture Ignore_Bits 为 0；每次 probe 20 UI，总 40 UI；真实调用沿用同一模型与分块值 | 源码行为确认；真实输出状态/时间原点修复属于独立行为变更 |
| clocks 消费 | `bert.py:575–576` 对 `(clock_times, clock_times[1:])` 做 pairwise | 实际得到一对长度 15000、14999 的数组；`if clock_time == -1` 抛 NumPy ambiguous truth `ValueError` | 已复现；对合法多 tick 数组也不符合标量遍历意图 |
| 入口与 metadata | `bert.py:531–532`、`web/ami.py:366–384` 只看请求、长度及首项（另排除 Tx GetWave） | 对非单调旧 raw 入口谓词仍为 True；成功路径文案将其称为 valid | 谓词不足以证明物理有效、实际消费或完整覆盖；旧失败没有成功 manifest，不能事后补“已使用” |
| 模型／来源 | 作者当前 `ibisami` C++ 见下节；旧 DLL 无对应 build identity | 存在源码级尾 sentinel 缺口；逐调用旧 DLL buffer 未保存 | 当前源码问题与旧 binary 行为分开；后者 UNKNOWN |

PyAMI 虽定义 `AmiLeaf/AmiBranch` dataclass，实际 grammar 与 `proc_branch()` 仍采用 tuple。不能为了匹配 PyBERT visitor 全局改变 parser 返回类型，否则会影响既有 `.ami` 配置解析。参数完整层级、同名 leaf、Table/非数值节点也需保持；不应顺带重命名或重构整棵动态参数树。

`cdr_locked/cdr_ui` 缺失时原生 zeros/empty 占位不等于模型返回状态。有效 clocks 分支中的 lock 由 Ignore_Bits 派生，dummy slicer 也不等于 Native DFE/CDR 适应。Tx GetWave 原分支会丢弃 Rx clocks，相关 ParseError 是另一已保留失败，不能合并为本次 tuple 问题。

## 旧 raw 的精确观察与不能推出的结论

direct/worker 共同结果：

| 项 | 值 |
|---|---|
| clock 数量／类型 | 15000／float64，全部 finite |
| 首／末时间 | `4.000000000000002e-9 s`／`1.2543000000000822e-6 s` |
| 零值／`-1` | 2496／0 |
| 零间隔／负间隔 | 2184／312 |
| 完整 48 槽块 | 312 块，每块前 40 项正且递增，末 8 项全 0 |
| 末尾剩余 | 24 项，正且递增 |
| 按位置观察前 40/48 项 | 共 12504 项，跨块严格递增；仅诊断，未输出替换向量 |

模式与 `bits_per_call=40`、容量 48、整 buffer 拼接相符。真实 waveform 的 375 个分块如均 append 48 项，会先形成 18000 槽，再按 15000 UI 截断；最终保存的是这个 aggregate，不是逐 C 调用 buffer。**没有证据确认每次 DLL 写了哪些槽、sentinel 在哪里，或被截掉的后续内容。** 不能把这些零都称为模型的有效 tick，也不能从 aggregate 恢复合法 clocks。

首 tick 的 4 ns 与两次 20 UI probe 消耗的累计时间一致，这是源码与数据支持的推断。现存源码的真实 waveform 从自己的时间向量起点消费；盲减 4 ns 不处理适应状态，也不能修复既有资格。需要把响应探测是否共享状态、真实 waveform 的首次 GetWave 原点和最终采样窗口一起冻结。

历史 probe 每路曾执行 C `AMI_Init=1`、`AMI_GetWave=377`（2 probe + 375 waveform chunks）；Python wrapper 计数为 1/3。这是**旧成本**，本轮仅从保存 ledger 读取，未再次执行。不能把 wrapper 数当 C 调用总数，也不能据本 probe 推出其他旧批次的 C 总数。

## clocks 合同与现存模型来源

[IBIS 5.1 正式规范 §10.3，印刷第 170 页](https://ibis.org/ver5.1/ver5_1.pdf#page=170) 已要求：clock 单位为 seconds；相对首次 GetWave 的 simulation start 使用累计时间；采样时刻为 edge-aligned tick 加半 UI；每次有效前缀后写 `-1`，无 tick 时首项为 `-1`；有效 tick 在单次和跨调用中严格递增。安全 buffer 容量不是有效 tick 数，sentinel 后内容不是有效数据。

[IBIS 6.1 §10.6](https://ibis.org/ver6.1/ver6_1.pdf) 引入 PAM4，未声明 Modulation 时默认 NRZ；PAM4 的 UI/bit_time 表示 symbol time。应按模型声明的版本核验，不能把较新规范可选参数强套到 AMI 5.1 模型。

| 既有资源 | 静态身份 | 已知与限制 |
|---|---|---|
| `models/ibisami/example_rx.ami` | SHA256 `876c9653d2d038781ece3167646c642623cfa49f8a0aa32edd1f3b10eff21904` | AMI 5.1；有 GetWave；没有 Modulation；Adaptive 是 DFE mode，不能声称 PAM4 CDR |
| `models/ibisami/example_rx.ibs` | SHA256 `28156d0a578fda44c02639df90082f457a13a3e7e45114d23f3adaef21c61f7f` | 文件版本 v0.1、2024-07-05；IBIS 7.1；列 Windows VisualStudio 64 executable；不能用其 IBIS 版本替代 `.ami` 版本 |
| `example_rx_x86_amd64.dll` | 363008 bytes；SHA256 `60e29f16dcfe1a40240956f0591b29f524ccc8844c4959671d0317178c1ff46c`；PE machine `0x8664` | 仅重读字节确认 AMD64；本轮未验证加载、依赖或执行 |
| PyAMI `example_tx_x86_amd64.dll` | 347136 bytes；SHA256 `83447b8066afe3407b54b9918e7a994016756b7587f814ab654165aa703f6362`；PE machine `0x8664` | Tx fixture，不能替代 Rx clocks 资格 |

既有 Rx bundle 的旧记录 hash 为 `8ebce8bbc5577eb1f5a721e515c0555080241a6eb27b303ce0e52fff634ffac1`。本轮未重新打包。`models/ibisami` 最近一次既有 Git 变更为 `4836138a35702f49cfbf91ee00621f29d167efd3`，它不是 DLL build commit 证明。

作者仓库调查固定于 [`capn-freako/ibisami@74555dd7445b38790d777f23491a39d16bfdc4df`](https://github.com/capn-freako/ibisami/tree/74555dd7445b38790d777f23491a39d16bfdc4df)。README 的 public-domain 描述不能替代实际 [BSD-3-Clause LICENSE](https://github.com/capn-freako/ibisami/blob/74555dd7445b38790d777f23491a39d16bfdc4df/LICENSE)。PyAMI 自身 LICENSE 是 BSD 两条件文本；两者许可分别记录。

| 作者固定源码 | Git blob SHA | 相关行为 |
|---|---|---|
| [`src/ami_rx.cpp:84–86`](https://github.com/capn-freako/ibisami/blob/74555dd7445b38790d777f23491a39d16bfdc4df/src/ami_rx.cpp#L84) | `82ac7873f4ba0c0de1c56acd0747941d356e08de` | 先写首项 `-1`；存在 DFE 时将同一 clocks 指针传入 apply |
| [`src/dfe.cpp:21–110`](https://github.com/capn-freako/ibisami/blob/74555dd7445b38790d777f23491a39d16bfdc4df/src/dfe.cpp#L21) | `b6e8560c3988b611bd940da0e003c90a375b415f` | constructor 初始化时间；apply 写 edge-aligned tick 并累计；整个函数未在有效 ticks 后补 `-1`；第 63 行 CDR adjust 被注释 |
| [`src/ibisami_api.cpp:120–167`](https://github.com/capn-freako/ibisami/blob/74555dd7445b38790d777f23491a39d16bfdc4df/src/ibisami_api.cpp#L120) | `f3a10fe13a030480b5956252722d209859e7a069` | 直传 clock 指针；复制返回参数后返回，不补 terminator |

该源码输出固定周期 clocks，不能据 DFE Adaptive 宣称实现 CDR tracking；固定周期本身也不等于违反 clocks 格式合同。后续验收需明确要求格式合规、实际消费还是 tracking 能力。以上源码未映射到本地旧 DLL，不能把当前源码观察写成旧 binary 实测结论。

## 候选 fixture 与获取路径

截至本轮没有新增 binary 下载。`SOURCE_BLOCKED` 表示缺实际包及核验材料，不表示供应商模型必定不支持 clocks。

| 路线／官方来源 | 能力证据 | 缺口／下一步 |
|---|---|---|
| 作者维护后的 example_rx NRZ | 与现存失败及公开 C++ 最接近 | NRZ 首选获取路线：要求维护者提供带合法 sentinel 的原始发布包、build commit、AMD64 依赖、至少两次连续 GetWave 的 golden；不本地改 DLL 输出或重编成替代资格。尚未联系维护者 |
| [AMD Versal/UltraScale+ GTM 下载入口](https://www.amd.com/en/support/downloads/adaptive-socs-and-fpgas/device-models/simulation-models.html)、[XAPP1392](https://docs.amd.com/r/en-US/xapp1392-pcb-chan-design-guidelines/Summary) | 官方文档讨论 56/112 Gbps PAM4，指向 secure model site | PAM4 候选，SOURCE_BLOCKED：需要有权账户取得包及条款；版本、AMD64、依赖、再分发权和 clocks 契约均未核验 |
| [Altera Agilex 7 F-Tile FGT 官方 KB](https://community.altera.com/kb/knowledge-base/%E2%80%8B%E2%80%8B%E2%80%8B%E2%80%8B%E2%80%8B%E2%80%8B%E2%80%8Bwhy-doesn%E2%80%99t-the-ibis-ami-model-for-the-agilex%E2%84%A2-7-fpga-f-tile-fgt-receiver/340013)、[官方获取答复](https://community.altera.com/discussions/fpga-device/ibis-aim-model-for-pam4/276005) | KB 指出 ≤1.7 Rx PAM4 相关性问题并推荐 2.1；NRZ 也可能改变 | SOURCE_BLOCKED：旧获取答复涉及 CNDA/支持申请，不推定当前账户有授权；需取得当前包、许可、AMD64 和 clocks golden，不能拿旧 1.7 作为 PAM4 基准 |
| [MathWorks CEI-112G-VSR 示例](https://www.mathworks.com/help/serdes/ug/CEI-112G-VSR-transmitter-receiver-ibis-ami-model.html) | 明确 PAM4、Rx DFECDR 和 Dual Init/GetWave DLL 导出 | 是生成工作流，非本轮已取得的公共预编译 fixture；需要有许可证的提供方交付原包及许可，本轮不构建或运行 |
| [Ansys v242 sample AMIs](https://ansyshelp.ansys.com/public/Views/Secured/Electronics/v242/en/Subsystems/Circuit/Content/Circuit/SampleIBISAMImodels.htm) | 列出 PCIeG6_TxRx、RX_PassThru_PAM4 等，经 SPISim/AEDT 生成 | 名称含 PAM4 不证明返回有效 clocks；未取得 binary、模型许可或 clocks 契约，不作为直接可用方案 |
| [SerDesDesign 许可说明](https://www.serdesdesign.com/home/web_documents/SerDes_Design_Free_Tool.pdf)、[2025 模型资料](https://www.serdesdesign.com/home/web_documents/models/Generate_Portable_IBIS_AMI_Models.pdf) | 描述 Windows/Linux 64-bit 和 CTLE/CDR/DFE 路线 | free tool 为可续期 node-locked，生成模型继承限制；旧公开 pass-through/TxFFE/RxCTLE 样例未声明所需 CDR，不为此 gate 下载；先取得可保存/共享的既有 NRZ/PAM4 包及 golden |

获取材料的最小清单：原 `.ibs/.ami/DLL` 包、许可证、发布版本/hash/build provenance、Windows AMD64 依赖、调制与合法速率范围、Ignore_Bits/最小符号数、clock 能力声明，以及至少两个连续 GetWave 调用的原 buffer、有效长度、sentinel、返回参数和 golden。器件有 CDR 不等于其 AMI 模型返回 clocks。任何对外联系或账户取包均未在本轮执行。

## 下一阶段可评审方案（未授权实施／未执行）

应按以下边界分别修复和评审；不能把纯解析修复扩大为未经声明的数值行为调整。

| 顺序 | 最小改动范围 | 先行的零库验证／成功标准 | 兼容与资格边界 |
|---|---|---|---|
| A | PyBERT GetWave 返回参数 visitor 与 Python str tap 筛选 | 保存字符串、空 root、嵌套数值、非数值/Table、同名 leaf、大小写 tap；保持完整 path，真实非空 taps 不再因接口失败 | 不改 PyAMI 全局 parser；不造未返回的 lock/UI/tap；Tx 返回参数语法错误独立保留 |
| B | PyAMI `AMIModel.getWave` 的有效前缀提取与跨 call 拼接 | 普通 buffer stub：首项 -1、合法多块、variable count、短末块、非有限/倒退、缺 sentinel、残留尾槽；有效序列不混入容量 padding、不按 UI 任意截断 | 保留安全容量；缺 sentinel 不能猜有效长度；不能排序、正值过滤、补 tick 或静默接受坏模型；依赖修改另立审查 |
| C | `run_ami_model/get_responses` 的响应探测与真实模型状态 | 先用纯状态 stub 明确两次 probe 消耗、实际首次 GetWave 原点、bits_per_call 残留；形成前后调用图 | 优先评审独立 probe instance／真实 waveform fresh initialization；会改变状态、wave/params/clocks 和 Init 次数，必须独立冻结，不能混在 A |
| D | PyBERT 标量相邻 tick 遍历、采样边界及 metadata | 合法 clock stub 可逐标量遍历；覆盖末 tick、半 UI、超时窗、Ignore_Bits、NRZ/PAM4 symbol time、fallback 与 TxGW；标签区分 returned/format-valid/eligible/consumed | `pairwise(clock_times)` 只是已定位的最小表达式修正方向；完整采样窗口及末 tick 策略仍需审查；不能只修标签后称已消费 |
| E | 合法 NRZ/PAM4 fixture | 先按上表静态核验来源、许可、版本、ABI、调制和 golden | 某行资源不足时保留 SOURCE_BLOCKED；不能由接受任意波形推断调制能力 |

### 分阶段 freeze 与拟预算

下表是供 PM 另定义任务的方案，**不是本轮剩余执行额度**。

| 阶段 | 执行前 freeze | 拟上限及停止条件 |
|---|---|---|
| 0：纯解析／数据 stub 修复验证 | 固定代码/依赖 diff、保存输入、预期结果和兼容矩阵 | Main/COM/coopt/真实库/Init/GetWave/原生 helper 全 0；本轮只有缺陷诊断，没有实施这些修复 |
| 1：逐调用 C buffer 有界预检 | 每个 fixture 的原包/hash/license/ABI/golden、准确 AMI 树、UI/ts、固定两块 waveform/长度/seed、buffer 容量及 sentinel 检查规则；固定 harness 和实际加载模块；原始 per-call buffer、return code、params 全保留 | 至多 NRZ/PAM4 各 1 个 fixture：每个 load≤1、Init≤1、GetWave≤2、Close≤1；合计 load≤2、Init≤2、GetWave≤4、Close≤2；Main/COM/coopt/原生数值 helper=0。任一来源、ABI、sentinel、单调或预期不符即停，不自动进入主仿真 |
| 2：真正消费配对验收 | 只在阶段 1 通过及 A–D 固定评审后；冻结全部 input/config、source、依赖、随机性、bit/sample/ignore/eye 窗口、绝对时基、容差和实际调用图；明确新旧状态语义 | NRZ direct+worker、PAM4 direct+worker，拟 4 Main；coopt/COM=0。fallback 若需回归，单独申请最多 2 Main，不占用有效 clocks 行。Init/GetWave 总上限必须根据最终模型与 probes 隔离方案算定后再授权，不存在“4 Main 自动包含无限内部调用” |

阶段 1 的 buffer 捕获必须在 native call 返回后、wrapper 聚合前保存，不能再只存 aggregate。阶段 2 除波形和响应外，要比较返回参数、raw clocks、实际采样 clocks/decisions、单位与分析 metadata；证据必须表明 AMI clocks 分支实际完成，不能仅凭入口谓词。direct/worker 一致只能证明实现一致，不能替代标准合同和 golden 核验。

目前新 fixture 未取得，A–D 未实现，阶段 1/2 尚无可执行 freeze，也无执行授权。下一步可先独立完成零库软件修复；真实预检必须等 PM 收到资源与固定预算后另定义。

## 本阶段成本账与原件保护

| 项目 | 本轮新增 |
|---|---:|
| Main / COM / coopt（含候选评估） | 0 / 0 / 0 |
| AMI_Init / AMI_GetWave / AMI_Close | 0 / 0 / 0 |
| 真实库加载 / 引擎构造 / 原生数值 helper | 0 / 0 / 0 |
| 新模型 binary 下载 / 编译 | 0 / 0 |
| 保存字符串纯 grammar 解析 | 750 |
| 保存数据、AST、普通 list 诊断工具执行 | 1 次；内部 elapsed `0.47033169999485835 s` |
| 本阶段全部调查 wall time / peak RSS | UNKNOWN；未连续测量，不能以 0 引擎称零时间或零资源成本 |

输入 SHA256、诊断结果和新增调用账均在 diagnostics.json。运行前后受检查的输入 hash 不变；Git 交付范围只含本目录。所有旧报告、失败、raw、source、freeze 和 ignored 内容均留在原位置；没有新 PR、没有关闭 issue、没有重跑旧矩阵。新提交的身份与范围检查另随交接消息给 PM，完成后停止写入返权。

4 个新文件均经 UTF-8 解码及无 BOM 检查。原始 stdout 日志使用 CRLF；默认 `git diff --cached --check` 将其中 CR 报作 trailing whitespace（exit 2），按 `git -c core.whitespace=cr-at-eol diff --cached --check` 检查通过（exit 0）。未为通过检查转换该原始日志字节，也未修改 `.gitattributes`。

## 固定源码链接

- [PyBERT bert.py（本次基线）](https://github.com/yx520143-G/PyBERT/blob/b96977a34ec5122bef9f6b4457a035535215ac8a/src/pybert/models/bert.py#L375)
- [PyBERT utility/ibisami.py](https://github.com/yx520143-G/PyBERT/blob/b96977a34ec5122bef9f6b4457a035535215ac8a/src/pybert/utility/ibisami.py#L145)
- [PyBERT web/ami.py](https://github.com/yx520143-G/PyBERT/blob/b96977a34ec5122bef9f6b4457a035535215ac8a/src/pybert/web/ami.py#L360)
- [PyAMI parser.py（固定 gitlink）](https://github.com/capn-freako/PyAMI/blob/5270d713e40bac2be5747bef09b92df79df9085b/src/pyibisami/ami/parser.py#L114)
- [PyAMI model.py（固定 gitlink）](https://github.com/capn-freako/PyAMI/blob/5270d713e40bac2be5747bef09b92df79df9085b/src/pyibisami/ami/model.py#L458)
