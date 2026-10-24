/* Source-backed, presentation-only catalog. No simulation code is loaded. */
(() => {
  const root = 'https://github.com/capn-freako/PyBERT/blob/1bc905d577d2f3bd9471421cfbf3d422d4e6080e/';
  const ref = (file, line) => ({ file, line, url: `${root}${file}#L${line}` });
  const traits = line => ref('src/pybert/pybert.py', line);
  const pipeline = line => ref('src/pybert/models/bert.py', line);
  const p = (key, label, value, range, description, extra = {}) => ({ key, label, value, range, description, ...extra });
  const group = (title, source, params, note = '') => ({ title, source, params, note });
  const map = (title, text, source) => ({ title, text, source });
  const txRows = [
    ['Pre-tap3', '−3 UI', '关闭', '0', '−0.05 … +0.05', '0.025'],
    ['Pre-tap2', '−2 UI', '启用', '0', '−0.10 … +0.10', '0.05'],
    ['Pre-tap1', '−1 UI', '启用', '0', '−0.20 … +0.20', '0.10'],
    ['Cursor', '0 UI', '自动', '1', '1 − Σ|其他 taps|', '—'],
    ['Post-tap1', '+1 UI', '关闭', '0', '−0.20 … +0.20', '0.10'],
    ['Post-tap2', '+2 UI', '关闭', '0', '−0.10 … +0.10', '0.05'],
    ['Post-tap3', '+3 UI', '关闭', '0', '−0.05 … +0.05', '0.025']
  ];

  const stages = [
    {
      id: 'source', number: '01', category: 'main', name: 'Source', title: '数据源与调制', icon: 'bits',
      summary: '从 PRBS 比特生成符号，再按每 UI 的采样网格展开。',
      location: 'Config. / Simulation Control', input: 'Pattern · Seed · Modulation', output: 'bits → symbols → x',
      mapping: [
        map('符号生成', 'NRZ 为二电平。普通 PAM-4 采用 Gray 映射 −1、−1/3、+1/3、+1，再乘 vod。Duo-binary 先做 XOR 预编码。', traits(633)),
        map('波形展开', 'repeat(symbols, nspui) 产生过采样波形。这里没有独立 DAC 位数、ADC 量化或模拟上升时间旋钮。', pipeline(202)),
        map('比特率与符号率', 'bit_rate 的单位是 Gbps。普通 PAM-4 的 UI 为 2 / (bit_rate × 10⁹) 秒；NRZ 为 1 / (bit_rate × 10⁹) 秒。', traits(651))
      ],
      groups: [
        group('速率与调制', traits(153), [
          p('bit_rate', 'Bit Rate · 比特率', '10 Gbps', '0.1–250 Gbps', '普通 PAM-4 每个符号承载 2 bit，符号率是比特率的一半。'),
          p('mod_type', 'Modulation · 调制', 'NRZ', 'NRZ / Duo-binary / PAM-4', '选择符号电平与编码方式。'),
          p('rlm', 'RLM · 电平失配指标', '0.95', 'Float · 无量纲', '原 GUI 位于 Rate & Modulation，PAM-4 时可编辑。当前计算只被 MMSE 使用，不改变时域 PAM-4 电平。', { status: 'optimizer', source: ref('src/pybert/gui/view.py', 124) }),
          p('vod', 'Vod · 发射电压尺度', '1 V', 'Float · 无显式上下限', '对符号电平乘以电压尺度；后续 Channel 包含端接分压。', { source: traits(275) })
        ]),
        group('测试码型', traits(156), [
          p('pattern', 'Pattern · 测试序列', 'PRBS-7', 'PRBS-7 / 9 / 11 / 13 / 15 / 20 / 23 / 31', '选择 LFSR 产生的伪随机序列。'),
          p('seed', 'Seed · 随机种子', '1', '整数；0 = 每次随机', '非零种子用于 PRBS 和随机噪声的可重复生成。')
        ], 'Nbits、EyeBits 与 nspui 属于全局仿真网格，可在“仿真与分析网格”查看。')
      ]
    },
    {
      id: 'tx', number: '02', category: 'main', name: 'Tx EQ', title: '发送端均衡', icon: 'filter',
      summary: 'Native 使用 UI 间隔的 FIR；也可由 Tx IBIS-AMI 模型提供均衡。',
      location: 'Equalization / Tx Equalization', input: '符号波形 x', output: 'Tx + Channel 累积响应',
      mapping: [
        map('3 前游标 + 主游标 + 3 后游标', 'GUI 提供 6 个非主游标 tap。主游标按 1 − Σ|其他 taps| 自动计算，不在表格中单独编辑。', traits(734)),
        map('物理关系与实现顺序', 'Native 主链先将 Tx FIR 与 Channel 脉冲响应卷积，再作用于输入 x。tx_out_h 表示 Tx + Channel，不是裸 Tx 引脚。', pipeline(340)),
        map('电气模型独立选择', 'tx_eq_sel 只控制均衡实现；tx_sel、rs、cout 属于 Channel 两端的电气建模，不与 AMI 模式合并成同一个开关。', traits(271))
      ],
      groups: [
        group('均衡实现', traits(273), [
          p('tx_eq_sel', 'EQ implementation · 均衡实现', 'Native', 'Native / IBIS-AMI', 'AMI 需有效的 IBIS、AMI 配置与平台动态库。'),
          p('tx_taps[].enabled', 'Tap enable · 启用抽头', 'Pre-tap2 / Pre-tap1 开启', 'Boolean · 每个非主游标 tap', '禁用 tap 在 FIR 中取 0。', { condition: 'Native Tx' }),
          p('tx_taps[].value', 'Tap value · 抽头权重', '全部 0', 'Float · 无量纲', '即使默认有两个 tap 开启，权重为 0 也不会产生预加重。', { condition: 'Native Tx' })
        ]),
        group('优化约束（与实际 Tx taps 分离）', traits(208), [
          p('tx_tap_tuners', 'Tx FFE search · 搜索表', '原生构造默认', 'enabled / min / max / step', 'Value 为所选优化获选候选，只读；显式 Use EQ 才修改实际 Tx taps。'),
          p('tx_c0_min', 'Minimum cursor · 最小主游标', '0', '无量纲', '原生 coopt 排除 cursor<=0 或低于此约束的 Tx 组合。')
        ])
      ],
      tables: [{ title: 'Native Tx tap 配置', columns: ['Tap', '位置', '初始状态', '初值', '优化范围', '优化步长'], rows: txRows, note: '范围与步长来自独立的 tx_tap_tuners；手动 Tx 权重与优化器搜索设置不是同一个对象。', source: traits(208) }]
    },
    {
      id: 'channel', number: '03', category: 'main', name: 'Channel', title: '互连与两端电气模型', icon: 'channel',
      summary: '将 Tx 端接、互连、Rx 端接合成通道响应；可选器件封装路径替换 lumped 端接。',
      location: 'Config. / Channel', input: 'Native 模型或通道文件', output: 'chnl_h · chnl_H · FEXT 响应',
      mapping: [
        map('Channel 的边界', 'rs/cout、rin/cin 的影响在 calc_chnl_h() 中并入通道。主链不再额外串接一个“Tx analog”或“Rx analog”滤波级。', traits(1430)),
        map('文件串接', 'multiple 模式将 ch_files 按顺序用网络 cascade 运算串接。只有选择相应 inter_sel，文件列表才生效。', traits(1446)),
        map('可选封装模型', 'pkg_enable 使用 Tx device ** channel ** Rx device 后再端接。该路径使用加入 IBIS on-die S 参数之前的网络。', traits(1388)),
        map('多 lane 边界', '单次选择一个 victim，其他 lane 可提供 FEXT 响应；并未为每条 lane 建立独立 Tx、Rx 或 CDR。', traits(1602))
      ],
      groups: [
        group('互连来源', traits(177), [
          p('inter_sel', 'Interconnect · 通道来源', 'native', 'native / single / multiple', '原生解析模型、单文件、多个文件串接。'),
          p('ch_file', 'Single File · 通道文件', '空', '.s2p / .s4p / .s8p / .s12p / .csv / .txt', 'GUI 支持的单文件入口。', { condition: 'inter_sel = single' }),
          p('ch_files', 'Multiple Files · 有序列表', '[]', 'GUI：single-ended .s4p', '文件按列表顺序串接。', { condition: 'inter_sel = multiple' }),
          p('renumber', 'Fix port numbering · 端口修正', 'False', 'Boolean', '检测并修正 4-port through-path 编号约定。', { condition: 'GUI 非 native 时可编辑' }),
          p('use_window', 'Apply window · 频域窗', 'False', 'Boolean', 'IFFT 前应用 raised-cosine 窗。GUI 在 native 时禁用编辑，但计算代码仍会读取已有值。'),
          p('lane_sel', 'Victim Lane · 受害通道', '0', '.s8p：0–1；.s12p：0–2', '索引从 0 开始，选择单文件内的 victim lane。', { condition: 'single + .s8p / .s12p' }),
          p('vita_end', 'VITA segment end · 段方向', 'None', 'None / tx / rx', '底层 import_channel/import_freq 的 VITA 68.x 提取参数；主 GUI 没有传递它。', { scope: 'api', source: ref('src/pybert/utility/sparam.py', 395) })
        ]),
        group('Native 损耗模型', traits(189), [
          p('l_ch', 'Length · 通道长度', '0.5 m', 'Float · 无显式上下限', 'Howard Johnson UTP 参数化通道的长度。'),
          p('Z0', 'Z0 · 差分特性阻抗', '100 Ω', 'Float · 无显式上下限', 'LC 区的特性阻抗。'),
          p('v0', 'v_rel · 相对传播速度', '0.67 c', 'Float · 无显式上下限', '以光速 c 为单位。'),
          p('Rdc', 'Rdc · 直流电阻', '0.1876 Ω/m', 'Float · 无显式上下限', '实际是单位长度电阻，GUI 单位标签简写为 Ohms。'),
          p('R0', 'R0 · 趋肤效应电阻', '1.452 Ω/m', 'Float · 无显式上下限', '频率相关损耗模型的电阻参数。'),
          p('w0', 'ω0 · 过渡角频率', '10⁷ rad/s', 'Float · 无显式上下限', '这是角频率，不能将默认值直接读作 10 MHz。'),
          p('Theta0', 'Loss tangent · 损耗角正切', '0.02', 'Float · 无量纲', '描述介质损耗。')
        ], '这一组仅在 inter_sel = native 时用于生成互连。'),
        group('Tx / Rx 电气端接', traits(271), [
          p('tx_sel', 'Tx electrical · 电气来源', 'native', 'native / ibis', '电气模型来源与 tx_eq_sel 相互独立。'),
          p('rs', 'Tx_Rs · 差分源阻抗', '100 Ω', 'Float · 无显式上下限', 'Native Tx 端接。', { condition: 'Native Tx；pkg_enable 关闭' }),
          p('cout', 'Tx_Cout · 每 pin 电容', '0.5 pF', '0.001–1000 pF', 'Native Tx 寄生输出电容。', { condition: 'Native Tx；pkg_enable 关闭' }),
          p('rx_sel', 'Rx electrical · 电气来源', 'native', 'native / ibis', '电气模型来源与 rx_eq_sel 相互独立。', { source: traits(306) }),
          p('rin', 'Rx_Rin · 差分输入阻抗', '100 Ω', 'Float · 无显式上下限', 'Native Rx 端接。', { condition: 'Native Rx；pkg_enable 关闭', source: traits(310) }),
          p('cin', 'Rx_Cin · 每 pin 电容', '0.5 pF', 'Float · 无显式上下限', 'Native Rx 寄生输入电容。', { condition: 'Native Rx；pkg_enable 关闭', source: traits(311) }),
          p('cac', 'Rx_Cac · AC 耦合电容', '1 μF', 'Float · 无显式上下限', '界面与配置保留该字段，但 calc_chnl_h() 中读取语句已注释，当前主链不使用。', { status: 'unused', source: traits(1441) })
        ])
      ]
    },
    {
      id: 'noise', number: '+', category: 'main', name: 'Noise', title: '电压噪声与 FEXT 注入', icon: 'noise',
      summary: '一个加法注入点。Native 下位于 Tx + Channel 之后、CTLE 之前。',
      location: 'Config. / Tx Level & Noise · Misc.', input: '周期噪声 · Gaussian 噪声 · FEXT', output: '加入接收输入的显式噪声',
      mapping: [
        map('Native 注入位置', 'rx_in = convolve(x, tx_out_h) + noise。虽然 GUI 将 Rn/Pn 放在 Tx Level & Noise，它们在全 Native 主链中加到 Channel 后。', pipeline(340)),
        map('周期噪声的形状', '矩形波通过固定 1 MHz 的二阶高通以模拟电容耦合。pn_freq 不是正弦时间抖动频率设置。', pipeline(245)),
        map('FEXT 的来源', 'Channel 提取 FEXT 响应，再与和 victim 相同的 x 波形卷积。不是各 aggressor 独立生成随机 PRBS。', pipeline(262)),
        map('AMI 组合限制', 'Native/Init Tx + Rx Init 时 noise 在 Rx AMI 输出后加入；Rx GetWave 时随 rx_in 输入。Tx GetWave 分支的下游当前未使用含 noise 的 rx_in。', pipeline(306))
      ],
      groups: [group('注入设置', traits(278), [
        p('rn', 'Rn · 随机电压噪声', '0.01 V RMS', 'Float · 无显式上下限', 'Gaussian 随机噪声的标准差。'),
        p('pn_mag', 'Pn · 周期噪声幅度', '0.01 V', 'Float · 无显式上下限', '矩形周期噪声源的幅度，随后进行高通滤波。'),
        p('pn_freq', 'f(Pn) · 周期噪声频率', '11 MHz', 'Float · 无显式上下限', '决定周期噪声源的周期。'),
        p('include_fext', 'Include FEXT · 加入串扰', 'False', 'Boolean', '其他 lane 作为 aggressors；响应由 Channel 提供。', { condition: 'GUI：single + .s8p / .s12p', source: traits(184) })
      ])]
    },
    {
      id: 'ctle', number: '04', category: 'main', name: 'Rx CTLE', title: '连续时间线性均衡', icon: 'filter',
      summary: '一零点、二极点的 Native CTLE。改变频率响应形状，补偿通道高频损耗。',
      location: 'Equalization / Rx Equalization / Native / CTLE', input: 'rx_in', output: 'ctle_out · ctle_out_h',
      mapping: [
        map('响应模型', '两个极点由 peak_freq 与 rx_bw 决定，零点由 peak_mag 决定。频率响应按最大幅度归一化；boost 不是独立的宽带电压增益。', ref('src/pybert/utility/sigproc.py', 313)),
        map('Native 开关', 'ctle_enable=False 时，全 Native 路径直接令 ctle_out=rx_in，旁路整个 CTLE 模型。', pipeline(410)),
        map('AMI 替代', 'Rx 使用 AMI 时，ctle_out 这个变量保存的是 Rx AMI 输出；它不再代表这个 Native CTLE 的输出。', pipeline(357)),
        map('文件导入现状', 'File 入口保留，但源码有明确 FIXME：import_channel() 返回 Network，此处仍将结果当作数组处理。', pipeline(275))
      ],
      groups: [
        group('实现与使能', traits(307), [
          p('rx_eq_sel', 'Rx EQ implementation · 实现', 'Native', 'Native / IBIS-AMI', 'Rx AMI 替代 Native CTLE；电气端接仍由 rx_sel 独立选择。'),
          p('ctle_enable', 'Enable · CTLE 开关', 'True', 'Boolean', '全 Native 主链中关闭后直接旁路 CTLE。', { condition: 'Native Rx' }),
          p('ctle_sel', 'Response source · 响应来源', 'Native', 'Native / File', '解析模型或外部响应文件。', { condition: 'Native Rx' })
        ]),
        group('Native 频率响应', traits(324), [
          p('peak_freq', 'CTLE fp · Peaking 频率', '5 GHz', 'Float · 无显式上下限', 'CTLE peaking 参数频率，同时用于确定一个极点。', { condition: 'Native CTLE 已启用' }),
          p('rx_bw', 'Bandwidth · 自然带宽', '12 GHz', 'Float · 无显式上下限', '未均衡信号路径的带宽参数，用于确定另一个极点。', { condition: 'Native CTLE 已启用' }),
          p('peak_mag', 'CTLE boost · 相对提升', '1.7 dB', 'Float · 无显式上下限', '控制零点位置和高低频响应的相对关系。', { condition: 'Native CTLE 已启用' })
        ]),
        group('外部响应', traits(321), [
          p('ctle_file', 'Filename · 响应文件', '空', 'GUI 过滤 .csv', '当前导入实现带 FIXME，不能把存在文件入口理解为路径已经验证可用。', { status: 'limitation', condition: 'ctle_sel = File', source: pipeline(275) }),
          p('use_ctle_file', 'File mode flag · 内部状态', 'False', 'Boolean', '由 ctle_sel 同步设置，不是额外的独立 GUI 开关。', { scope: 'internal', source: traits(1269) })
        ]),
        group('Native 优化约束', traits(251), [
          p('ctle_enable_tune', 'Optimize CTLE · 优化使能', 'True', 'Boolean', '与普通 CTLE 开关分离，显式 Use EQ 才应用。'),
          p('peak_freq_tune', 'Tuning fp · 优化频率', '5 GHz', 'GHz', 'Native coopt 的固定 peaking 频率。'),
          p('rx_bw_tune', 'Tuning BW · 优化带宽', '12 GHz', 'GHz', 'Native coopt 的固定带宽。'),
          p('min_mag_tune / max_mag_tune / step_mag_tune', 'Boost search · 提升网格', '2 / 12 / 1 dB', 'min / max / step', '预计候选数与预算见 Native EQ 优化工作区。'),
          p('peak_mag_tune', 'Selected boost · 获选结果', '未选候选', 'dB · 只读', '属于所选 opt ID，不自动写入普通 CTLE。')
        ])
      ]
    },
    {
      id: 'rxffe', number: '05', category: 'main', name: 'Rx FFE', title: '接收端前馈均衡', icon: 'taps',
      summary: '固定 FIR 系数。在当前时域仿真中不自行训练，通常由 Optimizer 或手工配置提供。',
      location: 'Equalization / Rx Equalization / Native / FFE', input: 'ctle_out', output: 'ffe_out · ffe_out_p',
      mapping: [
        map('直接构造 FIR', '主流程直接读取 rx_taps 的 enabled/value，以 1 UI 间距插零构造响应。它不调用 rx_ffe 属性中的隐式 cursor 规则。', pipeline(476)),
        map('优化与应用', 'Optimize EQ 先计算系数；Use EQ 将结果写回 rx_taps。仅运行仿真不会自动更新 Rx FFE。', ref('src/pybert/gui/handler.py', 169)),
        map('当前初始化细节', '类声明 Npre=4，但构造函数立即改为 5。静态推导唯一 unity tap 在 index 2、标签 Pre-tap3，Cursor 标签位于 index 5；默认仍只是纯延时。', traits(524)),
        map('Rx AMI 条件', 'rx_use_ami=True 时 Native Rx FFE 在仿真中被旁路，实际 rx_taps 保留；切换回调禁用的是 FFE 搜索表 ffe_tap_tuners。', pipeline(480))
      ],
      groups: [group('结构与权重', traits(367), [
        p('rx_n_taps', 'Ntaps · 总 tap 数', '15', 'Int；内部预建 100 taps', '负值改为 0；当前没有严格的 100 上限输入校验。'),
        p('rx_n_pre', 'Npre · 前游标 tap 数', '5（初始化后）', 'Int · 无统一显式范围', '类声明为 4，构造时改为 5，重排 tap 位置与标签。'),
        p('rx_taps[].enabled', 'Tap enable · 启用', '前 15 项', 'Boolean · 每 tap', 'Ntaps/Npre 改变会更新使能与位置；界面也可逐项勾选。'),
        p('rx_taps[].value', 'Tap value · 固定权重', '一项为 1，其余为 0', 'Float · 无量纲', 'Native 运行时使用的 FIR 系数；不进行 LMS 自适应。'),
        p('ffe_tap_tuners[].min_val / max_val', 'Search bounds · 权重范围', '−1 / +1', 'Float · 无量纲', '在 Optimizer 中设置；不是时域仿真时的自动裁剪。', { status: 'optimizer', source: traits(117) }),
        p('ffe_tap_tuners[].step', 'Search step · 搜索步长', '0.1', 'Float · 无量纲', '非 MMSE 的 Rx FFE 枚举搜索使用。', { status: 'optimizer', source: traits(117) })
      ])]
    },
    {
      id: 'dfe', number: '06', category: 'main', name: 'DFE / Slicer', title: '反馈均衡与符号判决', icon: 'feedback',
      summary: '历史判决生成反馈，求和节点扣除后游标 ISI；CDR 决定采样时刻，AGC 调整判决参考。',
      location: 'Equalization / Native / DFE · Optimizer / Rx DFE', input: 'ffe_out + 历史判决', output: 'dfe_out · decisions · bits_out_dfe',
      mapping: [
        map('反馈环', '求和节点计算 x − Σ(weight × decision)。在恢复时钟处做判决，并以误差更新 tap；自适应修正在 CDR 锁定后进行。', ref('src/pybert/models/dfe.py', 342)),
        map('关闭反馈仍有接收判决', '没有启用 tap 时创建 dummy DFE，仍提供 CDR、采样与比特判决。不能把“关闭 DFE”画成整个接收端消失。', pipeline(503)),
        map('连续 taps', '从 Tap1 开始读取连续启用的前缀，遇到第一个 disabled 即停止。不支持通过留空勾选表达 sparse/floating taps。', pipeline(522)),
        map('初值与训练结果', '通常每次仿真从零权重开始。MM 时钟模式会以预估 post-cursor 初始化 Tap1；优化器显示的 DFE value 不是时域训练初值。', pipeline(537))
      ],
      groups: [
        group('自适应与判决', traits(349), [
          p('gain', 'Gain · 误差反馈增益', '0.1', 'Float · 无量纲', '控制 decision-directed tap 修正量。'),
          p('n_ave', 'Nave · 更新间隔', '100', 'Float trait；语义为时钟计数', '累计平均修正量，锁定后每 n_ave 个时钟更新 tap。'),
          p('decision_scaler', 'Level · 判决电平尺度', '0.5 V', 'Float · 无显式上下限', '决定判决输出尺度及 PAM-4 等阈值；Use AGC 开启后会被更新。')
        ]),
        group('求和节点', traits(350), [
          p('sum_ideal', 'Ideal · 理想求和', 'True', 'Boolean', '理想无限带宽求和节点。'),
          p('sum_bw', 'Bandwidth · 求和带宽', '12 GHz', 'Float · 无显式上下限', '非理想节点的低通带宽。', { condition: 'sum_ideal = False' })
        ]),
        group('DFE tap 约束', traits(227), [
          p('dfe_tap_tuners[].enabled', 'Tap enable · 启用', 'Tap1–5；共 20 槽位', 'Boolean · 按行编辑', '原 GUI 可以逐行设置；引擎只取首个禁用 tap 之前的连续前缀。Disable All/Enable All 操作整组。'),
          p('dfe_tap_tuners[].min_val / max_val', 'Limits · 自适应边界', '按 tap 设定，见下表', 'Float · 无量纲', '运行时用于限制 DFE 系数。'),
          p('dfe_tap_tuners[].value', 'Optimized weight · 优化结果', '0', '只读结果', 'GUI 显示优化权重；仿真不会把它们直接当作训练初始权重。', { status: 'optimizer' })
        ])
      ],
      tables: [{ title: 'DFE 默认约束', columns: ['Tap', '启用', '最小权重', '最大权重'], rows: [['Tap1', '是', '−0.20', '+0.40'], ['Tap2', '是', '−0.15', '+0.15'], ['Tap3–5', '是', '−0.05', '+0.10'], ['Tap6–20', '否', '−0.05', '+0.10']], source: traits(227) }]
    },
    {
      id: 'analysis', number: '07', category: 'main', name: 'Observe', title: '误码与链路观察', icon: 'eye',
      summary: '观察多个中间节点，比较判决结果并绘制响应、眼图、抖动和浴盆曲线。',
      location: 'Responses · Results · Jitter', input: '中间波形 + 判决比特 + 参考比特', output: '误码计数 · 波形与统计',
      mapping: [
        map('测量，而非硬件处理级', 'Channel-only、Tx+Channel、CTLE、DFE 等节点分别提供观察数据。这里是旁路观察与分析，不是串接的接收器件。', pipeline(777)),
        map('比较窗口', '对末段 eye_bits 做相关对齐后比较比特。有限记录的零误码仅描述该记录，不能直接证明任意低目标 BER。', pipeline(603)),
        map('结果保存', '.pybert_data 保存的是指定响应/波形数组，不是整个对象或所有标量指标的完整快照。', ref('src/pybert/results.py', 35))
      ],
      groups: [group('观察指标', pipeline(603), [
        p('n_errs_dfe', 'DFE bit errors · 误码数', '运行后产生', '非负整数', 'DFE/Slicer 判决比特的误码计数。', { scope: 'output' }),
        p('n_errs_viterbi', 'Viterbi bit errors · 误码数', '未启用运行时为 −1', '整数；−1 = 未执行', 'Viterbi 路径另算一套判决结果。', { scope: 'output' }),
        p('Responses / Eyes / Jitter', 'Response & eye views · 图表', '运行后产生', '响应 / 波形 / 眼图 / 抖动频谱', '真实图表由 PyBERT 计算，本页面只展示模块说明。', { scope: 'output' }),
        p('Bathtubs', 'Crossing-jitter bathtub · 浴盆曲线', '运行后产生', '时间偏移与误码概率估计', '基于过零时间抖动；不能代替所有 PAM-4 电压眼高/噪声评估。', { scope: 'output', source: pipeline(1297) })
      ])]
    },
    {
      id: 'cdr', number: '↳', category: 'control', name: 'CDR', title: '时钟恢复与采样时刻', icon: 'clock',
      summary: '与 DFE/判决耦合的控制环。Bang-Bang 是动态环路，Mueller-Muller 在这里使用固定锁定相位。',
      location: 'Equalization / Native / CDR', input: 'DFE 求和节点的采样', output: 'clock_times · locked · UI estimate',
      mapping: [
        map('动态 Bang-Bang', '根据上一时钟点、边界点与当前时钟点的样本更新 UI/相位估计。比例分支与积分分支共同修正时序。', ref('src/pybert/models/cdr.py', 78)),
        map('固定 Mueller-Muller 锁定点', '从 slicer 输入脉冲响应和 DFE Tap1 限制求固定相位，按标称 UI 采样、从开始视为 locked；不模拟 MM 环路捕获动态。', pipeline(537)),
        map('AMI 时钟请求', 'Rx GetWave + Use Clocks 还需要实际返回有效时钟，才能跳过 run_dfe()。双 GetWave 组合当前丢弃 Rx 返回时钟，不能仅凭勾选视为已经旁路。', pipeline(306))
      ],
      groups: [group('时钟恢复设置', traits(357), [
        p('cdr_type', 'Type · 时钟模式', 'Bang-Bang', 'Bang-Bang / Mueller-Muller', '选择动态环路或固定 MM 锁定相位。'),
        p('delta_t_ui', 'Delta-t · 比例步长', '0.001 UI', 'Float · 无显式上下限', '运行时乘当前 UI 换算为秒。', { condition: 'Bang-Bang' }),
        p('alpha', 'Alpha · 相对积分增益', '0.01', 'Float · 无量纲', '积分分支相对于比例分支的强度。', { condition: 'Bang-Bang' }),
        p('n_lock_ave', 'Lock Nave · 判定窗口', '500', 'Int · UI 估计数量', '锁定判定使用的历史窗口。', { condition: 'Bang-Bang' }),
        p('rel_lock_tol', 'Lock tolerance · 锁定容差', '0.1', 'Float · 相对量', '锁定判断的相对容差。', { condition: 'Bang-Bang' }),
        p('lock_sustain', 'Lock sustain · 锁定迟滞', '500', 'Int · 判定历史长度', '平滑锁定状态切换。', { condition: 'Bang-Bang' })
      ])]
    },
    {
      id: 'agc', number: '↳', category: 'control', name: 'AGC', title: '判决参考电平跟踪', icon: 'level',
      summary: '根据采样电平更新 Level 与判决阈值。它是判决器的控制功能，不是输入波形上的模拟 VGA。',
      location: 'Equalization / Native / DFE / Use AGC', input: 'slicer samples', output: 'decision_scaler · thresholds',
      mapping: [
        map('实际更新对象', 'run_dfe() 对采样绝对值做平均，再按调制更新 decision_scaler 和 thresholds；没有对输入信号乘以可调模拟增益。', ref('src/pybert/models/dfe.py', 390)),
        map('与 AMI clocks 的关系', '只有实际进入使用有效 AMI clocks 的独立采样分支，才跳过包含此 AGC 的 run_dfe() 循环。', pipeline(557))
      ],
      groups: [group('电平跟踪', traits(355), [
        p('use_agc', 'Use AGC · 连续跟踪', 'True', 'Boolean', '连续调整 DFE 的 decision_scaler；关闭时使用设置的 Level。'),
        p('agc_n_ave', 'Averaging window · 内部平均窗口', '100', 'DFE 构造函数参数', '底层 DFE 对采样与其均值进行两级平均；主 GUI 不暴露该参数。', { scope: 'api', source: ref('src/pybert/models/dfe.py', 94) })
      ])]
    },
    {
      id: 'viterbi', number: '↗', category: 'control', name: 'Viterbi / FEC', title: '可选序列检测与 FEC', icon: 'trellis',
      summary: '在 DFE/CDR 之后形成另一条判决结果。ISI 检测读取样本；FEC 解码读取硬判决 bit pairs。',
      location: 'Config. / Channel / Rx · Results / Viterbi', input: 'DFE samples 或硬判决比特', output: 'bits_out_viterbi · 独立误码计数',
      mapping: [
        map('ISI sequence detection', '按恢复时钟从 DFE 输出采样，结合该相位的脉冲响应与估计电压噪声进行序列检测。N 个符号组成一个状态，状态数为 Lᴺ。', pipeline(664)),
        map('内置 FEC 的边界', '源码是 rate-1/2 卷积编码：一输入 bit 变成两个编码 bit，再映射一个 PAM-4 符号。不是 Ethernet RS-FEC。', ref('src/pybert/models/fec.py', 24)),
        map('集成限制', 'FEC 分支之后存在未赋值局部变量引用风险。本页面记录源码入口，不将它呈现为已验证可运行的完整 FEC 工作流。', pipeline(688))
      ],
      groups: [group('解码与可视化', traits(341), [
        p('rx_use_viterbi', 'Use Viterbi · 启用', 'False', 'Boolean', '启用可选后处理判决分支。'),
        p('rx_viterbi_symbols', 'Trellis Depth · 状态符号数', '4', 'Int · ISI 状态数为 Lᴺ', '默认 NRZ 16 states、PAM-4 256 states；增加 N 会增大计算量。'),
        p('rx_viterbi_fec', 'FEC decoding · 卷积码路径', 'False', 'Boolean；FEC depth ≥ 2', '选择 FEC 并设置 PAM-4；当前主 GUI 无此开关。', { scope: 'api', status: 'limitation' }),
        p('trellis_pan_control', 'Position · 图表位置', '0', '0–trellis_max_x', '只移动 trellis 图表，不改变链路。'),
        p('trellis_err_select', 'Error · 定位误码', '0', '0–trellis_max_err', '跳转到指定误码位置。'),
        p('trellis_max_err', 'of · 误码总数', '0', 'GUI 只读', '原 Results / Viterbi 的误码总数显示；当前没有运行结果。', { scope: 'output', source: ref('src/pybert/gui/view.py', 976) })
      ])]
    },
    {
      id: 'simulation', number: '∷', category: 'tools', name: 'Simulation', title: '仿真与分析网格', icon: 'grid',
      summary: '全局时间、频率与分析窗口配置，控制各 stage 共享的数据规模和响应网格。',
      location: 'Config. / Simulation Control · Analysis Parameters', input: '运行与分析设置', output: '时间网格 · 频率网格 · 分析窗口',
      mapping: [
        map('全局上下文', '这些设置影响多个模块的响应构建与分析，不应插入信号链成为一个滤波器。nspui 表示仿真采样网格，不是 ADC 分辨率。', traits(431)),
        map('响应长度边界', 'Channel 自动裁剪使用 20–100 UI 与 0.999 保留能量。手动 impulse_length 在 Channel 与 CTLE 路径存在 ns/s 换算不一致。', traits(1578)),
        map('分析窗口', 'EyeBits 不仅用于眼图，也用于末段误码比较。较短码型重复次数会限制 jitter 分解的可信度。', traits(1339))
      ],
      groups: [
        group('时间与数据规模', traits(153), [
          p('nbits', 'Nbits · 测试比特数', '15000 bits', '1,000–10,000,000', '生成的测试序列长度。'),
          p('eye_bits', 'EyeBits · 末段分析窗口', '10160 bits', 'Int；超出 Nbits 时会被限制', '眼图与比特比较使用的末段长度。'),
          p('nspui', 'Samples/UI · 过采样数', '32', '2–256 samples/UI', '每 UI 的波形采样数。'),
          p('debug', 'Debug · 调试输出', 'False', 'Boolean', '额外日志信息，不是信号处理开关。')
        ]),
        group('频率与响应分析', traits(185), [
          p('f_max', 'fMax · 最大频率', '40 GHz', 'Float；编辑时受 Nyquist 限制', '用于建模、信号处理与绘图的频率上界。'),
          p('f_step', 'fStep · 频率步长', '10 MHz', 'Float · 无显式上下限', '构建 H(f) 的频率间隔。'),
          p('impulse_length', 'Impulse response length · 长度', '0 ns · 自动', '0=自动；非零=手动', '非零手动值在 Channel/CTLE 两处换算不一致，应单独验证。', { status: 'limitation' }),
          p('thresh', 'Pj threshold · 识别阈值', '3 σ', 'Float · 无显式上下限', 'jitter 频谱中识别周期分量的阈值。', { source: traits(174) })
        ])
      ]
    },
    {
      id: 'package', number: '↥', category: 'tools', name: 'Device models', title: '器件、封装与 partial host', icon: 'package',
      summary: '作为 Channel 的构成选择，采用 P802.3dj/D3.3 Annex 178A 预设。',
      location: 'Config. / Interconnect / Tx/Rx Device Models', input: 'Tx/Rx preset + 原始通道网络', output: '含器件模型的 channel response',
      mapping: [
        map('替换关系', '启用后替换 lumped rs/cout、rin/cin 通道路径。它不增加一个独立 EQ，也不与被替换的 lumped 端接重复串接。', traits(1554)),
        map('on-die 与 host', '封装路径使用 ch_s2p_pre，因而不复用已追加的 IBIS on-die 网络。若通道文件已包含 host PCB，需要辨别 partial host 是否重复。', traits(1388))
      ],
      groups: [group('器件预设', traits(313), [
        p('pkg_enable', 'Enable · 器件模型', 'False', 'Boolean', '使用对应 Tx/Rx 端接、封装与适用 host 模型；面向 Native 电气模型。'),
        p('pkg_group', 'Group · 预设族', 'KR', 'KR / C2C / CR / C2M', '决定 case 可选集合。'),
        p('tx_pkg_case', 'Tx case · 发送端预设', 'A1', 'KR/C2C：A1/A2/B1/B2；CR：HL/HN/HH；C2M：host/module', '选择 Tx 器件预设。'),
        p('rx_pkg_case', 'Rx case · 接收端预设', 'A1', '选项与 Group 对应', '选择 Rx 器件预设。'),
        p('pkg_include_host', 'Partial host · 主机段', 'True', 'Boolean', '对定义了 partial host 的 CR、C2M host 等预设生效。')
      ])]
    },
    {
      id: 'ami', number: '⇄', category: 'tools', name: 'IBIS-AMI', title: '外部模型与替代实现', icon: 'model',
      summary: 'IBIS 描述电气模型，AMI 描述算法模型。具体参数由加载的 .ami 文件定义。',
      location: 'Config. / Tx or Rx · Equalization / IBIS-AMI', input: '.ibs + .ami + DLL/SO', output: 'Init 响应或 GetWave 波形 / 时钟',
      mapping: [
        map('显示模式与真实字段', '地图的 Native / AMI Init / AMI GetWave 是便于浏览的组合。源码实际由 *_eq_sel 与 *_use_getwave 控制，不能只写 *_use_ami=True。', traits(1152)),
        map('能力约束', 'Init 要求 Init_Returns_Impulse；GetWave 要求 GetWave_Exists。本页面没有加载动态库，不显示虚构的 Valid 或模型返回结果。', ref('src/pybert/utility/ibisami.py', 116)),
        map('Rx AMI 切换', '原生回调禁用 dfe_tap_tuners 和 FFE 搜索表 ffe_tap_tuners；实际 rx_taps 保留并在仿真中旁路。本页只保存草稿，不执行此回调。没有有效 AMI clocks 时仍使用原生采样/CDR/判决；后续重新开启 DFE taps 时还可能叠加其反馈。', traits(1334)),
        map('双 GetWave 的时钟限制', 'Tx 与 Rx 均为 GetWave 时，当前分支没有保存 Rx 返回 clocks；Use Clocks 不能单独保证采用模型时钟。', pipeline(320))
      ],
      groups: [
        group('模型接入', traits(294), [
          p('tx_ibis_file / rx_ibis_file', 'IBIS file · 电气模型', '空', '.ibs', '先加载对应侧有效模型，可选择其 component / pin / model。'),
          p('tx_use_ts4 / rx_use_ts4', 'On-die S-parameters · 芯片网络', 'False', 'Boolean；模型须有 Ts4file', '在适用通道路径中加入 on-die 网络。'),
          p('tx_ami_file / rx_ami_file', 'AMI configuration · 参数声明', '空', '.ami；GUI 只读显示', '由所选 IBIS 模型关联，定义 Model_Specific 参数。'),
          p('tx_dll_file / rx_dll_file', 'Model library · 算法动态库', '空', '.dll / .so；GUI 只读显示', '选择与平台匹配的算法实现。'),
          p('tx_use_getwave / rx_use_getwave', 'Use GetWave · 调用方式', 'False', 'Boolean', '选择时域 GetWave；若 Init 不返回响应，解析时可能自动开启。'),
          p('rx_use_clocks', 'Use Clocks · 请求模型时钟', 'False', 'Boolean；仅 Rx GetWave', '还要求实际返回有效 clocks；否则使用原生 CDR/判决路径。'),
          p('tx_use_ami / rx_use_ami', 'AMI active flag · 派生状态', 'False', 'Boolean', '由 EQ 选择与解析维护，不是推荐的模式配置入口。', { scope: 'internal' }),
          p('*_ibis_valid / *_ami_valid / *_dll_valid', 'Validity · 解析状态', 'False', '只读状态', 'GUI Valid 状态指示；当前 WebUI 不执行加载。', { scope: 'output' })
        ]),
        group('原 GUI 模型操作入口', ref('src/pybert/gui/view.py', 263), [
          p('btn_sel_tx', 'Tx Select · 选择模型', '需要有效 IBIS', '操作按钮', '打开 Tx component / pin / model 选择器。'),
          p('btn_view_tx', 'Tx View · 查看模型', '需要有效 IBIS', '操作按钮', '打开 Tx 电气模型查看器。'),
          p('btn_sel_rx', 'Rx Select · 选择模型', '需要有效 IBIS', '操作按钮', '打开 Rx component / pin / model 选择器。', { source: ref('src/pybert/gui/view.py', 468) }),
          p('btn_view_rx', 'Rx View · 查看模型', '需要有效 IBIS', '操作按钮', '打开 Rx 电气模型查看器。', { source: ref('src/pybert/gui/view.py', 469) }),
          p('btn_cfg_tx', 'Tx Configure AMI', '需要有效 AMI', '操作按钮', '打开由 Tx .ami 参数声明生成的配置对话框。', { source: ref('src/pybert/gui/view.py', 514) }),
          p('btn_cfg_rx', 'Rx Configure AMI', '需要有效 AMI', '操作按钮', '打开由 Rx .ami 参数声明生成的配置对话框。', { source: ref('src/pybert/gui/view.py', 580) })
        ], '入口保留并说明依赖；本页面不解析模型，也不调用外部 GUI。'),
        group('随附 example_rx.ami 的参数示例', ref('models/ibisami/example_rx.ami', 25), [
          p('ctle_mode', 'CTLE mode · 模式', '0', '0=Off / 1=Manual', '仅属于该示例 AMI 模型。', { scope: 'model' }),
          p('ctle_freq', 'CTLE frequency · 频率', '5e9 Hz', '1e9–5e9 Hz', '模型参数使用 Hz，而 Native 界面使用 GHz。', { scope: 'model' }),
          p('ctle_mag', 'CTLE magnitude · 提升', '0 dB', '0–12 dB', '示例模型的 CTLE 相对提升。', { scope: 'model' }),
          p('ctle_bandwidth', 'CTLE bandwidth · 带宽', '12e9 Hz', '5e9–50e9 Hz', '示例模型的带宽。', { scope: 'model' }),
          p('ctle_dcgain', 'CTLE DC gain · 直流增益', '0 dB', '−20–20 dB', '示例模型额外提供的直流增益参数。', { scope: 'model' }),
          p('dfe_mode', 'DFE mode · 模式', '0', '0=Off / 1=Manual / 2=Adaptive', '这是模型内部 DFE 的模式。', { scope: 'model' }),
          p('dfe_ntaps', 'DFE taps · 抽头数', '5', 'Integer；未声明 Range', '模型文件给出的初始值。', { scope: 'model' }),
          p('dfe_tap1 … dfe_tap5', 'DFE tap values · 初始权重', '均为 0', 'Float；未声明 Range', '模型内部的 tap 初值。', { scope: 'model' }),
          p('dfe_vout', 'Slicer output · 电平', '1 V', '0–1 V', '模型内部判决输出幅度。', { scope: 'model' }),
          p('dfe_gain', 'DFE adaptation gain · 增益', '0.1', '0–1', '模型内部误差反馈增益。', { scope: 'model' }),
          p('debug.dbg_enable', 'Debug · 模型调试', 'False', 'Boolean', '示例模型的调试总开关。', { scope: 'model' }),
          p('debug.dump_dfe_adaptation / debug.dump_adaptation_input', 'Debug dumps · 调试导出', 'False / False', 'Boolean', '分别控制模型的自适应数据与求和节点输入导出。', { scope: 'model' })
        ], '这一组只用于说明 Model_Specific 的结构，不是所有 Rx AMI 模型的通用参数表。')
      ]
    },
    {
      id: 'optimizer', number: '⌘', category: 'tools', name: 'Optimizer', title: '均衡参数搜索', icon: 'tune',
      summary: '在时域仿真之外寻找设置。Native 网格搜索可配合 MMSE，AMI 参数通过 TPE/Optuna 搜索。',
      location: 'Optimizer', input: '候选范围 + 通道响应', output: '候选系数 / 评分 → Use EQ',
      mapping: [
        map('两套设置对象', 'Reset EQ 把当前 Native EQ 复制到优化器；Optimize EQ 搜索；Use EQ 将 Tx FFE、CTLE、Rx FFE 结果写回实际仿真设置。', ref('src/pybert/gui/handler.py', 155)),
        map('评分与 BER 的区别', 'Native MMSE 以脉冲响应和噪声模型求解；AMI 每个候选调用 Init。不是对每个候选进行完整 GetWave 长记录 BER 仿真。', ref('src/pybert/threads/optimization.py', 276)),
        map('噪声假设边界', 'MMSE 当前使用 A_v=0.5 V、SNR_TX=25 dB、RJ/DJ=0，aggressor 列表为空。评分不等同于独立 COM 或最终误码数。', ref('src/pybert/threads/optimization.py', 290))
      ],
      groups: [
        group('搜索空间', traits(198), [
          p('tx_tap_tuners', 'Tx tap search · 候选', '见 Tx EQ tap 表', 'enabled / min_val / max_val / step / value', '独立于实际 tx_taps 的候选空间。'),
          p('tx_c0_min', 'Minimum Tx cursor · 主游标下限', '0', 'Float；同时排除 cursor ≤ 0', '约束优化器的最小 Tx 主游标；不是所有手动权重的统一校验。', { scope: 'api' }),
          p('ctle_enable_tune', 'CTLE search · 启用', 'True', 'Boolean', '优化器内的 CTLE 开关。'),
          p('peak_freq_tune', 'CTLE fp · 固定频率', '5 GHz', 'Float', '本轮搜索使用的 CTLE 频率参数。'),
          p('rx_bw_tune', 'CTLE BW · 固定带宽', '12 GHz', 'Float', '本轮搜索使用的 CTLE 带宽参数。'),
          p('min_mag_tune / max_mag_tune / step_mag_tune', 'CTLE boost grid · 提升网格', '2 / 12 / 1 dB', '下界 / 上界 / 步长', '枚举的 CTLE boost 范围。'),
          p('peak_mag_tune', 'Selected boost · 优化结果', '1.7 dB', 'GUI 只读', '初始值未必落在默认搜索网格中。', { scope: 'output' })
        ]),
        group('Rx 求解与 AMI 预算', traits(251), [
          p('use_mmse', 'Use MMSE · 求解器', 'True', 'Boolean；仅 Native Rx', '关闭时枚举 Rx FFE 并按 cursor/ISI 指标评分。'),
          p('rlm', 'RLM · MMSE 电平失配', '0.95', '无量纲', '仅 Native MMSE 读取；普通 PAM4 波形和非 MMSE 网格不消费。'),
          p('ami_opt_trials', 'AMI trial budget · 预算', '100', 'Int · 无显式上下限', 'Tx 或 Rx 使用 AMI 时的候选次数；没有搜索维度时只评估一次。'),
          p('tx_ami_tap_tuners / rx_ami_tap_tuners', 'AMI parameter search · 参数空间', '由模型声明生成', 'name / enabled / min_val / max_val / step / value', '具体可搜索参数随 .ami 文件变化，默认需选择要搜索的参数。')
        ])
      ]
    },
    {
      id: 'com', number: '◇', category: 'tools', name: 'COM', title: '独立 COM 评估', icon: 'chart',
      summary: '通过 PyChOpMarg 进行另一套配置驱动的 Channel Operating Margin 评估。',
      location: 'Config. / Misc. / Compute COM', input: '.s4p 通道 + 独立 COM 配置', output: 'com_value（dB）· com_msg',
      mapping: [
        map('独立旁支', 'GUI 的 compute_com() 只向 calc_com() 传 ch_file 和 cfg_file；不会直接继承当前 Tx/Rx EQ、时域噪声或 FEXT/NEXT 列表。', pipeline(1066)),
        map('配置来源', '空配置使用 PyChOpMarg IEEE_8023dj 默认值；指定表格时读取它的 COM 参数。这里不代表当前时域配置的 BER。', ref('src/pybert/models/com.py', 19))
      ],
      groups: [group('调用与结果', traits(405), [
        p('enable_com', 'Compute COM · 启用评估', 'False', 'Boolean', '在主仿真之后执行 COM。', { condition: 'single + .s4p' }),
        p('com_cfg_file', 'COM config · 参数表', '空', '.xls / .xlsx', '空时使用 PyChOpMarg 默认参数。'),
        p('com_value', 'COM value · 评估结果', '−999.0', 'dB；−999 为初始化/失败哨兵', '不是以该哨兵表示物理 margin。', { scope: 'output' }),
        p('com_msg', 'COM status · 状态', '空', '运行 / 错误信息', '记录独立 COM 调用状态。', { scope: 'output' }),
        p('fext_files / next_files / com_params', 'COM API inputs · 底层参数', 'None', 'calc_com() 的可选参数', '底层 API 能接收，但当前主 GUI 调用没有传入这些字段。', { scope: 'api', source: ref('src/pybert/models/com.py', 19) })
      ])]
    }
  ];

  stages.find(stage => stage.id === 'optimizer').groups.push(group('原 GUI 的 Rx tap 表', ref('src/pybert/gui/view.py', 805), [
    p('ffe_tap_tuners', 'Rx FFE · 搜索范围', '100 个槽位', 'Name / Enabled / Min / Max / Step / Value', '与 Rx FFE 模块中的搜索表共享同一份草稿。Enabled、Value 在原 GUI 只读。'),
    p('dfe_tap_tuners', 'Rx DFE · 自适应范围', '20 个槽位', 'Name / Enabled / Min / Max / Value', '与 DFE 模块共享同一份草稿；保留 Disable All / Enable All。Value 只读。')
  ]));
  stages.find(stage => stage.id === 'analysis').groups.push(group('原 GUI 图表与信息页', ref('src/pybert/gui/view.py', 919), [
    ['plot_h_tune', 'Optimizer / Pulse response', 919],
    ['plots_h', 'Responses / Impulses', 925], ['plots_s', 'Responses / Steps', 930],
    ['plots_p', 'Responses / Pulses', 935], ['plots_H', 'Responses / Frequency', 940],
    ['plots_dfe', 'Results / DFE', 950], ['plots_out', 'Results / Outputs', 955],
    ['plots_eye', 'Results / Eyes', 960], ['plots_bathtub', 'Results / Bathtubs', 965],
    ['plot_viterbi', 'Results / Viterbi', 970],
    ['plots_jitter_dist', 'Jitter / Jitter Dist.', 991], ['plots_jitter_spec', 'Jitter / Jitter Spec.', 996],
    ['jitter_info', 'Jitter / Jitter Info', 1000], ['perf_info', 'Info / Performance', 1007],
    ['instructions', "Info / User's Guide", 1011], ['console_log', 'Info / Console', 1012]
  ].map(([key, label, line]) => p(key, label, '未接入', '原生 GUI 展示项', key === 'instructions' ? '原生使用指南；当前页面提供本地研究文档与参数来源。' : key === 'console_log' ? '原生 Console 可编辑；当前页面没有引擎日志。' : '需要 PyBERT 运行或绘图数据；本页面登记对应关系，不生成示例结果。', { scope: 'output', source: ref('src/pybert/gui/view.py', line) }))));

  window.PYBERT_CATALOG = { version: '11.1.0', commit: '1bc905d', date: '2026-10-23', root, stages };
})();
