# PR #7 评审修复与桌面 Chrome 验证

日期：2026-10-24（Asia/Shanghai）。复现基线：`6209cebd318779f69e290a458bd6e995df64afd4`；原生语义依据仍为 `1bc905d577d2f3bd9471421cfbf3d422d4e6080e`。本次验收只覆盖桌面 Chrome 1280×720 的本地 HTTP 页面。

## 四项问题

| 问题 | 修复前证据 | 修改与验证 |
| --- | --- | --- |
| P2：单独恢复 Ntaps 后 tap 状态不一致 | Chrome 将 Ntaps 改为 9 后恢复默认，得到 `15 / 9 / 9`（Ntaps / Native Enabled 数 / 搜索表 Enabled 数）；刷新变为 `15 / 9 / 15`。见 [before-ntaps.json](before-ntaps.json)。 | 恢复与普通编辑共用依赖协调；仅恢复搜索表时根据当前 Ntaps 派生 Enabled。恢复、撤销、刷新及模块恢复的 10 步检查通过，见 [after-ntaps.json](after-ntaps.json)。手工关闭的 Native tap 在搜索表恢复与刷新后仍保留。 |
| P3：输入错误掩盖存储失败 | 成功加载后注入 `localStorage.setItem` 写入失败，再清空 bit rate；原界面只显示输入错误，没有“仅当前页面保留”。 | 将校验和保存状态分别显示。Chrome 故障注入检查了错误输入、有效输入、写入恢复；错误与保存状态同时可见。见 [after-storage.jpg](after-storage.jpg)。这是可控写入故障，未实际耗尽 Chrome 配额。 |
| P3：Rx AMI 错误描述实际 FFE taps 被禁用 | 原生 `_btn_disable_ffe_fired()` 操作 `ffe_tap_tuners`，不清除 `rx_taps`；仿真在 Rx AMI 分支旁路 Native Rx FFE。 | 修正模式提示、两处实现映射与研究文档，区分实际系数、搜索表、DFE 表及本页草稿行为。9 种 Tx/Rx 组合验证最终提示与时钟控件状态，见 [modes.json](modes.json)。 |
| P3：Rx EQ implementation 原 GUI 分组错误 | `view.py:552` 的 `rx_eq_sel` 属于 `Equalization / Rx`，位于 IBIS-AMI 子组之外。 | 修正索引路径；静态 129 项核对与 Chrome 逐项点击跳转通过，见 [gui-routes.json](gui-routes.json)。 |

## 验证范围

- `verify-draft-state.cjs` 的三个真实应用处理器回归用例在修复前全部失败，修复后全部通过；覆盖 Ntaps 恢复/撤销/持久化、搜索表恢复保留手工 Native taps、存储失败与输入校验独立显示。此脚本通过最小 DOM 替身调用实际处理器，布局另由 Chrome 验证。
- `verify-gui-coverage.cjs` 通过：129 个命名控件、5 类 tap 表、条件与只读状态；Chrome 实际点击了 129 个索引入口并检查目标字段/表/参考条目，非仅统计元数据。
- Native / Init / GetWave 的 9 种 Tx/Rx 组合通过；原生 AMI 模型能力和返回时钟仍是未接入状态。
- 单文件手工路径、多文件逐行顺序与刷新恢复通过，见 [manual-file-paths.json](manual-file-paths.json)。测试字符串只用于草稿，没有读入通道数据。
- 桌面页面无横向溢出，见 [layouts.json](layouts.json) 和 [desktop-1280x720.jpg](desktop-1280x720.jpg)。检查期间未捕获页面 JavaScript error/warn。
- 最终 Node 回归、覆盖校验、语法及编码检查结果保存在 [checks.txt](checks.txt)；`git diff --check` 通过。6 个本地 HTTP 页面源码文件的原始字节 SHA-256（含本机换行）保存在 [source-sha256.json](source-sha256.json)。

复跑（在仓库根目录，Node 已安装）：

```text
uv run --no-project node --test docs/research/pybert-signal-chain-ui/verify-draft-state.cjs
uv run --no-project node docs/research/pybert-signal-chain-ui/verify-gui-coverage.cjs
```

## 未验证项

- Chrome 扩展阻止文件选择器的自动填入，并要求启用“Allow access to file URLs”；系统文件选择器的单选/多选不能计为通过。手工填写路径的验证不替代它。
- 浏览器工具策略拦截 `file://` 导航，未验证直接双击本地 HTML 的流程。
- 未运行 PyBERT 仿真、COM 或 AMI 模型；此 PR 仍是配置草稿与信号链映射。Issue #2 继续暂停。

窄屏不属于本次验收范围。
