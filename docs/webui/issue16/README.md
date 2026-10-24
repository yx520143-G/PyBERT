# #16 外部 S8P/S12P 修复前后验证

本票交付限定范围的 **external simulation/model** 验证：新增 S8P/S12P 的 post/final importer 均匹配独立物理差分参考；两个有界 Native direct / 最终 Web fresh-worker 下游案例一致。**硬件实测 S8P/S12P 仍为 SOURCE_BLOCKED / NOT_EXECUTED。issue #16 保持 OPEN，等待 PM 独立验收。**

本 PR 只增加验证脚本和证据，没有修改 `src/`、依赖、子模块或物理计算。它不是父 #1 的最终 fresh 数值计算 review；#4 默认 COM gate、#10 有效 AMI clocks 及父票完成条件继续保留。

## 来源、输入与版本

| 资源 | 类型与原字节 | 原始物理布局（1-based） |
| --- | --- | --- |
| SI-Forum `backplane_25g_xtalk.s8p` | external model；1,439,461 B；50 MHz–50 GHz，1000 点；GHz / S / DB / 50 Ω；SHA256 `454b0a18c6f9c00b37186e3196ff4fd23fef049e1f2a3285b4fa75452f14016a` | header 明确 victim TX+/TX−/RX+/RX−=1/2/5/6；aggressor 原文只写 3,4→7,8。本分析声明 3/7 为 +、4/8 为 − 的邻对同序约定，**没有将其写成原作者逐端口显式极性或测量资格**。 |
| SignalIntegrity `TestWElementTest_testWElement3Pairs.s12p` | external W-element model；279,114 B；0–100 GHz，101 点；MHz / S / MA / 50 Ω；SHA256 `cbf87cf893b869a2eb899e4172e3daec1410829126a49c5d48d3de109bd4483e` | 原 net、WElement circuit 与作者 mixedmode 接线定义 (1+,2−)→(7+,8−)、(3+,4−)→(9+,10−)、(5+,6−)→(11+,12−)。Tx=左、Rx=右是分析方向标签。 |

来源 URL、作者/机构、日期/版本、许可边界、排除候选、检索路线见 [source-research.md](source-research.md)；机器可核对的全部 mapping/双 hash 见 [resources.json](resources.json)。原件、许可证、作者源码及四个重排输入均在本 worktree `local/resources/`，不随 PR 再分发。S8P 未发现明确再分发许可，S12P 源仓库为 GPL-3.0-or-later；本 PR 不重新授权这些文件。旧 `TwoLaneModel.s8p` 原件只保留对照，没有重复运行它或用内部构造 S12P 替代外部文件。

两原件均不符合 PyBERT plain 每四端口一个 lane 的原始布局。计算前已固定全端口 permutation，分别生成 interleaved `(TX+,RX+,TX−,RX−)` 和 grouped `(TX+,TX−,RX+,RX−)` 输入。原件不覆盖；四个转换矩阵与原矩阵按映射逐项 **bitwise exact**，频率与 Z0 相同，详见 [source-applicability.json](evidence/source-applicability.json)。没有模型再生成、裁剪 lane、关 FEXT 或更换易过样例。

| 角色 | 固定 Git commit |
| --- | --- |
| pre | `9a33d08458aa00782e90169c699857b8b19455a2` |
| post | `92c317401e723e13b5a04a809547dc77f4cf8269`（集成 merge `e29f87c177ac89fabdec2d5a34d8e6ea7e7cce7c`） |
| final | `153fcd5a426935387cbdccb1880cabb43f5f4e01` |

三个版本和两子模块均导出到隔离只读 source；实际 `PYTHONPATH`、`module.__file__`、字节 hash 与依赖全清单分别见 `environment-pre/post/final.json`。解释器为 `E:/serial-bus-simulator/.venv/Scripts/python.exe`，Python 3.12.10 / NumPy 2.5.1 / SciPy 1.18.0 / scikit-rf 2.0.1 / PyBERT 11.1.0；共享的是依赖安装，实际 PyBERT/PyAMI/PyChOpMarg 源码明确绑定本票快照。

