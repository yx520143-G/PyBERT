# AMI 接口补齐：第 2 步 F1/F2

2026-10-25。本步只补齐 Close 返回状态检查和 `AMI_parameters_out` 初始化。第 1 步的一次 Init、原两次 probes、同 handle Main、最终 Close 及取消自动 probe seed 绑定均保留。**真实 AMI 验收继续暂缓；F3–F6 未开始。**

## 修改结果

**F1：Close 状态。** 将 C `AMI_Close` 返回类型明确为 `c_long`，在 `last_close_call` 中分别记录 `status` 与 `returned`。仅返回 1 时正常结束；0 或其他非成功返回进入既有 `AMIModelError`。Python 调用异常时 `status=None / returned=False`，失败码返回时保留实际状态且 `returned=True`。继续在调用前放弃 handle 所有权，重复 Close／析构不重试。Init 失败与清理失败仍分别保存。成功码不会被标作物理释放已验证，`release_status` 仍为 `not_verified`；失败时仍为 `unknown`。

**F2：参数输出指针。** Init 时使用 `c_char_p(None)`；每一个 C GetWave chunk 调用前清空其内容为 NULL，含短末块和下一个 Python GetWave 调用。这样模型未写参数或失败前未写参数时，不会继承上一次返回。现有 observation 的 `params_raw` 保留 NULL、空 bytes、实际 root-only 字符串等区别；公开字符串接口仍保留原 root-only fallback，并在 docstring 中明确其含义。零长度 wave 没有 C 调用，因此不清掉上一观察值。

