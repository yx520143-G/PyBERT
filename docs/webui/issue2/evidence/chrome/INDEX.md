# Chrome 证据索引

最终补拍服务代码：`f67f07d54332143d10340b3fd56fedf63d5aab26`。CSS viewport 实测1280×720、DPR=1，见 `viewport.json`。工具PNG内容区1265×712，与CSS viewport尺寸分开记录，没有缩放图片冒充视窗尺寸。

最终两次真实Run均重新载入计算前冻结的完整YAML：

- NRZ：`968883ce-1c46-4204-93e4-e4484040f721`，seed1，canonical hash `6e54735ef018afc6d0a79e61b4995f8c16d5550a9ae17b6be5e97bc98401c5fd`。
- PAM4：`4df0395c-2ba0-4345-91c7-b7573c776d4c`，seed1，canonical hash `a6f0b0d01ce35222b102534c8b02c0a0fa9a6849b81f2acf347d435157a9f2d6`。

完整输入、数据目录、summary、日志和代码版本见对应 `final-run-<id>.json`。这两次Run只用于补齐最终UI证据，没有重做direct/reference数值矩阵。

## 已逐图目视核对的最终图表

切换控件与截图在不同的工具调用中执行；先确认所选成功ID、analysis和plot ID稳定，再采集 `getScreenshot()`，目视后保存同一原始图像字节。前5张关键补拍还重新用本地 `view_image(original)`核对，避免把过早截图当通过。

| PNG | 实际支持内容 | 所选成功run |
| --- | --- | --- |
| 01-nrz-dfe-spectrum.png | DFE Jitter Spec，total/independent/threshold，原生幅度比单位 | NRZ 968883ce |
| 02-rxffe-frequency.png | Responses / Frequency / Single，`ffe_H`，不是累计响应或jitter | NRZ 968883ce |
| 03-rxffe-waveform.png | Waveform，`wave.ffe_out`，真实Rx FFE输出 | NRZ 968883ce |
| 04-nrz-dfe-eye.png | `eye.dfe`，recovered clock_times，NRZ | NRZ 968883ce |
| 05-cdr-adaptation.png | CDR Adaptation，UI estimates (ps) 对记录时间 (ns) | NRZ 968883ce |
| 06-pam4-dfe-eye.png | `eye.dfe`，recovered clock_times，PAM4 | PAM4 4df0395c |
| 07-two-run-comparison.png | 两run ID、原生summary及mod_type输入差异，独立窗口保留 | 两者 |
| 18-help-version.png | 帮助、范围、原署名与实际f67版本信息 | About |
| 19-dfe-adaptation.png | DFE Adaptation，5个tap、record index与系数 | NRZ 968883ce |
| 20-dfe-jitter-dist.png | Total PDF与data-independent PDF，ps和1/ps | NRZ 968883ce |
| 21-dfe-jitter-info.png | 原生ISI/DCD/PJ pp、RJ sigma及DD参考统计 | NRZ 968883ce |
| 22-rx-input-eye.png | `eye.rx_in`，nominal fold，未改名成Tx独立waveform | NRZ 968883ce |

查看旧NRZ结果时当前草稿仍是PAM4，页面明确显示 `Older input · draft changed`；图表由所选NRZ run而非当前草稿决定。15/16两张参数画面支持3/2、0/0显示，完整100槽及enable数以对应JSON的DOM实测为准；这些是配置提交证据，不是新数值run。

## 交互和失败/取消证据

- `current-focus.json`：Seed2在当前焦点编辑后直接点击Run，任务 `84acea5c…`成功，结果输入seed2；这是输入提交测试，不替换冻结seed1数值基准。
- `chrome-abort.json`：真实Chrome在DFE运行时点击Abort，任务 `225593b7…`最终requested/observed/exited均true、cancelled，所选旧成功run `1e0b26a2…`保留。`lifecycle-cancel.json`另记录实际API请求时序、退出前两个409及成功ID不变。
- `yaml-roundtrip.json`与 `chrome-pam4.yaml`：实际Save As下载，经原生加载后canonical hash等于冻结PAM4；Save也实际产生同名下载副本。浏览器下载事件等待工具曾超时，文件落盘与原生重载检查实际成功。
- `save-as-repeat-escape.json`：先Download prime，再次打开、改名、Escape，逻辑名不变；`pybert-escape-probe-20261024.yaml`在Downloads中不存在，见交付适用表。取消不下载的判定由JSON/文件检查支持。
- `ntaps-15-5-to-3-2.json`、`ntaps-15-5-to-0-0.json`：通过Save显式flush后由原生observer收敛，实际启用3/0，完整100槽均保留。未提交中间态及初次失败另存为 `ntaps-before-input-commit-fix.json`、`ntaps-zero-before-save.json`，不能把它们算通过。
- `undo-during-normalize.json`、`undo-after-normalize.json`：处理中Undo锁定；结束后可撤销，后续回包后仍恢复原0/0。
- `lifecycle-failure.json`：故意错hash任务failed且两旧成功ID不变。未支持激活FEXT的YAML亦实际被拒绝，旧草稿/逻辑名/所选结果保留。
- `final-console-errors.json`：本次最终浏览器服务未见JS console error。存储写失败/输入错误独立恢复由交付的Native handler在 `verify_web_storage.cjs`中注入故障验证，不声称在Chrome中修改了真实存储权限。

08–14、17等前期操作截图保留为上下文；其操作结论以上述明确的JSON、实际文件和时序记录为准，不仅凭这些文件名作通过判定。

## 非通过/历史截图

`premature-*`、`premature-refresh-*`是过早抓帧，画面可能仍为Connecting、旧analysis或前一张图；全部排除在所称图表通过证据之外。`historical-*`是替换前原件，未逐图重新资格判定。`15-ntaps-three-before-commit-fix.png`是配置提交回归前的画面，同样不作当前通过证据。全部保留，不删除或重命名成通过。

机器可读的逐文件hash、状态和支持范围见 `screenshot-index.json`。
