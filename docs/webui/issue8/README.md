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
| 修复复核 | [双轴审查](review.md)：异步编辑/候选身份及预算问题已闭合；[v5](evidence/contracts-v5.log) 63 passed，[静态与 VM](evidence/static-v2.log) 通过。v4 的新测试 EyeBits 前置设置错误原件独立保留，不能当预算拒绝的成功证据 |
| 最终恢复 | Chrome 155.0.8059.85 / 1280×720；[分段恢复](evidence/chrome-v3/recovery-v5.log)、[新会话最终检查](evidence/chrome-v3/final-view-v2.log)。PAM4 两份 raw schema 2、NRZ、取消记录、两份 Run archive、YAML RLM/Use 来源恢复，0新增数值调用；图见 [MMSE](evidence/chrome-v3/09-readable-mmse.png)、[grid](evidence/chrome-v3/10-readable-grid.png) |
| 收尾源码与原件复核 | [132655 audit](evidence/delivery-audit-20261024-132655/report.json) 再次 738 checks / 0失败；[final source](evidence/final-source/report.json) 10 checks / 0失败，保存生产代码 `f64d482` 的源码 bytes/hash，三次浏览器重下载 record/raw exact，YAML config/runtime exact。仅管理/UI/预算增量通过状态测试；历史数值批次各自绑定其执行源码，不冒称重跑 final-source 数值批次 |
| PM 最终审查后修复 | 固定 `238b1cab` 的 PM 最终审查发现 Spec 2 P2（Standards 0），修复代码 `e55819a`；[独立 delta 复核](evidence/pm-fixes-v1/review.md) 两项闭合。[契约](evidence/pm-fixes-v1/contracts.log) 37 passed，[实际存档 API/observer 核对](evidence/pm-fixes-v1/saved-report.json) 100 checks / 0失败；13 原件、12 topology 冲突与12自洽 cursor 坏副本。新增 coopt/Main/数值 COM 均为0 |

上表中的历史批次各自保留执行源码、失败和成本，不能拼成不存在的同批全套成功。最终恢复脚本有 response inspector cache、错误消息断言、URL query 谓词及旧 CSS 缓存等取证失败，均保留在 `chrome-v3/`，分段恢复未新增 coopt/Main/COM。最后一行 CSS 修复经 Standards 只读确认。

## 保存与资源预算

`.pybert_opt` 是 schema 1 ZIP，恰含 `manifest.json` 和原 `arrays.npz`；不使用 pickle 活实例。保存完整冻结输入、RLM、资源 hash、候选/轴/权重/评分、状态、实际版本与生命周期。raw schema 1/2 可读，未知版本、required features、校验值、对象数组或坏轴拒绝。失败/取消保留其状态，不能 Use；非有限失败原数组可以作为失败诊断保存，不作成功图。

YAML 保存当前草稿；版本化 runtime 注释保留 RLM、Reset 初值和 Use 来源，并明确列出 Native `PyBertCfg` 无法表达的字段。候选 pulse/FOM/history 保存为独立 `.pybert_opt`。资源只保存引用/hash；重跑仍需按 #4/#5 契约绑定原资源。

预算：outer≤256、inner≤256、合计≤4096；Native 时间网格≤2,000,000 点、频率网格≤200,001 点；每记录≤768 MiB 原数组，合计1 GiB；最多16个会话计算记录、4个打开的优化 archive。预算拒绝不缩范围、不回退默认。验收 fixtures 各 outer≤16、非MMSE inner≤16。

存储预检逐类计入实际 MMSE pulse/H/范围和导出数组，观察器保留新数组前再次累计检查。活动优化期间不接受新 archive，保持预留容量。Use/Reset 响应与确认绑定冻结草稿 revision，候选详情加载中禁止 Use/Save，过期响应不改变当前来源。

Use EQ 要求当前 Rx FFE 的 `Ntaps/Npre` 与获选记录相同；不同会在应用前明确拒绝，用户可恢复原 topology 或针对当前 topology 重新优化。成功预览的 `after` 与 `after_input_hash` 来自最终 config。成功 raw schema 1/2 存档必须含真实 `curs_ix` / `curs_amp` 两端点，且与获选 pulse 峰值和时间轴一致；缺项、坏形状或不一致在发布前原子拒绝。失败/取消原件不补造成功 cursor，仍按原诊断边界保留。

本次修复使用现有原件，无需新 Chrome 会话：API 验证禁止启动 worker，仅将原配置观察器 inline 调用；[VM](evidence/pm-fixes-v1/ui.log) 验证拒绝后保留已选来源/草稿、不应用 EQ。[源码适用性](evidence/pm-fixes-v1/source-applicability.json) 记录原30份执行源中的28份不变、2份变化，变化源码和新增测试逐字节另存，旧报告/失败/raw 不回写。数值批次仍绑定原执行源码。

## 成本与保留限制

截至 [130843 audit](evidence/delivery-audit-20261024-130843/report.json)：真实 coopt **23 次**＝6 direct + 6数值 adapter + 11 Chrome（8成功、2取消、1原生失败）；真实 main **3次成功**，数值 COM **0次**。取消和自然完成的尝试均计成本。每次 elapsed、spawn→exit、候选数见审计；数值 fixtures 的峰值 RSS 已采样，Chrome 峰值 RSS 未采集，明确为 unknown，不能拿 fixture 峰值代替。

三次 Main 的 DFE errors 依次 **0、0、7**；Use 后新 Run 的 7 errors 原件保留，不主张 Use 改善误码。最终恢复、审查修复与审计新增 coopt/Main/数值 COM 均为0。owner 的 8773/8774/8775 验证服务与两个 Chrome 会话均已停止；原主 checkout 保持 `b9c56fe` 与既有两处 untracked 路径。

保留初始化缺 psutil（0计算）、file chooser 截断、旧 busy/轮询、过早断言、下载校验及取消未命中等原失败日志。普通鼠标取消尝试没有形成有效取消证据；Enter 与 force-click 的实际方法分别列出。所有 ignored raw/archive 在本 worktree 的 `evidence/**/local/` 与 `output/playwright/issue8/`，不加入 PR，不清理。

默认 COM 139756144 外层仍为 **OPEN / BLOCKED_BUDGET / NOT_EXECUTED**；#16 不执行。TIME/CTLE File/非零 impulse_length/package+FEXT、既有 PAM4 errors20 等限制不因本票解除。AMI/TPE 属于 #10，Viterbi 属于 #9。本票不主张 FOM/BER 改善、COM correlation 或资格认证。
