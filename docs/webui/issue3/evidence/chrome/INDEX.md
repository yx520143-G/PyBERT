# #3 真实 Chrome 图像索引

桌面 Chrome，100% zoom。01–27及provisional使用 CSS viewport 1280×720，工具输出原始 JPEG 为1265×712；28/29不设临时 viewport，使用当前2560×1313，原帧同尺寸。所有 jpg 保留原 bytes；机器索引 [screenshot-index.json](screenshot-index.json) 记录选择状态/标题/hash/viewport，交付适用表另外记录每张图片真实格式、像素、bytes/hash。owner 在观察实际 run/analysis/title 稳定后采集，逐张目视并用 view_image 回读所采纳文件。

显示 case `F-PAM4-01`/`F-NRZ-01` 来自保留的完整原生 raw 与本票冻结分析；test-only hydration 没有重新运行主仿真或交付产品 archive import。实际 identity 数值 task 和失败/取消 task ID 另见 README/生命周期 report。

## 采纳的图像与精确支持范围

| jpg | 所选 case / 验证范围 | capture source |
| --- | --- | --- |
| [04](04-final-pam4-five-point-distribution.jpg) | PAM4 同 run 五点、10条 total/independent PDF 图例，轴完整；run 控件在截图顶端之外，run由状态JSON及图下来源确认 | `170145b` |
| [06](06-final-pam4-ffe-spectrum-complete.jpg) | PAM4 独立 FFE 总/独立 TIE amplitude 与 threshold；MHz、native amplitude/UI 标度 | `aeb49cc` |
| [08](08-final-two-run-ffe-eyes-count-scale.jpg) | 两 run FFE eye、各自 ps/V 轴与共享 count 色标 | `68c1b4c` |
| [09](09-final-channel-three-frequency.jpg) | Channel raw/perfect-term、actual-term、trimmed 三频响；各自来源清楚 | `68c1b4c` |
| [10](10-final-channel-clean-eye.jpg) | PAM4 clean Channel-only eye，未选显示噪声 | `68c1b4c` |
| [11](11-final-channel-display-noise-eye.jpg) | 同 case 缓存 GUI-compatible σ1mV eye，复选状态和标题可见 | `68c1b4c` |
| [12](12-final-ffe-bathtub.jpg) | 独立 FFE crossing-jitter bathtub；log10 probability 与 timing-only 提示 | `68c1b4c` |
| [13](13-final-cdr-histogram.jpg) | CDR 完整 ui_ests 100-bin、ps/count | `68c1b4c` |
| [14](14-final-cdr-legacy-spectrum.jpg) | CDR f*UI / legacy log10 ratio，无 ×10/20 | `68c1b4c` |
| [16](16-final-jitter-info-table.jpg) | 五点 Info；rjDD/mu 的 unknown/unavailable raw reference 可见，表内其余内容可滚动 | `7c4cf9f` |
| [17](17-final-gui-crosswalk-frequency-route.jpg) | 从原 GUI Frequency responses 实际跳到 Channel，follow-node + H，三频响 | `7c4cf9f` |
| [20](20-final-channel-zoom-out.jpg) | 实际 Zoom out 后轴范围变化，保留真实曲线与所选 run；Zoom in/rectangle/reset 的轴文字记录在 interactions.json | `7c4cf9f` |
| [21](21-final-failed-task-old-result.jpg) | 只证明失败 task `193d929b...` 与旧所选 PAM4 结果分离；截图未包括完整图轴，不作完整图表通过证据 | `7c4cf9f` |
| [22](22-final-cancelled-task-old-result.jpg) | 只证明取消 task `cec1177a...` 与旧结果分离；requested/observed/exited完整ID见 cancel-state.json/report | `7c4cf9f` |
| [23](23-final-old-schema-unavailable.jpg) | schema2 NRZ 未保存 FFE eye，明确不可用、没有伪曲线或隐式分析 | `7c4cf9f` |
| [24](24-final-old-schema-rx-eye-preserved.jpg) | 同 schema2 的原 Rx input eye 仍可读取，保留旧输入标识 | `7c4cf9f` |
| [25](25-final-old-schema-dfe-info-preserved.jpg) | schema2 保存的 DFE Info、fit validity unknown 与其他点不可用说明；表内可滚动 | `b2bdb229` |
| [26](26-final-old-schema-channel-frequency-preserved.jpg) | schema2 保存的 actual-termination Channel H，标题明确三源视图不可用 | `e9c73c5` |
| [27](27-final-old-new-channel-frequency-comparison.jpg) | 旧/新 Channel H 比较；通用标题下旧数据的限制说明仍保留在图例 | `e9c73c5` |
| [28](28-final-ffe-pdf-source-metadata.jpg) | v2 PAM4 FFE PDF及展开的eye/jitter末段窗口；具体ID/source由metadata-v2-checks.json中实际DOM读取与断言支持，未声称图片包含全部JSON | `83b7515` |
| [29](29-final-cdr-full-record-metadata.jpg) | v2 PAM4 CDR histogram及展开的full_record来源窗口；完整240000样本/ID/source见同一DOM检查记录 | `83b7515` |

`68c1b4c→7c4cf9f` 仅增加文本分析时清除旧 inline 图高度的一行修复；前者的科学图表/render 数据与后者相同，后者的 Jitter Info 已单独重拍。`aeb49cc→68c1b4c` 只改多 eye 面板高度与共用 count 色标，06 单 spectrum 不受影响；170145b 的04 PDF 不受后续 auto-scroll/eye facet/text height 修改影响。没有声称早期图片逐字节执行了最终所有 JS。

`7c4cf9f→b2bdb229→e9c73c5` 只补旧 schema2 的 Info/Channel H 展示与限制标签，不改 schema3 科学数组或上述已采纳的新分析图。25/26/27 是对应分支的新增实拍。机器索引区分原始采集状态与最终采纳/排除判定；原帧未重绘。

`e9c73c5→83b7515` 修正display身份/source及CDR完整记录窗口，API/viewer显示来源metadata；原28张图片不作为修正后metadata通过的证据。065914已逐项确认所有科学/显示数组与061108完全相等；本轮28/29补拍来源窗口，[metadata-v2-checks.json](metadata-v2-checks.json)保存PAM4 FFE PDF、CDR histogram/spectrum三次实际DOM读取与具体ID/source/window断言，console error/warn为空。

## 保留但不用于所称最终图表通过的原件

- `provisional-ffe-axis-clipped.jpg`、01：图轴不完整；02为修复SVG样式前的完整 FFE眼图，03为描边污染下的五点PDF。
- 05：spectrum 图轴裁切；07：旧较小 two-eye 面板、无共享 count 色标，已由08替代。
- 15：旧 inline430px 高度造成 table 下移的实测原件，已由16替代。
- 18：Zoom in 到未包含曲线的范围且图轴裁切；19：rectangle 选择为空曲线区，均保留，不能用其证明完整曲线可读。20是包含真实曲线的缩放证据。Reset axes 及 tick 变化有独立 DOM 记录。

[failure-state.json](failure-state.json)、[cancel-state.json](cancel-state.json)、[interactions.json](interactions.json) 与图片互补。浏览器最后读取 error/warn 日志为空；不因此宣称独立物理准确性或完整原 GUI 测试。
