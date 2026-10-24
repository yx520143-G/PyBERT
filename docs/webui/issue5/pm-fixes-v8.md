# #5 忙碌中间态撤销与 legacy 保存能力修复

前轮固定 `9484efac38ba3d34197a0f0998127328d10acac8` 的PM增量终审认可身份校验和常规reset/undo，但确认忙碌、未归一化中间态的资源引用仍会丢绑定；另有legacy保存能力P3。当前产品固定 `fb97265b6bb3f13a0bea49980f8da0f506c43168`，只修这两项。

undo中的资源恢复只改一行：按app已恢复的当前draft重建resource refs，而非按仍为A的原生base。base、captured、pending patches、runtime和replay guard不替换；原生observer仍在槽位空闲后依序应用patches。

legacy缺完整原输入/物理轴，不能生成完整Web archive。所选legacy的full archive按钮禁用并显示原因，报告新增明确能力/原因，推荐文案、原生缺项错误、dialog和直接API拒绝均一致。原生23项subset齐全时仍能导出，独立sidecar始终保留；实际native-cli缺tx_out时仅native导出禁用，不补零、不编造身份、不新增legacy archive格式。

| 验证 | 结果 |
| --- | --- |
| 真实resources.js事件顺序 | [red](evidence/pm-fixes-v8/busy-reset-red.log) 稳定复现原代码undo后 `resource_bindings:{}`；[green](evidence/pm-fixes-v8/busy-reset-green.log) 修后完整pending状态exact，原retained/recovery/storage路径保持通过。测试加载shipped app/workbench/**resources.js**，无observer/main/COM |
| 定向legacy API/导出 | [JUnit](evidence/pm-fixes-v8/legacy-contracts.xml)：**6 passed / 35 deselected**。含实际缺项与无二次dB、23项齐全正向native构造、full archive拒绝/状态不变、full run推荐仍可用、坏容器和未知版本保留。未声称41项全套执行 |
| 真实桌面Chrome 1280×720 | [完整v8](evidence/pm-fixes-v8/ui/pm-fixes-v8.log)：用真实normalize worker gate稳定持槽；更换已上传、引用不同的B并编辑RxFFE Ntaps=9/Npre=2；base仍A，reset/undo后draft/B binding/所选记录exact；gate释放后实际normalize请求仍mode patch、config=A、原patch顺序，原生observer应用为B/9/2。随后Run实际422，原A replay guard仍生效 |
| legacy Chrome | 真实原native-cli文件导入后full archive按钮禁用、原因/stale/dialog/report一致；直接archive API 422明确缺物理轴；实际缺tx_out的原生导出禁用，sidecar真实下载且内容等于报告 |
| 最终审计 | [report](evidence/pm-fixes-v8/report.json) **14 checks通过**：两条原成功manifest/NPZ副本逐字节相同；本轮5个新增task全为normalize且退出，含真实gate任务；无新run/COM任务；相对前轮产品仅archive.py、legacy_results.py、workbench.js、results.js、index.html这五个存储/UI边界变化 |
| 双轴/静态 | [review追加](review.md)：Standards/Spec均0未关闭；Ruff E4/E7/E9/F、相关JS syntax、既有draft/storage回归通过 |

本轮 **0 main/0 COM**，未重跑既有2053数组/879新run数值仿真。原往返与数值事实继续使用其当时执行源码/原件边界；本轮archive.py新增legacy拒绝分支、legacy_report能力和UI由上述定向证据验证，不把旧报告的源码hash冒充当前全部源码。数值worker/producer和物理输入未修改。

前轮39项的38通过/1诊断文本失败及单项修正复验、所有历史失败/原raw继续保留。累计仍 **3 main（2成功+1取消）/0 COM**，另原CTLE preflight失败；PAM4 errors20、#4默认COM `BLOCKED_BUDGET / NOT_EXECUTED`、#16和后续专项边界不变。

服务8772及Chrome `pybert-issue5-pm-v8` 已停，[handoff](evidence/pm-fixes-v8/handoff.json)；主checkout仍b9c56fe及原untracked docs/research、source，原#2/#3/#4/#13、各轮local工件均未清理。PR #17保持draft，推送固定新HEAD后停止写入并返还PM终审；master、#5状态和#8派发不动。