接口依据为 [IBIS 6.1 §10.2.3，第 185、189–190 页](https://ibis.org/ver6.1/ver6_1.pdf#page=185)。本次对象为参数输出指针 `AMI_parameters_out`，不扩展为所有输出参数或完整 ABI 重构；未更改 `msg` 接口、时钟规则、参数历史投影或错误分层策略。

## 精确范围与来源

| 仓库 | 变更 |
|---|---|
| PyAMI | 生产文件仅 `src/pyibisami/ami/model.py`；扩展现有 `tests/ami/test_clock_lifecycle.py` |
| PyBERT | 更新 `PyAMI` gitlink 与 `pyproject.toml` direct URL；扩展 `tests/test_ami_single_init.py`，验证 Close 失败码经过真实宿主 helper 传播及 NULL 指针接线；另存本步记录、日志、审查报告 |

PyBERT 的 `src/`、GUI、Web、raw6 reader 没有本步修改。PyChOpMarg、其他依赖和包版本未变。`uv.lock` 的 PyAMI source 为 `{ editable = "PyAMI" }`，版本仍为 10.0.0；它没有 SHA 字段需要替换，因此锁文件逐字节保留。未运行全依赖重新解析或安装。

- PyBERT 基线：第 1 步提交 `9cefb5cca676628d85abf2756d150c109bcc9277`，分支 `codex/restore-ami-single-init`。
- PyAMI 基线：`d6d1f7fe7e58536546a1cfb9430c750cc2cb103e`；本步候选提交：`86f9d92de7b7ba8ad9a76d32337acdf2975a8111`，tree `10640b62182e73f19443676693375fd204fdfcb5`，分支 `codex/ami-close-output-pointers`。
- 新 PyAMI checkout 在本次 PyBERT 工作树的 `PyAMI/` 内；之前用于验证的外部 d6 checkout 未修改。
- 此阶段两个仓库均为本地 checkpoint，未推送、未创建 PR。新 pin 可由本地 checkout 解析；**尚未验证该 SHA 从远端 direct URL 安装**，不声称远端发布完成。

| 冻结文件 | SHA-256 |
|---|---|
| PyAMI/src/pyibisami/ami/model.py | cee3547238f8cecfa6e8c1ad01a401ed8c153b6a41a013ec47d789b78972b0d2 |
| PyAMI/tests/ami/test_clock_lifecycle.py | fd6988ec77f8424a4dc2dc00cf845cfe41a1807d3ddc174567a85af04cb01454 |
| tests/test_ami_single_init.py | 34a75fba94e7fb92a3f54298439daf9f7af4c955da7d7e8bbd18b75760b85a29 |
| pyproject.toml | dff373d212b805015789a4e9dddf6ea306444ae6615cf0da903b5252c7c3b8b2 |
| uv.lock（未改） | cc21cb7dd84c9729a6a2fedfda297af9fb195c0dd7e05a24f89fb7db87be4b12 |

## 验证

[验证输出](validation.log)保存最终测试、类型检查和 Ruff 基线对照；控制台输出只统一换行和删除行尾空格。

| 检查 | 结果 |
|---|---|
| PyAMI lifecycle＋response RNG | **73 passed**：56 个 lifecycle、17 个现有 RNG 测试 |
| PyBERT single Init＋clock Traits＋参数回归 | **42 passed，15 subtests passed**；35 条既有依赖弃用 warnings |
| model.py 定向 mypy | 通过；使用 `--follow-imports=silent --ignore-missing-imports --no-incremental`，不宣称整个仓库类型检查通过 |
| Ruff 0.17.2 | 修改文件的诊断与基线相同：PyAMI 生产文件 5 项、旧测试 25 项；PyBERT 测试 2 项。新增测试中的 dict 写法告警已清理，未改既有无关代码；不宣称完整 lint 通过 |
| Flake8 | 现成环境无该工具，未安装／运行 |
| git diff／pin | diff whitespace 检查通过；gitlink、direct URL 与实际 PyAMI HEAD 一致；lock 仍为原 workspace 记录 |

测试覆盖 Close 的成功、失败码、异常、析构、重新 Init 前清理失败、Init 与清理双错误以及幂等；覆盖 Init 输出未写／NULL／空／root／有值，以及每个 GetWave chunk、跨 Python 调用、失败和零长度调用的指针边界。PyBERT 两项新增 status=0 用例验证清理失败不会被当成运行成功，原始异常与 cleanup 异常均可取回。

先运行红测：17 failed / 39 passed，复现状态码未检查、输出指针非 NULL 和旧值复用。最初返回类型测试用 `c_int` 作为初值，在本机它与 `c_long` 是别名，因此该条先通过；改为初值 `None` 后单独红测确认未设置返回类型，随后生产修复通过。测试全部使用 Python ABI 替身，没有加载真实 AMI DLL；Init/GetWave/Close 包装、分块和两 probes 调用均为实际生产代码。

未执行真实 AMI、完整 Main／COM／GUI／Web 仿真，也未验证模型收敛、物理资源释放或 BER。现有非空同 epoch AMI clocks 仍等待 F5 映射，未恢复 C1。

## 复跑

现有 Python 3.13.15、NumPy 2.5.1、pytest 9.1.1 环境；已核对实际导入文件指向本次 PyBERT 和其下新的 PyAMI checkout。

```powershell
$env:UV_OFFLINE='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONPATH='C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator/src;C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator/PyAMI/src;C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/PyChOpMarg/src'
$taskUv='C:/Users/yx/AppData/Local/SerDesEqualizationExplorer/t06-candidates/9a75bfd50f2e8bf56b036e92d9923b2274c7babb/venv/Scripts/uv.exe'
$taskPython='C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/.venv/Scripts/python.exe'
# 在 PyBERT 工作树下运行
& $taskUv run --no-project --python $taskPython python -B -m pytest -q tests/test_ami_single_init.py tests/test_ami_clock_traits.py tests/test_ami_getwave_params.py -p no:cacheprovider --tb=short --disable-warnings
# 在其 PyAMI 子目录下运行
& $taskUv run --no-project --python $taskPython python -B -m pytest -q tests/ami/test_clock_lifecycle.py tests/ami/test_response_rng.py -p no:cacheprovider --tb=short --disable-warnings
& $taskUv run --no-project --python $taskPython python -B -m mypy --follow-imports=silent --ignore-missing-imports --no-incremental src/pyibisami/ami/model.py
```

本次 Ruff 使用已有缓存 `C:/Users/yx/AppData/Local/uv/cache/archive-v0/HvUhSgKRZOxef6bC/ruff-0.17.2.data/scripts/ruff.exe`，经同一 `uv run --no-project --python ...` 调用，参数为 `check --no-cache --output-format concise` 加对应文件；未下载安装。基线使用原外部 d6 checkout 的同名文件及原配置；父测试基线从第 1 步 HEAD 读取。

同一个 Astra 的独立审查见 [astra-review.md](astra-review.md)。此前七份算法审查原件与第 1 步记录均保留。
