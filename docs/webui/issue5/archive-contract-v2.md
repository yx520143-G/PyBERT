# #5 存档冻结 v2：独立子任务快照

追加 v1，不覆盖其原件。原 core manifest 的 execution_strategy 仅是子任务计划。外层 archive 的 subfunctions 保存捕获时间、关联 task ID、原 task 状态/日志/取消/退出信息，以及各自 com-input.json/com.json/terminal.json 的内容和 availability。尚未退出标 waiting_for_exit，未生成标 not_produced；不能借请求参数冒充实际来源。

打开后的外部参考仅使用 archive 已保存的子任务快照，不与当前 session 按同名 parent run 拼接。再保存参考保留原捕获时间/内容，不重跑 COM，不修改 parent。没有原运行创建时间的旧记录明确未知，保存时间不代替运行时间。

只读验收将使用 #4 的真实 core `c3cadfdc-13e8-4ed9-bee3-b3b11462cd96` 与 linked COM 原件；原 scalar −15.419984103278814 dB 仅作文件往返，不再次计算。#4默认139756144组合仍 BLOCKED_BUDGET/NOT_EXECUTED。
