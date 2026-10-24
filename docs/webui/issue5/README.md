# #5 结果存档、参考比较与草稿迁移

本票在独立 `codex/pybert-issue5-archive` worktree 实现完整 Web run archive、可信原生结果兼容、参考管理与 PR7 草稿迁移。当前 PM 返修产品提交为 `bdcaf50110755e00c9a3064d02081301c4feeb8c`，见 [本轮修复与追加证据](pm-fixes-v6.md)。首轮产品 `3ccb88f4e34db2a81a04a6b7a7f198f0c88e367d` 及交付 `246ce486388ac717409aa27adddfa533b21bb7a5` 的记录/证据保留。base 为 `f1d0ea80f9db8ab31e25963496875a44fe4a19d9`，base tree `86fbe940f37d08d5ed13738e263df678561d26fe`。未修改 native/GUI/CLI/MCP 算法、模型公式、依赖或 submodule gitlink。

入口为现有 Web 工作台“打开结果 / 加入比较”“保存所选结果”“原生保存 / 损失清单”“恢复所选输入到草稿”“移除/清除参考”。`Save`/`Save As` 继续保存当前配置，与保存所选成功记录分开。

按现有安装方式运行 `uv run pybert web`（缺 Web 依赖先 `uv sync --extra web`），浏览器访问 `http://127.0.0.1:8765`。逐项功能/后续票落点见 [功能矩阵](function-matrix.md)。

完整 `.pybert_run` 是 archive schema 1 的 ZIP，恰含 `manifest.json`、原字节 `arrays.npz`。保存完整原输入、summary/window/plots/datasets、原 manifest UTF-8 文本、NPZ 与逐数组校验值，以及保存时的 linked COM 任务/输入/结果可用性快照。只接受 raw schema 2/3/4、primitive finite numeric arrays；读 NPY header 先验预算，`allow_pickle=False`，未知必需版本、损坏或不完整数据原子拒绝。原资源缺失仍可看图；恢复输入后 Run 必须重绑同内容 hash 的资源，删除参考也不会解除独立 replay guard。

可信 `.pybert_data` 走显式勾选的本机 pickle 分支，界面明示可执行代码。仅原生 23 项清单/容器与有限数值结构受支持。无原轴时只显示 sample/frequency-bin index，频响保留已显示的 dB，禁止借当前物理轴叠加。实际 native-cli 文件的 `tx_out=None` 如实 absent，原生导出禁用；独立 sidecar 可下载。23 项均具备时测试确认复用原 `PyBertData` 构造器，不补零、不伪造 producer 版本。

临时成功缓存保持 2 条，每条数组上限 768 MiB；外部参考独立 ID，最多 4 条/1 GiB 数组，超预算拒绝而不淘汰。可显式删除参考；原 source run ID、输入和图层绑定不串用。每条曲线使用自己的轴；不同眼图网格并排，未插值/重采样后冒充数值一致。浏览器只保存轻量 schema2 草稿/配置/选择；原 PR7 schema1 键和非法 JSON 保留，未知/非法 retained 输入阻止 Run。只有结构合法的已知 optimizer computed metadata 可标非阻断。

## 验证结果与适用性

