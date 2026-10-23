/* Native snapshots, task identity and plots are separate from the editable prototype draft. */
(() => {
  const $ = id => document.getElementById(id);
  const ui = window.PYBERT_WORKBENCH, settings = window.PYBERT_SETTINGS;
  const clone = settings.clone;
  const tables = {tx_taps: ['enabled', 'value', 'min_val', 'max_val'], rx_taps: ['enabled', 'value', 'min_val', 'max_val'], tx_tap_tuners: ['enabled', 'pos', 'min_val', 'max_val', 'step'], ffe_tap_tuners: ['enabled', 'pos', 'min_val', 'max_val', 'step'], dfe_tap_tuners: ['enabled', 'min_val', 'max_val']};
  let base = null, captured = null, patches = [], normalized = null, revision = 0, normalizedRevision = -1;
  let activeTask = null, currentTask = null, runs = [], selected = null, normalizing = null, timer = null, disconnected = false, logicalName = '', renderToken = 0;
  const esc = v => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const equal = (a,b) => JSON.stringify(a) === JSON.stringify(b);
  async function api(path, body) {
    const response = await fetch(`/api/${path}`, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const value = await response.json();
    if (!response.ok) throw new Error(value.detail || response.statusText);
    return value;
  }
  function toDraft(config) {
    const draft = clone(settings.defaults);
    for (const [key,value] of Object.entries(config)) {
      if (tables[key]) draft[key] = value.map(row => Object.fromEntries(tables[key].map((column,i) => [column,row[i]])));
      else if (key in settings.fields) draft[key] = clone(value);
    }
    return draft;
  }
  function toNative(draft) {
    const config = clone(base);
    for (const key of Object.keys(config)) {
      if (tables[key]) config[key] = draft[key].map((row,i) => tables[key].map((column,j) => row[column] ?? config[key][i][j]));
      else if (key in settings.fields && !settings.fields[key].readonly && settings.fields[key].kind !== 'unavailable') config[key] = clone(draft[key]);
    }
    return config;
  }
  function record() {
    if (!base) return;
    const next = toNative(ui.getDraft());
    for (const key of Object.keys(next)) if (!equal(next[key], captured[key])) {
      const boundary = patches.findLastIndex(p => ['rx_n_pre','rx_n_taps'].includes(p.field));
      const existing = patches.findLastIndex(p => p.field === key);
      if (!['rx_n_pre','rx_n_taps'].includes(key) && existing > boundary) patches[existing].value = clone(next[key]);
      else patches.push({field:key,value:clone(next[key])});
    }
    captured = next;
  }
  function localError() {
    const draft = ui.getDraft();
    return Object.keys(settings.fields).map(key => settings.fieldError(key,draft)).find(Boolean) || Object.keys(tables).map(key => settings.tableError(key,draft)).find(Boolean);
  }
  function controls() {
    const locked = !base || !!normalizing || disconnected;
    for (const id of ['run','save-config','save-as','load-config']) $(id).disabled = locked || !!activeTask;
    $('abort').disabled = !activeTask || disconnected;
    $('inspector').inert = !!normalizing;
    for (const id of ['reset-draft','reset-stage','tx-mode','rx-mode','reset-modes']) $(id).disabled = !!normalizing;
    $('stale').textContent = selected ? (normalizedRevision !== revision || selected.input_hash !== normalized?.input_hash ? 'Older input · draft changed' : 'Matches validated input') : '';
  }
  async function normalizeDraft() {
    if (normalizing) return normalizing;
    if (activeTask) throw new Error('Native slot busy; input validation is pending.');
    document.activeElement?.blur();
    record();
    const error = localError();
    if (error) throw new Error(error);
    const expectedRevision = revision;
    const request = patches.length ? {mode:'patch', config:base, patches:clone(patches)} : {mode:'load', config:base};
    normalizing = api('normalize', request);
    $('input-status').textContent = 'Normalizing native observers…'; controls();
    try {
      const result = await normalizing;
      base = result.config; normalized = result; patches = [];
      ui.replaceDraft(toDraft(base)); captured = toNative(ui.getDraft());
      persistNative();
      normalizedRevision = expectedRevision;
      $('input-status').textContent = result.warnings.join(' ');
      return result;
    } finally { normalizing = null; controls(); }
  }
  function inputError(error) { $('input-status').textContent = `Input: ${error.message}`; controls(); }
  function persistNative() {
    try { localStorage.setItem('pybert-native-snapshot-v1',JSON.stringify({schema:1,config:base,name:logicalName})); }
    catch { /* The prototype draft-status independently reports storage failures. */ }
  }
  window.addEventListener('pybert-draft', event => {
    revision++; controls();
    if (event.detail.commit) {
      record();
      clearTimeout(timer);
      timer = setTimeout(() => { if (!activeTask && !normalizing) normalizeDraft().catch(inputError); }, 200);
    } else $('input-status').textContent = activeTask ? 'Draft edited; native validation pending until worker exit.' : 'Draft edited; commit the field to validate.';
  });
  function pickPlot() {
    const stage = ui.getStage(), kind = $('analysis-kind').value;
    const point = ({source:'ideal_signal',noise:'rx_in',tx:'rx_in',channel:'chnl_out',ctle:'ctle_out',rxffe:'ffe_out',dfe:'dfe_out',agc:'dfe_out',cdr:'dfe_out'})[stage];
    if (kind === 'response') {
      let response = ({channel:'chnl',tx:'tx',ctle:'ctle',rxffe:'ffe',dfe:'dfe'})[stage];
      if (!response) return null;
      if ($('response-scope').value === 'cumulative' && response !== 'chnl') response += '_out';
      return `${response}_${$('response-type').value}`;
    }
    if (kind === 'wave') return stage === 'analysis' ? 'waveforms' : point ? `wave.${point}` : null;
    if (kind === 'eye') return ['tx','noise'].includes(stage) ? 'eye.rx_in' : ['dfe','cdr','agc'].includes(stage) ? 'eye.dfe' : null;
    if (kind.startsWith('jitter.')) return ['dfe','analysis','cdr'].includes(stage) ? kind : null;
    if (kind === 'adaptation' || kind === 'cdr') return kind;
    return kind;
  }
  function empty(message) { Plotly.purge('plot'); $('plot').innerHTML = `<p class="empty-result">${esc(message)}</p>`; }
  async function renderAnalysis() {
    const token = ++renderToken;
    $('analysis-info').innerHTML = '';
    $('response-type').hidden = $('response-scope').hidden = $('analysis-kind').value !== 'response';
    if (!selected) return empty('No successful native run. Run the engine to inspect real data.');
    $('run-log-id').textContent = `Selected successful run: ${selected.run_id}`;
    $('run-log').textContent = (selected.logs || []).join('\n');
    const id = pickPlot();
    $('plot').classList.toggle('text-mode',['overview','jitter.info','compare'].includes(id));
    if (!id) return empty('This observation is unavailable in #2 at this node. Rx input and DFE eyes are supported; additional eye/jitter points are tracked in #3.');
    if (id === 'overview') {
      empty(`Run ${selected.run_id} · ${selected.effective_input.mod_type} · ${selected.input_hash.slice(0,12)}`);
      $('analysis-info').innerHTML = `<pre>${esc(JSON.stringify({summary:selected.summary,window:selected.window,warnings:selected.warnings,native_sha:selected.native_sha,adapter_sha:selected.adapter_sha},null,2))}</pre>`;
      return;
    }
    if (id === 'jitter.info') {
      empty('DFE crossing-jitter statistics · ISI/DCD/PJ peak-to-peak, RJ sigma; dual-Dirac estimates are reference only.');
      $('analysis-info').innerHTML = `<table><tr><th>Metric</th><th>ps</th></tr>${Object.entries(selected.summary.dfe_jitter_s).map(([key,value]) => `<tr><td>${esc(key)}</td><td>${(value*1e12).toPrecision(8)}</td></tr>`).join('')}</table><p>Native CTLE→DFE comparison includes Rx FFE. Crossing jitter does not certify voltage eye margin or BER.</p>`;
      return;
    }
    if (id === 'compare') {
      if (runs.length < 2) return empty('Two successful runs are required. Failed and cancelled tasks are excluded.');
      const [a,b] = await Promise.all(runs.map(r => api(`runs/${r.run_id}`)));
      if (token !== renderToken) return;
      const differences = Object.keys(a.effective_input).filter(key => !equal(a.effective_input[key],b.effective_input[key]));
      empty('Two immutable successful runs · inputs and native summaries');
      $('analysis-info').innerHTML = `<table><tr><th></th><th>A ${esc(a.run_id.slice(0,8))}</th><th>B ${esc(b.run_id.slice(0,8))}</th></tr>${['n_errs_dfe','chnl_dly_s','rel_power','initial_level_v','final_level_v'].map(key => `<tr><td>${key}</td><td>${a.summary[key]}</td><td>${b.summary[key]}</td></tr>`).join('')}</table><p>Input differences: ${esc(differences.join(', ') || 'None')}</p><pre>${esc(JSON.stringify(differences.map(key => ({field:key,A:a.effective_input[key],B:b.effective_input[key]})),null,2))}</pre><p>A window ${esc(JSON.stringify(a.window))}<br>B window ${esc(JSON.stringify(b.window))}</p>`;
      return;
    }
    if (!selected.plots[id]) return empty('This dataset is unavailable for this run.');
    const plot = await api(`runs/${selected.run_id}/plots/${id}`);
    if (token !== renderToken || plot.run_id !== selected.run_id) return;
    $('plot').innerHTML = '';
    await Plotly.newPlot('plot',plot.data,{title:{text:plot.title,font:{size:14}},margin:{l:65,r:30,t:50,b:50},xaxis:{title:{text:plot.xunit},type:plot.logx?'log':'linear'},yaxis:{title:{text:plot.yunit}},legend:{orientation:'h',y:-.22},paper_bgcolor:'#fff',plot_bgcolor:'#f7f9fc',font:{family:'Arial',size:11}},{responsive:true,displaylogo:false});
    $('analysis-info').textContent = `Run ${plot.run_id} · ${id} · ${selected.effective_input.mod_type}. ${id.startsWith('dfe') ? 'DFE response is a final-weight equivalent FIR, not a nonlinear transfer function.' : ''}`;
  }
  async function chooseRun(id) {
    const result = id ? await api(`runs/${id}`) : null;
    if ($('selected-run').value !== (id || '')) return;
    selected = result;
    controls(); await renderAnalysis();
  }
  async function poll() {
    if (disconnected) return;
    try {
      const state = await api('state');
      activeTask = state.active_task_id;
      currentTask = state.current_task_id;
      if (currentTask) {
        const task = await api(`tasks/${currentTask}`);
        $('task-state').textContent = `${task.operation} ${task.task_id.slice(0,8)} · ${task.state} · ${task.phase}${task.error ? ` · ${task.error}`:''}`;
        $('live-log-id').textContent = `Current task: ${task.task_id} · cancel requested=${task.cancel_requested}, observed=${task.cancel_observed}, exited=${task.worker_exited}`;
        $('live-log').textContent = [...task.logs,task.error || ''].join('\n');
      }
      if (!equal(state.runs.map(r => r.run_id),runs.map(r => r.run_id))) {
        const previous = runs.map(r => r.run_id); runs = state.runs;
        $('selected-run').innerHTML = '<option value="">Select successful run…</option>' + runs.map(r => `<option value="${r.run_id}">${r.effective_input.mod_type} · ${r.run_id.slice(0,8)}</option>`).join('');
        const latest = runs.findLast(r => !previous.includes(r.run_id));
        const id = latest?.run_id || (runs.some(r => r.run_id === selected?.run_id) ? selected.run_id : runs.at(-1)?.run_id);
        $('selected-run').value = id || ''; await chooseRun(id);
      }
      controls();
    } catch (error) { $('task-state').textContent = `Service unavailable: ${error.message}`; }
    setTimeout(poll,1000);
  }
  $('run').addEventListener('click',async () => {
    clearTimeout(timer);
    try {
      const input = await normalizeDraft();
      const task = await api('runs',{config:input.config,input_hash:input.input_hash,draft_revision:revision});
      activeTask = currentTask = task.task_id; controls();
      $('task-state').textContent = `Run ${task.task_id} · validating`;
    } catch (error) { inputError(error); }
  });
  $('abort').addEventListener('click',async () => { if (activeTask) { const task = await api(`tasks/${activeTask}/cancel`,{}); $('task-state').textContent = `${task.task_id} · ${task.state}; awaiting worker exit`; } });
  $('selected-run').addEventListener('change',() => chooseRun($('selected-run').value).catch(inputError));
  for (const id of ['analysis-kind','response-type','response-scope']) $(id).addEventListener('change',() => renderAnalysis().catch(inputError));
  document.addEventListener('click',event => { if (event.target.closest('[data-stage]')) renderAnalysis().catch(inputError); });
  window.addEventListener('hashchange',() => renderAnalysis().catch(inputError));
  $('load-config').addEventListener('click',() => $('config-file').click());
  $('config-file').addEventListener('change',async event => {
    const file = event.target.files[0]; if (!file) return;
    clearTimeout(timer);
    try {
      normalizing = file.text().then(yaml => api('normalize',{mode:'load',yaml})); controls();
      const result = await normalizing;
      base = result.config; normalized = result; patches = []; revision++; normalizedRevision = revision;
      ui.replaceDraft(toDraft(base)); captured = toNative(ui.getDraft());
      logicalName = file.name; $('config-name').textContent = logicalName;
      persistNative();
      $('input-status').textContent = result.warnings.join(' '); controls();
    } catch (error) { inputError(error); }
    finally { normalizing = null; controls(); }
    event.target.value = '';
  });
  function download(name) {
    const a = document.createElement('a'), url = URL.createObjectURL(new Blob([normalized.yaml],{type:'application/yaml'}));
    a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
    logicalName = name; $('config-name').textContent = name;
    persistNative();
  }
  async function save(as) {
    clearTimeout(timer);
    try { await normalizeDraft(); if (as || !logicalName) { $('save-name').value = logicalName || 'pybert.yaml'; $('name-dialog').showModal(); } else download(logicalName); }
    catch (error) { inputError(error); }
  }
  $('save-config').addEventListener('click',() => save(false)); $('save-as').addEventListener('click',() => save(true));
  $('name-dialog').addEventListener('close',() => { if ($('name-dialog').returnValue === 'save') download($('save-name').value); });
  $('help').addEventListener('click',() => $('help-dialog').showModal()); $('close-help').addEventListener('click',() => $('help-dialog').close());
  $('quit').addEventListener('click',() => { disconnected=true; controls(); $('task-state').textContent='Disconnected. You may close this tab; backend tasks continue.'; });
  async function init() {
    controls();
    let saved = null;
    try { if (ui.hasSavedDraft()) saved = ui.getDraft(); } catch { /* existing draft status shows storage failure */ }
    for (const key of ['rlm','rx_use_clocks','ami_opt_trials']) if (settings.fields[key]) settings.fields[key].readonly = 'Runtime/optimization extension is outside #2; retained separately, not exported into native YAML.';
    settings.tableInfo.tx_tap_tuners.readonly = ['value'];
    const version = await api('version'); $('version-info').textContent = JSON.stringify(version,null,2);
    const defaults = await api('normalize',{mode:'defaults'});
    base = defaults.config; normalized = defaults; normalizedRevision = revision;
    ui.setDefaults(toDraft(base));
    try { const previous=JSON.parse(localStorage.getItem('pybert-native-snapshot-v1') || 'null'); if (previous?.schema===1) { base=previous.config;logicalName=previous.name || ''; } } catch { /* Invalid storage is kept as a visible draft failure. */ }
    $('config-name').textContent=logicalName || 'Untitled';
    ui.replaceDraft(saved ? {...toDraft(base),...saved} : toDraft(base));
    captured = clone(base); record();
    if (saved && patches.length) { revision++; normalizedRevision=-1; }
    $('input-status').textContent = defaults.warnings.join(' '); controls();
    await poll();
  }
  init().catch(inputError);
})();
