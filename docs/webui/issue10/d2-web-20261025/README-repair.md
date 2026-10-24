# D2 修复轮交付（PR #33）

本记录是当前修复轮入口；README.md、validation-summary.json/v2、independent-review.md/v2 和 seal1 均保留各自历史阶段，不能视作当前候选的完整验收。PM原审查 [5640070393](https://github.com/yx520143-G/PyBERT/pull/33#pullrequestreview-5640070393) 的两个实现错误及自审发现的整数问题均已最小修复，仍交PM fresh review。

worker 收尾变量改为partial_snapshot，实际源码AST/symtable从 base global→9331 local→fixed global；Main调用参数AST不变。浮点时间轴按timestamp/相邻差ULP建立表示误差界，保留原t、firstintervalts、窗口和FFT。整数轴不借用浮点容差：原整数diff精确相等、原timestamp顺序和正diff检查，拒unsignedwrap/overflow掩盖；诊断分别标明规则。analysis静态接入uniform_grid_validation元数据。

## 验证边界

- 15red：实际高原点float网格nonuniform错误与worker作用域检查各失败，原件保留。16green：2用例通过，仅16点actualperiodseam + actualworkerAST/symtable；fullworker未运行。
- 自审新增integerP2后，在16/16cap处停止；[PM6389806920](https://github.com/yx520143-G/PyBERT/issues/10#issuecomment-6389806920) 批准仅16→18。17red的6个subtest失败及unsignedscalaroverflowwarning保留；18green2methods0fail，只验证已批准6组三点signed/unsigned合法/非均匀/倒退/大整数间隔相差1。18只对两个合法输入执行FFT，四个无效输入无FFT。
- 14实际协调器green继续只属于source75004b3；没有当前worker/clocks/analysis的完整collect重跑。float最后actualgreen source2aa3e7d，当前float/FFT关键赋值静态相同；18只integeractualgreen，输入sourcef94a782。各自source/test/runner/receipt绑定独立保留。

## 最终账目与限制

累计pure17315/25000，A5264/9000、B98/3000、C7910/8000、D42/999；launch18/18、guardedchildren17、NumPyimports16。新17/18每入口period_projection/validate_period各6，redpure12+green12、hist6+6、rfft6+2，严格用完获批24pure/12hist/8rfft增量。所有旧失败入口/genexpr/pairs分类不改。完整账目见validation-summary-v3.json、cost-ledger-v3.json；child/launcher有包含关系不相加，taskwall/RSS UNKNOWN。

独立复审Standards0；Specwrong0/scope0/partial1（independent-review-v3.md）。JSON14逐次elapsed仍UNKNOWN，完整序列化计时符合性未证明；02hostcopy时间、08/10malformedbuffer、08原4001blocked、13预检、首次seal组装失败、15/17red等全部历史原件/费用/缺口保留。原9331交付与external final-seal.json不覆盖；新封条以原fullmanifest+完整delta重建当前全tracked文件绑定，避免重复写大manifest并保持新增材料cap。PM可按父封条SHA、delta、全pathset及重建manifestSHA核对。

protected-final-check-v3.json再次核对旧16repos/271metadata/4874raw/2394materials+installed/16dirs、D1/#30seals、新952installedfiles及旧D2runs/launches。新seal另绑定01–18全部原件与当前source/Gitblob/HEAD/tree/clean；旧01–16不改写。

所有完整Main/run_worker/Execution.capture/DFE/decide/decode/真实trellis/modelABI/PyAMI/SciPy/数值RNG/COMcoopt/GUI/CLI/fullsuite/rootcollect/E均0。本轮是有界软件修复与静态接线证据，不是完整worker或模型资格。仅原DraftPR33 Refs10，owner固定提交后停写停测返权；不merge/关#10，#4默认COM与#1最终review/备份/私有化gate保持。
