/* Typed UI draft metadata. This module does not run or configure PyBERT. */
(() => {
  const number = (value, unit = '', extra = {}) => ({ kind: 'number', value, unit, ...extra });
  const select = (value, options, extra = {}) => ({ kind: 'select', value, options, ...extra });
  const toggle = value => ({ kind: 'boolean', value });
  const file = (accept, extra = {}) => ({ kind: 'file', value: '', accept, ...extra });
  const fields = {
    bit_rate: number(10, 'Gbps', { min: 0.1, max: 250 }),
    mod_type: select('NRZ', ['NRZ', 'PAM-4', 'Duo-binary'], { kind: 'radio' }),
    vod: number(1, 'V', { label: '发射电压 Vod', hint: '对应 PyBERT 的 vod：发射电压尺度。Vdd 通常指电源电压，本模型未提供独立 Vdd 设置。' }),
    pattern: select('PRBS-7', [7, 9, 11, 13, 15, 20, 23, 31].map(n => `PRBS-${n}`)),
    seed: number(1, '', { integer: true }),
    tx_eq_sel: select('Native', ['Native', 'IBIS-AMI']),
    rx_eq_sel: select('Native', ['Native', 'IBIS-AMI']),
    inter_sel: select('native', ['native', 'single', 'multiple'], { labels: ['Native · 原生模型', 'Single · 单个文件', 'Multiple · 文件串接'] }),
    ch_file: file('.s2p,.s4p,.s8p,.s12p,.csv,.txt'),
    ch_files: { kind: 'files', value: [], accept: '.s4p' },
    renumber: toggle(false), use_window: toggle(false),
    lane_sel: number(0, '', { integer: true, min: 0 }),
    l_ch: number(0.5, 'm'), Z0: number(100, 'Ω'), v0: number(0.67, 'c'),
    Rdc: number(0.1876, 'Ω/m'), R0: number(1.452, 'Ω/m'), w0: number(10000000, 'rad/s'), Theta0: number(0.02),
    tx_sel: select('native', ['native', 'ibis'], { labels: ['Native · 集总端接', 'IBIS · 电气模型'] }),
    rx_sel: select('native', ['native', 'ibis'], { labels: ['Native · 集总端接', 'IBIS · 电气模型'] }),
    rs: number(100, 'Ω'), cout: number(0.5, 'pF', { min: 0.001, max: 1000 }),
    rin: number(100, 'Ω'), cin: number(0.5, 'pF'),
    cac: number(1, 'μF', { hint: '原 GUI 允许编辑 Rx_Cac；当前 Native 通道计算没有读取此字段。草稿保留该值，不承诺波形变化。' }),
    rn: number(0.01, 'V RMS'), pn_mag: number(0.01, 'V'), pn_freq: number(11, 'MHz'), include_fext: toggle(false),
    ctle_enable: toggle(true), ctle_sel: select('Native', ['Native', 'File']), ctle_file: file('.csv'),
    peak_freq: number(5, 'GHz'), rx_bw: number(12, 'GHz'), peak_mag: number(1.7, 'dB'),
    rx_n_taps: number(15, '', { integer: true, min: 0, max: 100, hint: '此编辑器按源码预建的 100 个槽位提供 0–100 个 tap。底层 Python 字段未统一限制上界。' }),
    rx_n_pre: number(5, '', { integer: true, min: 0, max: 99, hint: '提交后由原生 observer 重排完整 100 槽 tap；运行中编辑将在 worker 退出后校验。完整 YAML 加载恢复保存的数组，不重复移位。' }),
    gain: number(0.1), n_ave: number(100), decision_scaler: number(0.5, 'V'),
    sum_ideal: toggle(true), sum_bw: number(12, 'GHz'),
    cdr_type: select('Bang-Bang', ['Bang-Bang', 'Mueller-Muller']),
    delta_t_ui: number(0.001, 'UI'), alpha: number(0.01),
    n_lock_ave: number(500, '', { integer: true }), rel_lock_tol: number(0.1), lock_sustain: number(500, '', { integer: true }),
    use_agc: toggle(true),
    rx_use_viterbi: toggle(false), rx_viterbi_symbols: number(4, 'symbols', { integer: true, min: 1, hint: 'Native ISI/MLSD；完整窗口预算在 Run 前检查，超预算不缩 Depth 或样本。' }),
    nbits: number(15000, 'bits', { integer: true, min: 1000, max: 10000000 }),
    eye_bits: number(10160, 'bits', { integer: true }), nspui: number(32, 'samples/UI', { integer: true, min: 2, max: 256 }),
    debug: toggle(false), f_max: number(40, 'GHz'), f_step: number(10, 'MHz'), impulse_length: number(0, 'ns'), thresh: number(3, 'σ'),
    pkg_enable: toggle(false), pkg_group: select('KR', ['KR', 'C2C', 'CR', 'C2M']),
    tx_pkg_case: select('A1', []), rx_pkg_case: select('A1', []), pkg_include_host: toggle(true),
    tx_ibis_file: file('.ibs', { label: 'Tx IBIS 文件' }), rx_ibis_file: file('.ibs', { label: 'Rx IBIS 文件' }),
    tx_use_ts4: { ...toggle(false), label: 'Tx on-die S-parameters', hint: '需要有效 Ts4file 与绑定文件；后端按真实模型预检。' },
    rx_use_ts4: { ...toggle(false), label: 'Rx on-die S-parameters', hint: '需要有效 Ts4file 与绑定文件；后端按真实模型预检。' },
    tx_use_getwave: { ...toggle(false), label: 'Tx Use GetWave' }, rx_use_getwave: { ...toggle(false), label: 'Rx Use GetWave' },
    rx_use_clocks: toggle(false),
    tx_c0_min: number(0), ctle_enable_tune: toggle(true), peak_freq_tune: number(5, 'GHz'), rx_bw_tune: number(12, 'GHz'),
    min_mag_tune: number(2, 'dB', { label: '最小 boost' }), max_mag_tune: number(12, 'dB', { label: '最大 boost' }), step_mag_tune: number(1, 'dB', { label: '步长' }),
    use_mmse: toggle(true), rlm: number(0.95), ami_opt_trials: number(100, '', { integer: true }),
    enable_com: toggle(false), com_cfg_file: file('.xls,.xlsx'),
    peak_mag_tune: { kind: 'unavailable', value: '', label: 'CTLE Result · Boost', readonly: '未执行优化；源码初始值为 1.7 dB，不作为本次结果。' },
    trellis_err_select: number(0, '', { integer: true, readonly: '在右侧 Analysis → Viterbi Trellis 操作，Error 0 表示未选；绑定所选 Run。' }),
    trellis_pan_control: number(0, '', { integer: true, readonly: '在右侧 Analysis → Viterbi Trellis 移动 Position；初始10symbols，按真实长度裁界，不 Run。' }),
    trellis_max_err: { kind: 'unavailable', value: '', readonly: '在右侧 Viterbi Trellis 显示所选 Run 的 bit-error entries，PAM4重复symbol条目保留。' }
  };
  for (const side of ['tx', 'rx']) {
    for (const type of ['ibis', 'ami', 'dll']) fields[`${side}_${type}_valid`] = { kind: 'unavailable', value: '', label: `${side.toUpperCase()} ${type.toUpperCase()} Valid`, readonly: '未加载 / 未验证模型。' };
    for (const type of ['ami', 'dll']) fields[`${side}_${type}_file`] = { kind: 'unavailable', value: '', label: `${side.toUpperCase()} ${type.toUpperCase()} File`, readonly: '由所选 IBIS 模型解析得到；当前未加载。' };
    for (const [action, label] of [['sel', 'Select'], ['view', 'View'], ['cfg', 'Configure AMI']]) fields[`btn_${action}_${side}`] = { kind: 'action', value: '', label: `${side.toUpperCase()} ${label}`, readonly: '需要解析并加载有效模型；本页面不调用模型 GUI。' };
    fields[`${side}_ami_tap_tuners`] = { kind: 'unavailable', value: '', label: `${side.toUpperCase()} AMI Params`, readonly: '未加载模型，暂无参数行。列为 Name / Enabled / Min val / Max val / Step / Value；Value 只读。' };
  }

  const bindings = {
    'tx_taps[].enabled': ['tx_taps'], 'tx_taps[].value': ['tx_taps'],
    'rx_taps[].enabled': ['rx_taps'], 'rx_taps[].value': ['rx_taps'],
    'ffe_tap_tuners[].min_val / max_val': ['ffe_tap_tuners'], 'ffe_tap_tuners[].step': ['ffe_tap_tuners'],
    'dfe_tap_tuners[].enabled': ['dfe_tap_tuners'], 'dfe_tap_tuners[].min_val / max_val': ['dfe_tap_tuners'],
    'tx_ibis_file / rx_ibis_file': ['tx_ibis_file', 'rx_ibis_file'],
    'tx_use_ts4 / rx_use_ts4': ['tx_use_ts4', 'rx_use_ts4'],
    'tx_use_getwave / rx_use_getwave': ['tx_use_getwave', 'rx_use_getwave'],
    'tx_ami_file / rx_ami_file': ['tx_ami_file', 'rx_ami_file'],
    'tx_dll_file / rx_dll_file': ['tx_dll_file', 'rx_dll_file'],
    '*_ibis_valid / *_ami_valid / *_dll_valid': ['tx_ibis_valid', 'rx_ibis_valid', 'tx_ami_valid', 'rx_ami_valid', 'tx_dll_valid', 'rx_dll_valid'],
    'tx_ami_tap_tuners / rx_ami_tap_tuners': ['tx_ami_tap_tuners', 'rx_ami_tap_tuners'],
    'min_mag_tune / max_mag_tune / step_mag_tune': ['min_mag_tune', 'max_mag_tune', 'step_mag_tune'],
    tx_tap_tuners: ['tx_tap_tuners'], ffe_tap_tuners: ['ffe_tap_tuners'], dfe_tap_tuners: ['dfe_tap_tuners']
  };
  const tableInfo = {
    tx_taps: { title: 'Native Tx FFE taps', stage: 'tx', columns: ['enabled', 'value'], note: '逐项配置非主游标权重。Cursor 由 PyBERT 在运行时计算；右侧响应属于所选成功 run。' },
    rx_taps: { title: 'Native Rx FFE taps', stage: 'rxffe', columns: ['enabled', 'value'], note: '完整保存 100 槽。Ntaps/Npre 提交由原生 observer 处理；固定 FIR 不参与 DFE 训练。输入值与所选 run 的训练结果分离。' },
    dfe_tap_tuners: { title: 'DFE taps 与自适应范围', stage: 'dfe', columns: ['enabled', 'min_val', 'max_val', 'value'], readonly: ['value'], note: 'Enabled/min/max 与普通 Run 共用；优化要求连续前缀。Value 属于所选优化的获选候选，不是时域自适应初值或训练状态。' },
    tx_tap_tuners: { title: 'Tx FFE 搜索空间', stage: 'optimizer', columns: ['enabled', 'min_val', 'max_val', 'step', 'value'], note: '这是 Optimizer 的搜索设置。Value 在原 GUI 可编辑，与 Tx EQ 的实际权重分开保存。' },
    ffe_tap_tuners: { title: 'Rx FFE 搜索范围', stage: 'rxffe', columns: ['enabled', 'min_val', 'max_val', 'step', 'value'], readonly: ['enabled', 'value'], note: '完整显示 100 个槽位。Enabled 只读并随 Ntaps/Npre 更新；Value 属于所选优化的获选候选，与实际 Rx taps 分开。' }
  };
  const txTemplate = [
    { name: 'Pre-tap3', pos: -3, enabled: false, min_val: -0.05, max_val: 0.05, step: 0.025 },
    { name: 'Pre-tap2', pos: -2, enabled: true, min_val: -0.1, max_val: 0.1, step: 0.05 },
    { name: 'Pre-tap1', pos: -1, enabled: true, min_val: -0.2, max_val: 0.2, step: 0.1 },
    { name: 'Post-tap1', pos: 1, enabled: false, min_val: -0.2, max_val: 0.2, step: 0.1 },
    { name: 'Post-tap2', pos: 2, enabled: false, min_val: -0.1, max_val: 0.1, step: 0.05 },
    { name: 'Post-tap3', pos: 3, enabled: false, min_val: -0.05, max_val: 0.05, step: 0.025 }
  ];
  const defaults = {
    ...Object.fromEntries(Object.entries(fields).map(([key, field]) => [key, field.value])),
    tx_taps: txTemplate.map(tap => ({ enabled: tap.enabled, value: 0 })),
    tx_tap_tuners: txTemplate.map(({ enabled, min_val, max_val, step }) => ({ enabled, min_val, max_val, step, value: 0 })),
    rx_taps: Array.from({ length: 100 }, (_, i) => ({ enabled: i < 15, value: i === 2 ? 1 : 0 })),
    ffe_tap_tuners: Array.from({ length: 100 }, (_, i) => ({ enabled: i < 15, min_val: -1, max_val: 1, step: 0.1 })),
    dfe_tap_tuners: Array.from({ length: 20 }, (_, i) => ({ enabled: i < 5, min_val: i === 0 ? -0.2 : i === 1 ? -0.15 : -0.05, max_val: i === 0 ? 0.4 : i === 1 ? 0.15 : 0.1 }))
  };
  const clone = value => JSON.parse(JSON.stringify(value));
  const keysFor = param => bindings[param.key] || (fields[param.key] ? [param.key] : []);
  const optionsFor = (key, values) => ['tx_pkg_case', 'rx_pkg_case'].includes(key)
    ? ({ KR: ['A1', 'A2', 'B1', 'B2'], C2C: ['A1', 'A2', 'B1', 'B2'], CR: ['HL', 'HN', 'HH'], C2M: ['host', 'module'] }[values.pkg_group])
    : fields[key].options;
  const multiLane = values => values.inter_sel === 'single' && /\.s(8|12)p$/i.test(values.ch_file.trim());

  function disabledReason(key, values) {
    if (fields[key]?.readonly) return fields[key].readonly;
    if (['ch_file', 'ch_files'].includes(key) && values.inter_sel !== (key === 'ch_file' ? 'single' : 'multiple')) return key === 'ch_file' ? '选择 Single 文件模式后可设置。' : '选择 Multiple 串接模式后可设置。';
    if (['renumber', 'use_window'].includes(key) && values.inter_sel === 'native') return '文件通道模式下可编辑。';
    if (['l_ch', 'Z0', 'v0', 'Rdc', 'R0', 'w0', 'Theta0'].includes(key) && values.inter_sel !== 'native') return '当前采用文件通道；Native 参数保留。';
    if (['lane_sel', 'include_fext'].includes(key) && !multiLane(values)) return '选择 Single .s8p / .s12p 通道后可设置。';
    if (['rs', 'cout', 'rin', 'cin'].includes(key)) {
      if (values.pkg_enable) return '器件模型已替代集总端接。';
      if (values[['rs', 'cout'].includes(key) ? 'tx_sel' : 'rx_sel'] !== 'native') return '此侧电气模型选择 Native 后可设置。';
    }
    if (['pkg_group', 'tx_pkg_case', 'rx_pkg_case', 'pkg_include_host'].includes(key) && !values.pkg_enable) return '启用器件模型后可设置。';
    if (['ctle_enable', 'ctle_sel', 'ctle_file', 'peak_freq', 'rx_bw', 'peak_mag'].includes(key)) {
      if (values.rx_eq_sel !== 'Native') return '当前由 Rx AMI 替代 Native CTLE。';
      if (key === 'ctle_sel' && !values.ctle_enable) return '启用 CTLE 后可切换响应来源；原 GUI 仍允许编辑已有参数。';
      if (key === 'ctle_file' && values.ctle_sel !== 'File') return '响应来源选择 File 后可设置。';
      if (['peak_freq', 'rx_bw', 'peak_mag'].includes(key) && values.ctle_sel !== 'Native') return '响应来源选择 Native 后可设置。';
    }
    if (key === 'tx_taps' && values.tx_eq_sel !== 'Native') return '当前由 Tx AMI 提供均衡，Native taps 保留。';
    if (['rx_n_taps', 'rx_n_pre', 'rx_taps'].includes(key) && values.rx_eq_sel !== 'Native') return 'Rx AMI 下原 GUI 隐藏 Native Rx FFE 设置，草稿保留。';
    if (['cdr_type', 'delta_t_ui', 'alpha', 'n_lock_ave', 'rel_lock_tol', 'lock_sustain', 'gain', 'n_ave', 'decision_scaler', 'use_agc', 'sum_ideal', 'sum_bw'].includes(key) && values.rx_eq_sel !== 'Native') return '原 GUI 在 Rx AMI 模式下隐藏此 Native 设置组；草稿保留。';
    if (key === 'tx_tap_tuners' && values.tx_sel !== 'native') return '原 GUI 仅在 Tx electrical = Native 时展示此表。';
    if (['ffe_tap_tuners', 'dfe_tap_tuners', 'ctle_enable_tune', 'peak_freq_tune', 'rx_bw_tune', 'min_mag_tune', 'max_mag_tune', 'step_mag_tune', 'use_mmse'].includes(key) && values.rx_sel !== 'native') return '原 GUI 仅在 Rx electrical = Native 时展示此优化设置。';
    if (['cac', 'rx_use_viterbi', 'rx_viterbi_symbols'].includes(key) && values.rx_sel !== 'native') return '原 GUI 在 Rx electrical = IBIS 时隐藏此 Native 设置。';
    if (key === 'sum_bw' && values.sum_ideal) return '关闭“理想求和”后可设置带宽。';
    if (['delta_t_ui', 'alpha', 'n_lock_ave', 'rel_lock_tol', 'lock_sustain'].includes(key) && values.cdr_type !== 'Bang-Bang') return '仅 Bang-Bang 动态环路使用。';
    if (key === 'rx_viterbi_symbols' && !values.rx_use_viterbi) return '启用 Viterbi 后可设置。';
    if (key === 'tx_use_getwave' && values.tx_eq_sel === 'Native') return '选择 Tx IBIS-AMI 后可设置调用方式。';
    if (key === 'rx_use_getwave' && values.rx_eq_sel === 'Native') return '选择 Rx IBIS-AMI 后可设置调用方式。';
    if (key === 'rx_use_clocks' && (values.rx_eq_sel === 'Native' || !values.rx_use_getwave)) return '仅 Rx AMI GetWave 支持时钟请求。';
    if (['peak_freq_tune', 'rx_bw_tune', 'min_mag_tune', 'max_mag_tune', 'step_mag_tune'].includes(key) && !values.ctle_enable_tune) return '启用 CTLE 搜索后可设置。';
    if (key === 'use_mmse' && values.rx_eq_sel !== 'Native') return '仅 Native Rx 使用 MMSE。';
    if (key === 'rlm' && (values.mod_type !== 'PAM-4' || !values.use_mmse)) return '仅 PAM-4 的 Native MMSE 优化读取 RLM；普通 Run 和非 MMSE 网格不读取。';
    if (key === 'ami_opt_trials' && values.tx_eq_sel === 'Native' && values.rx_eq_sel === 'Native') return 'Tx 或 Rx 使用 AMI 时设置搜索预算。';
    if (key === 'enable_com' && !(values.inter_sel === 'single' && /\.s4p$/i.test(values.ch_file.trim()))) return '选择 Single .s4p 通道后可启用。';
    if (key === 'com_cfg_file' && (!values.enable_com || disabledReason('enable_com', values))) return '启用独立 COM 评估后可设置。';
    return '';
  }

  function fieldError(key, values, { deferObserver = false } = {}) {
    const field = fields[key];
    if (!field || disabledReason(key, values)) return '';
    const value = values[key];
    if (field.kind === 'number') {
      if (typeof value !== 'number' || !Number.isFinite(value)) return '请输入有效数字。';
      if (field.integer && !Number.isInteger(value)) return '请输入整数。';
      if (field.min !== undefined && value < field.min) return `最小值为 ${field.min}${field.unit ? ` ${field.unit}` : ''}。`;
      if (field.max !== undefined && value > field.max) return `最大值为 ${field.max}${field.unit ? ` ${field.unit}` : ''}。`;
    }
    if (key === 'eye_bits' && typeof values.nbits === 'number' && value > values.nbits) return 'EyeBits 不能超过 Nbits；请调整分析窗口或测试长度。';
    if (key === 'rx_n_pre' && !deferObserver && typeof values.rx_n_taps === 'number' && value > Math.max(0, values.rx_n_taps - 1)) return 'Npre 应小于总 tap 数；总数为 0 时 Npre 为 0。';
    if (key === 'lane_sel' && multiLane(values) && value > (/\.s12p$/i.test(values.ch_file.trim()) ? 2 : 1)) return '该文件的 victim lane 索引超出范围。';
    if (key === 'max_mag_tune' && typeof values.min_mag_tune === 'number' && value < values.min_mag_tune) return '最大 boost 不能小于最小 boost。';
    if (key === 'step_mag_tune' && value <= 0) return '搜索步长应大于 0。';
    return '';
  }

  function tableError(key, values) {
    if (disabledReason(key, values)) return '';
    const rows = values[key];
    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      if (row.enabled === false) continue;
      for (const column of tableInfo[key].columns.filter(column => column !== 'enabled' && !tableInfo[key].readonly?.includes(column))) {
        if (typeof row[column] !== 'number' || !Number.isFinite(row[column])) return `第 ${i + 1} 行需要有效数字。`;
      }
      if (row.min_val > row.max_val) return `第 ${i + 1} 行的最小权重不能大于最大权重。`;
      if (row.step !== undefined && row.step <= 0) return `第 ${i + 1} 行的搜索步长应大于 0。`;
    }
    return '';
  }

  function validTapCount(values) {
    return Number.isInteger(values.rx_n_taps) ? Math.max(0, Math.min(100, values.rx_n_taps)) : 0;
  }

  function reconcile(key, values) {
    if (key === 'pkg_group') {
      for (const caseKey of ['tx_pkg_case', 'rx_pkg_case']) if (!optionsFor(caseKey, values).includes(values[caseKey])) values[caseKey] = optionsFor(caseKey, values)[0];
    }
    if (key === 'rx_n_taps' && !fieldError(key, values)) {
      values.rx_taps.forEach((tap, i) => { tap.enabled = i < values.rx_n_taps; });
      values.ffe_tap_tuners.forEach((tap, i) => { tap.enabled = i < values.rx_n_taps; });
      if (values.rx_n_pre >= values.rx_n_taps) values.rx_n_pre = Math.max(0, values.rx_n_taps - 1);
    }
    if (key === 'ffe_tap_tuners') values.ffe_tap_tuners.forEach((tap, i) => { tap.enabled = i < validTapCount(values); });
  }

  function restore(saved) {
    const values = clone(defaults);
    for (const [key, value] of Object.entries(saved || {})) {
      if (!(key in defaults)) continue;
      if (tableInfo[key]) {
        if (!Array.isArray(value) || value.length !== defaults[key].length) continue;
        value.forEach((row, i) => {
          for (const column of tableInfo[key].columns.filter(column => !tableInfo[key].readonly?.includes(column))) if (typeof row?.[column] === typeof defaults[key][i][column] || (column !== 'enabled' && row?.[column] === '')) values[key][i][column] = row[column];
        });
      } else if (fields[key].kind === 'files') {
        if (Array.isArray(value) && value.every(item => typeof item === 'string')) values[key] = value;
      } else if (typeof value === typeof defaults[key] || (fields[key].kind === 'number' && value === '')) values[key] = value;
    }
    for (const [key, field] of Object.entries(fields)) if (['select', 'radio'].includes(field.kind) && !optionsFor(key, values)?.includes(values[key])) values[key] = optionsFor(key, values)[0];
    reconcile('ffe_tap_tuners', values);
    return values;
  }

  window.PYBERT_SETTINGS = { fields, tableInfo, defaults, txTemplate, clone, keysFor, optionsFor, disabledReason, fieldError, tableError, validTapCount, reconcile, restore };
})();
