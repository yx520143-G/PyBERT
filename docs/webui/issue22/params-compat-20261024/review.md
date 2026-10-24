# #22 固定候选只读自审

2026-10-24。按 `code-review` skill 分为独立 Standards/Spec 两个只读 agent；root 为唯一 writer 并汇总落盘。

固定比较：`git diff 98f30f871aaf6e1a277317096c68295890c92a79...80100e262e433076396819e3d29aedc20bdad30a`。

提交：`80100e2 fix: consume Rx AMI GetWave tuple parameters (#22)`；候选 tree `6d283adc05ff6c7fd76c4e67c4ee724c55084b7d`。两位 reviewer 读取时工作区 clean。Spec 为 [issue22.json](issue22.json) 的完整 live 正文；标准为根 CLAUDE 和用户 AGENTS 指令。仓库没有 `docs/agents/issue-tracker.md`，本票明确给出的 live issue 路线已足够，不以通用 setup 作为阻塞。

后续只增加报告/交接文档，产品文件、测试和 runner 的 green05 SHA256 保持不变。此自审不代替 PM 对最终 PR 的 fresh review。

## Standards

**0 findings；baseline smell：0 findings。**

- `bert.py`：纯参数消费集中于一个 helper；调用点和根层查询修改与新键结构直接相关，失效 import 已删除。未见违反用户“高内聚、精准修改、简洁优先”要求或根 CLAUDE 的改动。
- 定向测试：执行实际生产函数 AST，使用固定原 parser grammar，避免构造引擎；未见重复实现修复作为 oracle 的问题。
- 新证据：历史红灯和中间快照属于明确保留的证据，不判为 Duplicated Code。62 个变更文件均可严格 UTF-8 解码且无 BOM。

新增 Main、COM、coopt、AMI Init/GetWave/Close、真实模型库加载、引擎构造、原生 helper、parser 调用均 0；未修改文件或重跑测试。

## Spec

**0 findings。**

对照 #22 的“沿用固定 PyAMI parser 的真实返回契约”“保持完整层级与数值含义”“不得用填0、广播、按最短截断”等要求，最终 helper 和 caller 已覆盖 tuple/tree、完整路径、根层查找、tap 筛选排序及每 call 形状边界。非数值、混合、Table、空返回和参数变化均有明确处理；未发现缺失实现、越界行为或明显错误。

保存的 green05 为实际生产函数 AST 测试，12 项通过；scope 核验限定了源变更，原四文件及七项输入保持原字节。此次仅读取源码、快照和日志，未重跑测试或 parser；新增模型、引擎、helper 调用均 0。真实 clocks 仍 BLOCKED，符合本票边界。

两轴结论分别为 Standards 0、Spec 0，没有需要 root 修改产品代码的 finding。
