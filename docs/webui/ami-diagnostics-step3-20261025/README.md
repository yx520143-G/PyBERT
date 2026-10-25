# 第 3 步 F3/F4：参数历史与 GetWave 错误分层

2026-10-25。只实施最终清单的第 3 步；F5/F6 和真实 AMI 验收继续暂缓。同一位 Astra 已完成 Standards／Spec 两个维度的独立审查与定向复跑：三个 P2 均已修复并复核关闭，最终未关闭 findings 为 0。这不代表真实模型资格通过。

## 固定来源与范围

- PyBERT 基线：`23c72c512a3ef2068dfa268b192df12799d42bc7`，tree `aae548ee948a5ac9188f97b49543ef7b810d44c3`。
- PyAMI 基线：`86f9d92de7b7ba8ad9a76d32337acdf2975a8111`。本步候选：`207bd902ee1e344c9f9053e8150ced8ac143b14d`，tree `ef9f093881259a8e3f1955524804142094de5593`。
- 工作目录：`C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator`；沿用既有父仓库／嵌套 PyAMI 工作分支。
- 产品代码仅 `src/pybert/models/bert.py` 与 `PyAMI/src/pyibisami/ami/model.py`。父仓库同步 `PyAMI` gitlink、`pyproject.toml` 的 direct URL SHA；`uv.lock` 保持 editable workspace 来源，版本仍为 10.0.0，没有重新锁定或安装依赖。
- 测试仅修改既有 `tests/test_ami_getwave_params.py`、`PyAMI/tests/ami/test_clock_lifecycle.py`，新增 `tests/test_ami_parameter_projection.py`；其余新增文件为本目录报告和验证记录。
- 第 1／2 步报告、最终清单所在目录七个原件、原生 DFE/CDR/Viterbi、GUI、Web、raw6 validator 和旧数值证据均未修改。

父子提交均为本地 checkpoint；远端没有发布新依赖提交，没有验证远端安装。

## F3 的行为与实际消费者

`getwave_parameters()` 保留 parser tuple 修复、完整 tuple path、root／重复路径／混合结构／语法错误识别。生产 Rx 调用传入实际 `AMIParamConfigurator`：按声明取 Out/InOut 的必需叶节点，并核对根名；必需叶缺失、空值、非叶结构或不能转换的必需数值仍抛错。解析器曾跳过声明时，不声称已验证完整的必需输出集；仅空 `Model_Specific` 容器触发的已知 parser warning 不当作丢失声明。

辅助 numeric path 只有每次调用均可用才发布完整历史；仅某次缺失或不可转换时，整条辅助历史 unavailable，其余独立历史仍保留。不补零、不截断、不把 String／Boolean／Table 强制投影成浮点 tap 列。Table 行数变化不会因为统一数组形状要求而失败。本 helper 不是完整的 AMI 参数符合性验证器，未新增完整 Type／Format／范围验证。

仅同一父路径下、声明为 Type Tap 且位置名为整数的单组列可能形成矩阵，按位置排序；同次列长不齐则该矩阵 unavailable，多组不会被拼成一个矩阵。名字包含 `tap` 本身不构成分组依据。历史保存的 750 个参数字符串保持原件，五条 numeric history 的全部值、首末值仍核对；旧测试中仅靠名称推导矩阵的预期已按 F3 更新。

实际 Rx Main 将 `parameter_history` 存入既有 `ami_clock_info`：包含 `parameter_strings`、不可用路径、tap 矩阵状态与原因。这里的 strings 是 `getWave()` 返回 API 的字符串，可能包含既有 NULL／空内容的 root-only fallback，不能冒充 DLL 原始字节。原始 `params_raw` 仍保留在 PyAMI 的每 C call 记录中。

