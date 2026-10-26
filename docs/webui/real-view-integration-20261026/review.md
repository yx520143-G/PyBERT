# 独立审查记录

日期：2026-10-27。两名独立审查者按 Standards / Spec 两个维度只读复核，比较范围为 `git diff 16ee4f4...5324fb0`。审查没有修改服务或执行新的 Main。

## Standards

**0 findings：硬违例 0，需要处理的 smell 0。**

- 改动限于验收材料和前端回归测试，产品、依赖及子模块差异为空，符合用户“精准修改”的要求。
- `tests/web_workbench.test.cjs` 复用生产 `workbench.js`，通过延迟响应验证记录切换、不可用结果和失败状态，没有复制数值算法或增加产品抽象。
- `verify_native.py` 使用原生配置加载、Main 和既有 collector，按 dtype、shape、bytes 比较；符合仓库 `CLAUDE.md` 复用原生计算的要求。固定本机路径符合该脚本的验收用途。
- 浏览器脚本分别承担被动网络观察和实际绘图核对，未替换请求或数据。README 保留了浏览器中断、警告、未测量项目与范围边界。
- 29 条浏览器检查中，19 条保存精简 CLI 结果，10 条保存完整 `evidence`；不能将它们表述为全部保留了完整网络对象。

Standards：总发现 0，无需修复项。

## Spec

**可行动发现 0；scope creep 0；错误实现 0。已披露的历史证据保留限制 1 项。**

- 真实计算与输入闭环符合计划。独立核对确认 A/B/C 均 succeeded、worker exit code 0，服务端请求与 manifest 的 requested/effective input 及 hash 一致。直接读取已存 NPZ 重新逐项比较，A 444/444、C 445/445 数组的 dtype、shape、bytes 全等；137 项冻结 hash 一致。
- 五类前端状态场景已有定向测试，未将替身失败声称为真实失败仿真。A 重开后的 NPZ 与原文件完整 bytes 一致，草稿及 revision 不变，额外 Run 为 0。
- 计划允许既有链路无需产品改动。当前差异只有测试及证据；3 次 Web Main + 2 次直接 Main 在预算内，未扩展 AMI、COM、优化或 Viterbi。
- 历史保留限制：A/B 完整浏览器侧 POST / 网络对象未留存；服务端实际请求、任务、数组、截图和早期逐视图检查仍在，C 有完整浏览器捕获。README 和总报告已明确披露。可接受限定 Native 计算—显示交付，不能表述为 A/B 完整浏览器网络证据均已保存。

Spec：可行动发现 0；保留上述证据完整性限制，不扩大验收结论。
