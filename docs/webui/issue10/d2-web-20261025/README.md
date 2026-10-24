# D2：Web AMI clocks consumers

本次仅交付 #10 的 D2 软件适配，基线 `0f04562c50a12fae637fece04da100c44c86617e` / tree `790d13dc87bf00d2b31f8aaf128157a937fe0c93`。合同见 [原合同](https://github.com/yx520143-G/PyBERT/issues/10#issuecomment-6388483807) 及 [预算补充](https://github.com/yx520143-G/PyBERT/issues/10#issuecomment-6388850218)，完整副本保存在本目录。新独立 clone、env/cache；D1 保持封存。

## 实现与边界

单一 clocks helper 校验 fresh producer、原 mask/indices/window/profile，供两处 DFE Eye、分段 CDR、100-bin histogram、冻结连续原 grid FFT 与 archive/Viterbi 使用。仅 dense ui_ests 允许与 bool mask 配对的 NaN；其余 finite gate 不变。实际 AMI 记录采用 raw6 + clock_contract2 + ami-clock-grid-v2，Web/外层 archive schema 仍1；旧 raw2–5 保留。保存/重开保留原 manifest/NPZ/NaN bytes，不重算 engine/Eye/FFT。

worker 在 Main 离开后、取消及 collect 前取 host-owned snapshot；失败/取消保存独立 partial manifest/NPZ 与阶段/错误。完整 ABI buffer 仍属独立 B sidecar；helper valid prefix 不是完整 buffer 备份。Viterbi 只验证手工软件 payload 的最后 W 个 producer 索引；public AMI+Viterbi gate 保留。PAM4 缺少生产声明/offset/mapping 时仍 unsupported/UNKNOWN。

## 实际软件验证

每个 guarded child 在执行前冻结并 commit source/case/runner/plan/environment/guards；用例从开始即不在默认 pytest 发现范围。仅 AST 实际定义和锁定 NumPy；无关 FFE jitter/bathtub/trellis/display noise 使用明确命名的普通 stub，不获得算法或模型资格。

| 记录 | 实际结果 |
|---|---|
| 01/03/05/07/11 | 缺 seam 的 red，原失败全部保留 |
| 02/04/06 | mask/NaN、fresh producer/裁剪、实际 Eye/CDR 内核通过 |
| 08-archive-green | 目录原名；实际 FAILED/BLOCKED_BUDGET，pure 3934 + 既有67 = attempted entry4001；该入口在函数体前被拦截，不称原4000cap合规 |
| 09 | stdlib guard-only 预期 exit86；只有 before 哨兵，body/caught/after/下一 case 均不存在；非数值 green |
| 10 | 完整 archive 新/旧版本、lossless bytes、拒绝路径通过 |
| 12 | actual phase/write/annotate、独立 partial、取消/缺 producer/保存失败通过；完整 worker 未运行 |
| 13 | plan 自哈希预检失败，child/产品/NumPy0；仍计启动槽，记录保留 |
| 14 | actual one AMI collect→extend_analysis 和静态接线共2用例通过；两次DFE Eye各4 trace、NaN payload42、CDR histogram/FFT、disabled及手工 enabled Viterbi finalW通过 |

累计 pure **17,273/25,000**；A 5,264/9,000、B 98/3,000、C 7,910/8,000、review D0/999；启动槽14/16（13个guarded child，含stdlib09；NumPy import12）。collect1、extend_analysis1、eye_data14、calc_eye13、clock_data11、clock_display3、histogram10、rfft4、safe_log10 47、Viterbi extend4/validate11、resize13、archive read_arrays29/validate_run13/save2/load6、annotate3、Execution.write1、partial保存4。每次 generator/pairs 恢复均保留计数，未重分类降账。完整计数、bytes、elapsed 与原件见 validation-summary.json、cost-ledger.json 和各 runs/launches receipt。child 被 launcher 包含，二者时间不相加；task wall/RSS 为 UNKNOWN。

全 PyBERT/Main/my_run_simulation/update_results/fullworker/Execution.capture/DFE/decide/decode/真实 trellis/run_ami_model/PyAMI/model binary/SciPy/NumPy及display RNG/COM/coopt/GUI/浏览器/CLI服务/fullsuite/rootcollect 调用均0。stdlib 原子文件名可能使用系统熵，RNG0 仅指上述数值 RNG。软件数组和 stub 不是生产模型、硬件或 E 资格。

## 证据限制与审查

Standards 0；Spec 1（P2 evidence partial，产品实现问题0），完整报告见 independent-review.md。第14批 collect 既有直接 JSON manifest 写入和 plot_payload 读取未进入逐次计时 instrumentation；原 manifest/NPZ/hash 保留，写1/读1和物理 bytes 单列，但 elapsed 为 UNKNOWN。不得称全部序列化逐项计时完整，也不重跑以伪补历史。

02 的20次数组 copy 由10个完成 fixture 可推知，原 runner 无逐次时间；04起才有 hostcopy trace。08/10 部分失败的内存 malformed buffer 未逐一 raw-bound，原 source/case/archive/output 保留；后续新增 raw blob 捕获不追补历史。13 原预检 stdout/traceback 仅工具转录，失败 receipt 与原 plan 已存，elapsed UNKNOWN。

设计固定 ref 的 GitHub contents 查询404，使用已有设计 repo 的该 Git blob 原件；一次全 comments/较宽 source 工具展示曾截断，后续已限定范围完整读取。初始只读检查曾使用 D1 Python（无产品/NumPy或旧环境写入），正式 bootstrap 及以后均 standalone/new env。两次静态 lock 定位失败在安装/导入前 assert 停止，仅工具转录；修正为 stdlib tomllib + Python3.13/win32 marker 后，按锁定 NumPy2.5.1 wheel SHA256 安装并验证952文件/951 RECORD。

08 原 profiler RuntimeError 可能被 unittest 吞掉并撤销 profiling；后续守卫改为受限 stdlib 收尾后不可恢复 os._exit86，09 哨兵验证了实际停止路径。语义参考 [sys.setprofile](https://docs.python.org/3.13/library/sys.html#sys.setprofile) 和 [os._exit](https://docs.python.org/3.13/library/os.html#os._exit)；实际证据以09原件为准。NumPy ctypes/pyd 记录是限定 Python audit 事件，不是全系统 DLL trace。

## 保护与交接

protected-final-check.json：旧16仓库 HEAD/tree/default status、271元数据、4874 raw、2394材料/installed source、16旧env/cache目录、D1/#30 seals 及新952安装文件全部匹配。新缓存/env及全部失败原件保留。最终 seal 位于独立 bootstrap cache，绑定交接 HEAD/tree/clean、文件 raw/Git blob 与最后 green source，避免 seal 自引用。

仅本人 fork 的单一 Draft PR Refs #10，交 PM fresh review 后停写停测；不 merge/关票。E 未开始；#10保持open，#4默认COM BLOCKED_BUDGET/NOT_EXECUTED、#1最终数值review/备份/私有化gate均保留。

PM已在 [6389554270](https://github.com/yx520143-G/PyBERT/issues/10#issuecomment-6389554270) 固定登记第14批 JSON计时/Native full collector未运行等边界；副本见 PM-evidence-boundary-6389554270.json。此为阶段证据确认，非最终验收；C只余90，A/B余额不挪用，未新增预算或运行。