post 与 final 的整个 `sparam.py` 字节相同，实际 SHA256 为 `aa1dd145b27e326de8add66aed7d268db83a761a33047a2418c85bd432019a10`；pre 为 `4f4955a304aaa330ae2a1b5e98dc7cf1ddf541027d6e3f046df10b8d3dd50c84`。AST 核对：pre/post 只有 `import_freq`、`import_fext` 在所列旧函数中不同；`se2mm/sdd_21`、through detector、插值、`import_channel` 等相同。post/final 的全部所列 importer/helper AST 相同。原 #13 四个相关 test 文件也与 final 相同；旧 49-test 报告仅作源码适用性证据，没有冒充本次新回归。

**Git 与执行字节边界：** 五组 zip 与导出文件逐字节相同；260 个导出文件对 Git blob 为 12 个 byte-exact、248 个仅 EOL 差异、0 个未解释差异。265 条 source 清单还包括五个 zip。实际 CRLF freeze SHA256 是 `a2b85d54e603571a613999bb7f72f86771eb493ceb94b63c0049aa94c7a5ea70`；Git `f1ddcab0` 中 LF 表示为 `9f0b368f7df7428a9621c1310e19104a32d08eeed70b0dd17d13f94179a03023`，两 hash 不相等。运行 guard 使用实际执行文件 hash。离开本机重建时必须核对这种字节差异，不能仅据相同 commit 声称字节相同。

## 计算前冻结与独立参考

首轮冻结提交 `f1ddcab05b6fff8493f9a8c860c75b6b05675b8f`，见 [freeze-v1.json](freeze-v1.json)，早于首个 reservation/验收调用。所有原件/重排/物理 pair、victim/aggressor、两种 through 编号与 renumber、完整 NRZ/PAM4 配置、seed/noise/bit time/eye/ignore 窗口、单位容差、执行 source 与环境、分层预算均已物化。

独立参考不调用 PyBERT 的 mapping/helper：单独解析原 SE Touchstone 完整矩阵，从原物理接线定义 B，每行 +/− 导体系数为 ±1/√2，然后 `Sdd=B·Sse·Bᵀ`。本范围为各 SE port 均实数 50 Ω 的 power-wave 定义，Zdiff=100 Ω，未选 SE 入射波为零；不推广到不等/复数 Z0。每条 through/FEXT 都检查完整差分 2×2 S 矩阵，包含反射和双向传输。参考代码见 [external_lane_reference.py](../../../tools/external_lane_reference.py)。

importer 使用全部原频率点；下游使用 0–40 GHz / 10 MHz 的实际 native 网格，独立参考按预冻结的 magnitude / unwrapped phase 插值及现有带外策略投影。S8 原件没有 DC：native 的带外 transfer 在 DC 为 0，此项不是实测或原件提供的 DC。复数实部/虚部分开采用 rtol=1e−10、atol=1e−12；f 为 rtol=1e−12、atol=1e−6 Hz；phase 仅在双方 magnitude>1e−8 时检查，atol=1e−8 rad。下游时间/电压/精确计数门槛沿用 #2/#3/#4，未事后放宽。

## importer 逐路径结论

每版 15 个 case：2-lane 与 3-lane 的全部 victim、跳过 victim 后的全部 aggressor，interleaved renumber=false/true 与 grouped renumber=true。旧版不要求处处失败。

| 版本 | 完整 case | Through 路径 | FEXT 路径 |
| --- | ---: | ---: | ---: |
| pre | 0/15 匹配物理参考 | **10/15 本来正确** | 0/24 |
| post | 15/15 | 15/15 | 24/24 |
| final | 15/15 | 15/15 | 24/24 |

pre 的五个 interleaved / renumber=false through 有误；其余十个 through 正确，但 FEXT 仍错。post/final 最大 real 误差约 5.375e−14、imag 约 7.139e−14。逐 case / path / matrix / component / phase / f / Z0 的完整判定与失败点分别在 [pre](evidence/pre-importer-report.json)、[post](evidence/post-importer-report.json)、[final](evidence/final-importer-report.json)。完整 complex arrays、原 SE 矩阵、f/Z0 保存为本地 NPZ，由最终 raw 清单逐文件定位和核 hash。

