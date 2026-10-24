# PR31：修复 runner 专用测试的默认收集回归

PM 对初次交付 `2f0a60104551410041f00e03750a6de5a13bc0bb` 的 [fresh review](https://github.com/yx520143-G/PyBERT/pull/31#pullrequestreview-5639104111) 发现一个 Standards P2：`tests/test_ami_probe_main.py` 导入的 `c1_under_test` 仅由专用 runner 注入，普通 pytest 收集无法解析。该发现来自静态审查，没有实际 pytest 失败日志；原 01–10 guarded 结果仍只证明原声明范围。

本次将该文件原字节迁为 [guarded_probe_main_cases.py](../guarded_probe_main_cases.py)，移出 `tests/` 并使用不匹配默认 `test_*.py` / `*_test.py` 的名字。runner 仅将 `test` 路径改为 evidence 下的新文件。没有 ignore/skip、新 bootstrap 或 pytest 配置变更；其他测试及 conftest、两个产品源码、依赖/lock/license 均保持。新的专用入口仍是 [run_guarded.py](../run_guarded.py)，guard 顺序和内容经 AST 证明未变。

## 验证和实际入口

[static-plan.json](static-plan.json) 先冻结两次静态检查的范围和命令；每次 [check_entry.py](check_entry.py) 在分析前保存 source、caller、case 文件、runner、checker、plan、环境、配置和完整 tests Python 文件清单。它只读取字节/AST，不调用 pytest、conftest 或任何产品模块。

- [01-static-red](runs/01-static-red/receipt.json) exit1：确认原默认收集路径存在注入模块 import，尚未迁移。它是实际运行的静态检查 red，不是实际 pytest 收集失败。
- [02-static-green](runs/02-static-green/receipt.json) exit0，9 项检查通过：旧收集路径已移除，新 case 字节与原件相同，名字不匹配默认模式，runner 指向新位置且 AST 仅路径变化，其他测试/配置/产品完全不变。两个静态批次 pure seam/stubs/pytest/产品执行均为 0。
- [11-entry-green](../runs/11-entry-green/receipt.json) exit0：使用迁移后的实际 runner/cases 执行原当前矩阵，9 methods、35 次实际纯协调器、29 次 error constructor；selected fake factory53、initializer49、initialize47、RNG28、get_responses27、getWave12、Close51。input copy120、buffer copy119、record copy98、message decode14。blocked attempts 为 0；全部真实禁止入口仍为 0。

实际执行命令为：

```powershell
uv run --no-project --python E:/serial-bus-simulator-dependencies/pybert-issue30-probe-main/.venv/Scripts/python.exe python -I -B docs/webui/issue30/probe-main-20261025/run_guarded.py 11-entry-green
```

输出目录拒绝覆盖；`11-entry-green` 已保存，后续经授权复验必须使用新的唯一 run id，并先冻结新计划。普通仓库测试入口仍为 CLAUDE.md 的 `uv run pytest tests/` / `make test`。本次没有运行这些命令或 root pytest collection，因为现有 conftest 会导入产品；上述静态路径证明不扩大为整个 pytest/conftest 的运行健康或 fullsuite 通过。

## 原件与费用

[startup.json](startup.json) 固定初次交付全部 127 文件 raw hash、原 tests Python 清单及应保持字节；[inputs](inputs/) 保留原 README、review、verification、cost ledger、plan、runner 和 test。原 01–10 snapshot/receipt/log 均保持，未用新数据覆盖原事实。初次 verification/review 仍是 v1 历史；新的复审及 v2 封存另列。

本次新增 guarded 内部 elapsed `1.528305999992881 s`；两次静态内部 elapsed 分别 `0.09999210000387393 s`、`0.10217580001335591 s`，与 guarded 成本分列。累计 11 个 guarded 批次为 165 次实际纯协调器、135 次 error constructor、内部 elapsed `4.152754799972172 s`。初次失败、bootstrap 成本和 UNKNOWN 均保留；完整费用见 [cost-ledger.json](../cost-ledger.json)。本次只读 rg 查询曾包含不存在的根 conftest.py，exit2 与观察缺口在 startup 中保留；未执行任何产品或测试。

首次 staged whitespace 检查因新快照的原有 CRLF/Makefile 空白停止，尚未 commit；[首次记录](staged-check-first-failure.json) 明确原工具输出截断缺口。随后对未变的 staged 输入另做 [完整再观察](runs/03-staged-check-recapture/receipt.json)，exit2、内部 elapsed `0.08657980000134557 s`，不冒充恢复首次原输出。仅在 `.gitattributes` 增加本修复 raw runs 路径的 whitespace 属性，未改 hooks 配置。617,339 B 诊断原件仍在本地原路径，唯一该新日志使用本 clone `.git/info/exclude` 精确排除；Git 保存 [lossless gzip](runs/03-staged-check-recapture/stdout.txt.gz) 和 [raw/storage hashes](runs/03-staged-check-recapture/storage.json)，解压后逐字节相同。这样保留原件和原有 500 KiB hook，未排除任何测试。此前未 staged 的 diff 检查没有覆盖这些当时未跟踪的 raw 文件，不能替代 staged 检查。

本修复只处理 PR31 的收集入口 P2；D1→D2→E 按 PM 最新指令在既有 #10 内串行跟踪，不新建 issue。实际模型/ABI/数值/有效 clocks 与 COM gate 未验收。
