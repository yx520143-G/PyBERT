# #30 / PR31 入口修复的独立双轴复审

2026-10-25；固定候选 `5858668dc0ca8f3bbc7be0bef48eae70e1f3ebef` / tree `72d9c11a81f3a62e6ae69269856be24dfded8ae8`，工作区 clean。完整 diff 为 `git diff 3d942f30d892e038a2b52b5e876d11d94c511820...HEAD`；修复 delta 为 `git diff 2f0a60104551410041f00e03750a6de5a13bc0bb...HEAD`，共三条提交。按 `code-review` skill 分轴只读审查，未运行 checker、runner、pytest、hooks 或产品 import。

PM 对初次最终 `2f0a601` 提出的唯一 [Standards P2](https://github.com/yx520143-G/PyBERT/pull/31#pullrequestreview-5639104111) 是 runner 专用 case 的普通 pytest 收集回归；该发现来自静态审查，不能称为实际 pytest 失败日志。初次 [review.md](review.md) 与 [verification.json](verification.json) 保持原字节历史。当前相关通过批次是 11，最终 v2 manifest 另列。复审后的封存提交只补说明/审查/manifest 和已知只读费用，不改变 source/cases/runner/checker/plan 或重跑测试。

## Standards

审查者 `/root/issue30_standards_review`：**hard 0 / actionable heuristic 0；原 P2 已关闭。**

针对 CLAUDE.md:47–54 的常规测试入口要求，原 runner 专用文件已 100% 原字节迁至 evidence，文件名不匹配默认 pytest 模式；runner 第 23 行仅更新读取路径，其余文本及 guards 原样。其余 38 个测试文件、conftest、pytest 配置、Makefile 和产品源码均未改，无新增测试 ignore/skip。

独立核验原 127 文件均保留为当前文件或相同字节存档，01–10 未变；107 项协调/入口检查的 receipt 输入/输出关系匹配，当前六项执行输入与 11 原件一致。保存的结果为 9 methods、35 seam、29 error constructors，累计计数和成本一致。

617,339 B 本地诊断原件与 Git 内 gzip 解压结果逐字节一致；本地 exclude 仅指向该日志，whitespace 属性仅覆盖新 raw runs，hooks 配置未改。新文本 UTF-8/no BOM、JSON/AST 静态检查无问题。静态 red、截断缺口、staging 失败及误报均明确保留，没有冒称实际 pytest 失败或 hooks 通过。

结论限于 P2 入口修复及现有证据一致性，不证明完整 pytest/conftest 运行健康、模型数值或 clocks 资格。

## Spec

审查者 `/root/issue30_spec_review`：**missing/partial 0 / scope creep 0 / implemented wrong 0**。

P2 入口问题已按 PM 允许的迁移方案解决：case 原字节移出 tests，新名字不匹配默认 pytest 模式；runner 仅改路径。其余 38 个测试文件、conftest、配置和两个产品文件字节不变，没有扩大 ignore/skip。

静态检查 9 项 green 的依据成立；01-static-red 明确属于静态检查失败，没有冒称实际 pytest 日志。证据只证明该入口缺陷消除，未声称整个 pytest/conftest 运行健康。

11-entry-green 保存的 source、caller、cases、runner、plan、venv.cfg 六项与当前文件完全一致。记录为 9 methods、35 次生产纯 seam、29 次内部 error constructor，非零 stub 单列；累计账为 165/135，elapsed `4.152754799972172 s`，与 receipts 一致。

原交付 127 项均在原路径或逐字节归档保留；01–10、v1 review/seal 未改。111 项批次输入/输出关系通过（含 staged 再观察的额外 4 项）。617,339 B 原日志与 gzip 解压内容及双方 hashes 一致；本地排除仅该日志，无测试排除。staged 失败、截断缺口、错误 mixed 判定和 UNKNOWN 均保留，未冒称真实 hooks/pytest 通过。

本次所有只读入口 exit0；模型、D/E、有效 clocks 与 COM gate 保持原边界。v2 seal 在审查后补充，不计缺项。只读观察范围与已知费用见 [review-read-costs.json](pytest-entry-fix/review-read-costs.json)。

Standards findings 0（原 P2 关闭，无最差项）；Spec findings 0（无最差项）。PM 对新最终 HEAD 的 fresh review 仍待完成。
