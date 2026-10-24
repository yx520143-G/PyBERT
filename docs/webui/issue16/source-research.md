# #16 外部资源调查

2026-10-24。只读调查由 research agent 完成，唯一 owner 获取原件、整合、冻结和执行；调查阶段没有 PyBERT/skrf 数值调用或服务。所有外部原件、许可和接线源码存放在本 worktree `local/resources/`，不随 PR 再分发。精确长度、SHA256、格式、频率、Z0 与映射见 `resources.json` 和 `freeze-v1.json`。

## 本次采用

| 资源 | 来源与分类 | 端口依据与权限 |
| --- | --- | --- |
| `backplane_25g_xtalk.s8p` | SI-Forum / Rune Bæverrud，LinkLab 9000 manual v0.17.0 §11.6 已存在的 physical-model sample；**simulation/model，非实测**。 | 原文件 header 明确 victim TX+/TX−/RX+/RX− = 1/2/5/6，aggressor 3/4→7/8。后一对以相同 +/− 次序分析。公开 sample 供本地 import/evaluation；未找到明确再分发许可，原件及派生重排均仅本地保留。 |
| `TestWElementTest_testWElement3Pairs.s12p` | SignalIntegrity / Teledyne LeCroy / Nubis Communications 外部 W-element regression fixture；**simulation/model，非实测**。 | 原 single-ended net 与 `WElement.py` 定义导体 j→j+6；作者 `WireBond3Pairs.net` 将 (1,2)/(7,8)、(3,4)/(9,10)、(5,6)/(11,12) 接到 mixedmode 的 +/−。原件属于 GPL-3.0-or-later 仓库；保留完整 LICENSE 与作者源码。 |

