# #28：将 PyAMI RNG 接口的固定 SHA 接入 PyBERT

2026-10-24。[live #28](https://github.com/yx520143-G/PyBERT/issues/28) 完整合同见 [issue-28.json](issue-28.json)。本票将依赖来源推进到已验收 RNG API 的 F2，保留两个全新安装环境与来源证据；没有调用新 API 或实施 C1。

## 来源和最小修改

新独立 clone：`E:/serial-bus-simulator-dependencies/pybert-issue28-rng-pin`，branch `codex/pybert-issue28-rng-pin`。PyBERT 起点 `1fde555ecf1120ba245e2249c1b2b777a42ce762` / tree `922e31c4c037e71f6f9a8d6fbeb64fcb5d4ee40e`，写证据前 clean；独立 `.git`，无 alternates、objects link count 1。新子模块元数据仅在本 clone 的 `.git/modules` 内。[clone.json](clone.json) 与 [startup.json](startup.json) 保留实际路径、启动状态及前序保护。

PyAMI **F2=`d6d1f7fe7e58536546a1cfb9430c750cc2cb103e`**，tree `1a74ae9844f657e5567c435345fdd561a1f747fe`。已从本票新子模块核对其两个父提交：旧 F `e222e4094629e1ce9a2f8058ab42439fc21fadd8` 和 #27 交付 `3bc5d43f81160bd022624c6c48b4a42651a874b8`；F2 tree 与已验收交付相同。声明版本仍为 `10.0.0`，原 LICENSE 与构建配置保留。

产品元数据只改 PyAMI gitlink 与 `pyproject.toml` 标准 `pyibis-ami[gui]` direct URL 的完整 SHA。保留本人 fork URL、GUI extra、其他约束、workspace、许可证及 PyBERT/PyAMI 计算源码。`.gitmodules` 不变，PyChOpMarg gitlink/checkout 仍为 `ca905e793fcf6330929471317ca32e7611578e5d` / `3.4.0`；只在新 clone 的本地 Git config 中将其传输 URL 指向 HTTPS。

[08-uv-lock](commands/08-uv-lock/receipt.json) 是真正的 `uv lock`，exit 0，解析 234 个包。**lock 原始字节前后相同，无 registry 升级 diff。** workspace source override 仍将 PyAMI 解析为 editable 路径，不能手填 SHA 冒充 lock 再生成结果。F2 由 gitlink、实际 checkout/tree 与已安装文件共同证明，普通 pip 则从标准依赖 URL 获取 F2。[metadata-check.json](metadata-check.json) 保留结构与字节检查。

## 安装前冻结与两条新路线

[bootstrap-plan.json](bootstrap-plan.json)、[environment-bootstrap-plan.json](environment-bootstrap-plan.json)、[source-inputs.json](source-inputs.json) 和 [install-plan.json](install-plan.json) 记录命令、源码身份、工具、实际解释器、独立 env/cache、guards 与零模型预算。Python `3.13.15`，uv `0.11.23`，B 的 pip `26.2.2`；实际版本输出保存在 commands/01、02、11、11a、11b，A/B 解释器并非复用旧环境的安装结果。

[capture.py](capture.py) 为每个唯一批次保存 command、cwd、相关环境、执行前输入、原始 stdout/stderr、exit 与 elapsed；相同输入字节按 SHA256 只存一份，批次逐一引用该快照，拒绝覆盖。captured commands 的原始输出没有截断或修写。通用安装器的系统库活动没有完整 trace，不能将所有底层活动写成 0。

| 路线 | 实际安装 | 来源结果 |
|---|---|---|
| A：uv workspace | 新 clone 的 `.venv`，`uv sync --locked --no-dev` | exit 0；PyAMI/PyBERT/PyChOpMarg 均为新 clone 的 editable 路径；[14-source-A](commands/14-source-A/source-receipt.json) 通过 |
| B：普通 pip | 新 `E:/serial-bus-simulator-dependencies/pybert-issue28-pip-venv`，该环境 `python -I -B -m pip --isolated install` 项目 | exit 0；PyAMI 为 site-packages 中的 VCS 来源安装；[15-source-B](commands/15-source-B/source-receipt.json) 通过 |

B 使用普通 pip、官方 index、本票独立 cache，没有 uv workspace override、预装 PyAMI 或 `--no-deps`。唯一额外 constraint 是 [pip-constraints.txt](pip-constraints.txt) 的 `pychopmarg==3.4.0`，沿用未改的基线版本。B 的 PyChOpMarg 为该版本的 registry wheel；A 为固定 Git checkout 的 editable 源码，两者来源不能等同。

A 的 PyAMI PEP 610 是 `file://` 本地 URL、`dir_info.editable=true`，没有 VCS 字段；不伪造其 commit_id。B 的 PyAMI `direct_url.json` 与 [pip report](commands/13-pip-install/pip-report.json) 可追溯到本人 fork，`commit_id`、`requested_revision` 均为完整 F2。PyBERT A 为 editable，B 为从本票目录构建的普通 wheel。实际 METADATA、WHEEL、RECORD、INSTALLER、direct_url 原件按各自存在性保存在两批 dist-metadata 目录，hash 在 source receipt 内。

两环境均禁用 system site-packages；真实 executable/prefix/sys.path、ModuleSpec、来源文件与 GUI extra 版本均已核验。[environment-differences.json](environment-differences.json) 如实列出 **17 项版本差异**：例如 NumPy A `2.5.1` / B `2.5.4`、SciPy A `1.18.0` / B `1.18.1`，以及 A 独有 greenlet、B 的 pip。B 的独立 registry 解析不等于修改 uv.lock，也不证明两个完整数值环境相同。

## 来源核验及零产品/模型预算

[verify_source.py](verify_source.py) 在产品 import 前安装 import/audit/profile guards，仅安全导入实际 `pyibisami` 顶层包。用 PathFinder ModuleSpec 定位实际 model 文件与 PyBERT/PyChOpMarg 的安装解析路径，读取源文件和 AST；不导入 `pyibisami.ami` 或 model 模块体，不构造 response-key 常量，也没有用 fake constructor 冒充导入。

每路实际核验 **91 个 Python 源文件**：35 个 PyAMI 文件与 F2 Git blobs、56 个 PyBERT 文件与本票固定输入在 CRLF→LF 后 hash 一致。checkout、Git blob 与实际安装文件的 raw hash 分别保留，不将 EOL 归一化写成 byte-exact。两路 PyChOpMarg 的各 23 个实际 Python 文件也只读记录了 hash，没有冒称其来源/文件等同。

实际安装位置的 `get_responses` AST 确认旧五个 positional 参数保持，新增 `rng` 是 keyword-only 且默认 None；AST dump 包含实际 annotation。这是源码和签名证据，没有执行该函数。共执行 **2 次安全顶层包模块体**（每路一次），model 模块体、response-key 构造、所有生产方法、Main/COM/coopt、AMIModel/Initializer 实例、C Init/GetWave/Close、模型 CDLL、engine/DSP/helper/parser、模型下载编译均 **0**；两批 blocked_attempts 为空。

没有运行 #24/#27 测试、fullsuite、旧 DLL test_init、CLI/`python -m pybert --version`、GUI、服务或浏览器。本票没有新的模型资格、算法、seed 策略、C1 probe/main 隔离、D/Web/archive/E 或链路数值结果。

## 原始失败、费用与封存

[cost-ledger.json](cost-ledger.json) 记录 **17 个安装/来源 commands**，均 exit 0，内部 elapsed 合计 `229.49530680001772 s`；A 同步 `54.7916714999883 s`，B pip 安装 `147.57298740000988 s`。新 clone/switch 另计 `55.753896100010024 s`；这些不是总任务 wall 或模型时间。总任务 wall、peak RSS UNKNOWN。

首次 bootstrap 的 existence guard 因我将 UV cache 放在目标 clone 内而停止，原输出/exit 1 保存在 [bootstrap-attempt-01.json](bootstrap-attempt-01.json)。仅本票新 cache 移到独立目录后 clone 成功，缓存保留，未碰旧材料。没有把这次失败改成通过。实际 AST preflight 将验证器误写的旧参数名 `pad_bits` 更正为源码的 `max_run_length`，详见 [preflight-amendment.json](preflight-amendment.json)；这发生在验证执行前，旧脚本快照保留。随后 [verification-plan.json](verification-plan.json) 冻结增加的 PyBERT/PyChOpMarg PathFinder 来源检查；安装输入未变，未因此重跑安装或测试。

候选提交前的首次 Git diff-check 因三份冻结 JSON 的 CRLF 被当作尾随空白而 exit 2，commit 未创建。首次 tool 展示被截断；[static-commit-attempt-01.json](static-commit-attempt-01.json) 明确记录这一缺口，同一 staged index 的完整重复失败诊断保存在 [18-diffcheck-red](commands/18-diffcheck-red/receipt.json)。仅对这三份 JSON 增加 CR-at-EOL 识别并保留默认空白检查，原字节不变；[19-diffcheck-green](commands/19-diffcheck-green/receipt.json) 通过。两批额外静态检查与首次未计内部 elapsed 分开入账，没有重跑安装或产品验证。

原始 lock/pip report 超过 500 KiB，raw metadata 含原生 EOF/换行格式。`.gitattributes` 保持字节；hook 配置仅为本票 raw commands/inputs 增加 EOF/mixed 保留范围，并精确排除两个超限原件，前序 #25 例外语义不变。没有宣称实际 hooks/full lint 通过；新脚本已通过 Python 3.10 AST、119 列检查并实际完成两路来源核验。

[startup.json](startup.json) 引用前序 4,874 项原件清单，另保护旧 11 个仓库 HEAD/tree/status、94 项 Git 元数据及 409 项 #25/#27 材料/已安装源码 hash。旧 env/cache 与本票新 env/cache 全部保留，未清理主 checkout 的既有 untracked 文件。#24/#27 的失败、软件调用和费用没有重跑或重置。

交付仅为本人 PyBERT fork master 的唯一 Draft PR，明确 Refs #28，不自行 merge/close。双轴自审见 [review.md](review.md)，最终 hash 封存见 [verification.json](verification.json)；固定最终 HEAD/tree/clean 后停止写入并交 PM fresh review。后续迁移/C1 与私有化由 PM 按授权安排；本票不解除 #10 有效 clocks/E SOURCE_BLOCKED、#4 默认 COM BLOCKED_BUDGET/NOT_EXECUTED 或父 #1 最终 fresh 数值 review。