| 检查 | 结果与原件 |
| --- | --- |
| saved-only 历史保存/重开 | [104338 report](evidence/saved-roundtrip-20261024-104338/report.json)：#2/#3/#4 五组 **2053 数组**，原 NPZ/manifest 字节、dtype/shape/C-order bytes、所有 plot payload、linked 历史 COM task/input/result exact；0 main/0 COM；原件 hash 未变 |
| 真实 Chrome Run | PAM4 与 NRZ 两成功，NRZ 刷新重连保持同 task；NRZ DFE/CDR 期间 Abort；另有 CTLE preflight 失败。两成功原数据分别 **440/439 数组，共 879**，对 #4 SINGLE 独立 worker 原件逐项 exact。完整95字段、runtime、bindings、window、非性能 summary exact。见 [raw audit](evidence/chrome-raw-audit-20261024-110155/report.json) |
| 下载归档 | Chrome 实际下载 NPZ/manifest 与各 run 原件 exact；编辑 NRZ 时保存旧 PAM4，旧输入与数据不变。存档不要求原资源存在。恢复输入→移除参考→缺资源阻止→同 hash 重绑→实际 PAM4 Run 成功 |
| 视图/比较 | [phase7](evidence/chrome-v2/ui/phase7-analysis.log)：49 个视图检查，加 Jitter Info/输入差异；当前 NRZ 与重开 PAM4 频率6条曲线各用原坐标，眼图各有时间/电压网格。切图/缩放/加载不 Run |
| 失败/预算/legacy | [phase9 prefix](evidence/chrome-v2/ui/phase9-files.log) 与 [phase9b completion](evidence/chrome-v2/ui/phase9b-budget-complete.log)：坏 archive/未知版本/下载503不改原记录；Save As Escape、空文件选择；真实可信 legacy、缺 tx_out 与损失 sidecar；第五参考拒绝、清除参考保留两成功/草稿 |
| 服务重启 | [phase10d](evidence/chrome-v2/ui/phase10d-restart.log)：新服务没有临时成功/资源，重开两 archive 可比较。最终 [phase13 before](evidence/chrome-v2/ui/phase13-selection-before.log)/[after](evidence/chrome-v2/ui/phase13-selection-after.log)：有效记录按原 ID 恢复且清查询提示；实际重启再刷新，原 ID 保留、明确不可用，未伪造成功 |
| 历史活跃 COM 快照 | [phase11c](evidence/chrome-v2/ui/phase11c-com-snapshot.log)、[来源](evidence/com-snapshot/source-report-v2.json)：只读回放 #4 原始 running/final task，所有 start 禁止；Chrome 保存 running 后，把同 ID 会话切为原 succeeded，再重开/重存 archive，仍保持原 running/waiting_for_exit；父 NPZ/manifest 与子快照 exact。**这是历史快照回放，本票没有执行 COM** |
| PR7/存储故障 | [phase12b](evidence/chrome-v2/ui/phase12b-storage.log)：由真实原 catalog/settings 生成112字段完整 v1 fixture，逐字段 exact/retained，旧键原字节不改，新来源为完整 SHA；非法 JSON/未知 schema/未知 retained 拒绝；真实 Chrome 注入存储写失败后输入26仍在，恢复保存27。最终配置下载的 [95字段核对](evidence/chrome-v2/config-save-audit.json) exact |
| 契约测试 | [final v5](evidence/archive-contracts-final-v5.log)：17 passed，含坏版本/NPZ对象拒绝、资源 guard、原子失败、预算、legacy、active snapshot、不串会话 |
| 已有契约/兼容 | [core v3](evidence/core-contracts-v3.log)：74 passed/5 failed（缺未初始化 submodule 文件）；固定 submodule 后 [定向 v4](evidence/submodule-fixed-com-contracts-v4.log) 7 passed，解除5个原路径错误，原失败保留。[CLI/MCP](evidence/compatibility-v1.log) 4 passed；GUI/CLI/MCP 本 worktree import 通过；未新跑 native GUI/CLI 全仿真 |
| 最终源字节 | [closeout-v1](evidence/closeout-v1/report.json)：11 checks passed；104338 全部 Python 源字节仍相同；真实 Run 后仅 draft.js/workbench.js UI 修正，并由最终 Chrome/JS 复验。文档 HEAD 不替代执行源码 hash |
| 双轴复核 | [review](review.md)：Standards/Spec 各 0 未关闭 finding；原问题和修复记录保留。Ruff E4/E7/E9/F、JS syntax、`verify_web_draft.cjs`/`verify_web_storage.cjs` 通过 |

## 调用成本与边界

| task | 终态 | created→finished 秒（含 spawn/退出） | main/COM |
| --- | --- | ---: | --- |
| PAM4 `c4532a94-3702-44e9-9869-106b3198cf79` | succeeded/exited；DFE errors **20** | 7.836384 | 1/0 |
| NRZ `573aed1e-b3b5-4977-8d6b-a482b94fdd2a` | succeeded/exited；DFE errors 0 | 10.195427 | 1/0 |
| NRZ `7876578d-ae5e-4f75-82d9-88a106b1b803` | cancelled/exited；不计成功 | 5.771289 | 1/0 |
| CTLE `47c6eedb-b7b9-49cd-afbb-88d7673002ca` | preflight failed/exited | 3.712789 | 0/0 |