S8P 的 [manual](https://www.si-forum.no/tools/linklab/manual) 与[原件入口](https://www.si-forum.no/siforum-static/eye/samples/backplane_25g_xtalk.s8p?v=1791651621)已下载保留。原 header 同时明确模型由 `make_samples.mjs` 制作，使用 dielectric/copper/impedance-step/via-stub 模型，不能因文件名而标成测量。

S12P 固定 source commit 为 `1922a1591100700aa8bd635964cd688012b8668d`，原件 Git blob 为 `fd236e9a54139fc8443f578b153ff2fe4ec5deb6`。文件历史最后修改为 PetePupalaikis 的 `4fa0bd7791e848f8988ae899ae9e2ca9bef2f113`（2020-11-10T23:40:55Z）；这是来源历史，不是本次生成模型。

- [固定原件](https://github.com/Nubis-Communications/SignalIntegrity/blob/1922a1591100700aa8bd635964cd688012b8668d/Test/TestSignalIntegrity/TestWElement/TestWElementTest_testWElement3Pairs.s12p)
- [single-ended net](https://github.com/Nubis-Communications/SignalIntegrity/blob/1922a1591100700aa8bd635964cd688012b8668d/Test/TestSignalIntegrity/TestWElement/TestWElementTest_testWElement3Pairs.net)、[作者 mixed-mode 接线](https://github.com/Nubis-Communications/SignalIntegrity/blob/1922a1591100700aa8bd635964cd688012b8668d/Test/TestSignalIntegrity/TestWElement/WireBond3Pairs.net)
- [WElement circuit](https://github.com/Nubis-Communications/SignalIntegrity/blob/1922a1591100700aa8bd635964cd688012b8668d/SignalIntegrity/Lib/SParameters/Devices/WElement.py)、[converter 的 +/−/D/C 与 √2 normalization](https://github.com/Nubis-Communications/SignalIntegrity/blob/1922a1591100700aa8bd635964cd688012b8668d/SignalIntegrity/Lib/Devices/MixedModeConverter.py)
- [原测试](https://github.com/Nubis-Communications/SignalIntegrity/blob/1922a1591100700aa8bd635964cd688012b8668d/Test/TestSignalIntegrity/TestWElement/TestWElement.py)固定 `df=0.001, Z0=50, scale=0.001`、100 GHz / 100 intervals；[原 RLCG 输入](https://github.com/Nubis-Communications/SignalIntegrity/blob/1922a1591100700aa8bd635964cd688012b8668d/Test/TestSignalIntegrity/TestWElement/wires_1mil_80um_3.8_3pair.txt)注明 MMTL/NMMTL_2DLF simulation、2020-11-10、6 signal conductors / 1 ground plane / 4 ground wires。
- [许可证](https://github.com/Nubis-Communications/SignalIntegrity/blob/1922a1591100700aa8bd635964cd688012b8668d/LICENSE.txt)、[历史提交](https://github.com/Nubis-Communications/SignalIntegrity/commit/4fa0bd7791e848f8988ae899ae9e2ca9bef2f113)

L1/L2/L3 与 Tx=左/Rx=右是本次声明的分析方向标签；没有把它写成仪器测量标注。只进行 port permutation 与 DB/MA→RI 表示转换，全部导体和频率点保留。独立 expected 从原 SE 矩阵和作者接线构造，未使用派生输入的 PyBERT mapping/helper。

## 排除与缺口

- 旧 `TwoLaneModel.s8p` 仅保留对照：原件 SHA256 `0f6cbb032432eadc8c1bee4f382ef25e3c06fe0718fae07fc835e495067d5abf`，330007 bytes；旧 #13 全部 raw/失败与预算未改，新验证不重复计算旧 baseline。
- `WireBond3Pairs.s12p` / `WireBond3PairsWElement.s12p` 已是 mixed-mode 输出，不能再当 SE12 做差分变换。
- `TransmissionLineSimulation.s8p` 对应单个 tline、R40/R65、couplers、current-to-voltage 和八个 voltage outputs；不是 two-lane SE8 通道。[原 net](https://github.com/Nubis-Communications/SignalIntegrity/blob/1922a1591100700aa8bd635964cd688012b8668d/Test/TestSignalIntegrity/TransmissionLineSimulation.net)
- Molex `SP-170382-0001_RevE2.s8p` 有[官方 electrical-model report](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/electricalmodeldocumentpdf/170/170382/1703820001-000.pdf)，但本次未取得原模型 ZIP，未用于计算。[当前产品页](https://www.molex.com/en-us/products/part-detail/1703820001)显示 limited information；调查 agent 的直接页面请求曾 20 秒超时。报告是 HFSS 模型且印 CONFIDENTIAL；[Legal](https://www.molex.com/en-us/about/legal)没有授予一般再分发许可。
- [Xilinx DesignCon 2015 原演示](https://www.xilinx.com/publications/events/designcon/2015/tu2slides-ibis-ami-model-simulations-over-six-eda-platforms.pdf)提及实测 S12P；未找到同时具备原文件、物理端口和权限依据的数据入口，不能据此补为实测。
- [IEEE 官方 tools 目录](https://www.ieee802.org/3/dj/public/tools/index.html)与 [Design C 包](https://www.ieee802.org/3/dj/public/tools/c2m/lim_3dj_06_2309.zip)是另外的模型候选；没有下载、计算，也没有启动历史 COM。

**硬件实测 plain S8P 与 S12P 均为 SOURCE_BLOCKED / NOT_EXECUTED。** 这两项不随模型对照通过而升级。

## 实际检索路线

1. 本机 `rg --files E:/ -g '*.s8p' -g '*.s12p' -g '*.S8P' -g '*.S12P'` 文件名调查，找到 SignalIntegrity 公开副本及既有项目产物；未改动或在 SerDes 路径启动计算。后续采用公开原作者固定来源重新取得文件。
2. SignalIntegrity repository redirect、recursive Git tree、fixture 历史、net/test/device 原源码；GitHub `extension:s8p` / `extension:s12p` 检索。它们是检索范围，不表示完整互联网清单。
3. Web 查询 `s8p/s12p + measured/download/Touchstone`，对 Samtec、Molex、Hirose、IEEE、MathWorks、Xilinx、Teledyne SPARQ 定向调查。owner 另查 `"s8p" "measured" channel download`、`"s8p" "zip" Molex`、`"s8p" "coupled" "github.com"`、`"s8p" "Touchstone" "download" "connector"`，GitHub API `extension:s8p backplane` 返回 0。

没有猜测缺失 port map，没有以非 plain domain 代替文件覆盖，没有自行生成新 S12P。下游仅使用冻结的 native 端接与原 producer；不作标准、硬件或全端口/速率推广。
