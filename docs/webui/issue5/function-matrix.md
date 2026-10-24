# #1 功能矩阵在 #5 的落点

以 [#1 快照](fixtures/issue-1-snapshot.md) 为清单。下列“已接入”仅说明本票归档/视图复用的已采集数据；各 producer 的数值基线和局限沿用 #2/#3/#4。真实 Chrome 的 [phase7 全视图结果](evidence/chrome-v2/ui/phase7-analysis.log)、[raw audit](evidence/chrome-raw-audit-20261024-110155/report.json) 与 [README 验证表](README.md) 提供本票证据。

| #1 原功能 | #5 落点/验证 | 状态与边界 |
| --- | --- | --- |
| Data Rate/Modulation/PRBS/Seed/Nbits/Nspui | Source/Simulation；完整95字段冻结、两真实Run及PR7迁移 | 已接入；构造/采样语义沿用#2，seed1非零噪声原样 |
| EyeBits/Pj Threshold/fMax/fStep/Impulse length | Observe/Channel分析设置与原window | 已接入已有能力；手动impulse长度原生限制沿用#4 |
| Vod/Rn/Pn/f(Pn) | Source与Noise加法支路；frozen真实输入 | 已接入；电压噪声与时间jitter不混用 |
| Native Channel损耗、两端R/C、Single/Multiple/端口/顺序/FEXT、Package | Channel电气/资源；归档原ordered resource identity/hash与输入 | 沿用#4支持域；#5新Run仅SINGLE A，其他模式复用原数据/契约，不冒称本票新全矩阵 |
| Native Tx taps、CTLE、Rx FFE 100槽/observer | 各EQ节点与原完整配置 | 已接入；实际native分支/Tx GetWave等边界沿用#4；不在前端重算tap/响应 |
| DFE prefix/gain/Nave/level/AGC/summing、CDR锁定控件 | DFE/AGC/CDR控制支路；原运行summary/适应数组 | 已接入；原MM固定锁点语义，不宣传捕获动态 |
| Responses / Impulse、Step、Pulse、Freq. | 节点 Analysis/Responses，h/s/p/H × chnl/tx/ctle/ffe/dfe 共20项；归档所有 dataset/plot metadata | 已接入；single/cumulative、DFE equivalent/diagnostic 保留，不把等效响应当真实线性DFE |
| Results / Outputs | Waveform ×5观察点；真实 NRZ Rx FFE 输出截图06 | 已接入；raw 与1000点显示投影分开，取窗来自所选记录 |
| Results / DFE | DFE Adaptation、CDR Adaptation/Histogram/Spectrum；summary最终level/weights | 已接入；最终结果不覆盖requested输入，AGC原0.5与最终值独立 |
| Results / Eyes | Eye ×5观察点；当前NRZ/已保存PAM4独立两套网格截图12/18 | 已接入；各自clock/window/电压网格；不以颜色或插值证明相等 |
| Results / Bathtubs | Jitter Bathtub ×5观察点 | 已接入；crossing jitter诊断不等于电压margin/完整BER资格 |
| Jitter / Dist. | Jitter Dist. ×5；原PDF/bins/metadata归档 | 已接入；缺数据按producer availability/reason |
| Jitter / Spec. | Jitter Spec. ×5；各自频率轴/窗口 | 已接入；没有另造公式 |
| Jitter / Info | all-points表、原统计/拒斥比、单位和来源；截图09 | 已接入；保持CTLE→DFE统计含RxFFE的原语义 |
| 新Rx FFE jitter/bathtub | 上述ffe独立观察点 | 已接入；本票往返exact，producer基线与identity-FFE核对沿用#3 |
| Viterbi/FEC、error/bit/symbol窗口 | Viterbi/FEC节点与未计算状态 | **#10待专项验收**；本票只保留已产生记录，未计算不冒充DFE真实误码 |
| 状态栏 BitErrs/Jitter/ChnlDly/TxPwr | 所选run overview与日志/summary；两真实成功Run | 已接入；PAM4 DFE errors20保留，性能不作严格数值equal |
| 状态栏/工具 COM | 原任务独立ID、完整子快照与文件可用性；phase11c历史快照回放 | 有界旧真实XLS记录可归档；本票0 COM；#4默认COM gate仍BLOCKED_BUDGET/NOT_EXECUTED |
| File / Load Config | 工具栏Load Config；真实frozen NRZ/PAM4 YAML、失败/恢复输入统一状态提交 | 已接入；完整配置/资源身份沿用#4，失败保留原草稿 |
| File / Save Config / Save As | 当前草稿、原逻辑名；phase14实际下载NRZ.yaml；phase9 SaveAs Escape | 已接入；只交付下载，不承诺覆盖本地原路径 |
| File / Load Results | raw upload→完整校验→新增独立reference ID | 本票新增；坏/未知版本原子拒绝；可信legacy显式降级 |
| File / Save Results | 保存所选成功run，不保存当前草稿到旧数组 | 本票新增；PAM4编辑期间旧归档原字节exact |
| View / Clear Loaded Waveforms | 移除所选参考/清除加载参考 | 本票新增；保留2成功、草稿、原source与文件；第五参考超预算不淘汰 |
| Simulation / Run / Abort | 顶栏任务ID/阶段/取消request、observed、exited | 本票2成功+1取消真实Chrome；刷新不断任务；旧成功仍独立可选 |
| Optimization / Tune / Abort / Use / Reset EQ | Optimizer节点与既有输入表、未来computed metadata保留 | **#8未实现专项运行/候选应用验收**；保留字段不等于已运行；Reset EQ不冒充恢复全默认 |
| AMI模型加载/能力/优化 | Device models/IBIS-AMI节点 | **#9待专项验收**；本票不执行模型DLL或声称完整AMI支持 |
| View / Debug Mode、Info / Console | debug字段与当前task/所选run两份日志 | 已接入且归档保留；本票未要求可编辑控制台 |
| Info / Performance | run overview原summary | 已接入；费用created→finished另列，不拿开发wall-clock当物理结果 |
| Help / Getting Started / User's Guide / About | 现有Help/About与原帮助链接/版本/SHA/fork | 沿用已交付入口，#5更新存档操作提示；未重写原帮助内容 |
| File / Quit | Disconnect按钮 | 沿用Web断开语义；不隐式取消后端，交付时显式停服务 |
| 搜索/GUI反查/模式与129 Items | 信号链导航、搜索、GUI索引 | 沿用PR7/#2–4；不是仿真功能完成证明 |
| 恢复默认/撤销/刷新/localStorage | 草稿恢复与schema1→2；phase12b完整112字段/存储失败；phase13查询与重启 | 本票迁移/失败恢复已验证；raw不存localStorage；未知/非法输入阻止Run |

TIME/CTLE File/impulse_length/package+FEXT、legacy缺物理轴/tx_out、原eye显示噪声/clock fallback及短窗口限制继续保留。尚未完成的后续专项和默认COM gate不据本票打勾。
