# 执行源适用性

| 批次 | 实际来源 | 与最终产品的关系 |
| --- | --- | --- |
| 首次冻结 | `4a6ce7f`，manifest `7161f81…` | 0次计算。完整输入/预算/容差先提交，不能当运行源码 |
| 数值 140115 / 140200 | Native/capture 代码 `d1a5979`；每批 `before-execution.json` 和 `source/` 在调用前保存，direct 报告和 adapter manifest 各自保存真实 hash | 六组完整数值对照只绑定这批代码；disabled 的 UI 差异单列，不说整个批次所有源都固定 d1a5979 |
| disabled UI 补存 | [source-supplement](evidence/source-supplement-v1/README.md) | 四项实际字节匹配，旧 index 是事后重建并 hash exact，非运行前封存。原 reports 不回写 |
| lifecycle 141052 | `102a17f` 后的 Windows source-key 修复增量，全部实际 Python/static 字节在 `source/` | 两注入失败/一真实取消；此前 lifecycle 前置校验失败单列，0 Main |
| saved-audit 141440 | 验证代码 `e4823de`，仅读取已存原件 | 63 checks，0 Main/COM；最终代码又对全部实际记录执行完整校验 |
| Chrome v1 | 产品 `e4823de`，`before-execution.json` / `source/` | 最终审计确认三次成功 manifest 的 source 表逐项 exact。服务保留原件的行政 hook 不改变引擎或两个成功缓存索引。取消也保留实际 request/terminal |
| 最终产品 | `70eeb0d6e25e6834dd75bd305f25154d2f5f67d6` | 其后仅证据/工具/文档。相对首次数值仅增加完整性校验、有限正整数预检与色标标题；`collect` / `run_worker` / `extend` 函数 AST 与 d1a5979 相同，原 native 模块去除只读增量后与3807基线全模块 AST 相同 |
| Chrome v2 | 70eeb0d 源表、真实 helper 字节另存 `serve_web_viterbi.py` | 原 archive 的 Error/raw/log/色标 SVG 与重存，0新 Main；原计算记录仍标其原 source，不借当前代码补造 |
| 最终 delivery audit | [143549](evidence/delivery-audit-20261024-143549/report.json) 及 `source/` / `verifier.py` | 2899 checks / 0失败；2871完整数组 exact、原下载/重开 raw/source bytes exact。审计本身0 Main/COM |

`actual_source_sha256` 是执行时磁盘源字节的补充，不等于 Python 已加载模块的 Git HEAD 证明；本批数值执行中共同 Python/native 文件未改，纯 UI 差异已逐项说明。最终文件不是一次不存在的“最终全量仿真”证据。

`evidence/**` 使用 `-text` 保留实际 CRLF/LF 源字节和 hash；不把 Git 换行归一化后的源当原执行字节。原始冻结提交和 v1 manifest/request 不因这项证据属性更改。

#10 衔接：raw schema5 的 `decoding` 是 Native ISI 结果，不能用 AMI 内部状态补填；继续拒绝 FEC。AMI 的运行/时钟条件另按 #10 接入和冻结。本票不新增 owner、并行 worker 或 AMI 模型执行。