本票合计 **3 main（2成功+1取消）/0 COM**，另1个 preflight 任务；observer/config normalization 会启动串行配置 worker，但不进入主仿真/COM。以上不是全部开发 wall-clock，也不抹去取消/失败成本。NRZ/PAM4 固定输入、资源 A hash、非零噪声/seed、窗口与既有容差见 [执行前 freeze](fixtures/chrome-execution-v1/manifest.json)，其 SHA256 为 `6ab618dbed62732738b2d0bdc35b10fa89924dadf568b58e6655402a170c5d3f`。原参数和物理公式未因归档验证改变。

#4 默认 COM gate 继续 **BLOCKED_BUDGET / NOT_EXECUTED**，139756144 outer candidates、0次默认 COM；本票归档兼容不解除它。TIME/CTLE File/impulse_length/package+FEXT 原生边界保留；PAM4 errors20 不称 qualification。#8/#9/#10 专项未实现，完整 native GUI/CLI 仿真未在本票重跑。

## 原件、失败和本机位置

所有证据追加，未清理旧 worktrees 或主工作区。当前 managed worktree 为 `C:/Users/yx/.codex/worktrees/pybert-issue5-archive/serial-bus-simulator`。大 raw/archives/resources 留在 ignored `evidence/**/local/` 和 `output/playwright/`；NPZ/pickle/模型库不入 PR。提交中提供 JSON、完整 task/manifest、日志/脚本、hash 与截图；本机独立审计可读取保留原件。

`saved-roundtrip-102330` 因早期 raw 无 schema 被拒绝；`102512` 为未封存源字节的历史验证，只以 `104338` 建立固定源码证据。core-v3 的原5路径失败保留。Chrome phase1 为 filechooser 截断的局部尝试，不能当整段通过；phase6 首次取消被迁移错误本地阻止（0 main），修后 phase6b 实际取消；phase9 在第四次同文件选择前因 finally reset 竞态超时，phase9b 从保留的3参考继续完成。phase10/10b/10c 为状态/observer 等待断言的局部失败，phase10d及最终phase13补足；phase11/11b 为验证用 fixture endpoint 被静态 mount 遮蔽导致等待超时，修复只读回放工具后 phase11c 完成；phase12 首次错误要求尚未写回的持久化 blocking 标记，改为验证执行阻止后 phase12b 完成。原失败日志/原版脚本均保留；01/02/25 等截图是阶段性视图，最终 COM 明细见26。

Chrome 控制台保留 favicon404、服务重启连接失败、预期422/503等；不声称零控制台错误。08截图的旧“正在查询/不可用”混合文案由最终查询状态修复及phase13证据替代，旧图保留。

新写源码/文档默认 UTF-8 without BOM。[编码检查](evidence/encoding-audit.json) 中140个文本为UTF-8、无BOM；唯一历史 `core-contracts-v3.log` 含旧控制台非UTF-8原字节，按证据保留，不转码覆盖；同次JUnit XML可机器读取。Git whitespace检查针对源码/工具/新文档通过，原始终端输出的CRLF和空白不改写。

验证使用只读 #4 venv 的依赖、显式 `uv run --no-project --python .../.venv/Scripts/python.exe`，`PYTHONPATH` 指向本 worktree；PyBERT/Web/GUI/MCP 模块路径已检查。本 worktree PyAMI/PyChOpMarg 初始化到既有固定 gitlink，未更新版本。验证服务与 Chrome 会话在交付前停止；状态见 [handoff v2](evidence/handoff-v2.json)，追加更正原handoff中#13目录标签为实际`pybert-native13-ports`，原件保留。本票保持 draft，等待 PM 终审，不 merge、不关闭 #1/#4、不派下一票。
