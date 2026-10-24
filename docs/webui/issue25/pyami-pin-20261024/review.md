# #25 固定候选双轴只读复核

基线 `35a71a6b79a00693a2f2862184552894752899c0`。最终复核候选 HEAD `8ae4bce323507b7a18c1dadb9f7529dc8fceb369`，tree `fe172087cab114a3004fb1c1c5a156ce9188dc34`，代理核验时 clean。diff 为 `git diff 35a71a6b79a00693a2f2862184552894752899c0...HEAD`；commit list：

- `fa76df8 build: pin reviewed PyAMI fork for uv and pip`
- `8ae4bce build: preserve raw dependency evidence in hooks`

根是唯一 writer。按 code-review 技能分别委派独立 Standards、Spec 只读代理，完整 live #25 已明确提供，不另建 tracker/setup。代理仅阅读 Git、文件、AST、hash、metadata 与已有 receipt，没有运行 hook、安装、验证脚本、产品 import、测试、helper、parser 或模型。

## Standards

**最终 hard 0 / actionable smell 0。**

按 CLAUDE.md、pyproject.toml、.pre-commit-config.yaml、LICENSE 和用户 AGENTS 复核。初始 `fa76df8` 发现 2 项 P2：check-added-large-files 会拒绝 20 个原始大文件，end-of-file-fixer 会改 raw 字节；`.gitattributes` 无法豁免 hooks。根在 `8ae4bce` 为本票 startup/lock/pip-report 添加精确 large-file 排除，并对本票 commands/inputs 排除 EOF/mixed-line-ending 自动改写。新增普通脚本/文档未被排除，其余 hooks 保持；原始 bytes 不变，两项已关闭。

capture.py 集中命令、输入/输出和费用；verify_source.py 集中来源断言/guards。未发现需增加抽象的 actionable smell。普通新增文件为 UTF-8 without BOM，两个脚本静态 AST 3.10 与 119 列检查通过。产品元数据修改范围小，原 LICENSE、native src、PyChOpMarg、uv.lock 无 diff。

静态 raw hook 初次报告因比较 CRLF/LF 不同视图而出现 EOF false positive，原报告保留在 raw-hook-check.json；raw-hook-check-final.json 明确纠正。没有以静态规则评估冒充实际 hook 或完整 lint 通过。

## Spec

**missing/partial 0 / scope creep 0 / implemented-wrong 0。**

合同“uv workspace也必须实际使用F”“两种安装方式分别验证”落实为 A editable 和 B PEP 610 来源、distribution metadata、同一组 35 PyAMI + 56 PyBERT 源文件两路核验。uv lock 原始结果 exit 0、234 包，17 份 lock 快照相同；没有伪称 editable 含 VCS commit。固定 F/tree/祖先与 gitlink/standard URL 一致，PyChOpMarg 和算法不变。

“先guards再做必要safe import”“来源迁移成功不等于NRZ/PAM4模型资格”边界明确：仅顶层包 import，model ModuleSpec/AST，无 model 模块体或生产方法调用。17 个 receipt 及原始 hash/费用相符；strict、B+8、rng/probe/D/E 和 PyPI 限制已披露。独立 clone/子模块无 alternates，旧 7 仓库状态、54 项 Git 元数据和 4874 项原件 hash 保持。

针对 `8ae4bce` 的增量复核确认：本票窄域 hook 例外服务于合同原件保存要求，没有增加产品行为或放宽模型边界；原材料、依赖和验证脚本未改，17 份 receipt/output hash 再匹配。Draft PR 和 PM fresh review 为随后交付步骤，此结论不是 PM 验收或模型资格。

两轴最终各自为 0，原 Standards 两项发现保留并已关闭；本报告不跨轴合并结论。
