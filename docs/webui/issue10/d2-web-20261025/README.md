# D2：Web AMI clocks consumers

基线0f04562c50a12fae637fece04da100c44c86617e/tree790d13dc87bf00d2b31f8aaf128157a937fe0c93；仅#10 D2。完整合同见D2-contract-comment.json，覆盖设计阶段零数值旧限制。独立clone、新env/cache，D1继续封存。设计ref的GitHub contents查询404，使用已存在设计repo的该固定Git blob原件，未猜ref。一次全issue comments与一次较宽源码展示发生工具截断，后续限定目标合同/源码范围完整读取；未把截断输出当完整原件。启动前只读检查曾用D1 Python解释器，无产品/NumPy调用或旧环境写入；正式bootstrap及后续均使用standalone/new env，D1安装文件hash已核对。

两次静态lock定位失败：先匹配到dependency的numpy字符串误选chaco；再错误选取第一个numpy package2.2.6，忽略多版本resolution marker，均assert停止（exit1，无安装/导入/数值调用）。工具转录保留输出，未额外保存全stdout；改用stdlib tomllib并核对3.13/win32 marker后冻结实际2.5.1 wheel URL/hash。

每批实际计算前冻结完整case/输入/实际源/test/runner/预算/环境/guards并commit；guarded case从一开始不在默认pytest发现范围。预算4000 pure、collect/extend_analysis各32、eye_data/calc_eye各128、clock_data/display/hist/rfft各128、safe_log10 256、Viterbi.extend64/validate256、resize256、archive.read_arrays/validate_run各256、save/load各64、annotate/Execution.write/partial.save各128；最多16动态批/60s。NPZ/hostcopy/JSON/hash/header等另计，数据预算16MiB/产物、512MiB累计；不启动E或完整Main/模型。

全部失败、raw与成本保留；新env仅允许锁定最小NumPy，不装GUI/SciPy。启动时实际产品/NumPy/模型调用0。
