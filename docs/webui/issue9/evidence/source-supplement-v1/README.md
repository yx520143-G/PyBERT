# 首轮源码适用性追加

两批 `before-execution.json` 与 source/ 保存的是批次开始时的实际源字节。批次内实施了 UI，因此不能声称所有执行方的全量 source hash 均固定为 `d1a5979`。

PM 独立核验：V-DISABLED adapter 与 batch-before/direct 的共同 Python/native 计算文件 hash 全部相同，仅 `index.html` / `settings.js` / `workbench.css` / `workbench.js` 变化，并新增 `viterbi.js`。这里保存后四项的实际字节；它们匹配该 adapter 的 source 表。

`index.html` 当前多了 Viterbi Trellis option。`index-reconstructed.html` 是**事后重建**：从当前字节只删除该 option，SHA256 为 `2e984957c38c58927b005ebe67c6e75f7c9e166d57983493f6789ec708f33334`，与 V-DISABLED adapter 的实际源 hash exact。它不是运行前封存文件。当前 index 另存为 `index.html`。旧 reports 和原件保持不变，不因纯 UI 差异重跑数值。

首次数值之后对 `web/viterbi.py` 增加的是只读 archive 完整性校验；原 decoder 和采集计算未变。各批数值仍绑定各自封存源，最终校验需对旧原件重做，无需重新仿真。

原生覆盖边界：PAM4-ERROR 的 470 bit errors 对应 470 unique symbols，重复 symbol 条目 0；全部本轮原生 probability 数组的零值数为 0。受控 contract fixture 含 `[2,3] → [1,1]` 和概率零值，仅用于协议/视图检查，不能冒称原生观测。
