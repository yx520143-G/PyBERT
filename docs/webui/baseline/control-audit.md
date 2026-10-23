# 控件、菜单和图位逐项审计

范围依据为 [保存的 Issue #1 快照](evidence/issue-1-snapshot.json)。`V` 表示真实截图/可访问树观察；`I` 表示执行过所述交互；`S` 表示固定 SHA 源码定义，未冒充实测。每行均登记状态，**V 不等于全部编辑/加载/运行行为已验收**。本期/延期是 Web 计划状态，并非已实现状态。

基准图缩写：C=[01 Config](screenshots/01-config-default.png)，E=[02 Equalization](screenshots/02-equalization-default.png)，O=[03 Optimizer](screenshots/03-optimizer-default.png)。对应 `.uia.txt` 保留在 `evidence/`。隐藏项只确认当前 native 状态未展示；没有加载外部 IBIS/AMI/通道文件，也没有执行自动优化。

## Config.：C01–C27

| ID | 真实观察/默认可见值 | 状态、启用/只读核对与 Web 处理 | 证据 |
| --- | --- | --- | --- |
| C01 | Bit Rate 10.0 Gbps | V：数字可编辑；本期 | C |
| C02 | Samps. per UI 32 | V：数字可编辑；本期；未穷举整数范围 | C |
| C03 | NRZ；真实切到 PAM-4，恢复 NRZ | V/I：两种状态；S：枚举另含 Duo-binary，未留展开选项证据；Web 仅 NRZ/PAM4，Duo-binary 延期禁用 | C、25、26 UIA；pybert.py 枚举定义 |
| C04 | RLM 0.95 | V/I：NRZ 禁用，PAM4 启用；Web 始终禁用、不保存、不设置 | [25](screenshots/25-pam4-rlm.png)、26 UIA |
| C05 | Pattern PRBS-7 | V：枚举入口可用；完整选项/算法本次未遍历 | C |
| C06 | Seed 1 | V：可编辑；Web 保留 0=random、非零复现语义 | C |
| C07 | Nbits 15000、EyeBits 10160 | V/I：Nbits输入8000后Enter使EyeBits=8000；6000后Tab使EyeBits=6000；用户鼠标Run后4000进入引擎并失败，输入提交和运行成功分开记录 | [20](screenshots/20-nbits-enter-before.png)–[23](screenshots/23-nbits-tab-after.png)、[47](screenshots/47-user-numeric-run-after.png)、numeric-mouse-run-failure.txt |
| C08 | Vod 1.0 V | V：可编辑；本期 | C |
| C09 | Rn 0.01 V、Pn 0.01 V、f(Pn) 11 MHz | V：三个数字可编辑；帮助/数值含义按 #1；本次未逐项改值 | C |
| C10 | Debug 未勾选 | V：可用；与 View 的共用字段绑定据 S，未切换双向同步 | C、menu-view |
| C11 | Compute COM、Include FEXT 均灰态未勾选 | V：桌面初态禁用；Web 明确延期，运行要求 false | C |
| C12 | Impulse Response Length 0.0 ns | V：可编辑；0 的自动语义据 S/#1 | C |
| C13 | Pj Threshold 3.0 sigma | V：可编辑；后端分析继续执行的范围按 #1 | C |
| C14 | fMax 40 GHz、fStep 10 MHz | V：两个数字可编辑；未试非法关系 | C |
| C15 | Tx/Rx sel 均 Native；Ibis 单选入口可见 | V：native 组可见；Web Ibis 入口延期禁用；未进入 Ibis | C |
| C16 | Tx_Rs 100 Ohms、Tx_Cout 0.5 pF | V：pkg_enable=false 时可编辑；S：not pkg_enable 联动，未实际开启封装 | C |
| C17 | Model Native，Single/Multiple 入口可见 | V：native 参数组展示；Web 仅 native，其余禁用 | C |
| C18 | Fix port numbering、Apply window 均灰态未勾选 | V：native 初态禁用；Web 延期且要求 false | C |
| C19 | Length 0.5 m、Loss Tan. 0.02 | V：可编辑 | C |
| C20 | Z0 100 Ohms、v_rel 0.67 c | V：可编辑 | C |
| C21 | Rdc 0.1876 Ohms、w0 10000000.0 rads./s、R0 1.452 Ohms | V：可编辑；Ohms 是桌面原标签，Web Ω/m 差异已登记 | C |
| C22 | Single File / Victim Lane / Multiple Files / COM Config 未展示 | V：native 下隐藏；S：按 inter_sel/enable_com/扩展名条件显示；未展开内部控件；延期 | C；view.py:315–380 |
| C23 | Enable=false；Group KR、Tx/Rx case A1、Partial host=true 均灰态 | V：常驻组位置及初态；未切 Enable=true；Web 整组延期 | C |
| C24 | Rx_Rin 100 Ohms、Rx_Cin 0.5 pF | V：pkg_enable=false 时可编辑；S：not pkg_enable 联动，未实际开启封装 | C |
| C25 | Rx_Cac 1.0 uF | V：原位置可编辑；Web 保留兼容并说明 native 不使用；未补算法 | C |
| C26 | Use Viterbi=false、Trellis Depth=4 灰态 | V：初态；S：深度按开关联动，未切换；Web 延期 | C |
| C27 | Tx/Rx IBIS 分组未展示 | V：Native 下隐藏；S：文件、valid、ts4、选择/查看按钮定义；未进入或调用模型；延期 | C；view.py:248–272、453–477 |

## Equalization：E01–E14

| ID | 真实观察/默认可见值 | 状态、启用/只读核对与 Web 处理 | 证据 |
| --- | --- | --- | --- |
| E01 | Tx/Rx eq sel 均 Native；Ibis-ami 入口可见 | V：native 组展示；Web AMI 选项延期禁用 | E |
| E02 | Tx 表6行：Pre-tap3/2/1、Post-tap1/2/3；仅Pre-tap2/1 enabled；Value全0 | V：Name/Enabled/Value 列与原顺序；S：Name只读、其余可编辑，禁止排序/重排；本表未做提交交互 | E；view.py:525–545 |
| E03 | CTLE Enable=true、Native 选中 | V/I：关闭 Enable 后 Native/File 模式灰态；Web Native 本期、File 延期 | [30](screenshots/30-ctle-disabled.png)、31 UIA |
| E04 | CTLE fp 5.0 GHz、Bandwidth 12.0 GHz、boost 1.7 dB | V/I：Enable=false 时三个数字仍可编辑；恢复后值保留 | E、30、31 UIA |
| E05 | CTLE File 输入未展示 | V：Native 下隐藏；S：ctle_sel=File时显示；Web File延期，不新增开关 | E；view.py:594–613 |
| E06 | CDR Type Bang-Bang | V/I：实际切 Mueller-Muller 后恢复；Web 两种模式本期 | [32](screenshots/32-cdr-mm.png)、33 UIA |
| E07 | Delta-t 0.001 UI、Alpha 0.01 | V/I：MM下两项灰态，值保留，恢复BB启用 | E、32、33 UIA |
| E08 | Lock Nave. 500、Tol. 0.1、Sus. 500 | V/I：MM下三项灰态，值保留，恢复BB启用 | E、32、33 UIA |
| E09 | Ntaps 15、Npre 5 | V：实际构造/启动实例值；后续同值聚焦不改变值；未测试修改数量的联动边界 | E、table-submission.yaml |
| E10 | FFE 表 Name/Enabled/Value；Pre-tap3=+1.000、Cursor=0；前15启用，其后禁用 | V/I：Pre-tap5/4/2分别改 .02/.03/.04，用Enter/Tab/失焦结束并保存；后续 Pre-tap5=.05 活动编辑器经用户鼠标Run后关闭并另存。S：Name只读。02 PNG可见20行至Post-tap14，UIA枚举21行至Post-tap15；均不等于GUI YAML保存的100 tuples | [35](screenshots/35-table-enter-before.png)–[40](screenshots/40-table-blur-after.png)、[51](screenshots/51-table-mouse-run-before.png)、[52](screenshots/52-user-table-run-after.png)、table-submission-check.json、table-mouse-run-post-check.json |
| E11 | DFE Gain 0.1、Nave. 100 | V：可编辑；单位/类型按原模型；未逐项修改 | E |
| E12 | Level 0.300 V、Use AGC=true | V：可编辑输入；先前GUI导出0.30014859348604045，表格样本运行后导出0.3019818488973055；未独立冻结每次AGC输入，不能把事后导出冒充输入快照；Web草稿与AGC结果分离 | E、table-submission.yaml、table-mouse-run-post.yaml |
| E13 | Ideal=true、Bandwidth 12.0 GHz灰态 | V/I：Ideal=false启用Bandwidth，恢复true禁用且保留12.0 | [28](screenshots/28-dfe-nonideal.png)、29 UIA |
| E14 | Tx/Rx AMI 内部组未展示 | V：Native下隐藏；S：路径/valid只读、GetWave/clocks/配置按钮定义；未实例化AMI；延期 | E；view.py:490–589 |

## Optimizer 与 Info：O01–O07、I01–I02

| ID | 真实观察/默认可见值 | 状态、启用/只读核对与 Web 处理 | 证据 |
| --- | --- | --- | --- |
| O01 | Rx DFE 表 Name/Enabled/Min val/Max val/Value；Tap1–5 enabled；Tap1[-.2,.4]、Tap2[-.15,.15]、后续[-.05,.1] | V：表格/列/顺序；S：enabled/min/max可编辑、连续tap语义；本表未交互改界限；GUI YAML20 tuples。Web基本配置本期 | O、table-submission.yaml；view.py:830–859 |
| O02 | Disable all 在左、Enable all 在右，均可见可用 | V：动作位置/初态；未实际触发；Web两动作本期 | O |
| O03 | Rx DFE Value 可见行全 +0.000 | V：可见零值；S：style=readonly；未试写。与非零Results适应曲线不同绑定；Web保留列、标未提供调优结果 | O、08；view.py:844 |
| O04 | Tx FFE 名称/Enabled/Min/Max/Step/Value六列、六行 | V：原表格位置；S：name只读，调优字段绑定；Web整组延期 | O |
| O05 | CTLE Configuration Enable=true；fp5、bw12、Min2/Max12/Step1；Result CTLE boost1.7 | V：Configuration/Result分组及数值；S：Result只读；Web整组延期 | O |
| O06 | Rx FFE Use MMSE=true；Name/Enabled/Min/Max/Step/Value表格 | V：位置/初态；S：name/enabled/value只读；GUI YAML100 tuner tuples；Web整组延期 | O；view.py:799–829 |
| O07 | 下方优化结果图可见；AMI trial budget/AMI Params 未展示 | V：原结果图与当前隐藏状态；S：AMI条件可见定义；未优化或实例化AMI；全部延期 | O；view.py:724–734、861–913 |
| I01 | Performance by Component；列 Component / Performance (Msmpls./min.)；行 Channel、Tx Preemphasis、CTLE、FFE、DFE、Viterbi、Jitter Analysis、TOTAL、Plotting | V：实际HTML内容；S：只读展示；未单独测试该页运行后刷新。Web无值须unavailable，不伪造绘图性能一致 | [16](screenshots/16-info-performance.png)；view.py:1007 |
| I02 | User's Guide与Console文本页均可见 | V/I：Console插入探针成功后撤销；桌面Console可编辑，Web只读是已批准差异；Guide只读定义据S，未试写 | [17](screenshots/17-info-guide.png)、[18](screenshots/18-info-console.png)、[19](screenshots/19-console-edit-probe.png)、19-restored UIA |

## 菜单与状态栏

下表按**实际显示顺序**记录。显示可用仅代表当时菜单未灰态，不表示执行了所有动作。代理经 Save Config As 保存证据文件；两类 Run 样本由用户实际鼠标操作，代理采集后态。

| 菜单 | 真实顺序/快捷键/初态 | Web 约定 | 图 |
| --- | --- | --- | --- |
| File | Load Results；Save Results；分隔；Load Config. Ctrl+O；Save Config. Ctrl+S；Save Config. As... Ctrl+Shift+S；分隔；Quit Ctrl+Q；均可见可用 | Results与Quit延期；配置本期文件选择/下载，不声称覆盖原路径；不劫持浏览器键 | [File](screenshots/menu-file.png) |
| View | Debug Mode Ctrl+`（未选）；Clear Loaded Waveforms；均可用 | Debug本期；Clear Loaded Waveforms延期，不替代清空Run | [View](screenshots/menu-view.png) |
| Simulation | Run Ctrl+R；Abort；Ready时两项仍可用 | Run/Abort本期，按运行状态管理；数字框、活动表格的用户鼠标提交均已观测；两样本终态分别记录 | [Simulation](screenshots/menu-simulation.png)、47、52、53 |
| Optimization | Tune EQ Ctrl+T；Abort Ctrl+Esc；分隔；Use EQ Ctrl+U；Reset EQ；Ready时仍可用 | 全部延期禁用；不连带禁用Rx DFE基本配置 | [Optimization](screenshots/menu-optimization.png) |
| Help | Getting Started；About；均可用 | 本期本地Web说明/原帮助链接及实际版本署名；本次未执行帮助外链 | [Help](screenshots/menu-help.png) |
| 状态栏 | 初始Ready.、Perf.(Msmpls./min.)、ChnlDly(ns)、BitErrs、TxPwr(mW)、Jitter(ps)、COM；保存后Configuration saved. | Web绑定run ID、结果所属配置和明确终态；不能仅靠Ready判成功 | C、[45](screenshots/45-mouse-run-before.png) |

## 本期18个图位

下表的“字段”来自固定源码/#1契约（S）；本次真实截图（V）核对图位、标题和轴，**未据图像证明原始数组/窗口/数值一致**。UL=左上，UR=右上，LL=左下，LR=右下。

| ID | 真实页/位置 | 观察到的轴/标题要点 | 字段绑定（S） | 证据 |
| --- | --- | --- | --- | --- |
| P-CH | Pulses UL Channel | Time(ns)/Pulse Response(V) | chnl_p、t_ns_chnl | [06](screenshots/06-responses-pulses.png) |
| P-TX | Pulses UR +Tx De-emphasis & Noise | ns/V；标题不改变无噪声pulse语义 | tx_out_p | 06 |
| P-CTLE | Pulses LL +CTLE | ns/V；含IBIS-AMI附注 | ctle_out_p | 06 |
| P-DFE | Pulses LR +DFE | ns/V；Native DFE附注 | dfe_out_p | 06 |
| F-CH | Frequency UL Channel | Frequency(GHz)对数x；Frequency Response(dB)；Actual Term.蓝、Perfect Term.黑、Trimmed Impulse红 | chnl_H、chnl_H_raw、chnl_trimmed_H | [07](screenshots/07-responses-frequency.png) |
| F-TX | Frequency UR +Tx | GHz/dB；Incremental/Cumulative | tx_H、tx_out_H | 07 |
| F-CTLE | Frequency LL +CTLE | GHz/dB；Incremental/Cumulative | ctle_H、ctle_out_H | 07 |
| F-DFE | Frequency LR +DFE | GHz/dB；Incremental/Cumulative | dfe_H、dfe_out_H | 07 |
| O-CH | Outputs UL Channel | Time(ns)/Output(V)，双曲线 | ideal_signal、chnl_out、t | [09](screenshots/09-results-outputs.png) |
| O-TX | Outputs UR +Tx | ns/V | rx_in、t | 09 |
| O-CTLE | Outputs LL +CTLE | ns/V | ctle_out、t | 09 |
| O-DFE | Outputs LR +DFE | ns/V | dfe_out、t | 09 |
| E-CH | Eyes UL Channel | Time(ps)/Signal Level(V)，色图；计数含义据S | chnl_out→calc_eye | [10](screenshots/10-results-eyes.png) |
| E-TX | Eyes UR +Tx | ps/V，计数色图；含义据S | rx_in→calc_eye | 10 |
| E-CTLE | Eyes LL +CTLE | ps/V，计数色图；含义据S | ctle_out→calc_eye | 10 |
| E-DFE | Eyes LR +DFE | ps/V，计数色图；含义据S | dfe_out、clock_times→calc_eye | 10 |
| D-CDR | DFE UL CDR Adaptation | Time(ns)/UI(ps) | ui_ests、t | [08](screenshots/08-results-dfe.png) |
| D-TAPS | DFE UR DFE Adaptation | Sample Number；y无轴标题，多tap曲线；无量纲权重含义据S | adaptation，x为权重记录序号 | 08 |

其余原图/页位也已截图：Impulses、Steps，DFE后两格时钟图，Bathtubs、Viterbi，Jitter三子页，Optimizer结果图。它们按 #1 延期；没有增加独立RxFFE第五格或COM页。独立RxFFE数值对照义务不因图延期取消。

## 未被本次实测覆盖的边界

- 每次鼠标Run的不可变输入身份与唯一run ID：原GUI未提供。表格后态、两条完成日志及事后导出不能替代Web的冻结输入/结果绑定验收。
- 封装开关对Tx/Rx数字灰态的切换、Viterbi深度联动、Debug双向同步、Enable/Disable all动作，以及各输入范围/非法值校验；本次仅记录可见初态与S条件。
- Tx taps、Optimizer DFE界限表的逐表提交/只读拒写测试；本次表格实际提交样本为Rx FFE，不能推广成所有编辑器都通过。
- 非native隐藏面板内部的运行、文件选择、模型有效性/只读行为；这些仍为延期边界，未通过静态声明冒充实测。
