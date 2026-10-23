# 交互证据与适用边界

这是桌面 GUI 行为记录，不是 Web 实现验收。起点是同一次实际启动的 PyBERT 窗口，源码/环境见 [baseline.md](baseline.md)。代理输入通过公开 Computer Use API；两类直接 Run 由用户实际鼠标操作，代理事后采集。没有向运行中的模型注入 Python 值或用离屏控件替代 GUI。

## 已执行

| 测试 | 操作与观察 | 证据 |
| --- | --- | --- |
| 数字 Enter | Nbits从15000全选输入8000，未按Enter时EyeBits仍10160；按Enter后EyeBits=8000，并出现 `EyeBits has been held at Nbits` 提示；随后确认提示 | 20-before、21-after PNG/UIA |
| 数字 Tab失焦 | Nbits8000输入6000，输入期间EyeBits仍8000；Tab移到EyeBits后两者为6000 | 22-before、23-after PNG/UIA |
| RLM条件 | NRZ→PAM4，RLM 0.95从灰态启用；恢复NRZ后灰态 | 25 PNG/UIA、26 UIA |
| DFE Ideal条件 | Ideal=true时Bandwidth12.0灰态；Space切false后启用；恢复true后灰态 | 28 PNG/UIA、29 UIA |
| CTLE Enable条件 | Enable=false后Native/File入口灰态，fp5/bw12/boost1.7仍启用；随后恢复true | 30 PNG/UIA、31 UIA |
| CDR Type条件 | Bang-Bang→Mueller-Muller，Delta-t/Alpha/Nave/Tol/Sus五项灰态并保留值；随后恢复BB | 32 PNG/UIA、33 UIA |
| 表格 Enter | Rx FFE Pre-tap5 Value编辑0.02，按Enter关闭编辑器，显示+0.020 | 35-before、36-after PNG/UIA |
| 表格 Tab | Rx FFE Pre-tap4 Value编辑0.03，Tab关闭编辑器并移到下一行，显示+0.030 | 37-before、38-after PNG/UIA |
| 表格焦点转移 | Rx FFE Pre-tap2 Value编辑0.04；用公开set_value对CTLE fp设同值5.0，使焦点转到该数字框；表格编辑器关闭，显示+0.040 | 39-before、40-after PNG/UIA |
| GUI配置保存 | File→Save Config. As...，保存到evidence/table-submission.yaml；其中rx_taps第1/2/4 tuples值为.02/.03/.04，Nbits/EyeBits均6000 | table-submission.yaml、table-submission-check.json、43 UIA |
| 数字直接鼠标Run | 代理留Nbits=4000活动编辑器、EyeBits6000；用户鼠标Simulation→Run并报告EyeBits4000/仿真已结束；代理事后采集两数字4000，stderr证明引擎bits=4000，但calc_ber异常、GUI状态仍Running | 45-before、47-after PNG，48 UIA、numeric-mouse-run-failure.txt |
| 表格直接鼠标Run | 4000/3000下Rx FFE Pre-tap5活动编辑器输入.05，未按Enter/Tab；用户鼠标Run后代理采集编辑器关闭、+0.050；Console有两条完成记录、stderr无新增，事后GUI导出首tuple=.05 | 51-before、52-after、53-console PNG/UIA，table-mouse-run-stderr-check.json |
| 运行后另存 | File→Save Config. As...，用原生文件对话框Alt+N输入独立路径、Alt+S保存；核对4000/3000、rx_taps[0]值.05、decision_scaler=0.3019818488973055 | 54 UIA、55 PNG/UIA、table-mouse-run-post.yaml、table-mouse-run-post-check.json |
| Console编辑 | Info/Console末尾输入 `[BASELINE_EDIT_PROBE]` 可见；Ctrl+Z移除，UIA中确认探针不再存在 | 19 PNG/UIA、19-console-restored.uia.txt |

数字/表格测试只证实上述值在结束编辑后保留，且被GUI导出。UIA在表格编辑器仍打开时已报告格式化新值；**不能据此断言模型只在Enter/Tab/失焦时才更新，或编辑期间模型完全未变**。失焦测试为公开API转移焦点，不是鼠标点击Run测试。表格样本不代表Tx/Optimizer表的所有编辑器已验收。

## 工具限制与恢复

首轮 Windows Graphics Capture 报 `FrameArrived timed out: timed out waiting on channel`，恢复后又报窗口捕获超时；按文档停止反复重试，改用 screenshot skill 捕获真实窗口。首轮 `sky.click` 报 `coordinate input geometry is unavailable`。

首轮用户物理Esc停止时立即停止。用户明确说“请继续呢，还没完成”后恢复本轮，重新获取实时窗口和索引。新一轮一次截图恢复仍报 `FrameArrived timed out: timed out waiting on channel`；在Nbits活动编辑框输入4000后，对实时索引160的Simulation菜单发起一次鼠标click恢复，仍报 `coordinate input geometry is unavailable`，未触发Run，未用快捷键冒充。精确错误见 [mouse-recovery-error.txt](evidence/mouse-recovery-error.txt)。

