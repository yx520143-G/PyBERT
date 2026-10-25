# AMI 接口第 2 步 F1/F2：Astra 独立审查

2026-10-25。**Standards：0 findings；Spec：0 findings。** 本步可以形成本地 checkpoint。审查只覆盖最终清单的 F1/F2；F3–F6 未开始，真实 AMI 验收继续暂缓。

## 固定对象

- 父仓库：`C:/Users/yx/.codex/worktrees/pybert-final-parity/serial-bus-simulator`，分支 `codex/restore-ami-single-init`，base/HEAD `9cefb5cca676628d85abf2756d150c109bcc9277`。审查其当前未提交 diff。
- PyAMI：父工作树内的 `PyAMI/`，分支 `codex/ami-close-output-pointers`；base `d6d1f7fe7e58536546a1cfb9430c750cc2cb103e` → 候选 `86f9d92de7b7ba8ad9a76d32337acdf2975a8111`，tree `10640b62182e73f19443676693375fd204fdfcb5`。候选工作树干净。
- Spec：[最终修改清单 F1/F2](../fresh-algorithm-review-20261025/final-modification-checklist.md)。Standards：用户的最小范围／精准修改要求及父子仓库 `CLAUDE.md`。沿用同一 Astra，按 `code-review` 两轴审查，没有派生其他审查者。

## Standards

**可执行 findings：0。** PyAMI 生产改动仅为 `model.py` 的 17 行 diff，配套扩展既有 lifecycle 测试；父仓库只更新 gitlink、精确 dependency pin 和宿主回归测试，另保存本步证据。没有改父仓库生产源码、GUI、Web/raw6 reader、R1/R2 probe 流程或无关计算。

代码继续使用现有 Close 所有权、`AMIModelError` 和 observation 结构，没有新框架或完整 ABI 重构。已读取保存的定向 mypy 与 Ruff 基线对照记录：前者通过，后者保留既有诊断而未增加新项；本审查未重复运行这两项。Flake8 未运行，不宣称完整仓库 lint/type-check 通过。父子 diff whitespace 检查无错误。

## Spec

**可执行 findings：0。** 已独立核对官方 [IBIS 6.1 §10.2.3，第 185、189–190 页](https://ibis.org/ver6.1/ver6_1.pdf#page=185)：Close 声明返回 `long`，1 为成功、0 为失败；Init 与每次 GetWave 的参数输出指针内容应在调用前初始化为 NULL。

| 要求 | 审查结论 |
|---|---|
| Close 返回类型和状态 | `PyAMI/src/pyibisami/ami/model.py:353–356,383–394` 明确 `c_long`，先保存实际 `status` 与 `returned=True`，再判定成功。非 1 返回进入原 `AMIModelError`；调用异常保留 `status=None / returned=False`。状态失败不会被当成未调用或未返回。 |
| 清理所有权和双错误 | Close 前放弃 handle 所有权，重复 Close／析构不会重试；重新 Init 前的 Close 失败会阻止新 Init。Init 本身失败后 cleanup 失败仍可单独取得。父级真实 `run_ami_model` 的失败码用例确认单独 cleanup 失败阻止成功，双错误保留 primary 与 cleanup。 |
| 释放证据含义 | 成功码对应 `release_status="not_verified"`，失败仍为 `unknown`。实现和记录都没有把返回 1 当作物理资源释放已独立验证。 |
| Init 参数输出指针 | `model.py:496` 使用 `c_char_p(None)`；测试区分未写、显式 NULL、空 bytes、root-only 和有值字符串，且不覆盖先前已复制的 observation。 |
| 每个 C GetWave 前清空 | `model.py:598` 位于 chunk 循环内、紧邻 C 调用前。包含短末块和后续 Python 调用；不是仅在 Python `getWave()` 入口清一次。未写参数或失败前未写时，`params_raw` 为本次 None，不复用上次值。空 wave 不调用 C，原观察值保留。 |
| raw 与公开字符串接口分开 | Init/GetWave observation 保留 None、空 bytes 和实际 bytes；现有 `ami_params_out` root-only fallback 保持并明确说明。没有把宿主补出的 root-only 字符串写入 `params_raw`。 |
| R1/R2 与依赖接入 | 原单 Init、两 probes、同 handle Main、最终 Close、可选 RNG 与默认无 seed 注入均通过回归。父 gitlink、direct URL 精确 SHA、实际子仓库 HEAD 一致；实际导入新工作树源码。`uv.lock` 仍为 editable `PyAMI`、版本 10.0.0，字节未改，未重新解析其他依赖。 |

## 独立复跑

通过既有 `uv run --no-project` 环境运行，实际模块路径已核对为本次父工作树 `src/pybert` 与其下 `PyAMI/src/pyibisami`。Python 3.13.15、NumPy 2.5.1、pytest 9.1.1。

| 定向测试 | 独立结果 |
|---|---|
| PyAMI `tests/ami/test_clock_lifecycle.py`、`tests/ami/test_response_rng.py` | **73 passed**，0.24 s，exit 0 |
| 父仓库 `tests/test_ami_single_init.py`、`tests/test_ami_clock_traits.py`、`tests/test_ami_getwave_params.py` | **42 passed + 15 subtests passed**，35 warnings，0.65 s，exit 0 |

合计 **115 passed + 15 subtests**。测试使用 Python ABI 替身，未加载真实 AMI DLL；覆盖 Close 成功／失败码／异常、幂等和双错误，以及参数输出指针的逐 C 调用边界。`c_long` 测试验证 ctypes 绑定元数据，不能替代实际二进制 ABI 验证。复跑命令、其他保存的验证证据见 [本步实施记录](README.md) 和 [日志](validation.log)。

## 范围限制

本结论是本地集成审查。候选子提交和父 checkpoint 尚未推送，未验证远端 direct URL 安装；不声称发布完成。未运行真实 AMI、完整 Main、COM、GUI/Web 端到端，也不推导模型收敛、BER、缓冲容量或物理释放资格。本步只处理 `AMI_parameters_out`，不声称补齐所有输出接口或完整 ABI。F3–F6 按原清单保留，不作为本步新增 findings。

本审查只新增本文件，未修改产品、测试或历史报告，未执行 Git 写操作、安装或额外模型运行。

## 冻结 SHA-256

| 文件 | SHA-256 |
|---|---|
| `PyAMI/src/pyibisami/ami/model.py` | `cee3547238f8cecfa6e8c1ad01a401ed8c153b6a41a013ec47d789b78972b0d2` |
| `PyAMI/tests/ami/test_clock_lifecycle.py` | `fd6988ec77f8424a4dc2dc00cf845cfe41a1807d3ddc174567a85af04cb01454` |
| `tests/test_ami_single_init.py` | `34a75fba94e7fb92a3f54298439daf9f7af4c955da7d7e8bbd18b75760b85a29` |
| `pyproject.toml` | `dff373d212b805015789a4e9dddf6ea306444ae6615cf0da903b5252c7c3b8b2` |
| `uv.lock`（未改） | `cc21cb7dd84c9729a6a2fedfda297af9fb195c0dd7e05a24f89fb7db87be4b12` |
