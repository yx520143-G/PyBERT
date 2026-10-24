# #25：PyAMI fork 固定 SHA 的安装来源接入

2026-10-24。本票为 [live #25](https://github.com/yx520143-G/PyBERT/issues/25) 的 S1 来源接入；完整读取结果见 [issue-25.json](issue-25.json)，不是模型资格验证。用户已通过 PM 授权本人 fork、完整 SHA 接入及两条隔离安装，接受含 direct URL 的本 fork 暂不能发布 PyPI 的限制；不写 capn-freako 上游。

## 固定来源与独立工作区

- PyBERT 基线 HEAD `35a71a6b79a00693a2f2862184552894752899c0`，tree `d8334daffacbc19cc638b03bbdc2dc3f9736be7e`。
- 独立 clone：`E:/serial-bus-simulator-dependencies/pybert-issue25-pyami-pin`，分支 `codex/pybert-issue25-pyami-pin`，启动时 clean。旧 managed worktrees 与主 checkout 共用 Git common-dir，故使用合同允许的 `clone --no-hardlinks --no-checkout` 后显式 switch；独立 `.git`、无 alternates、object link count 1。子模块元数据仅在新 clone 的 `.git/modules` 下。
- 唯一依赖 **F**：`e222e4094629e1ce9a2f8058ab42439fc21fadd8`，tree `b9bd99398a8893f0c3d301e7758eec8f9d3858d0`，来自 [本人 fork PR #1](https://github.com/yx520143-G/PyAMI/pull/1) 的普通 merge。已核验 tree 和已验收候选 `41d08c85bfc017978b31bae0ef76c6ee9641ec39` 相同，后者为 F 的祖先。F 声明版本 `10.0.0`，处于原 `>=10.0.0,<11` 范围，原 LICENSE 保持。
- PyChOpMarg gitlink/checkout 保持 `ca905e793fcf6330929471317ca32e7611578e5d` / `3.4.0`；仅新 clone 的本地 submodule URL 配置使用 HTTPS，未改它的 `.gitmodules` 声明、源码或版本。

[startup.json](startup.json) 保存启动与旧来源保护快照；旧主 checkout 已有未跟踪 `docs/research/`、`source/`，它们没有被清理。启动 clean 指新 clone 写证据前的状态，不代表实施中的 WIP 一直 clean。

## 必要元数据修改与 lock 语义

产品改动只有：`.gitmodules` 的 PyAMI URL 改为本人 fork；PyAMI gitlink 固定 F；标准 `project.dependencies` 改为 `pyibis-ami[gui] @ git+https://github.com/yx520143-G/PyAMI.git@e222e4094629e1ce9a2f8058ab42439fc21fadd8`。GUI extra、项目版本 `11.1.0`、其余依赖约束、optional extras、workspace 结构与 source overrides 均保留。

实际执行 [08-uv-lock](commands/08-uv-lock/receipt.json) 的 `uv lock --python <已记录的解释器>`：exit 0，Resolved 234 packages。**重新生成结果与基线 lock 字节相同，没有 uv.lock diff，也没有 registry 升级。** uv 的显式 workspace source 覆盖标准依赖来源，因此 lock 中仍为 `editable = "PyAMI"`；不能将这个本地路径伪称为含 F 的 VCS direct_url，也没有手填 SHA/comment 冒充生成结果。

uv 的 F 由已检出的 gitlink/checkout 和实际 editable 文件哈希共同证明；普通 pip 不读取 uv workspace override，由标准 PEP 508 direct URL 获取 F。只改 gitlink 无法解决普通 pip 的旧来源问题，本次对两种实际安装分别验证。[metadata-check.json](metadata-check.json) 保存结构比较和 lock 结果，原始输入在 [inputs](inputs)。

## 两条全新隔离安装

安装前已固定 [install-plan.json](install-plan.json)、来源清单 [source-inputs.json](source-inputs.json) 与验证脚本 hash。命令、cwd、工具路径、相关环境变量、完整 stdout/stderr、输入快照、退出码和 elapsed 均由 [capture.py](capture.py) 存在各唯一 commands 目录，目录拒绝覆盖。

| 路线 | 实际环境与命令 | 安装和来源结果 |
|---|---|---|
| A：uv workspace | 新 clone 的 `.venv`；`uv sync --locked --no-dev --python <既有解释器>`，UV_PROJECT_ENVIRONMENT 显式指向新目录 | 安装 exit 0；PyAMI 为新 clone 的 editable 路径；[13-source-A](commands/13-source-A/source-receipt.json) 通过 |
| B：普通 pip | 新 `E:/serial-bus-simulator-dependencies/pybert-issue25-pip-venv`；先 `uv venv --seed`，再该环境 `python -I -m pip --isolated install <本新clone>`，完整 flags 见计划/receipt | 安装 exit 0；PyAMI 在该 venv 的 site-packages，PEP 610 commit_id/requested_revision 均为完整 F；[14-source-B](commands/14-source-B/source-receipt.json) 通过 |

B 使用普通 pip、官方 index、独立 cache，并非 `uv pip` 或 workspace override，也没有 `--no-deps`/预先塞入 PyAMI。其唯一额外 constraint 为 [pip-constraints.txt](pip-constraints.txt) 的 `pychopmarg==3.4.0`，来自未改的基线版本，避免安装时顺带升级。B 的 PyChOpMarg 是该版本的 PyPI wheel；没有把它冒充为 ca905e7 的 Git 来源或声称其文件与 editable 完全相同。

A 的 PyAMI `direct_url.json` 为本地 file URL + `dir_info.editable=true`，**没有 VCS commit_id 字段**。A 的 checkout F 和 hash 核验独立记录。B 的 PyAMI `direct_url.json` 是 GitHub fork URL + `vcs_info.vcs=git`、完整 F；其 PyBERT 为普通 wheel 安装的本地目录来源，非 editable。两环境均 `include-system-site-packages=false`，实际 sys.prefix/executable/sys.path、distribution metadata/Requires-Dist、GUI extra 已安装版本和 module 路径均留存。

Python 为 `3.13.15`，uv `0.11.23`，B pip `26.2.2`；完整版本输出见 commands/01、02、03、11。两环境的其余 registry 版本不同，例如 NumPy A `2.5.1` / B `2.5.4`，SciPy A `1.18.0` / B `1.18.1`；[environment-differences.json](environment-differences.json) 保存全部 17 项差异，包括 B 的 pip 及 A 独有的 greenlet。此为新 pip 对既有约束的独立解析，不是修改 uv.lock 升级，也不证明两个完整数值环境相同。

## 最小来源核验与 guard 边界

[verify_source.py](verify_source.py) 在任何产品 import 前安装 import/audit/profile guards，封锁 ctypes/dlopen、PyBERT/PyChOpMarg、NumPy/SciPy、parser、GUI 及 helper 相关导入和生产方法执行。只安全导入 `pyibisami` 顶层包，记录其真实 `__file__`；model 由实际环境的 ModuleSpec 定位，API 存在性由 AST 检查，**没有执行 model 模块体**。

这样也避免了 F 的 model import 会发生的四个 `AmiModelResponseKey` 构造/`__post_init__` 调用。没有用 fake constructor 替换它来冒充导入。`AMIModel`/Initializer、get_responses、initialize/getWave/close、run_ami_model、grammar parser 与 DSP helper 均未调用；source receipts 的 blocked_attempts 也为空。

两路线各自读取实际安装位置的 **同一组 91 个 Python 源文件**：35 个 PyAMI 文件与 F Git blobs、56 个 PyBERT 文件与基线比较，均在 CRLF→LF 后 hash 相同；原始 bytes hash 也保留，不把 EOL 差异隐藏成 byte-exact。API 检查含 close、initialize、getWave、三项 last_* 与 AMIModelError。它们证明来源与静态 API 存在性，不证明 model import/runtime、ABI 或仿真运行通过。未运行 pytest、现有 DLL test_init、CLI/`python -m pybert --version`、服务、浏览器或 GUI。

## 原始记录、费用与限制

[cost-ledger.json](cost-ledger.json) 汇总本票 17 个 captured commands，均 exit 0，内部 elapsed 合计 `231.37263920000987 s`；其中 A 同步 `46.84127889999945 s`、B pip 安装 `154.26222759998927 s`。新 PyBERT clone 另记录 `5.021198800008278 s`；这不是完整任务 wall 或模型时间。总任务 wall、peak RSS UNKNOWN。普通 Python 包的下载/安装/build 与模型编译分账，完整 warning/输出保留；安装器内部通用平台/系统库活动未按模型调用进行追踪。

本票 owner 未调用 Main、COM、coopt、AMI C Init/GW/Close、模型 CDLL/engine、原生 DSP helper、AMI grammar parser；生产 wrapper 方法/fake callbacks、额外模型包下载/模型编译均 0。依赖 Git 传输可能包含其既有 example binaries，但没有加载它们。#24 的 37 项旧回归、失败和费用维持原封存，没有重跑或重置预算。没有写共享 venv/global/site-packages 或旧子模块补丁。

本证据目录用 `.gitattributes` 保持原 bytes，仅对 commands/inputs 的 raw 快照关闭 whitespace 解释。首次 Standards 自审发现 check-added-large-files 的 500 KiB 限制及 end-of-file-fixer 会与原件保存冲突；`.gitattributes` 不会豁免 hooks。因此 `.pre-commit-config.yaml` 仅对本票 20 个超限的 startup/lock/pip-report 快照配置 large-file 排除，并对本票 commands/inputs 排除 EOF/mixed-line-ending 自动改写。没有改动原始 bytes；check-ast/json/yaml/merge-conflict 等仍有效，普通文档和两个新脚本继续检查。保留所有原输出，不修剪失败/警告或通过修改 lock 掩盖来源。

F 的 strict clocks 适用于所有 GW（含 Tx、response probes、Init 内 probes）；合法 prefix/epoch/status 等由 #24 定义。历史 B+8 只是兼容容量，不能证明任意 DLL 的容量上界或防止写越界。F **尚无可选 rng、probe 隔离、D/Web/归档接入或 E 资源资格修复**，这些另票处理。本来源迁移不是有效 NRZ/PAM4 clocks 或真实模型资格，#10/#4/#1 的剩余 gate 保留。

含 Git direct URL 的本 fork 暂不具备 PyPI 发布路径，pip 安装需要 Git/GitHub 可达；这不是 PyPI 发行或已发布新版本。交付仅为本人 PyBERT fork 的唯一 Draft PR，不自行 merge 或关闭 #25。独立双轴只读复核见 [review.md](review.md)，最终 hash 封存见 [verification.json](verification.json)；固定最终 HEAD/tree/clean 后停写返权给 PM fresh review。