该处 tap history 随后会被 native DFE 返回值或 AMI-clock 分支的空反馈覆盖；CDR UI history 会被所选时钟消费者覆盖。因此移除了这一处无时间轴依据的 repeat／zero-pad 展示投影，避免辅助历史造成无关失败。模型 lock history 可用性仍单独记录；native DFE 继续给出其自身 lock trace。AMI timed 分支不会因此获得伪造的 lock trace，其非空同 epoch clocks 仍因 F5 未完成而 unsupported。这里未把 AMI tap/CDR 历史改作下游数值配置。

参数树与 Out/InOut 的依据为 [IBIS 6.1 第 202 页](https://ibis.org/ver6.1/ver6_1.pdf#page=202)；Table 使用展开后的叶值、至少返回一行及允许行数变化见 [第 197–198 页](https://ibis.org/ver6.1/ver6_1.pdf#page=197)。本步拒绝 declared Table 的空 payload／嵌套结构；没有实现完整列数／列类型符合性检查。这些条款没有把 numeric projection 的全路径集合或所有带 tap 名字的字段规定成同一个矩阵。

## F4 的行为与限制

GetWave 的既有记录增加发生阶段和 failure kind，区分：C 前准备、原生调用边界未知、失败返回码、clock 接口失败、成功返回后的宿主捕获／解码／结果组装，以及取消。`_epoch_failed` 的含义是无法安全继续该 epoch，不再以它推断模型内部状态已损坏。

- 首个 C 调用前的普通输入准备失败：没有新样点消费，不污染 epoch；调用者修正输入后可显式再次调用。代码不自动重试。
- 本次 Python 调用已有成功 chunk，之后准备失败，或 C 中进度未知：停止续跑，保留此前记录；不重发已处理输入。
- 非 1 status 和非法 raw clocks：保持失败与停止策略。跨 C chunk／Python call 的单调检查、NaN 预填、sentinel 检查不变。
- status=1 之后参数捕获或 UTF-8 解码失败：记录为宿主返回后错误，保留可独立复制的 wave、clock buffer 和原始参数字节。参数接口是否有效无法确定时仍不返回完整成功 tuple，不把 malformed 输出自动降为 warning。
- wave／clock／params 分项捕获，后项失败不抹去已取得的前项；原生异常或明确失败码与附加 capture 错误同时发生时，保留原始原因和附加错误。
- `completed_samples` 只累计本次 Python invocation 内明确 status=1 的 C 调用样本数；不是未返回／失败 C 调用实际消费量的证明，也不是 F5 所需跨 probes/Main 的完整 epoch 账本。
- 取消照常传播并停止；原有单 Init、两 probes 后同 handle Main、最终幂等 Close 不变。

F3 的辅助数值历史可 unavailable；F4 的必需接口输出或进度无法安全确定仍停止。这两个层次共同避免把可选历史问题与 DLL 执行失败混为一谈，没有新增通用事件／状态框架。

## 验证

本轮执行 152 项定向测试及 15 个子测试，全部通过：

| 层 | 范围 | 结果 |
|---|---|---|
| PyAMI | `test_clock_lifecycle.py`、`test_response_rng.py`，Python callbacks 代替 DLL | 83 passed |
| PyBERT | 新参数声明／投影、旧 parser/raw fixtures、单 Init 编排、Traits clock record | 69 passed + 15 subtests |
| 类型检查 | PyAMI `model.py`，沿用当前环境 | 0 issues |
| Ruff | 父仓库 13 条、子仓库 29 条 | 均为基线已有诊断；子基线为 30 条，新测试文件 0 条；不声称全库 lint 通过 |
| 差异和文本 | 两仓库 `git diff --check`，候选文件 UTF-8 without BOM，旧原件 hash | 通过 |

初始 red 记录：新增 F4 的 7 个阶段测试失败，旧 56 项 lifecycle 通过；新增 F3 夹具首次缺少规范保留字段，修正夹具后 16 项在旧函数缺少声明／observation 接口处失败。随后实现与定向修正为 green。新增的后续测试覆盖附加捕获失败、失败码＋捕获双错误、实际 Rx 调用语句在普通 dict／Traits dict 下保存观察，以及 declared Table 不隐藏混合结构。父任务自查另修正空 `Model_Specific` 容器误拒绝；该测试首次过度假定 warning 列表仅含一项，随后改为验证指定 warning 存在并测试实际投影结果。

实际导入已核对为本 worktree 的 `src/pybert/models/bert.py` 和 `PyAMI/src/pyibisami/ami/model.py`；Python 3.13.15、pytest 9.1.1。使用原有 issue4 环境、离线且不安装依赖。完整真实 Main、真实 AMI DLL、COM、GUI／Web 未运行；既有 35 条依赖 deprecation warnings 保留。[验证记录](validation.log)含父测试结果节选、完整子测试输出、类型和 lint 对照；仅规范化行尾和去除尾随空格。

复跑环境与命令：

```powershell
$env:UV_OFFLINE='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONPATH='C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator/src;C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator/PyAMI/src;C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/PyChOpMarg/src'
$step3Uv='C:/Users/yx/AppData/Local/SerDesEqualizationExplorer/t06-candidates/9a75bfd50f2e8bf56b036e92d9923b2274c7babb/venv/Scripts/uv.exe'
$step3Python='C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/.venv/Scripts/python.exe'
# 父 worktree
& $step3Uv run --no-project --python $step3Python python -B -m pytest tests/test_ami_parameter_projection.py tests/test_ami_getwave_params.py tests/test_ami_single_init.py tests/test_ami_clock_traits.py -q
# PyAMI 子目录
& $step3Uv run --no-project --python $step3Python python -B -m pytest tests/ami/test_clock_lifecycle.py tests/ami/test_response_rng.py -q
& $step3Uv run --no-project --python $step3Python python -B -m mypy src/pyibisami/ami/model.py --follow-imports=silent --ignore-missing-imports --no-incremental
```

## 最终候选 SHA-256

Astra 指出三个 P2，并分别先复现再修复：其一是必需非 Table 数值叶被错误返回为行结构时，会落入辅助 history unavailable，现已在声明叶处明确拒绝；其二是同组已声明数字 Tap 与普通命名叶共存时，被 parser 的 list／tuple 表示差异误判为 mixed，现按声明识别这些子叶；其三是 declared Table 的空 payload／子分支／嵌套行被提前跳过，现明确拒绝，合法正例使用真实 wire 格式 `(table 1 2)` 与 `(table 1 2 3 4)`。真正未声明 Table row 混入 branch、atoms／children 混合仍拒绝。三组回归和完整父定向套件均 green，同一审查者已独立复核关闭。

| 文件 | SHA-256 |
|---|---|
| `src/pybert/models/bert.py` | `e99b7b68495581d3da8c55aa7af30136c5960672456f69a02fa45e72b1206e5a` |
| `tests/test_ami_getwave_params.py` | `b70241e27652b4bf1164db9f4cb7ba4bcbb2482c5ebc6df29beb773b8813c50f` |
| `tests/test_ami_parameter_projection.py` | `e8aaf12c3750879451f1f0b3029169f6cb59f422519fe4e183b399141c1ce148` |
| `PyAMI/src/pyibisami/ami/model.py` | `0defb0bfea016a5bf9d29e1b77643cc43c87d2cfb2b2c5a9681b350abd6863ed` |
| `PyAMI/tests/ami/test_clock_lifecycle.py` | `c12ddbacb4ae7309541ab5d058a117c3976943aed41d34b461d3b14e5c8f2380` |
| `pyproject.toml` | `215daf0d03dacbcd94dc3ebef822aa19e1904432d9bd66625734a876e6655248` |
| 未修改的 `uv.lock` | `cc21cb7dd84c9729a6a2fedfda297af9fb195c0dd7e05a24f89fb7db87be4b12` |

原始约束见 [最终清单](../fresh-algorithm-review-20261025/final-modification-checklist.md) F3/F4；[Astra 审查报告](astra-review.md)由同一位审查者单独填写。当前提交固定的是软件行为，不是实际模型数值恢复验收。
