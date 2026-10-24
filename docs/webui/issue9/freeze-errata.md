# 冻结材料文字勘误

`4a6ce7f` 的 v1 manifest 中 `config_scope` 写作“112 fields”。本批完整输入与继承的 #2 原输入实际均为 **95 个顶层 key**，集合完全相同；其内含完整 tap 表。95 是 `PyBertCfg` 经 `snapshot` 排除 `date_created` / `version` 后的顶层字段数。112 不是本批输入的正确计数，不能据此声称有 112 个顶层字段。

这是文字口径勘误。原 manifest、7 份 request 和 YAML 的 bytes/hash 保留；不更换输入、seed、窗口、预算、容差或预登记 case，不因此重跑数值。PM 在首次数值前独立核验了字段集合和全部继承/request hash。