## 必要下游回归

完整配置为 [D-LL8-NRZ](fixtures/D-LL8-NRZ.json) 与 [D-SI12-PAM4](fixtures/D-SI12-PAM4.json)，继承 #4 的固定输入，分别选择 lane0 / lane1，FEXT 为 1 / 2 路。均 Native Tx/Rx、seed=1、非零 PN/RN、nbits=15000、PRBS-7、nspui=32、eye_bits=10160，pkg/window/COM/AMI 关闭；Rs/RL=100 Ω、Cout/Cin=0.5 pF。FEXT 沿用原生 coherent PRBS 假设，不引入新 aggressor 物理模型。

| Case | 窗口 | post→final direct | final direct→实际 fresh Web worker | DFE 错误（pre→post/final） |
| --- | --- | --- | --- | --- |
| D-LL8-NRZ | UI=100 ps；15000 UI；480000 samples；eye=10160 UI；ignore=154880 samples | 72 个 raw arrays，差 0 | 同 72 arrays，84 个分量检查，差 0 | 2439→0/0 |
| D-SI12-PAM4 | UI=200 ps；7500 UI；240000 samples；eye=5080 UI；ignore=77440 samples | 76 个 raw arrays，差 0 | 同 76 arrays，89 个分量检查，差 0 | 5080→0/0 |

独立映射参考核对实际 `chnl_H_raw` 与各 `fext_i_H`；冻结 Rs/RL 与差模 Z0 相等，因此 FEXT 的 native 端接 renormalization 为 identity。post/final/worker 的五条 frequency response 最大 complex 误差约 7.03e−16。实际端接/trimmed channel、FEXT h/H/各路电压、base noise、总干扰及相应 t/f/trim window 均保留；base+各 FEXT 按原顺序求和与 native total **exact**。所有输入 identity、worker resource hash、窗口、FEXT ns 轴均通过保存数据核对。

pre 两例均正常完成 producer，但其错误 FEXT 返回 native trim start index=−1：轴状态保留为 `UNKNOWN_INVALID_NATIVE_START_INDEX`，没有把 t[-1] 伪装成有效起点，也没有修旧输出。pre→post 分别有 54 / 59 个 raw 分量检查不同；这些是修复影响观察。短序列 DFE 数字仅说明这两个固定输入的行为，不构成测量、BER 尾部、硬件资格或全场景改善结论。原 native jitter covariance warnings 继续保留，未因整体回归而认定其拟合尾部有效。

实际 worker 是最终 source 的 `Tasks → run_worker`，每 case 一个 manager、一个 spawn process，以免两个成功 run 的生产缓存淘汰原件。两 task ID：`45ba1960-2b0f-4be7-8ddf-98cbb1f5fbe8`、`f7bf38da-47be-4c2d-b198-263fde160678`；state=succeeded、exitcode=0、worker_exited=true，均已实际 join。无 cancellation request/observed。本票没有 Chrome UI 重测。

全部保存数据核对、逐例差异与完整 worker manifest 在 [saved-data-report.json](evidence/saved-data-report.json)、[NRZ manifest](evidence/D-LL8-NRZ-worker-manifest.json)、[PAM4 manifest](evidence/D-SI12-PAM4-worker-manifest.json)。该报告只核对本票的 72/76 个 native raw 字段及相关 metadata，不声称重新验收 worker 的全部其他图表或分析数组。

## 尝试、成本与可复核边界

