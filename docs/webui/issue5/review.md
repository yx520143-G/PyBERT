# #5 首轮固定实现双轴复核及追加终审修复

固定产品 HEAD：`3ccb88f4e34db2a81a04a6b7a7f198f0c88e367d`；共同 base：`f1d0ea80f9db8ab31e25963496875a44fe4a19d9`。两个独立 review agents 只读检查，未运行主仿真/COM，未编辑文件。复核使用 #1/#5 已封存全文、合同 v1/v2/v3、仓库规范与 code-review skill 的 smell baseline。

## Standards

原 P2 已闭环；最后增量新增实质 finding **0**，硬规范违规 **0**，未解决阻断 **0**。保留字段的执行分类由已知字段和结构重新校验，重启选择状态修正范围集中，未发现无关改动或新增物理公式。

原问题是 Load Config 与恢复 archive 输入重复提交状态；已合并到 `applyLoadedInput`，定向检查通过。最后复核覆盖 `0bd84ba`、`8e3d9fc`、`3ccb88f`。

## Spec

固定 `3ccb88f4e34db2a81a04a6b7a7f198f0c88e367d` 增量复核：未发现新 Spec 问题。查询前仅显示待确认；查询后区分记录存在与缺失；有效记录按原 ID 恢复，空选择不会擦除旧存储 ID。

最终代码 Spec 轴：**0 项未关闭 finding**，此前报告的 4 项 P2 均已关闭：实际 PR7 存储键接入；删除参考后仍保留独立资源 replay guard；未知 legacy producer 版本不升级冒充；未知 retained 字段不能借持久化 `blocking:false` 绕过执行阻止。

Standards：0 项未关闭；Spec：0 项未关闭。此复核不代替 PM 固定交付终审，不授权 merge 或关闭上层事项。

## PM 对 246ce486 的 fresh 终审与返修

PM 终审新增 Spec **2 P2 + 1 P3**；Standards **0 硬违规 + 1 判断性 Data Clumps**。PR 保持 draft，PM 将唯一实施 ownership 交回。此记录追加，不覆盖原四项已闭环 P2。

| 本轮 finding | 修复/验证 | 结论 |
| --- | --- | --- |
| P2：reset/undo只恢复字段，丢 replay guard/原输入扩展/资源绑定和迁移阻断 | `e75b13d` 同步捕获app/native同一份reset历史，undo恢复完整快照；原坏draft/native storage也按原bytes恢复。真实archive/未知retained两条回归与Chrome路径通过 | 已闭环 |
| P2：自洽archive缺input_hash等仍先发布，选中后渲染失败 | 发布前按raw2/3/4最低必需身份/结构校验，不重算/补造hash；19类自洽坏metadata原子拒绝，三schema正向和五组真实2053数组往返通过 | 已闭环 |
| P3：function-matrix责任票反置 | Viterbi/FEC更正为#9，AMI为#10 | 已闭环 |
| 返修复核补充P3：坏JSON reset→undo未恢复storageAvailable，提示可误称已保存 | `bdcaf50`将该flag纳入app快照，真实状态渲染/Chrome断言恢复“仅当前页面保留” | 已闭环 |

Standards 独立 agent 对 `e75b13d` 静态读取：新增硬违规0、新增实质判断性finding0；Data Clumps在聚合快照结构上收敛。对 `bdcaf50` 两行storage flag增量依据变更描述确认设计一致，未重新读取或运行工具。Spec独立agent对 `e75b13d` 两P2/票号P3闭环，指出上述补充P3；随后固定 `bdcaf50110755e00c9a3064d02081301c4feeb8c` 确认该P3关闭，当前范围0未关闭。两轴未运行主仿真/COM或编辑文件。

本轮当前轴结论：Standards **0 未关闭硬违规/实质finding**；Spec **0 未关闭 finding**。最终仍由PM对新固定交付终审。

## PM 对 9484efac 的增量终审与 v8 修复

PM确认前轮身份校验P2、票号P3及常规reset/undo修复有效；另确认忙碌且未归一化的中间态仍有P2，并指出legacy保存能力P3。以下追加，不覆盖前轮记录或费用。

| finding | 修复/证据 | 结论 |
| --- | --- | --- |
| P2：base=A、draft/captured/patches/binding=B时，undo按base恢复resource refs，随后同一事件的真实resources监听器删B绑定 | undo仅按已恢复的 `ui.getDraft()` 重建资源引用；base不替换，captured/patches/guard照原快照保留。真实resources.js回归稳定red→green；Chrome真实normalize gate持槽期间编辑B/FFE→reset/undo→释放，实际请求仍以A为base、按原顺序应用patches，B绑定和guard保留 | 已闭环 |
| P3：legacy无完整身份却启用full archive，并在推荐/缺项错误/dialog宣称可用 | UI禁用并说明缺完整原输入/物理轴；report能力/推荐、native缺项错误、dialog与full archive API拒绝一致；不造身份，不新增格式；有效native subset/sidecar保留 | 已闭环 |

固定产品 `fb97265b6bb3f13a0bea49980f8da0f506c43168` 的两独立agent复核：Standards新增硬违规0、实质判断性finding0、阻断0；Spec两项闭环、无新增finding。均只读，无编辑/主仿真/COM。证据见 [v8](pm-fixes-v8.md)。当前两轴0未关闭，仍等待PM对新固定交付终审。
