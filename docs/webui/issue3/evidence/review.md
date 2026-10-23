# #3 fresh 只读 review 修复记录

reviewer：当前任务的 `analysis_review` 子 agent；owner 为唯一 writer。reviewer 未修改文件、切分支、运行仿真或向其他 chat 发送消息。

| finding | 修复与验证 |
| --- | --- |
| P2：失败 DD tail fit 的 rjDD/mu_pos/mu_neg 仍作普通有效值展示 | `analysis.py` 保存 raw 并单列 fit availability/reason；`workbench.js` 显示 unavailable/unknown raw reference。pjDD 与 bounded dj_pos/dj_neg 不受连带影响。PAM4 保存 raw 与最终 Chrome Jitter Info 可核对。 |
| P2：原 GUI 反查没有接入新图 | `gui-map.js` 有界 analysis routes；`app.js` 关闭索引、切目标节点、派发分析导航；viewer 复用原选择逻辑。随后发现 route 会继续执行旧 guiEntry 并覆盖目标，已在分支末尾立即 return。真实 Chrome Frequency responses → Channel 三频响通过。 |
| P2：CDR finite/非零分母仍可能在除法后溢出 | `clock_display` 对 ratio 与最终 display 再查 finite，抛出 ValueError 进入 unavailable，raw FFT 保留。`[0,1e-320,1]` 函数测试通过。 |

reviewer 最终回复确认上述三项和 route fall-through 均闭环，未发现其他已确认的具体错误。此 review 不是独立物理模型验证；数值、UI 与源码适用表分别提供证据。

最终兼容性自查发现旧 schema2 的 DFE Info 与 Channel H 应继续保留，owner 在 `b2bdb229` 补回保存数据的展示。reviewer 确认读取路径无重算/旧 run 修改，同时指出 compare-runs 通用标题会遮掉旧 Channel 的限制说明。`e9c73c5` 将说明同时写入 trace 图例与 metadata；Chrome 25/26/27 分别验证旧 Info、旧单频响、旧新比较图。reviewer 对最后两次提交只读复核，确认该 finding 关闭，无新增 finding，未改文件。

PM Spec 复核追加两个 P2：显示 dataset 缺 observation ID/source 关系；完整 CDR 数据错误继承 eye/jitter 末段窗口。owner 的两个确定性回归先失败（point=None、window 缺 full-record scope），修复后原11项＋新增2项全部通过。修复包括 API 对每个 plot 返回其 dataset metadata，viewer 使用 plot 的真实窗口。审查还补充旧 DFE 三个 spectrum Y 的 UI 依赖，以及 clock_times 必须用自身事件轴而非逐样本 t 范围。

原 reviewer 对固定 HEAD `83b75154a52a11a06506a4416503326c95ae02d8` 只读收口：上述两 P2 与追加两细节均闭环；核对065914三个fixture及431/432/431数组与061108完全相等，无新增 finding。reviewer 未写文件、运行仿真或执行 Chrome；28/29 与来源 DOM 记录由 owner 另做。Standards 的 P3 重复 calc_eye 无计时证据，属非阻断意见，本轮没有顺带重构。