| 层 | 实际调用 / 成本 |
| --- | --- |
| importer 独立 batch | 45 `import_freq` +45 `import_fext`；另外 45 次独立 skrf reader 核对；三版 case 总 elapsed 约 1.781 / 1.769 / 1.781 s（不含进程导入启动） |
| Native direct | 8 Main，其中首 pre 两次采集失败、其后批准重试两次；累计 direct elapsed 38.991 s，含构造、执行、采集 |
| 最终 Web worker | 2 Main；parent 含 spawn/exit+join elapsed 18.964 / 12.008 s；child elapsed 14.472 / 7.654 s，二者不重复相加 |
| 总 Main | **10/10**，原 cap8 + PM 明确批准的 +2，仅补同两例 pre raw 采集；无未登记重跑 |
| native 端口调用累计 | 独立 batch 外，10 Main 各有 `import_freq`/`import_fext` 一次；因此两者全票各 55 次。helper 内部子网络/插值不是额外 Main。 |
| 构造 | direct 8 个 PyBERT；worker 各 2 个（其中一个用于生产 validate 默认快照）；静态字段检查/报告/字节审计为 0 个 |
| COM/coopt/AMI/binary | numerical COM=0、coopt=0、AMI_Init/GetWave=0、binary load=0。每 Main 的 `compute_com` disabled early-return 入口单列；初两份原 `COM:1` 标签保留，不能误写成数值 COM。 |
| 峰值 / 存储 | peak RSS **UNKNOWN**；原始输入、source、失败、输出与中间报告约 300 MB，低于冻结 2 GiB cap。最终清单按实际字节记录。 |

首冻结脚本曾因错误引用不存在的 #3 metadata 文件失败，2.975 s、0 acceptance/0 Main；原 staging 保留，详见 [preparation-attempt-1.json](preparation-attempt-1.json)。

首次 pre 两 Main 均 Ready 后，owner 的采集脚本误把 `tx_out` 当波形 trait；两份 capture_failed 原报告/partial NPZ/effective input/成本全部保留。修正只改采集字段与 COM 计数标签，见 [capture-amendment-v2.json](capture-amendment-v2.json)（`2b829c5e`）。PM 读取原件后明确批准 +2；额外调用前提交 [budget-amendment-v3.json](budget-amendment-v3.json)（`5ec0cdd`），原 ledger 不删，每次 retry 独立 `pre-capture-retry-v3` 身份。无引擎 AST 核对各版全部 61 个采集字段，missing=0，见 [字段检查](evidence/no-engine-capture-fields.json)。

保存数据 analyzer 还发生一次 boolean subtraction 的纯分析错误（2.638 s、0 Main），原源文件与错误保留；后来只将 boolean 转 int8 做预冻结 exact 比较，未变容差或物理参考。另一份中间报告曾将 pre 已知无效 trim 轴误并入 corrected-scope 总判定；原报告本地保留，最终按 pre failed/UNKNOWN 与 post/final 判定分别列示。所有数值原件未重写。详见 [分析失败记录](evidence/report-analysis-attempt-1.json)与 raw 清单。

运行方式为 `uv run --no-project --python E:/serial-bus-simulator/.venv/Scripts/python.exe python tools/verify_external_lanes.py <mode> <version>`；`environment` 不构造引擎，`importer/direct/worker` 消耗一次性 scope ledger，已消费的条目拒绝再次运行。当前 run 记录已耗尽预算，不因给出命令而授权重跑。保存数据可用 `tools/report_external_lanes.py` 复核，source/重排可用 `tools/audit_external_sources.py` 复核；两者 0 Main / 0 importer。

主 checkout、前序 owner worktrees、ignored raw 和历史失败未改动；没有启动历史 COM、没有服务常驻、没有清理/归档任何原件。硬件实测、任意 pin map、未测 victim 的下游全矩阵、其它速率/package、IEEE/Matlab correlation 与有效 AMI clocks 均没有被本票升级为通过。

Owner fresh 自审见 [self-review.md](self-review.md)：Standards 0；Spec 发现验证工具 selector/reservation P2，已通过 CLI/ledger 前拒绝 selector 修复，0 Main 回归与独立增量复核关闭。实际已执行批次没有 selector，不影响原结果/成本。最终原件逐文件清单见 [local-artifacts-final.json](evidence/local-artifacts-final.json)，包括后来补存的执行 driver 源码与未改写的中间报告；PM 正式 final review 另行进行。
