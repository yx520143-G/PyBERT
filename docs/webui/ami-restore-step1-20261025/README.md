# AMI 原流程恢复：第 1 步实施记录

2026-10-25。范围：最终修改清单 **R1/R2**，以及恢复后必需的来源标签和合法空 clocks 分流。本步不实施 F1–F6；真实 AMI 验收继续暂缓。

## 修改结果

- `run_ami_model` 使用单模型主体：一次 Init → 现有 `get_responses(bits_per_call=40)` 的两次 probes → 同一 handle 上 Main → 取得宿主拥有的返回值 → `finally Close`。删除 C1 重初始化分支及孤立 helper。
- Rx caller 不再传入 `_probe_seed=self.seed`。现有 PyAMI `get_responses(rng=...)` 可选接口不变；默认仍是无参数 `default_rng()` 私有 entropy RNG，Main 的全局 seed 策略不改。
- Main 的 `bits_per_call=0` 继续继承 probes 后的 40；非零请求原样传给既有 wrapper。channel/FEXT、probe 输入及其长度、第二次 probe 的 convolution 均沿用既有实现。
- 正常返回前复制结果；Init、probe、Main、复制或中断异常都经过最终清理。原始异常单独发生时继续传播；若清理也失败，`_AMICleanupError` 分别保留 `primary_error` 和 `cleanup_error`。不自动重试或重新 Init。
- 来源改为 `same_init_after_probes`，invocation 标识不冒称模型 Init epoch。合法空 clocks 在 origin guard 之前回退 Native；请求非空同 epoch clocks 时以 `unsupported_origin_mapping` 明确失败，等待独立 F5 映射。没有静默换用 Native 或猜测原点。

生产修改只有三个文件：`src/pybert/utility/ibisami.py`、`src/pybert/models/bert.py`、`src/pybert/utility/ami_clock.py`。测试修改为新增 `tests/test_ami_single_init.py`、扩展 `tests/test_ami_clock_traits.py`。既有 `tests/test_ami_getwave_params.py` 只运行，不修改。

保留 status 检查、handle 所有权和幂等 Close、有效 clock prefix／sentinel、NaN 输出缓冲预填、raw clocks 单调性、tuple/string 参数兼容、Traits Dict 写入等既有修复。本步没有修改依赖、submodule、native GUI、Web/raw6 reader 或其他计算公式。Close 返回码与输出指针缺口仍归后续 F1/F2。

## 验证与证据边界

[完整定向测试输出](targeted-tests.log)（保存时去除行尾空格）：**40 passed，15 subtests passed**，35 条既有依赖弃用 warnings；`git diff --check` 通过。

| 验证 | 已检查内容 |
|---|---|
| 真实包装代码、Python ABI 替身 | 未加载任何 AMI DLL；实际执行当前固定 PyAMI 的 initializer、get_responses、getWave 分块与 Close 包装代码 |
| 原适应历程 | Ignore_Bits=23、4 samples/UI；两个 probes 各 172 samples，分别分为 160+12；同一 handle 和状态累计到 Main，第二个 probe 复用首个 probe 的输入并作原 convolution |
| Main 分块 | 166 samples；B=0 时 160+6，B=7 时 28×5+26；无 padding、截断或重发 |
| RNG／caller | 替身捕获默认 RNG 工厂确为无参数调用；全局 RNG 状态不变；执行实际 Rx caller 两条 AST 语句，确认无自动 seed 参数且来源标签正确 |
| 生命周期 | Init／两 probe／Main 的失败、双重异常、仅 cleanup 失败、复制失败、中断；最终 Close、无重新 Init／自动重试；返回数组在 Close 前取得独立副本 |
| 共享 helper | Init-only 及 FEXT 长短行准备，保持原缩放、padding／截断与 convolution |
| clock／Traits | 普通 dict 和真实 Traits Dict；合法空 clocks 不要求 origin 映射，非空未映射 clocks 不消费，原 malformed／采样／Eye／partial 检查继续通过 |
| 参数兼容回归 | 原 12 个参数测试及 15 个子测试，包括 750 条历史返回字符串，未改历史测试 |

第一次红测为 15 failed / 9 passed，其中 caller AST 选择器先选到了另一个 Rx 分支，属于测试定位问题；修正选择器后单独红测确认目标 caller 仍传 `_probe_seed=123`。产品修改后先 36 项通过，补齐共享 helper／中断测试后最终 40 项通过。

这些结果证明本步宿主调用与错误处理合同，不证明真实模型的训练状态、隐藏全局状态、BER、时钟映射或结果资格。未执行真实 AMI、完整 Main 仿真、COM、GUI/Web 端到端，也未重跑旧重型审查。Ruff／flake8 在本次现成验证环境中未安装，未为本步安装依赖；不宣称完整仓库 lint 通过。

## 固定来源与复跑

- PyBERT base：`ab36b656a61cb6866da98105d72f6cacfb118031`，tree `8412b639f4dd6f51c227e19d649a333fbad9d6a2`；分支 `codex/restore-ami-single-init`。
- PyAMI：`d6d1f7fe7e58536546a1cfb9430c750cc2cb103e`；运行源 `E:/serial-bus-simulator-dependencies/pybert-issue30-probe-main/PyAMI/src`，`ami/model.py` SHA-256 `0e5a18c6d3402f10e2fb85af147f6ee961e5c67ae21fec555b1842f51a870442`，与该 HEAD 一致。
- PyChOpMarg：`ca905e793fcf6330929471317ca32e7611578e5d`，使用下列现成工作树的源码，未改动。
- Python 3.13.15，pytest 9.1.1，NumPy 2.5.1；已核对实际模块路径指向本次 PyBERT 工作树和上述固定依赖。

```powershell
$env:UV_OFFLINE='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONPATH='C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator/src;E:/serial-bus-simulator-dependencies/pybert-issue30-probe-main/PyAMI/src;C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/PyChOpMarg/src'
& 'C:/Users/yx/AppData/Local/SerDesEqualizationExplorer/t06-candidates/9a75bfd50f2e8bf56b036e92d9923b2274c7babb/venv/Scripts/uv.exe' run --no-project --python 'C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/.venv/Scripts/python.exe' python -B -m pytest -q tests/test_ami_single_init.py tests/test_ami_clock_traits.py tests/test_ami_getwave_params.py -p no:cacheprovider --tb=short --disable-warnings
```

复跑目录为 `C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator`。未用当前未初始化 submodule 的路径代替实际依赖来源，未触发 uv sync／安装。

| 最终审查候选文件 | SHA-256 |
|---|---|
| src/pybert/utility/ibisami.py | 6c919116d4e8d1736e53de7e1f573f003ba5c547aa46f69b9133998b08307402 |
| src/pybert/models/bert.py | f56b4bf73853fd50d79c049053d66b839656a4d2ef899ba11c924bd162371e2c |
| src/pybert/utility/ami_clock.py | 93dbda66f8dc8887847fb5062ff22c8b30fcee145b7213f059b437fe955064f6 |
| tests/test_ami_single_init.py | 8edc3ca11efe1af7bceca2a87a8b3dafa318e08ff1b43fc0a7723eac52c04cf9 |
| tests/test_ami_clock_traits.py | f53474b20c2693c7144499d757329d4612d3912c121cbd375d89363e2c5ef49b |

同一个 Astra 的独立审查见 [astra-review.md](astra-review.md)。此前 `fresh-algorithm-review-20261025` 下七份文件的 SHA-256 已逐一复核未变，历史失败、raw 数据和归档未重写。