表格后态采集后，原生另存前再次收到物理Esc停止通知并停止。用户明确授权“继续收尾并推进 #2”后恢复实时窗口，仅完成配置另存和文档提交，没有追加仿真。#2 仍由 PM 复核基线后派发。

另有一次 `user input was detected in this window; call get_window_state before continuing`，已重新观察后继续。原生保存对话框的UIA索引设置两次报缓存不可用，改用对话框的Alt+N文件名快捷键和Alt+S保存成功。这些工具错误不作为应用行为结论。

## 数字鼠标测试与后续独立表格现场

数字鼠标测试前的真实状态见 [45-mouse-run-before.png](screenshots/45-mouse-run-before.png) 和 [46-mouse-run-blocked.uia.txt](evidence/46-mouse-run-blocked.uia.txt)：

- Config. 页 Nbits活动编辑框文本 **4000**，EyeBits仍 **6000**；未按Enter/Tab、未成功点开Simulation。
- NRZ、seed1、Rn0.01、Pn0.01，CTLE启用、Bang-Bang、Ideal=true；Use AGC=true。
- Rx FFE测试值 .02/.03/.04已保存；其它可见输入保留。当前图/状态栏仍属于此前结果，不与新草稿自动绑定。
- 状态栏为 `Configuration saved.`；保存文件是6000/6000时的配置，不能把该字符串理解为4000已保存或已运行。

### A. 数字框直接鼠标 Run（提交已验证，运行失败）

用户在上述现场用鼠标Simulation→Run，明确回复“已完成：EyeBits 为 4000，仿真已结束”。来源是**用户实际鼠标操作，代理事后采集**，不是自动鼠标接口成功。

代理重新读取并截图，Nbits/EyeBits均4000，但状态栏仍 `Running DFE/CDR...`。stderr包含Thread-1、Thread-2的 `ValueError: calc_ber()`，`len(bits_ref)=3994`、`len(bits_tst)=4000`、`bit_dly=6`、`len(bits)=4000`。因此输入采用证据成立，运行终态记录为异常失败、GUI状态陈旧；不采纳“已结束”为成功证明，也不声称只有一次Run。完整失败日志独立复制保留。

输入身份见numeric-mouse-run-identity.json：先前GUI导出table-submission.yaml，加随后观测到的nbits=4000/eye_bits=4000变化。原GUI没有run ID/不可变快照，第二次运行的AGC输入没有独立冻结；没有伪造一个“原始4000/4000导出”。

### B. 活动表格直接鼠标 Run（提交已验证，普通运行正常返回）

1. 为第二个独立样本，先将EyeBits提交为3000，Nbits保持4000；不修改或覆盖4000/4000失败样本、不改算法。Equalization / Rx FFE的Pre-tap5从0.02输入为 **0.05**，保持编辑器打开，未按Enter/Tab。现场见 [51-table-mouse-run-before.png](screenshots/51-table-mouse-run-before.png)，配置准备见49 UIA。
2. 用户明确回复“已点击 Run，表格显示 +0.050”。代理事后读取 [52](screenshots/52-user-table-run-after.png)，活动编辑器已关闭、表格值为 +0.050，状态为 Ready；再读取 [53 Console](screenshots/53-user-table-run-console.png)。完成日志为 `2026-10-23 16:01:27.975318+00:00` 与 `16:01:50.456489+00:00` 两条，不能声称仅一次运行。
3. [stderr 比对](evidence/table-mouse-run-stderr-check.json) 确认相对失败日志没有新增字节。结合Console完成记录和实际后态，可记录此普通运行交互样本正常返回，不能单靠Ready或无新增stderr下结论。
4. 通过原生菜单另存 [table-mouse-run-post.yaml](evidence/table-mouse-run-post.yaml)，[检查记录](evidence/table-mouse-run-post-check.json) 确认nbits=4000、eye_bits=3000、首个rx_taps tuple值0.05。状态栏 `Configuration saved.` 见 [55](screenshots/55-post-config-saved.png)。这是运行后的完整GUI配置导出，不是每次Run开始前的冻结快照；其中decision_scaler=0.3019818488973055不得倒推为两次运行的原始输入。

完整观察身份见 [table-mouse-run-identity.json](evidence/table-mouse-run-identity.json)。原GUI未提供run ID，无法逐次冻结AGC输入；也未独立提取每次运行的原始数组。该证据完成了此表格样本的提交行为记录，不替代Web数值验收。A的失败与B的正常返回分别保留；其他表类型不能自动视作通过。A身份文件中 `independent_next_sample.run_not_yet_observed` 保留准备当时的事实，B的后续结果以本节和独立身份文件为准。
