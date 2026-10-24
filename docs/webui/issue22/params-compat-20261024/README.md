# #22 Rx GetWave 返回参数兼容修复

日期：2026-10-24（Asia/Shanghai）。对应 [live issue #22](https://github.com/yx520143-G/PyBERT/issues/22)，派发时正文保存在 [issue22.json](issue22.json)。本票只处理方案 A；**有效 NRZ/PAM4 AMI clocks 仍 BLOCKED**。

新 worktree：`C:/Users/yx/.codex/worktrees/pybert-issue22-ami-params/serial-bus-simulator`，分支 `codex/pybert-issue22-ami-params`。指定起点 HEAD `98f30f871aaf6e1a277317096c68295890c92a79`，tree `ca9655f64f1caa745156791ac7c3c51d327c8800`；该起点在 master `b96977a` 上仅增加四份封存调查材料。managed 工具最初创建 detached HEAD，随后在修改前显式创建以上分支，HEAD/tree 不变。

## 修改与消费合同

生产入口为 `src/pybert/models/bert.py::getwave_parameters(params)`；Rx GetWave 原分支直接调用它。函数仍调用原 PyAMI `ami_parse`，没有新增 grammar。测试只抽取该**实际生产函数 AST**，不导入 PyBERT 或 PyAMI 模块。

| 输入／边界 | 明确结果 |
|---|---|
| 固定 parser 的 `(name, values)` tuple 树 | 按实际 tuple/list 类型访问，数值 atom 仍经 Python `float` 转换 |
| 嵌套数值、不同路径的同名 leaf、名字中含点号 | 使用模型根以下的完整 tuple 路径；不拼接或覆盖，模型根名称不成为参数 key |
| 根层 `cdr_locked/cdr_ui` 数值 | 调用处四处键查找改为单元素 tuple；之后的 repeat、resize、占位和状态语义保持原代码 |
| tap 名称 | 各路径分量做大小写不敏感的 `"tap" in name.lower()`；按完整路径 Python 字典序排序，根层名称仍是原本大小写敏感的字典序，不按编号自然排序 |
| 无调用、空 root、空/纯空白返回字符串、无 taps | 不生成 tap 行；空白返回表示本次没有可用数值参数，不添加伪 root 或数值 |
| 空 leaf、非数值 leaf、数值与文本混合的 atom leaf | 整个值不可用，从数值字典省略；不丢文本后仅取部分数字 |
| parser 产生的 Table plain-list rows | 整值不可用，不将行号/列压成数值参数或 taps；按返回类型处理，不仅凭参数名称判断 |
| 同一 node 混合 named children 与 atom/row | 明确 `ValueError`，带参数完整路径；不推测树结构 |
| 重复完整路径（包括数值与非数值重复）、多 call 根名改变 | 明确拒绝，防止覆盖或混合不同模型返回树 |
| 后续 call 新增/缺失数值路径、数值路径变成不可用 | 整组拒绝并列出 call、missing/added 路径；不保留不完整 tap 历史冒充完整输出 |
| 同一 call 各 tap 列长度不同 | 明确拒绝；在已验证等长后才转置，不按最短长度截取、补零或广播 |
| 不同 call 的共同 tap 长度变化 | 允许，逐 call 对齐后追加原数值；即使总长度相同，单 call 不齐仍拒绝 |
| 非空非法语法 | 原 parser 异常继续传播；没有更换或扩展原 grammar 的语法边界 |

数值路径一致性是本次纯消费者支持的明确边界，包含非 tap 数值参数；未实现可选参数的稀疏历史或自动恢复。非数值/空/Table 省略不代表模型没有输出原文，原始 `params_out` 继续由原采集路径保留。本函数不生成逐样本时基，返回的 tap 行只是原返回数值的历史，不宣称已对齐真实 waveform。

只删除因本次移动而无用的 `AmiLeaf/AmiNode` import；既有 `AmiFloats` 等无关代码未清理。未改 PyAMI、gitlink、依赖、`run_ami_model/get_responses`、模型状态、随机性、调用顺序、时基、clocks 数量/值/容差/窗口、pairwise/采样/入口谓词或 Web metadata。

原 lock/UI 缺失时的占位、Ignore_Bits 派生 lock、clocks 分支清空 taps、Tx GetWave ParseError、buffer 聚合、响应探测状态共享与合法 fixture 缺口均继续保留在 #10，不能由本票结果提升资格。

## 红→绿及证据适用性

先把原 375–407 参数消费块原样提取到生产纯函数，未先修 bug。[verify_scope.py](verify_scope.py) 比较 baseline 原块与 red 函数体 AST，确认完全相同；red 的 caller 只是调用该函数。原始完整 baseline 源保存在 [source/baseline-bert.py](source/baseline-bert.py)。

每一批保留实际 `bert.py`、测试文件、runner、完整 tests.log、receipt.json 及 SHA256。不会用最新代码冒充早期批次执行源；后续绿色不会覆盖红灯。

| 批次 | 实际结果 | 纯 grammar 次数 | 内部 elapsed s |
|---|---|---:|---:|
| red-01-original | 1 test，direct/worker 两个 `.name` 错误；另原 tap lambda 对保存的 dfe_tap1 报 str.tolower | 751 | 0.404908300 |
| red-02-source-lines | 相同红灯；改进 loader 保留真实源码行号后重验 | 751 | 0.334139300 |
| green-01-saved | 同一实际 750 份字符串测试通过 | 750 | 0.351883700 |
| red-03-value-boundaries | 5 tests，3 errors：非数值、无调用、混合 node | 9 | 0.263262300 |
| green-02-value-boundaries | 6 tests 通过，含真实 750 份字符串 | 759 | 0.455407700 |
| red-04-history-shapes | 5 tests，8 subtest failures + 2 errors；暴露缺失/新增、重复、错位、root 边界 | 18 | 0.401900200 |
| green-03-history-shapes | 11 tests 通过 | 777 | 0.677745000 |
| red-05-blank-output | 1 test，空字符串按原 parser 报错 | 1 | 0.028859500 |
| green-04-complete | 12 tests 通过 | 780 | 0.393269300 |
| green-05-review-candidate | loader 去除仅红灯需要的 dataclass/NumPy、换行调整后，同一 12 tests 通过 | 780 | 0.414497600 |

第一批 loader 通过 `ast.unparse` 编译函数，因此 traceback 显示的文件名正确但行号偏移；该原批保留，red-02 改为直接编译原 AST 节点，提供正确行号。原 tap lambda 的独立诊断使用从真实首条参数串解析的名称，直接执行原生产 lambda，没有手抄筛选修复当 oracle。750 字符串来自旧失败 direct/worker 各 375；其 tap 首末值使用已保存原文中的独立字面量验证。

这些是 12 项独立测试的演进批次，不将各批通过数相加作为覆盖数。所有 10 批累计纯解析 5376 次，测量的批次内部 elapsed 总和 `3.725872899958631 s`；这不是整个任务的 wall time。准备命令及提交检查失败单列在 [preparation-failures.txt](preparation-failures.txt)，不算产品红灯或模型调用。

当前生产文件 SHA256：`67aa464abc4f6e78dc72527aa9cf00ec3151125c8a66f4e79bc95c1a68571b7a`；green-05 测试 SHA256：`764767955114fd4e2565da6bf4f9c5f0432fb54b10986e9155ce8f241c9df308`；runner SHA256：`214bd0f581bd61fbf3af60e12dc4d17282c62d1a5df779ddd8abd9a09feb8835`。

## 固定来源与零引擎验证

固定 PyAMI gitlink：`5270d713e40bac2be5747bef09b92df79df9085b`；PyChOpMarg：`ca905e793fcf6330929471317ca32e7611578e5d`。本 worktree 未初始化或更新 submodule。

测试使用 [固定 parser.py 原字节](source/parser.py) 的 85–143 行纯 grammar；其 SHA256 `2c2e688e3257476d38c175bcd37bb8050b253ad822139c55001eff920ba65594`，与封存旧 worktree 一致，原 [PyAMI LICENSE](source/PyAMI-LICENSE) 一并保留。来源为封存 worktree 的 `PyAMI/src/pyibisami/ami/parser.py`，对应 [固定上游源码](https://github.com/capn-freako/PyAMI/blob/5270d713e40bac2be5747bef09b92df79df9085b/src/pyibisami/ami/parser.py)。这份副本是测试来源快照，不是新的生产 parser。

实际解释器复用 `C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/.venv/Scripts/python.exe`，Python 3.13.15、parsec 3.17。所有 shell 命令均经 `uv run --no-project --python <该解释器>`。不安装依赖，不设置产品 PYTHONPATH，不导入会带入引擎的包。

本票的常规测试 seam 已在 live #22 中明确授权。用直接 unittest runner 绕开 `tests/conftest.py` 中会构造/运行 PyBERT 的仿真 fixtures，不跑通用全套或旧矩阵：

```text
uv run --no-project --python <既有解释器> python docs/webui/issue22/params-compat-20261024/run_batch.py <新的批次名>
uv run --no-project --python <既有解释器> python docs/webui/issue22/params-compat-20261024/verify_scope.py <新的核验文件名.json>
```

批次和核验输出路径必须不存在，防止重放覆盖原件。[scope-review-candidate.json](scope-review-candidate.json) 另外确认：

- 原参数块提取 AST 完全相同，红灯来源确为原生产逻辑。
- 排除新 helper、原参数处理块、两项失效 import，并仅规范化四处根层 key 查找后，剩余**整个模块 AST** 与 baseline 相同，涵盖全部数值和 clocks 代码。
- 原调查四文件逐 Git blob/磁盘 bytes 相同，原七个输入 hash 仍相同。
- 每批实际 source/test/runner 的保存文件与 receipt hash 全部一致；每批真实调用账全为 0。

本新证据目录的局部 `.gitattributes` 使用 `* -text`，只为保留原字节；不改根属性文件或旧证据换行。正常源码和测试继续遵循仓库文本策略，所有新文本均 UTF-8 without BOM。

全文件 `diff --check` 曾对原始 unittest tests.log 的尾空格报 exit 2。保留原日志后，仅排除本票 `*/tests.log` 原件检查其余 staged 文件；不转换或删除失败日志来通过检查。局部 `.gitattributes` 被根 `.gitignore:114` 的 `.*` 忽略，已仅对该新文件显式 force-add，其他 ignored 内容未动。

## 成本、评审与交接

| 本票新增项目 | 实际 |
|---|---:|
| Main / COM / coopt（含候选） | 0 / 0 / 0 |
| AMI_Init / AMI_GetWave / AMI_Close | 0 / 0 / 0 |
| AMI 真实库加载 / 引擎构造 / 原生数值 helper | 0 / 0 / 0 |
| 模型下载 / 编译 / 新 fixture | 0 / 0 / 0 |
| 纯 parser 次数（10 个已保存批次） | 5376 |
| 已测批次内部 elapsed 总和 | 3.725872899958631 s |
| 全任务 wall time / peak RSS | UNKNOWN，未连续测量 |

只读 Standards/Spec 自审已完成，两轴各 0 findings，未重跑 parser/测试或引擎。详见 [review.md](review.md)：固定候选 `80100e262e433076396819e3d29aedc20bdad30a` / tree `6d283adc05ff6c7fd76c4e67c4ee724c55084b7d`。之后只增加报告和交接文档，green05 的生产/测试/runner hash 均未变；不扩大回归。

最终 Draft PR、HEAD/tree、停止写入与返权状态由最终交接消息固定；本报告不自引用提交 hash。不得自行 merge/关闭 #22/#10/#4/#1。
