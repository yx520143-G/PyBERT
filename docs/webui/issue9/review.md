# 独立双轴审查

固定初审 `3807bd2...102a17f`，reviewers `/root/standards_review` 与 `/root/spec_review` 只读独立执行；没有运行数值或浏览器。标准来自当前 AGENTS 指令、CLAUDE.md 与 code-review 的 Fowler 启发；规格由 live #9 连接器读取后冻结，未引入缺失的 issue-tracker setup 作为许可门槛。

## Standards

硬规则违规 **0**，启发式 finding **0**。可选 capture、原 decoder 不变、trellis producer 仅抽取复用；未见要求修复的过度抽象、重复算法或无关改动。

另提供验证预算建议：adapter verifier 的等待原无 deadline。已加 180s 测试上限、明确取消请求/退出和必要的测试预算终止边界；后者不算合作取消成功。原通过数值未因此重跑。

## Spec

初审 **2项**：

- P1：Windows `actual_source_sha256` 反斜杠键无法通过 POSIX 键检查，造成成功发布与旧 archive 打开失败。读取键统一斜杠，兼容既有 Windows/POSIX 字段，并补 contract。原 lifecycle 前置失败留存，0次 Main。
- P2：把 raw schema5 降为4而保留非法 decoding，可绕过新扩展校验。现在旧 raw2/3/4 携带任何 decoding 均拒绝；旧记录缺扩展正常加载为“未采集”。自洽坏副本在发布前拒绝且旧 inventory 保持。

独立 delta 固定复核 `e4823de24700ad1480bd1a341d054384142e6841`：两项均闭环，**新增 Spec finding 0**；只读核对 63项审计0失败/0main/COM，旧版本兼容明确为受控派生。最终有限数值预检和色标显示增量另随交付复核，不冒称旧数值批次重新执行。

两轴分别计数：Standards 0 / Spec 初审2、已闭环2。最后产品/证据 delta 的独立收口记录由最终交接补充。
