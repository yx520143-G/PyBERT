# #5 PM 终审返修与追加证据

前次固定交付 `246ce486388ac717409aa27adddfa533b21bb7a5` 的 fresh 终审发现两项 P2 和责任票号 P3。当前产品为 `bdcaf50110755e00c9a3064d02081301c4feeb8c`（主体修复 `e75b13d`，存储状态补充 `bdcaf50`），同 draft PR #17；旧证据、原失败和费用均保留。

reset 前由app捕获可见draft、retained/recovery/migration/存储状态，并同步请求workbench捕获base/captured/patches、runtime、资源绑定、source record、replay guard、恢复标志与归一化状态；undo一次恢复该聚合快照。Load完整配置会失效旧undo。非法JSON/原生配置快照不能被undo时的持久化覆盖。没有新增物理公式或引擎路径。

archive发布前验证既有raw2/3/4共同身份、必需结构，以及raw4已有的输入/资源身份和扩展容器。只验存在性/类型/摘要长度与hex格式，不重算input/resource hash、不补默认身份、不引入泛化schema框架。原字段和source manifest仍逐字节保留。Viterbi/FEC责任票修为#9，AMI为#10。

| 验证 | 证据/结果 |
| --- | --- |
| 无引擎JS回归 | [reset-final](evidence/pm-fixes-v6/reset-final.log)：真实旧NRZ manifest驱动shipped app/workbench handlers，完整native/visible快照、未知retained原值/阻断、坏draft/native原bytes/状态三组通过；无observer/main/COM |
| API最低身份 | [v6 JUnit](evidence/pm-fixes-v6.xml)：39项中38通过，run_id拒绝行为正确但字段名诊断断言失败；只修诊断文本后 [定向v7](evidence/pm-fixes-v7-runid.xml) 1通过、38 deselected。新增19种自洽缺失/错类型、三schema正向；原17项回归保持覆盖。**不是声称同一次固定HEAD运行39全绿** |
| 真实旧版本往返 | [114225](evidence/saved-roundtrip-20261024-114225/report.json)：五组2053数组、原manifest/NPZ/全部plot payload/子记录exact，raw2/3/4均在新校验器下通过，源原件未变，0main/COM |
| Chrome原输入guard | [v7完整结果](evidence/pm-fixes-v6/ui/pm-fixes-v7.log)：打开真实NRZ archive→恢复输入并绑A→全部默认→undo，完整config/runtime/bindings/source/guard与可见draft exact；同名不同bytes B实际POST Run返回422且未产生新run任务 |
| Chrome坏metadata原子性 | 自洽缺失/整数input_hash的文件实际打开被拒绝；草稿、选择、参考逐项不变，预置两条真实旧成功原件仍在；截图pm-v7-02 |
| Chrome迁移/存储状态 | 未知retained `{gain:123}` reset后清阻断、undo恢复原值与阻断和native快照；坏JSON reset→undo恢复原bytes/阻断/“仅当前页面保留”；截图pm-v7-03/04 |
| 最终适用性/费用 | [report](evidence/pm-fixes-v6/report.json) 12 checks通过；相对首轮closeout仅archive.py/app.js/workbench.js产品内容变化。新saved-only报告的全部Python源hash与当前相同；旧数值worker/producer未变，不新增主仿真以补文档 |
| 双轴复核 | [review追加](review.md)：原四项P2保留；本轮两P2、票号P3和补充存储提示P3已闭环，当前0未关闭 |

Chrome使用真实桌面1280×720，专用服务把所有非normalize worker硬拒绝；预置两条原成功记录是从保留原件复制后的只读回放，不能算本轮新成功。正式回归服务新建15个task全部normalize且已退出；初始服务的defaults observer另见 [initial-service](evidence/pm-fixes-v6/initial-service.json)。**本轮0 main/0 COM，累计仍3 main（2成功+1取消）/0 COM，另原CTLE preflight失败**。原PAM4 errors20、#4默认COM BLOCKED_BUDGET/NOT_EXECUTED、#16及后续专项边界不变。

首个Chrome v6脚本在初始化写回前比较了存储旧`blocking:false`与当前分类`true`，误报未知字段丢失；原脚本/失败日志保留。v7等待初始化完成并按当前迁移分类比较原值及阻断，全段完成。截图01/03/04的当前task栏含轮询瞬态，最终所有新task均已退出；不把截图中短暂状态当新仿真结果。

Ruff E4/E7/E9/F、app/workbench/reset JS syntax、既有draft/storage回归通过。fixture-report记录坏archive只改metadata并同步外层完整性，数组原字节未变；资源B仅为本机验证fixture，原A未改，未执行B仿真。

8772服务和本轮Chrome会话已停止，无活动worker；[本轮handoff](evidence/pm-fixes-v6/handoff.json)。主checkout仍`b9c56fe76bafb901d58dd53cda54e2ad5093fe6c`及原未跟踪docs/research、source；#2/#3/#4/#13 raw和本轮local fixture全部保留，无cleanup/archive。推送固定新HEAD后返还PM终审，PR保持draft，不合并/关票/派下一票。
