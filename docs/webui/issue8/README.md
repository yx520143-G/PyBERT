# #8 Native EQ 优化

从 `5fcf8285b042fe1fe92c068b1c3311fa87a50de0` / tree `c06164a0b87c4577073477c71a9ec05aee5125ee` 独立实施。仅写 fork `yx520143-G/PyBERT`；主 checkout、前任 worktrees、失败原件未清理。规格见 [live #8 快照](spec-snapshot.md)。

Native Tx FFE / CTLE / Rx FFE / bounded ideal DFE 的非 MMSE 网格和 MMSE 均复用 `coopt`。节点可编辑搜索约束，独立优化工作区展示候选 pulse、原始 FOM、获选 ID、输入/资源身份与模型边界。Tune 与 Run/COM/原生归一化共享一个 fresh-spawn 槽位；worker 同步调用，不启动另一条优化线程。

候选不自动应用。Use EQ 展示冻结输入与当前草稿冲突，用户明确选择后仅应用原 handler 的 Tx/CTLE/RxFFE 字段；不写入 DFE 初值。Reset 复用原 handler，只同步实际 EQ 的初值/enable，不重置范围、DFE 或 Run。原始输入、草稿、候选和成功 Run 分开；普通 Run 不消费 RLM。

MMSE 使用原代码固定 Tx level 0.5 V、SNR 25 dB、DJ/RJ=0 与空 aggressor；Rn 进入 eta0。每次实际 MMSE 调用保存输入 pulse/H/范围、独立 Hz/s 网格、cursor、RLM 与输入 hash。候选是理想 bounded DFE 的等效 pulse，MMSE cursor=1；不是 `dfe_out`、恢复 CDR、BER 或标准 COM。

## 验证与原件

| 项目 | 证据与边界 |
| --- | --- |
| 首次计算前冻结 | `06dc89f`；[v1 manifest](fixtures/v1/manifest.json) SHA256 `a8b1922b1652a734ac0a524528d8a3b970a056b3f9124fb0a74c71b77f5d6e2f`。4份完整 Native 输入，outer=4，grid inner=2，继承 #2 非零 seed/noise；全部 tap/枚举顺序/资源/轴窗口/容差预定。RLM=.95/.80 两份 PAM4；文件资源为 #4 的 A |
| 首轮数值 | [122031](evidence/numerics-20261024-122031/report.json)：4 direct + 4 adapter，各独立实例串行；136 数组、候选顺序/获选身份/FOM/轴均通过。实际执行的是带可选观察器的同一 helper，不冒称另跑了未修改 base |
| 首轮源码补存 | [source supplement](evidence/numerics-20261024-122031/source-supplement-v1/report.json)：事后补存执行 native/verifier 字节；owner 确认首次计算后两文件未变。不能把 fixture-only HEAD 当实际执行源码。默认调用的完整模块 AST 去除观察增量后等于 base；原报告不回写 |
| 实际 MMSE 输入 | `d838995` 的 [计算前扩展](fixtures/mmse-context-v2/manifest.json) 保持原物理请求/容差，增加实际输入记录；[130501](evidence/numerics-20261024-130501/report.json) 2 direct + 2 adapter，原输出与每次 MMSE 输入 hash 均通过 |
| 无新计算审计 | [130843](evidence/delivery-audit-20261024-130843/report.json)：738 checks、0失败；252 direct/adapter 数组 dtype/shape/C-order bytes exact；两普通 PAM4 Run 的全部原数组 exact，只有 RLM runtime 不同；各优化 archive 重开 record/raw bytes exact；最终默认 native AST exact。审计本身 0 coopt/0 main/0 COM |
| Chrome 1280×720 | [v1](evidence/chrome-v1/)：MMSE/非MMSE、候选切换、100 FFE 槽、Use 冲突取消与确认、Use 后新 Run、Reset、原生 RuntimeError failed、预算422。三次成功 Main 均有实际下载 archive |
| 执行中取消 | [phase4d](evidence/chrome-v1/phase4d.log)：先断言 enabled，再 force click 命中短 coopt 窗口；原检查点观察 Event、退出/join 链路完整。原鼠标尝试自然完成，不能当取消成功 |
| 无 force 键盘取消 | [keyboard abort](evidence/chrome-v2/keyboard-abort.log)：预登记的 [outer16/inner16](fixtures/cancel-ordinary-v2/manifest.json)，Enter 操作先返回 requested=true/observed=false/exited=false，随后原检查点观察并实际退出。与 force-click 案例分别记录 |
| 契约与兼容 | [v2](evidence/contracts-v2.log) 120 passed；[v3](evidence/contracts-v3.log) 60 passed。包含既有 Web/archive/resource/COM 故障协议、CLI version、MCP config/tool 注册；COM 均为故障注入或预取消生命周期，0数值 COM。未跑默认优化、未新跑完整 native GUI/CLI 仿真 |

最终存档重开与固定源码复核记录在收尾追加；上表中的历史批次各自保留执行源码、失败和成本，不能拼成不存在的同批全套成功。

## 保存与资源预算

`.pybert_opt` 是 schema 1 ZIP，恰含 `manifest.json` 和原 `arrays.npz`；不使用 pickle 活实例。保存完整冻结输入、RLM、资源 hash、候选/轴/权重/评分、状态、实际版本与生命周期。raw schema 1/2 可读，未知版本、required features、校验值、对象数组或坏轴拒绝。失败/取消保留其状态，不能 Use；非有限失败原数组可以作为失败诊断保存，不作成功图。

YAML 保存当前草稿；版本化 runtime 注释保留 RLM、Reset 初值和 Use 来源，并明确列出 Native `PyBertCfg` 无法表达的字段。候选 pulse/FOM/history 保存为独立 `.pybert_opt`。资源只保存引用/hash；重跑仍需按 #4/#5 契约绑定原资源。

预算：outer≤256、inner≤256、合计≤4096；Native 时间网格≤2,000,000 点、频率网格≤200,001 点；每记录≤768 MiB 原数组，合计1 GiB；最多16个会话计算记录、4个打开的优化 archive。预算拒绝不缩范围、不回退默认。验收 fixtures 各 outer≤16、非MMSE inner≤16。

## 成本与保留限制

截至 [130843 audit](evidence/delivery-audit-20261024-130843/report.json)：真实 coopt **23 次**＝6 direct + 6数值 adapter + 11 Chrome（8成功、2取消、1原生失败）；真实 main **3次成功**，数值 COM **0次**。取消和自然完成的尝试均计成本。每次 elapsed、spawn→exit、候选数见审计；数值 fixtures 的峰值 RSS 已采样，Chrome 峰值 RSS 未采集，明确为 unknown，不能拿 fixture 峰值代替。

保留初始化缺 psutil（0计算）、file chooser 截断、旧 busy/轮询、过早断言、下载校验及取消未命中等原失败日志。普通鼠标取消尝试没有形成有效取消证据；Enter 与 force-click 的实际方法分别列出。所有 ignored raw/archive 在本 worktree 的 `evidence/**/local/` 与 `output/playwright/issue8/`，不加入 PR，不清理。

默认 COM 139756144 外层仍为 **OPEN / BLOCKED_BUDGET / NOT_EXECUTED**；#16 不执行。TIME/CTLE File/非零 impulse_length/package+FEXT、既有 PAM4 errors20 等限制不因本票解除。AMI/TPE 属于 #10，Viterbi 属于 #9。本票不主张 FOM/BER 改善、COM correlation 或资格认证。
