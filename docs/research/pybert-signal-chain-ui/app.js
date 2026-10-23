/* Local configuration draft only: no model loading or simulation backend. */
(() => {
  const { stages } = window.PYBERT_CATALOG;
  const settings = window.PYBERT_SETTINGS;
  const storageKey = 'pybert-chain-draft-v1';
  let draft = settings.clone(settings.defaults);
  let storageAvailable = true;
  let loadMessage = '';
  let lastReset = null;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
    if (saved?.schema === 1 && saved.commit === window.PYBERT_CATALOG.commit) draft = settings.restore(saved.values);
    else if (saved) loadMessage = '旧草稿的版本不同，当前显示此版本的默认值。';
  } catch { storageAvailable = false; loadMessage = '无法读取本地草稿；本次修改仍可在当前页面保留。'; }
  const $ = id => document.getElementById(id);
  const escape = value => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const categories = { main: '主信号链', control: '控制与判决旁支', tools: '全局设置与工具' };
  const icons = {
    bits: '<path d="M2 17h4V7h5v10h5V7h6"/>',
    filter: '<path d="M3 18h18M4 17V5M5 16l6-1 5-9h5"/>',
    channel: '<path d="M3 8h18M3 16h18M7 5v6M17 13v6"/>',
    noise: '<circle cx="12" cy="12" r="8.5"/><path d="M8 12h8M12 8v8"/>',
    taps: '<path d="M4 18V8M9 18V4M14 18v-7M19 18v-4M2 18h20"/>',
    feedback: '<path d="M3 9h14l-3-3m3 3-3 3M20 15H6l3 3m-3-3 3-3"/>',
    eye: '<path d="M2 12s4-6 10-6 10 6 10 6-4 6-10 6-10-6-10-6Z"/><circle cx="12" cy="12" r="2.5"/>',
    clock: '<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',
    level: '<path d="M3 7h18M3 17h18M7 4v6M16 14v6M3 12h18"/>',
    trellis: '<path d="m4 5 8 14 8-14M4 19 12 5l8 14"/><circle cx="4" cy="5" r="1.2"/><circle cx="4" cy="19" r="1.2"/><circle cx="20" cy="5" r="1.2"/><circle cx="20" cy="19" r="1.2"/>',
    grid: '<rect x="4" y="4" width="16" height="16" rx="1"/><path d="M4 9h16M4 15h16M9 4v16M15 4v16"/>',
    package: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>',
    model: '<path d="m8 5-6 7 6 7M16 5l6 7-6 7M14 3l-4 18"/>',
    tune: '<path d="M5 3v18M12 3v18M19 3v18"/><path d="M2 8h6M9 16h6M16 7h6"/>',
    chart: '<path d="M4 3v17h17M8 15l4-5 4 2 5-7"/>',
    link: '<path d="M14 3h7v7M21 3 10 14M10 5H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5"/>',
    folder: '<path d="M3 7V5h7l2 3h9v12H3Z"/>'
  };
  const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.filter}</svg>`;
  const sourceLink = source => `<a class="source-link" href="${escape(source.url)}" target="_blank" rel="noopener noreferrer" title="打开固定版本源码 ${escape(source.file)}:${source.line}">${escape(source.file.split('/').pop())}:${source.line} ${icon('link')}</a>`;
  const allParams = stages.flatMap(stage => stage.groups.flatMap((group, gi) => group.params.map((param, pi) => ({ stage, group, param, rowId: `param-${stage.id}-${gi}-${pi}` }))));
  const initialId = location.hash.slice(1);
  const state = { stageId: stages.some(stage => stage.id === initialId) ? initialId : 'source', tab: 'settings', scope: 'all', focusRow: null };
  const stageById = id => stages.find(stage => stage.id === id);
  const mode = () => ({ tx: draft.tx_eq_sel === 'Native' ? 'native' : draft.tx_use_getwave ? 'getwave' : 'init', rx: draft.rx_eq_sel === 'Native' ? 'native' : draft.rx_use_getwave ? 'getwave' : 'init', clocks: draft.rx_use_clocks });
  const changed = key => JSON.stringify(draft[key]) !== JSON.stringify(settings.defaults[key]);
  const stageKeys = stage => [...new Set(stage.groups.flatMap(group => group.params.flatMap(settings.keysFor)))];

  function saveDraft() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({ schema: 1, commit: window.PYBERT_CATALOG.commit, values: draft }));
      storageAvailable = true;
      loadMessage = '';
    } catch { storageAvailable = false; }
  }

  function syncModes() {
    const { tx, rx } = mode();
    $('tx-mode').value = tx;
    $('rx-mode').value = rx;
    $('ami-clocks').disabled = rx !== 'getwave';
    $('ami-clocks').checked = rx === 'getwave' && draft.rx_use_clocks;
  }

  function updateDraftStatus() {
    const modified = Object.keys(settings.defaults).filter(changed).length;
    const errors = Object.keys(settings.fields).filter(key => settings.fieldError(key, draft)).length + Object.keys(settings.tableInfo).filter(key => settings.tableError(key, draft)).length;
    const storageStatus = storageAvailable ? '草稿已保留' : '仅当前页面保留';
    $('draft-status').classList.toggle('has-errors', errors > 0);
    $('draft-status').innerHTML = `<strong>${errors ? `${errors} 项待修正` : storageStatus}</strong><span>${modified ? `${modified} 项设置已修改` : '源码默认配置'}${errors ? ` · ${storageStatus}` : ''}</span>`;
    for (const stage of stages) {
      const item = $('stage-nav').querySelector(`[data-stage="${stage.id}"]`);
      item?.classList.toggle('has-draft', stageKeys(stage).some(changed));
      item?.classList.toggle('has-error', stageKeys(stage).some(key => settings.fields[key] ? settings.fieldError(key, draft) : settings.tableError(key, draft)));
    }
  }

  function renderNav() {
    $('stage-count').textContent = `${stages.length} MODULES`;
    $('stage-nav').innerHTML = Object.entries(categories).map(([category, title]) => `<div class="nav-group"><h2>${title}</h2>${stages.filter(stage => stage.category === category).map(stage => `<button class="nav-item${state.stageId === stage.id ? ' active' : ''}" type="button" data-stage="${stage.id}" ${state.stageId === stage.id ? 'aria-current="true"' : ''}>${icon(stage.icon)}<span>${stage.name}</span><small>${stage.groups.reduce((sum, group) => sum + group.params.length, 0)}</small></button>`).join('')}</div>`).join('');
  }

  function node(id, title, subtitle, className = '') {
    const stage = stageById(id);
    return `<button type="button" class="chain-node ${className}${state.stageId === id ? ' selected' : ''}" data-stage="${id}" aria-label="${escape(title)}：${escape(subtitle)}，查看设置"><span class="node-top">${icon(stage.icon)}${id === 'noise' ? '' : `<small>${stage.number}</small>`}</span><strong>${title}</strong><span class="node-subtitle">${subtitle}</span></button>`;
  }

  function mini(id, title, extraClass = '') {
    const stage = stageById(id);
    return `<button type="button" class="mini-node ${extraClass}${state.stageId === id ? ' selected' : ''}" data-stage="${id}" title="${escape(stage.title)}">${icon(stage.icon)}${title}</button>`;
  }

  function renderMap() {
    const { tx, rx, clocks } = mode();
    const txGetWave = tx === 'getwave';
    const rxAmi = rx !== 'native';
    const clocksConditional = rx === 'getwave' && clocks && !txGetWave;
    const modeNames = { native: 'Native FFE', init: 'AMI Init', getwave: 'AMI GetWave' };
    const noise = node('noise', 'Noise', txGetWave ? '路径限制' : '加法注入', `noise${txGetWave ? ' limited' : ''}`);
    const receiver = rxAmi ? node('ami', 'Rx AMI', rx === 'init' ? 'AMI Init' : 'AMI GetWave', 'ami') : node('ctle', 'Rx CTLE', !draft.ctle_enable ? '已关闭 · 旁路' : draft.ctle_sel === 'File' ? '文件响应' : 'Native · 已启用', draft.ctle_enable ? '' : 'bypass');
    const path = [node('source', 'Source', `${escape(draft.mod_type)} · ${escape(draft.pattern)}`), node('tx', 'Tx EQ', modeNames[tx], tx === 'native' ? '' : 'ami'), node('channel', 'Channel', draft.inter_sel === 'native' ? 'Native · 两端电气' : draft.inter_sel === 'single' ? '单文件 · 两端电气' : '文件串接 · 两端电气')];
    path.push(...(rx === 'init' && !txGetWave ? [receiver, noise] : [noise, receiver]));
    path.push(node('rxffe', 'Rx FFE', rxAmi ? '旁路 · Rx AMI' : '固定 FIR 系数', rxAmi ? 'bypass' : ''));
    path.push(node('dfe', rxAmi ? 'Slicer' : 'DFE / Slicer', clocksConditional ? '条件采用模型时钟' : rxAmi ? 'Native 采样 / 判决' : '自适应反馈 / 判决'));
    $('chain-map').innerHTML = `<div class="signal-path">${path.join('<span class="signal-arrow" aria-hidden="true"></span>')}</div><div class="chain-supports"><div class="support-cell"><span class="support-label">并入 Channel ↑</span>${mini('package', 'Device models')}</div><div class="support-cell"><span class="support-label">多节点测量 ↗</span>${mini('analysis', 'Observe')}<span class="support-divider"></span><span class="support-label">响应 · 眼图 · 误码</span></div><div class="support-cell control-cell"><span class="support-label">判决控制 ↑</span>${mini('cdr', 'CDR', clocksConditional ? 'conditional' : '')}${mini('agc', 'AGC', clocksConditional ? 'conditional' : '')}<span class="support-divider"></span>${mini('viterbi', '↗ Viterbi')}</div></div>`;
    const notes = [];
    if (txGetWave) notes.push('Tx GetWave：当前源码未将含显式 noise 的 rx_in 用于下游输出，噪声注入路径存在限制。');
    else if (rx === 'init') notes.push('Rx Init：显式噪声在 Rx AMI 输出后加入。');
    else if (rx === 'getwave') notes.push('Rx GetWave：显式噪声随 rx_in 输入模型。');
    else notes.push('Native：噪声在 Channel 后相加；CDR / AGC 控制采样与判决，不作为串行滤波级。');
    if (rxAmi) notes.push('原生 Rx AMI 回调禁用 DFE taps 与 FFE 搜索表；实际 Rx FFE 系数保留并在仿真中旁路。本页保留 Native 草稿，不执行该回调。');
    if (clocksConditional) notes.push('模型时钟仍须实际有效，届时才跳过 Native CDR / AGC；此图不表示已返回时钟。');
    if (rx === 'getwave' && clocks && txGetWave) notes.push('双 GetWave 分支当前丢弃 Rx 返回 clocks，请求时钟也不会自动旁路 Native CDR。');
    $('mode-note').className = `mode-note${txGetWave ? ' warning' : ''}`;
    $('mode-note').innerHTML = `<span class="note-mark" aria-hidden="true">${txGetWave ? '!' : 'i'}</span><span>${notes.join(' ')}</span>`;
    syncModes();
  }

  function stageContext(stage) {
    const { tx, rx, clocks } = mode();
    if (stage.id === 'analysis') return { label: '多节点观察', text: '', kind: '' };
    if (stage.id === 'noise' && tx === 'getwave') return { label: '当前图示：路径限制', text: 'Tx GetWave 分支下，显式 noise 的 rx_in 没有用于下游输出。以下参数仍记录其定义，不代表当前组合已应用它们。', kind: 'warning' };
    if (stage.id === 'ctle' && rx !== 'native') return { label: '当前图示：AMI 替代', text: '当前选择 Rx AMI。以下是 Native CTLE 的设置，在当前图示中由 Rx 模型替代；模型参数请查看 IBIS-AMI。', kind: 'muted' };
    if (stage.id === 'rxffe' && rx !== 'native') return { label: '当前图示：旁路', text: 'Rx 使用 AMI 时，主流程旁路 Native Rx FFE。这里保留 Native 配置的参数目录。', kind: 'muted' };
    if (stage.id === 'dfe' && rx !== 'native') return { label: '当前图示：保留判决', text: '正常切换 Rx AMI 会关闭 Native DFE taps。没有实际有效的模型时钟时，仍经 Native CDR / 采样 / 判决；随后重新启用 DFE taps 可能再叠加反馈。', kind: 'muted' };
    if (['cdr', 'agc'].includes(stage.id) && rx === 'getwave' && clocks) return { label: '当前图示：条件生效', text: tx === 'getwave' ? '当前双 GetWave 分支丢弃 Rx clocks，Native CDR / AGC 不会因为这一请求而自动旁路。' : 'Use Clocks 只是请求。只有 Rx 真正返回有效时钟，主流程才跳过包含 Native CDR / AGC 的 run_dfe()。', kind: 'warning' };
    if (stage.id === 'tx' && tx !== 'native') return { label: '当前图示：AMI Tx', text: `当前选择 Tx AMI ${tx === 'init' ? 'Init' : 'GetWave'}。Native Tx tap 表用于对照；实际模型的可调参数由其 .ami 文件决定。`, kind: 'muted' };
    return { label: stage.category === 'main' ? '主链模块' : stage.category === 'control' ? '耦合控制 / 旁支' : '设置 / 工具', text: '', kind: '' };
  }

  function renderOverview() {
    const stage = stageById(state.stageId);
    const context = stageContext(stage);
    $('stage-overview').innerHTML = `<div class="stage-overview"><div class="stage-badge">${icon(stage.icon)}</div><div class="stage-intro"><div class="stage-kicker">${stage.category === 'main' ? 'SIGNAL PATH' : stage.category === 'control' ? 'CONTROL & DECISION' : 'CONFIGURATION'} <span> / </span><span class="category-label">${categories[stage.category]}</span></div><h2 id="stage-title">${stage.title}<span>${stage.name}</span></h2><p>${stage.summary}</p><div class="stage-location">${icon('folder')}${stage.location}</div></div><span class="stage-status ${context.kind}">${context.label}</span></div><div class="io-strip"><span><span class="io-label">INPUT</span><strong>${stage.input}</strong></span><span class="io-arrow" aria-hidden="true">→</span><span><span class="io-label">OUTPUT</span><strong>${stage.output}</strong></span></div>${context.text ? `<p class="stage-context">${context.text}</p>` : ''}`;
    $('parameter-count').textContent = stage.groups.reduce((sum, group) => sum + group.params.length, 0);
    $('mapping-count').textContent = stage.mapping.length;
  }

  function badges(param) {
    const scopes = { api: 'API · 无主 GUI', internal: '内部状态', model: '示例模型定义', output: '只读输出' };
    const statuses = { unused: '主链未使用', limitation: '实现限制', optimizer: '优化器字段' };
    const labels = [];
    if (param.scope && scopes[param.scope]) labels.push(`<span class="param-badge">${scopes[param.scope]}</span>`);
    if (param.status) labels.push(`<span class="param-badge ${param.status === 'optimizer' ? 'optimizer' : 'warning'}">${statuses[param.status]}</span>`);
    return labels.length ? `<div class="param-badges">${labels.join('')}</div>` : '';
  }

  function renderParameters() {
    const stage = stageById(state.stageId);
    const groups = stage.groups.map((group, gi) => {
      const params = group.params.map((param, pi) => ({ param, pi })).filter(({ param }) => state.scope === 'all' || !param.scope || param.scope === 'gui');
      if (!params.length) return '';
      return `<section class="parameter-group"><div class="group-heading"><h3>${group.title}<small>${params.length}</small></h3>${sourceLink(group.source)}</div><table class="parameter-table"><colgroup><col><col><col><col></colgroup><thead><tr><th scope="col">参数 / 源码字段</th><th scope="col">初始默认值</th><th scope="col">范围 / 单位</th><th scope="col">作用与生效条件</th></tr></thead><tbody>${params.map(({ param, pi }) => {
        const rowId = `param-${stage.id}-${gi}-${pi}`;
        return `<tr id="${rowId}" class="${state.focusRow === rowId ? 'focused-row' : ''}"><td><span class="parameter-label">${escape(param.label)}</span><code>${escape(param.key)}</code>${badges(param)}</td><td><span class="default-value">${escape(param.value)}</span></td><td class="range-cell">${escape(param.range)}</td><td><div class="parameter-description">${escape(param.description)}</div>${param.condition ? `<span class="parameter-condition">${escape(param.condition)}</span>` : ''}${param.source ? `<div class="row-source">${sourceLink(param.source)}</div>` : ''}</td></tr>`;
      }).join('')}</tbody></table>${group.note ? `<div class="group-note">${group.note}</div>` : ''}</section>`;
    }).join('');
    const tables = (stage.tables || []).map(table => `<section class="detail-table"><div class="group-heading"><h3>${table.title}</h3>${sourceLink(table.source)}</div><table class="parameter-table"><thead><tr>${table.columns.map(column => `<th scope="col">${column}</th>`).join('')}</tr></thead><tbody>${table.rows.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody></table>${table.note ? `<div class="group-note">${table.note}</div>` : ''}</section>`).join('');
    $('parameter-panel').innerHTML = groups || tables ? groups + tables : '<div class="empty-state">这个模块的条目属于 API、内部状态、模型定义或分析输出。<br><button type="button" id="show-all">显示全部条目</button></div>';
  }

  function inputControl(key, label) {
    const field = settings.fields[key];
    if (field.kind === 'unavailable') return `<output id="control-${key}" class="unavailable-value" aria-label="${escape(label)}">未提供 · ${escape(field.readonly)}</output>`;
    if (field.kind === 'action') return `<button id="control-${key}" class="secondary-button" type="button" disabled>${escape(label)}</button>`;
    const value = draft[key];
    const reason = settings.disabledReason(key, draft);
    const error = settings.fieldError(key, draft);
    const attrs = `id="control-${key}" data-setting="${key}" aria-label="${escape(label)}" aria-describedby="help-${key} error-${key}" aria-invalid="${Boolean(error)}"${reason ? ' disabled' : ''}`;
    if (field.kind === 'boolean') return `<label class="switch-control"><input type="checkbox" role="switch" ${attrs}${value ? ' checked' : ''}><span class="switch-track" aria-hidden="true"></span><span class="switch-word">${value ? '已开启' : '已关闭'}</span></label>`;
    if (field.kind === 'radio') return `<div class="option-grid" role="radiogroup" aria-label="${escape(label)}">${field.options.map((option, i) => `<label class="option-card${value === option ? ' checked' : ''}"><input id="control-${key}${i ? `-${i}` : ''}" type="radio" name="${key}" data-setting="${key}" value="${escape(option)}"${value === option ? ' checked' : ''}${reason ? ' disabled' : ''}><strong>${option}</strong><small>${['二电平调制', '四电平调制', '相关编码'][i]}</small></label>`).join('')}</div>`;
    if (field.kind === 'select') return `<select ${attrs}>${settings.optionsFor(key, draft).map((option, i) => `<option value="${escape(option)}"${value === option ? ' selected' : ''}>${escape(field.labels?.[i] || option)}</option>`).join('')}</select>`;
    if (field.kind === 'number') return `<div class="number-control"><input type="number" ${attrs} value="${escape(value)}" step="${field.integer ? '1' : 'any'}"${field.min !== undefined ? ` min="${field.min}"` : ''}${field.max !== undefined ? ` max="${field.max}"` : ''} autocomplete="off">${field.unit ? `<span class="input-unit">${field.unit}</span>` : ''}</div>`;
    const input = field.kind === 'files' ? `<textarea ${attrs} rows="3" placeholder="每行一个文件名或路径，按串接顺序排列" spellcheck="false">${escape(value.join('\n'))}</textarea>` : `<input type="text" ${attrs} value="${escape(value)}" placeholder="输入文件名或路径" spellcheck="false" autocomplete="off">`;
    return `<div class="file-control">${input}<label class="file-picker${reason ? ' disabled' : ''}">选择文件<input type="file" data-file-key="${key}" accept="${field.accept}"${field.kind === 'files' ? ' multiple' : ''}${reason ? ' disabled' : ''} aria-label="选择 ${escape(label)}"></label></div><small class="file-hint">选择文件仅记录文件名；不读取或上传内容，可手工填写路径。</small>`;
  }

  function fieldCard(param, key, id, source) {
    const field = settings.fields[key];
    const label = field.label || param.label;
    const reason = settings.disabledReason(key, draft);
    const error = settings.fieldError(key, draft);
    const initial = Array.isArray(field.value) ? '空列表' : typeof field.value === 'boolean' ? field.value ? '开启' : '关闭' : field.value === '' ? '空' : field.value;
    return `<div class="setting-card${field.kind === 'radio' || field.kind === 'files' ? ' wide' : ''}${reason ? ' inactive' : ''}${changed(key) ? ' modified' : ''}" id="${id}" data-field-card="${key}"><div class="setting-heading"><label for="control-${key}">${escape(label)}</label><button class="field-reset" type="button" data-reset-field="${key}"${changed(key) ? '' : ' hidden'} aria-label="恢复 ${escape(label)} 默认值">恢复</button></div>${inputControl(key, label)}<p class="setting-description" id="help-${key}">${escape(field.hint || param.description)}</p><div class="field-meta"><code>${escape(key)}</code><span>默认 ${escape(initial)}${field.unit ? ` ${field.unit}` : ''}</span></div>${param.status === 'limitation' ? '<span class="setting-caution">此路径有已记录的实现限制，详见参数说明。</span>' : ''}<p class="field-condition" data-field-condition="${key}"${reason ? '' : ' hidden'}>${escape(reason)}</p><p class="field-error" id="error-${key}" role="status"${error ? '' : ' hidden'}>${escape(error)}</p><details class="field-details"><summary>范围与来源</summary><p>${escape(param.range)}</p>${sourceLink(param.source || source)}${badges(param)}</details></div>`;
  }

  function tapLabel(key, i) {
    if (key.startsWith('tx_')) return settings.txTemplate[i].name;
    if (key === 'dfe_tap_tuners') return `Tap${i + 1}`;
    const pos = i - (Number.isInteger(draft.rx_n_pre) ? draft.rx_n_pre : 0);
    return pos === 0 ? 'Cursor' : `${pos < 0 ? 'Pre' : 'Post'}-tap${Math.abs(pos)}`;
  }

  function tapTable(key) {
    const info = settings.tableInfo[key];
    const reason = settings.disabledReason(key, draft);
    const error = settings.tableError(key, draft);
    const columns = { enabled: '启用', value: '权重', min_val: '最小权重', max_val: '最大权重', step: '搜索步长' };
    const rows = draft[key];
    const bulk = key === 'dfe_tap_tuners' ? `<div class="tap-actions"><button type="button" class="secondary-button" data-dfe-bulk="disable"${reason ? ' disabled' : ''}>Disable All · 全部禁用</button><button type="button" class="secondary-button" data-dfe-bulk="enable"${reason ? ' disabled' : ''}>Enable All · 全部启用</button></div>` : '';
    const table = `<p class="tap-note">${info.note}</p>${bulk}<p class="tap-inactive"${reason ? '' : ' hidden'}>${reason}</p><div class="tap-table-scroll"><table class="tap-editor"><thead><tr><th scope="col">Name / Tap</th>${info.columns.map(column => `<th scope="col">${columns[column]}${info.readonly?.includes(column) ? ' · 只读' : ''}</th>`).join('')}</tr></thead><tbody>${rows.map((row, i) => `<tr${row.enabled === false ? ' class="tap-off"' : ''}><th scope="row">${tapLabel(key, i)}<small>${key.startsWith('tx_') ? `${settings.txTemplate[i].pos > 0 ? '+' : ''}${settings.txTemplate[i].pos} UI` : `index ${i}`}</small></th>${info.columns.map(column => {
      if (info.readonly?.includes(column)) return column === 'enabled' ? `<td><span aria-label="${escape(info.title + ' ' + tapLabel(key, i) + ' 启用状态只读')}">${row.enabled ? 'True' : 'False'}</span></td>` : '<td><span class="unavailable-value" title="未执行优化，当前没有结果">未提供</span></td>';
      const isChanged = row[column] !== settings.defaults[key][i][column];
      const label = `${info.title} ${tapLabel(key, i)} ${columns[column]}`;
      const attrs = `data-tap-table="${key}" data-tap-index="${i}" data-tap-column="${column}" aria-label="${escape(label)}"${reason ? ' disabled' : ''}`;
      return `<td><input class="tap-input${isChanged ? ' modified' : ''}" type="${column === 'enabled' ? 'checkbox' : 'number'}" ${attrs}${column === 'enabled' ? row[column] ? ' checked' : '' : ` value="${escape(row[column])}" step="any"`}></td>`;
    }).join('')}</tr>`).join('')}</tbody></table></div>${rows.length ? '' : '<p class="tap-note">当前 Ntaps 为 0，增加总 tap 数后可编辑权重。</p>'}<p class="field-error table-error" id="table-error-${key}" role="status"${error ? '' : ' hidden'}>${escape(error)}</p>`;
    return key === 'ffe_tap_tuners'
      ? `<details id="settings-table-${key}" class="settings-group tap-group"><summary class="settings-group-heading">${info.title}<span>Optimizer · 展开编辑</span></summary>${table}</details>`
      : `<section id="settings-table-${key}" class="settings-group tap-group"><div class="settings-group-heading"><h3>${info.title}</h3><code>${key}</code></div>${table}</section>`;
  }

  function renderSettings() {
    const stage = stageById(state.stageId);
    const tables = new Set();
    let referenceCount = 0;
    const groups = stage.groups.map((group, gi) => {
      const items = group.params.map((param, pi) => ({ param, pi })).sort((a, b) => Number(b.param.key === 'mod_type') - Number(a.param.key === 'mod_type'));
      const cards = items.map(({ param, pi }) => {
        const keys = settings.keysFor(param);
        if (!keys.length) referenceCount++;
        keys.filter(key => settings.tableInfo[key]).forEach(key => tables.add(key));
        return keys.filter(key => settings.fields[key]).map((key, ki) => fieldCard(param, key, `setting-${stage.id}-${gi}-${pi}${ki ? `-${ki}` : ''}`, group.source)).join('');
      }).join('');
      return cards ? `<section class="settings-group"><div class="settings-group-heading"><h3>${group.title}</h3><span>本地草稿</span></div><div class="settings-grid">${cards}</div></section>` : '';
    }).join('');
    $('settings-panel').innerHTML = `${loadMessage ? `<p class="editor-notice">${loadMessage}</p>` : ''}${stage.id === 'ami' ? '<p class="editor-notice">这里只记录模型文件名与调用方案。尚未解析模型、确认能力或运行动态库；Model_Specific 示例与只读解析状态可在“参数说明”中查看。</p>' : ''}${groups}${[...tables].map(tapTable).join('')}${!groups && !tables.size ? '<div class="empty-state">此模块显示分析结果，当前没有仿真数据。<br>可以在“参数说明”中查看支持的输出与入口。</div>' : ''}${referenceCount ? `<div class="reference-shortcut"><span>还有 ${referenceCount} 个结果、内部状态或参考条目。</span><button type="button" data-tab="parameters">查看参数说明 →</button></div>` : ''}`;
    updateFieldFeedback();
  }

  function updateFieldFeedback() {
    for (const card of $('settings-panel').querySelectorAll('[data-field-card]')) {
      const key = card.dataset.fieldCard;
      const field = settings.fields[key];
      const reason = settings.disabledReason(key, draft);
      card.classList.toggle('inactive', Boolean(reason));
      const conditionNode = card.querySelector('[data-field-condition]');
      conditionNode.textContent = reason;
      conditionNode.hidden = !reason;
      for (const control of card.querySelectorAll('[data-setting]')) {
        control.disabled = Boolean(reason);
        if (field.kind === 'radio') {
          control.checked = draft[key] === control.value;
          control.closest('.option-card').classList.toggle('checked', control.checked);
        } else if (field.kind === 'boolean') {
          control.checked = draft[key];
          card.querySelector('.switch-word').textContent = draft[key] ? '已开启' : '已关闭';
        } else {
          if (['tx_pkg_case', 'rx_pkg_case'].includes(key) && [...control.options].map(option => option.value).join('/') !== settings.optionsFor(key, draft).join('/')) control.innerHTML = settings.optionsFor(key, draft).map(option => `<option value="${option}">${option}</option>`).join('');
          if (control !== document.activeElement || field.kind === 'select') control.value = field.kind === 'files' ? draft[key].join('\n') : draft[key];
        }
      }
      const picker = card.querySelector('[data-file-key]');
      if (picker) { picker.disabled = Boolean(reason); picker.parentElement.classList.toggle('disabled', Boolean(reason)); }
      const error = settings.fieldError(key, draft);
      const errorNode = $(`error-${key}`);
      errorNode.textContent = error;
      errorNode.hidden = !error;
      card.classList.toggle('invalid', Boolean(error));
      card.classList.toggle('modified', changed(key));
      card.querySelector('[data-reset-field]').hidden = !changed(key);
      card.querySelector('[data-setting]')?.setAttribute('aria-invalid', String(Boolean(error)));
    }
    for (const key of Object.keys(settings.tableInfo)) {
      const table = $(`settings-table-${key}`);
      if (table) {
        const reason = settings.disabledReason(key, draft);
        const reasonNode = table.querySelector('.tap-inactive');
        reasonNode.textContent = reason;
        reasonNode.hidden = !reason;
        for (const control of table.querySelectorAll('[data-tap-table]')) {
          control.disabled = Boolean(reason);
        }
        for (const button of table.querySelectorAll('[data-dfe-bulk]')) button.disabled = Boolean(reason);
      }
      const node = $(`table-error-${key}`);
      if (node) { node.textContent = settings.tableError(key, draft); node.hidden = !node.textContent; }
    }
    updateDraftStatus();
  }

  function edited({ render = false } = {}) {
    saveDraft();
    renderMap();
    renderOverview();
    if (render) renderSettings();
    else updateFieldFeedback();
  }

  function showReset(keys, message) {
    lastReset = settings.clone(draft);
    for (const key of keys) draft[key] = settings.clone(settings.defaults[key]);
    for (const key of keys) settings.reconcile(key, draft);
    for (const key of ['tx_pkg_case', 'rx_pkg_case']) if (!settings.optionsFor(key, draft).includes(draft[key])) draft[key] = settings.optionsFor(key, draft)[0];
    edited({ render: true });
    $('toast-message').textContent = message;
    $('draft-toast').hidden = false;
    $('undo-reset').hidden = false;
  }

  function clearUndo() {
    lastReset = null;
    $('draft-toast').hidden = true;
  }

  function editField(target, commit) {
    const key = target.dataset.setting;
    const field = settings.fields[key];
    if (!field || settings.disabledReason(key, draft)) return;
    if (target.type === 'radio' && !target.checked) return;
    clearUndo();
    draft[key] = field.kind === 'boolean' ? target.checked : field.kind === 'number' ? target.value === '' ? '' : Number(target.value) : field.kind === 'files' ? target.value.split('\n').map(line => line.trim()).filter(Boolean) : target.value;
    if (commit) settings.reconcile(key, draft);
    if (['rx_n_taps', 'rx_n_pre'].includes(key)) {
      if (key === 'rx_n_taps' && !settings.fieldError(key, draft)) for (const list of [draft.rx_taps, draft.ffe_tap_tuners]) list.forEach((tap, i) => { tap.enabled = i < draft.rx_n_taps; });
      for (const tableKey of ['rx_taps', 'ffe_tap_tuners']) {
        const table = $(`settings-table-${tableKey}`);
        if (!table) continue;
        const wasOpen = table.open;
        table.outerHTML = tapTable(tableKey);
        if (wasOpen) $(`settings-table-${tableKey}`).open = true;
      }
    }
    edited();
  }

  function renderMapping() {
    const stage = stageById(state.stageId);
    $('mapping-panel').innerHTML = `<p class="mapping-intro">按 PyBERT 11.1.0 / 1bc905d 的实现解释；每条映射均可跳转到固定版本源码。</p><div class="mapping-grid">${stage.mapping.map((item, i) => `<article class="mapping-card"><span class="mapping-number">MAPPING / ${String(i + 1).padStart(2, '0')}</span><h3>${item.title}</h3><p>${item.text}</p>${sourceLink(item.source)}</article>`).join('')}</div>`;
  }

  function setTab(tab) {
    state.tab = tab;
    for (const name of ['settings', 'parameters', 'mapping']) {
      $(`tab-${name}`).setAttribute('aria-selected', String(tab === name));
      $(`tab-${name}`).tabIndex = tab === name ? 0 : -1;
    }
    $('inspector').dataset.view = tab;
    $('settings-panel').hidden = tab !== 'settings';
    $('parameter-panel').hidden = tab !== 'parameters';
    $('mapping-panel').hidden = tab !== 'mapping';
    $('scope-control').hidden = tab !== 'parameters';
    $('reset-stage').hidden = tab !== 'settings' || !stageKeys(stageById(state.stageId)).length;
  }

  function renderStage() {
    renderNav();
    renderMap();
    renderOverview();
    renderSettings();
    renderParameters();
    renderMapping();
    setTab(state.tab);
  }

  function selectStage(id, rowId = null) {
    if (!stageById(id)) return;
    state.stageId = id;
    state.focusRow = rowId;
    state.tab = 'settings';
    let targetId = rowId;
    if (rowId) {
      state.scope = 'all';
      $('scope-filter').value = 'all';
      const entry = allParams.find(item => item.rowId === rowId);
      const keys = entry ? settings.keysFor(entry.param) : [];
      if (keys.length) targetId = settings.tableInfo[keys[0]] ? `settings-table-${keys[0]}` : rowId.replace('param-', 'setting-');
      else state.tab = 'parameters';
    }
    renderStage();
    if (location.hash !== `#${id}`) location.hash = id;
    if (rowId) {
      const target = $(targetId);
      if (target?.tagName === 'DETAILS') target.open = true;
      target?.classList.add('focused-setting');
      target?.scrollIntoView({ block: 'center' });
    }
    else if (window.scrollY > $('inspector').offsetTop) $('inspector').scrollIntoView({ block: 'start' });
  }

  function closeSearch() {
    $('search-results').hidden = true;
    $('search').setAttribute('aria-expanded', 'false');
  }

  function search() {
    const query = $('search').value.trim().toLowerCase();
    if (!query) return closeSearch();
    const terms = query.split(/\s+/);
    const hits = allParams.map(entry => ({ ...entry, score: entry.param.key.toLowerCase() === query ? 3 : entry.param.key.toLowerCase().includes(query) ? 2 : 1 })).filter(entry => terms.every(term => `${entry.stage.name} ${entry.stage.title} ${entry.group.title} ${entry.param.key} ${entry.param.label} ${entry.param.description} ${entry.param.value} ${entry.param.range}`.toLowerCase().includes(term))).sort((a, b) => b.score - a.score);
    $('search-results').hidden = false;
    $('search').setAttribute('aria-expanded', 'true');
    $('search-results').innerHTML = hits.length ? `<div class="search-status" role="status">${hits.length} 个匹配${hits.length > 40 ? ' · 显示前 40 项，请缩小关键词' : ''}</div>${hits.slice(0, 40).map(entry => `<button type="button" class="search-result" data-stage="${entry.stage.id}" data-row="${entry.rowId}"><small>${entry.stage.name}</small><strong>${escape(entry.param.key)}</strong><span>${escape(entry.param.label)}</span></button>`).join('')}` : '<div class="search-empty" role="status">没有匹配的参数。试试 “peak_mag”、“时钟” 或 “AMI”。</div>';
  }

  document.addEventListener('click', event => {
    const guiButton = event.target.closest('[data-gui-key]');
    if (guiButton) {
      const entry = guiEntry(guiButton.dataset.guiKey);
      if (entry) {
        $('gui-crosswalk').open = false;
        selectStage(entry.stage.id, entry.rowId);
        const key = guiButton.dataset.guiKey;
        const control = $(`control-${key}`) || $('settings-panel').querySelector(`[data-dfe-bulk="${key === 'btn_disable' ? 'disable' : 'enable'}"]`);
        if (control) { control.closest('.setting-card')?.classList.add('focused-setting'); control.scrollIntoView({ block: 'center' }); }
      }
    }
    const bulkButton = event.target.closest('[data-dfe-bulk]');
    if (bulkButton && !bulkButton.disabled) {
      clearUndo();
      draft.dfe_tap_tuners.forEach(tap => { tap.enabled = bulkButton.dataset.dfeBulk === 'enable'; });
      edited({ render: true });
    }
    const stageButton = event.target.closest('[data-stage]');
    if (stageButton) {
      const fromNav = stageButton.closest('#stage-nav');
      selectStage(stageButton.dataset.stage, stageButton.dataset.row || null);
      if (fromNav) $('stage-nav').querySelector('[aria-current="true"]').focus({ preventScroll: true });
      closeSearch();
    }
    const tabButton = event.target.closest('[data-tab]');
    if (tabButton) setTab(tabButton.dataset.tab);
    if (event.target.id === 'show-all') {
      state.scope = 'all';
      $('scope-filter').value = 'all';
      renderParameters();
    }
    const resetField = event.target.closest('[data-reset-field]');
    if (resetField) showReset([resetField.dataset.resetField], '已恢复此项默认值。');
    if (!event.target.closest('.search-wrap')) closeSearch();
  });
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
      event.preventDefault();
      $('search').focus();
    }
    if (event.key === 'Escape') { closeSearch(); $('search').blur(); }
    if (event.target.closest('[role="tablist"]') && ['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
      event.preventDefault();
      const tabs = ['settings', 'parameters', 'mapping'];
      const tab = event.key === 'Home' ? 'settings' : event.key === 'End' ? 'mapping' : tabs[(tabs.indexOf(state.tab) + (event.key === 'ArrowRight' ? 1 : 2)) % tabs.length];
      setTab(tab);
      $(`tab-${tab}`).focus();
    }
    if (document.activeElement === $('search') && event.key === 'ArrowDown' && !$('search-results').hidden) {
      event.preventDefault();
      $('search-results').querySelector('button')?.focus();
    }
  });
  $('search').addEventListener('input', search);
  $('search').addEventListener('focus', search);
  $('scope-filter').addEventListener('change', event => { state.scope = event.target.value; renderParameters(); });
  function changeModes(event) {
    clearUndo();
    if (event.target.id === 'ami-clocks') draft.rx_use_clocks = event.target.checked;
    else {
      const side = event.target.id === 'tx-mode' ? 'tx' : 'rx';
      draft[`${side}_eq_sel`] = event.target.value === 'native' ? 'Native' : 'IBIS-AMI';
      draft[`${side}_use_getwave`] = event.target.value === 'getwave';
      if (side === 'rx' && event.target.value !== 'getwave') draft.rx_use_clocks = false;
    }
    edited({ render: true });
  }
  for (const id of ['tx-mode', 'rx-mode', 'ami-clocks']) $(id).addEventListener('change', changeModes);
  $('reset-modes').addEventListener('click', () => showReset(['tx_eq_sel', 'rx_eq_sel', 'tx_use_getwave', 'rx_use_getwave', 'rx_use_clocks'], 'Tx / Rx 实现方案已恢复为 Native。'));
  $('reset-draft').addEventListener('click', () => showReset(Object.keys(settings.defaults), '全部设置已恢复为源码默认值。'));
  $('reset-stage').addEventListener('click', () => showReset(stageKeys(stageById(state.stageId)), '本模块已恢复默认值。'));
  $('close-toast').addEventListener('click', clearUndo);
  $('undo-reset').addEventListener('click', () => {
    if (!lastReset) return;
    draft = lastReset;
    clearUndo();
    edited({ render: true });
  });
  $('settings-panel').addEventListener('input', event => {
    const target = event.target;
    if (target.matches('[data-setting]') && !['checkbox', 'radio', 'select-one'].includes(target.type)) editField(target, false);
    if (target.matches('[data-tap-table]') && target.type === 'number') {
      clearUndo();
      const { tapTable: key, tapIndex: index, tapColumn: column } = target.dataset;
      draft[key][index][column] = target.value === '' ? '' : Number(target.value);
      target.classList.toggle('modified', draft[key][index][column] !== settings.defaults[key][index][column]);
      edited();
    }
  });
  $('settings-panel').addEventListener('change', event => {
    const target = event.target;
    if (target.matches('[data-setting]')) editField(target, true);
    if (target.matches('[data-tap-table]') && target.type === 'checkbox') {
      clearUndo();
      const key = target.dataset.tapTable;
      const index = Number(target.dataset.tapIndex);
      draft[key][index].enabled = target.checked;
      edited({ render: true });
      $('settings-panel').querySelector(`[data-tap-table="${key}"][data-tap-index="${index}"][data-tap-column="enabled"]`)?.focus({ preventScroll: true });
    }
    if (target.matches('[data-file-key]') && target.files.length) {
      clearUndo();
      const key = target.dataset.fileKey;
      draft[key] = settings.fields[key].kind === 'files' ? [...target.files].map(file => file.name) : target.files[0].name;
      edited({ render: true });
    }
  });
  window.addEventListener('hashchange', () => { const id = location.hash.slice(1); if (stageById(id) && id !== state.stageId) selectStage(id); });
  function guiEntry(key) {
    if (['btn_disable', 'btn_enable'].includes(key)) key = 'dfe_tap_tuners';
    return allParams.find(entry => settings.keysFor(entry.param).includes(key) || entry.param.key === key);
  }
  function renderGuiIndex() {
    const groups = Map.groupBy(window.PYBERT_GUI.items, item => item.path);
    $('gui-index').innerHTML = `<p class="gui-intro">按原 GUI 的分组定位 ${window.PYBERT_GUI.items.length} 个命名控件。按钮可直达设置或参考说明；“未接入”不代表已经运行或完成迁移。<a href="gui-audit.zh-CN.md">查看本次核对记录 ↗</a></p>${[...groups].map(([path, items]) => `<details class="gui-section"><summary>${escape(path)}<span>${items.length} 项</span></summary><div class="gui-rows">${items.map(item => {
      const entry = guiEntry(item.key);
      const field = settings.fields[item.key];
      const status = field?.readonly ? '未接模型 / 数据' : settings.fields[item.key] || settings.tableInfo[item.key] || item.key.startsWith('btn_') ? '本地草稿' : '参考 · 未接入';
      return `<div class="gui-row"><div><strong>${escape(item.label)}</strong><code>${item.key}</code></div><span class="gui-status">${status}</span>${entry ? `<button type="button" class="text-button" data-gui-key="${item.key}">${entry.stage.name} →</button>` : '<span>未接入</span>'}<a class="source-link" href="${window.PYBERT_CATALOG.root}src/pybert/gui/view.py#L${item.line}" target="_blank" rel="noopener noreferrer">源码 ↗</a></div>`;
    }).join('')}</div></details>`).join('')}<details class="gui-section"><summary>菜单与状态栏<span>操作范围</span></summary><div class="gui-menu-list">${window.PYBERT_GUI.menus.map(menu => `<p><strong>${menu.name}</strong> · ${menu.items.join(' / ')}</p>`).join('')}<p>Debug Mode 对应 Simulation / Debug 草稿。Load / Save 原生配置与结果、Run / Abort、Tune / Use / Reset EQ、Quit 及原生帮助窗口均未接入；本地“恢复默认”不等于原生 Reset EQ。</p><p>状态栏的运行状态、性能、延时、误码、功率、抖动和 COM 均依赖引擎，本页不提供运行值。</p></div></details>`;
  }
  renderGuiIndex();
  renderStage();
})();
