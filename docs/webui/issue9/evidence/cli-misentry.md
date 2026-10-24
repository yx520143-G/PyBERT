# CLI version 误入口与费用更正

Owner 两次错误调用了 `python -m pybert --version`。`src/pybert/__main__.py` 是 GUI 入口，直接构造 `PyBERT()`，不解析 version 参数；`PyBERT.__init__(run_simulation=True, gui=True)` 默认先调用一次 `simulate(initial_run=True)`，随后 `configure_traits` 因 `ETS_TOOLKIT=null` 抛出异常。两次进程均 exit=1；不是 CLI version 通过，也不是 GUI 验收。

1. 第一次发生在提交产品 `70eeb0d` 后、contracts-v3 后的工具命令中。输出已从统一执行 session 2470 事后取回，见 `cli-misentry-first-tool-output.log`；它是序列化工具输出，不能声称原始 stdout 文件字节。
2. 第二次发生在最终静态记录命令中，原始 stderr/stdout 文件为 `cli-version.log`，`static-final.json` 正确保留 exit=1。

两次均计入总 Main 费用，因此原先19次计划内 Main 的报告追加为 **21次**。这两次没有预登记输入、没有完整 raw 或逐次数值终态/peak/elapsed 采集，保持 unknown，不能用事后构造默认实例补造结果，也不加入 #9 数值比较。原默认 `rx_use_viterbi=False`（pybert.py）与 `enable_com=False`（pybert.py）的无参数入口证据说明没有默认 trellis/full COM 请求，不等于输出资格证明。相关 Native/source 文件在整个误入口期间未修改，可追溯产品70eeb0d及 delivery-audit 的实际源字节；`__main__.py` 从3807基线未改。

随后改用 `[project.scripts]` 的真实入口：`python -c "from pybert.cli import cli; cli()" --version`。输出 `-c, version 11.1.0`、exit=0，日志为 `cli-version-corrected-v2.log`。该 Click version 分支不构造 PyBERT、不执行 Main；修正结果另存 `static-corrected-v2.json`，不覆盖失败原件。
