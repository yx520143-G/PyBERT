Refs #22。

Rx GetWave 返回非空参数时，固定 PyAMI grammar 产生 tuple 树，原生 visitor 却读取 dataclass 属性并失败；后继 tap 筛选还调用 Python str 不存在的方法。本 PR 将这段消费集中为实际生产纯函数，按完整 tuple 路径保存数值，修正大小写不敏感 tap 筛选，并保持根层 lock/UI 参数查找兼容。

非数值、混合 atom、Table 和空返回明确不可用；重复路径、数值路径新增/缺失、同次调用 tap 列错位明确拒绝。跨调用共同长度变化可保留，不补零、广播或截短历史。产品改动仅在 `src/pybert/models/bert.py`；保留原调查四文件及每批红/绿的完整源码、日志和成本。

验证：最终 12 项纯函数定向测试通过，包含旧 direct/worker 的 750 份真实返回字符串及 path/shape 边界；保存了原 tuple visitor 和 str tap 筛选红灯。范围核验确认除约定参数块、helper、失效 import 和四处根层 key 查找外，剩余完整模块 AST 与基线相同。只读 Standards/Spec 自审各 0 findings，评审不新增测试或 parser 调用。

新增 Main、COM、coopt 候选、AMI_Init/GetWave/Close、模型库加载、引擎构造、原生数值 helper 均 0。全部十批纯 parser 共 5376 次，测得批次内部 elapsed 合计 3.725872899958631 s；全任务 wall/RSS UNKNOWN。

报告与来源：`docs/webui/issue22/params-compat-20261024/README.md`；最终执行源为 green-05-review-candidate，固定自审代码提交 80100e262e433076396819e3d29aedc20bdad30a。

有效 NRZ/PAM4 clocks 仍 BLOCKED。PyAMI buffer/probe 状态、时基与调用顺序、clocks pairwise/采样/入口/metadata、模型 fixture 均未改动或运行；本 PR 不提升 #10 或父票资格。交 PM fresh review 后决定集成，不自行 merge 或关闭 issue。
