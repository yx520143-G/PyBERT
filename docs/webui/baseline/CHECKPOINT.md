# GUI 基线采集检查点：采集完成，交 PM 终审

2026-10-23 至 2026-10-24（Asia/Shanghai），在固定源码 `1bc905d577d2f3bd9471421cfbf3d422d4e6080e` 上使用 Astra / max / Fast 完成 #1 的五项设计基线采集。交付分支为 `codex/webui-gui-baseline`；本目录随所属 Git 提交冻结，不修改产品代码或数值算法。

- 七个顶层页、全部现有子页、五个菜单、状态栏和布局有真实PNG及对应UIA；50控件和18个本期图位已逐项记录，V/I/S证据边界见 [control-audit.md](control-audit.md)。
- 数字Enter/Tab、表格Enter/Tab/焦点转移、CTLE/CDR/Ideal与RLM条件切换已留证；本期只读定义与实际展示交叉记录，未冒充逐项拒写测试。
- 用户直接鼠标Run的数字样本采用4000但发生calc_ber异常，4000/4000失败日志和陈旧Running状态保留。独立表格样本为4000/3000、Pre-tap5=.05；事后有两条正常完成日志且stderr无新增。
- 原生另存 `evidence/table-mouse-run-post.yaml` 已核对4000/3000及首tuple=.05。该文件是运行后实例状态，不是冻结输入；原GUI没有run ID，不能声明只有一次Run或各次AGC输入完全相同。
- [manifest.json](manifest.json) 枚举材料；[checksums.sha256](checksums.sha256) 校验完整性。PNG虽然被仓库全局规则忽略，仍只对本目录截图显式加入版本。

工具曾两次报告用户物理Esc停止，均停止了后续GUI操作；用户分别明确恢复后才继续。最后一次恢复仅另存配置与文档收尾，没有追加运行。WGC/鼠标自动接口限制及人工操作来源见 [interactions.md](interactions.md)。

实施者结论：五项设计基线记录完成，提交PM终审；不自行勾选GitHub验收项、不关闭#1。用户已授权后续推进#2，由PM接受本基线并另行派发。本次没有实施#2–#5、push或创建PR。保留不属于本次提交的 `docs/research/`、`source/` 与 `docs/webui/PM_HANDOFF.md`。
