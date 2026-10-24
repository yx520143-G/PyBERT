# #5 schema 与历史验证适用性补充 v3

追加记录，不改 v1/v2。完整格式只接受已发布 raw schema 2/3/4。早期 #2 `043542` 未带 raw_schema 的研究工件在 `saved-roundtrip-20261024-102330` 被拒绝；更正输入选择为 #2 README 指定最终 `050800` raw2，随后 `102512` 的5组2053数组及所有图形payload exact，无新主计算。原拒绝报告保留，不将早期未版本化工件称作已支持archive版本。

`102512` 是未提交实现字节的历史验证，saved_by_adapter_sha 当时是文档HEAD `bd83b59`，不能当作已执行该Git tree。其当时未同步封存源码hash；最终将以固定实现后的saved-only补验建立源码字节适用性。旧报告、原NPZ/manifest与子记录不改写。

PM随后核实 #4 `chrome-20261024/final-idle.json` 保存了原linked COM `a803f4ca-83f2-4031-a31c-af5213fc71d8` 的完整task。新增验证使用该有来源hash的task、com-input/result原件与原终态/日志/取消/退出信息；`terminal.json` 该目录确未生成，保持 not_produced。原102512中task envelope absent的有限陈述由这份追加证据扩充，不覆盖原件。

草稿v2与本机配置快照v2独立于catalog顺序，按稳定field ID迁移schema1，保留完整SHA来源；未应用的有效/未知/非法字段保留原值与原因，禁止直接Run，用户可显式Load完整配置或恢复默认。非法JSON保留原键；读写失败与仿真错误分别报告。原schema1键不删除；只保存轻量输入和选择，未保存raw。

参考数组总预算1GiB/4条，临时成功缓存保持2条且每条数组上限768MiB；新成功超预算保留原两条，不将截断数组当完成。下载仅交付浏览器，不声称确认磁盘覆盖。原生tx_out=None边界、TIME/CTLE File/impulse_length/package+FEXT及#4默认COM未执行继续保留。
