/* Native snapshots, task identity and plots are separate from the editable prototype draft. */
(() => {
  const $ = id => document.getElementById(id);
  const ui = window.PYBERT_WORKBENCH, settings = window.PYBERT_SETTINGS;
  const clone = settings.clone;
  const tables = {tx_taps: ['enabled', 'value', 'min_val', 'max_val'], rx_taps: ['enabled', 'value', 'min_val', 'max_val'], tx_tap_tuners: ['enabled', 'pos', 'min_val', 'max_val', 'step'], ffe_tap_tuners: ['enabled', 'pos', 'min_val', 'max_val', 'step'], dfe_tap_tuners: ['enabled', 'min_val', 'max_val']};
  let base = null, captured = null, patches = [], normalized = null, revision = 0, normalizedRevision = -1;
  let activeTask = null, currentTask = null, runs = [], selected = null, normalizing = null, timer = null, pendingValidation = false, disconnected = false, logicalName = '', renderToken = 0;
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
      const previous = patches.at(-1);
      if (!['rx_n_pre','rx_n_taps'].includes(key) && previous?.field === key) previous.value = clone(next[key]);
      else patches.push({field:key,value:clone(next[key])});
    }
    captured = next;
  }
  function localError() {
    const draft = ui.getDraft();
    const changingTapCount = patches.some(patch => patch.field === 'rx_n_taps');
    return Object.keys(settings.fields).map(key => settings.fieldError(key,draft,{deferObserver:key==='rx_n_pre' && changingTapCount})).find(Boolean) || Object.keys(tables).map(key => settings.tableError(key,draft)).find(Boolean);
  }
  function controls() {
    const locked = !base || !!normalizing || disconnected;
    for (const id of ['run','save-config','save-as','load-config']) $(id).disabled = locked || !!activeTask;
    $('abort').disabled = !activeTask || disconnected;
    $('inspector').inert = !!normalizing;
    for (const id of ['reset-draft','reset-stage','tx-mode','rx-mode','reset-modes','undo-reset']) $(id).disabled = !!normalizing;
    $('stale').textContent = selected ? (normalizedRevision !== revision || selected.input_hash !== normalized?.input_hash ? 'Older input · draft changed' : 'Matches validated input') : '';
  }
  async function normalizeDraft() {
    if (normalizing) return normalizing;
    if (activeTask) throw new Error('Native slot busy; input validation is pending.');
    document.activeElement?.blur();
    record();
    pendingValidation = false;
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
  function validateWhenIdle() {
    if (pendingValidation && !activeTask && !normalizing) normalizeDraft().catch(inputError);
  }
  function persistNative() {
    try { localStorage.setItem('pybert-native-snapshot-v1',JSON.stringify({schema:1,config:base,name:logicalName})); }
    catch { /* The prototype draft-status independently reports storage failures. */ }
  }
  window.addEventListener('pybert-draft', event => {
    revision++; controls();
    if (event.detail.commit) {
      record();
      pendingValidation = true;
      clearTimeout(timer);
      timer = setTimeout(validateWhenIdle, 200);
    } else $('input-status').textContent = activeTask ? 'Draft edited; native validation pending until worker exit.' : 'Draft edited; commit the field to validate.';
  });
  function observation() {
    return $('analysis-point').value === 'node' ? ({channel:'chnl',tx:'tx',noise:'tx',ctle:'ctle',rxffe:'ffe',dfe:'dfe',cdr:'dfe',agc:'dfe',analysis:'dfe'})[ui.getStage()] : $('analysis-point').value;
  }
  function pickPlot(chosenPoint = observation()) {
    const stage = ui.getStage(), kind = $('analysis-kind').value;
    const point = ({chnl:'chnl_out',tx:'rx_in',ctle:'ctle_out',ffe:'ffe_out',dfe:'dfe_out'})[chosenPoint];
    if (kind === 'response') {
      let response = chosenPoint;
      if (!response) return null;
      if (response === 'chnl' && $('response-type').value === 'H') return 'channel.frequency';
      if ($('response-scope').value === 'cumulative' && response !== 'chnl') response += '_out';
      return `${response}_${$('response-type').value}`;
    }
    if (kind === 'wave') return point ? `wave.${point}` : stage === 'source' ? 'wave.ideal_signal' : null;
    if (kind === 'eye') return chosenPoint ? `eye.${chosenPoint}${chosenPoint === 'chnl' && $('channel-noise').checked ? '.gui_noise' : ''}` : null;
    if (kind.startsWith('jitter.') && kind !== 'jitter.info') return chosenPoint ? `jitter.${chosenPoint}.${kind.split('.')[1]}` : null;
    return kind;
  }
  function empty(message) { Plotly.purge('plot'); $('plot').innerHTML = `<p class="empty-result">${esc(message)}</p>`; }
  async function renderAnalysis() {
    const token = ++renderToken;
    $('analysis-info').innerHTML = '';
    $('response-type').hidden = $('response-scope').hidden = $('analysis-kind').value !== 'response';
    $('channel-noise-label').hidden = $('analysis-kind').value !== 'eye';
    if (!selected) return empty('No successful native run. Run the engine to inspect real data.');
    $('run-log-id').textContent = `Selected successful run: ${selected.run_id}`;
    $('run-log').textContent = (selected.logs || []).join('\n');
    const id = pickPlot();
    $('plot').classList.toggle('text-mode',['overview','jitter.info','compare'].includes(id));
    if (['overview','jitter.info','compare'].includes(id)) $('plot').style.height='auto';
    if (!id) return empty('No matching observation at this node. Choose an explicit Point.');
    if (id === 'overview') {
      empty(`Run ${selected.run_id} · ${selected.effective_input.mod_type} · ${selected.input_hash.slice(0,12)}`);
      $('analysis-info').innerHTML = `<pre>${esc(JSON.stringify({summary:selected.summary,window:selected.window,warnings:selected.warnings,native_sha:selected.native_sha,adapter_sha:selected.adapter_sha},null,2))}</pre>`;
      return;
    }
    if (id === 'jitter.info') {
      if (!selected.observations) {
        empty(`Legacy DFE crossing-jitter summary · raw schema ${selected.raw_schema_version}. Other observations, fit validity and rejection segments are unavailable; no calculation started.`);
        $('analysis-info').innerHTML = `<table><tr><th>Stored DFE metric</th><th>ps · raw reference</th></tr>${Object.entries(selected.summary.dfe_jitter_s || {}).map(([key,value]) => `<tr><td>${esc(key)}</td><td>${(value*1e12).toPrecision(8)}${['rjDD','mu_pos','mu_neg'].includes(key)?' · fit validity unknown':''}</td></tr>`).join('')}</table>`;
        return;
      }
      empty('Crossing jitter · ISI/DCD/PJ peak-to-peak, RJ sigma; dual-Dirac is reference only, not bathtub parameters.');
      const info = Object.values(selected.observations), metrics = ['isi','dcd','pj','rj','pjDD','rjDD','mu_pos','mu_neg','dj_pos','dj_neg'];
      function statistic(p,key) {
        if (p.statistics_s[key] == null) return esc(p.reason);
        const raw=(p.statistics_s[key]*1e12).toPrecision(8);
        return ['rjDD','mu_pos','mu_neg'].includes(key) && p.dual_dirac_fit?.availability !== 'available' ? `${esc(p.dual_dirac_fit?.availability || 'unknown')} · raw reference ${raw}` : raw;
      }
      $('analysis-info').innerHTML = `<table><tr><th>Metric (ps)</th>${info.map(p => `<th>${esc(p.label)}</th>`).join('')}</tr>${metrics.map(key => `<tr><td>${key}</td>${info.map(p => `<td>${statistic(p,key)}</td>`).join('')}</tr>`).join('')}</table><p>PAM4: only symmetric transitions about 0V inform the crossing statistics. Data-independent PDF is not a tail extrapolation. Bathtubs use separated RJ and bounded dj_pos/dj_neg; this is a timing estimate.</p>${info.map(p => `<p>${esc(p.label)} · DD fit ${esc(p.dual_dirac_fit?.availability || 'unknown')}: ${esc(p.dual_dirac_fit?.reason || 'finite native fit covariance')}.</p>`).join('')}<table><tr><th>Segment</th><th>Metric</th><th>Rejection ratio</th></tr>${selected.jitter_rejection.map(r => `<tr><td>${esc(r.segment)} (${r.source}→${r.target})</td><td>${r.metric}</td><td>${r.availability === 'available' ? r.raw_ratio.toPrecision(7) : esc(r.reason)}</td></tr>`).join('')}</table>`;
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
    const compare = $('compare-mode').value, kind = $('analysis-kind').value;
    const pointKinds = ['response','wave','eye','jitter.dist','jitter.spec','jitter.bathtub'];
    const points = compare === 'points' && pointKinds.includes(kind) ? ['chnl','tx','ctle','ffe','dfe'] : [observation()];
    let sources = [selected];
    if (compare === 'runs') {
      const other = runs.find(r => r.run_id !== selected.run_id);
      if (!other) return empty('Two successful runs are required for chart comparison.');
      sources.push(await api(`runs/${other.run_id}`));
    }
    if (token !== renderToken) return;
    const requests = sources.flatMap(run => points.map(point => {
      let id=pickPlot(point);
      if (!run.analysis_version) {
        if (id === 'channel.frequency') id='chnl_H';
        if (id === 'eye.tx') id='eye.rx_in';
        if (id === 'jitter.dfe.dist') id='jitter.dist';
        if (id === 'jitter.dfe.spec') id='jitter.spec';
      }
      return {run,id};
    }));
    const missing = requests.filter(r => !r.run.plots[r.id]);
    if (missing.length) return empty(`Analysis unavailable for ${missing.map(r => `${r.run.run_id.slice(0,8)} / ${r.id} (raw schema ${r.run.raw_schema_version})`).join(', ')}. Saved runs are immutable; switching views does not calculate missing datasets.`);
    const charts = await Promise.all(requests.map(async r => {
      const plot=await api(`runs/${r.run.run_id}/plots/${r.id}`);
      if (!r.run.analysis_version && r.id === 'chnl_H') {
        plot.title='Legacy Channel actual termination · raw schema 2; three-source view unavailable';
        plot.data.forEach(trace => { trace.name='Legacy actual termination · three-source view unavailable'; });
        plot.metadata={...plot.metadata,legacy_note:plot.title,source_field:'chnl_H'};
      }
      return {...plot,run:r.run};
    }));
    if (token !== renderToken) return;
    const unavailable = charts.filter(p => p.availability === 'unavailable');
    if (unavailable.length) return empty(unavailable.map(p => `${p.run_id.slice(0,8)} · ${p.title}: ${p.reason}`).join(' | '));
    const first = charts[0], heatmap = first.data[0]?.type === 'heatmap';
    if (charts.some(p => p.xunit !== first.xunit || p.yunit !== first.yunit || p.logx !== first.logx || (p.data[0]?.type === 'heatmap') !== heatmap)) return empty('Incompatible units, axis scales or dataset types; no index-based overlay is allowed.');
    $('plot').innerHTML = '';
    const facets = heatmap && charts.length > 1, rows = facets ? Math.ceil(charts.length/2) : 1;
    $('plot').style.height = `${facets ? rows*300+130 : $('work-area').classList.contains('viewer-expanded') ? 430 : 310}px`;
    const layout = {title:{text:charts.length === 1 ? first.title : `${compare === 'runs' ? 'Two runs' : 'Same run · all points'} · ${kind}`,font:{size:13}},margin:{l:65,r:35,t:60,b:100},xaxis:{title:{text:first.xunit},type:first.logx?'log':'linear'},yaxis:{title:{text:first.yunit}},legend:{orientation:'h',y:-.3,font:{size:10}},paper_bgcolor:'#fff',plot_bgcolor:'#f7f9fc',font:{family:'Arial',size:11},annotations:[]};
    if (facets) { layout.margin.r=70; layout.coloraxis={colorscale:'Viridis',colorbar:{title:{text:'count'}}}; }
    const data = charts.flatMap((p,i) => {
      const suffix = i ? String(i+1) : '', x = `x${suffix}`, y = `y${suffix}`;
      if (facets) {
        const col = i%2, row = Math.floor(i/2);
        layout[`xaxis${suffix}`] = {domain:[col*.53,col*.53+.43],anchor:y,title:{text:p.xunit}};
        layout[`yaxis${suffix}`] = {domain:[1-(row+1)/rows+.11/rows,1-row/rows-.08/rows],anchor:x,title:{text:p.yunit}};
        layout.annotations.push({text:`${p.run_id.slice(0,8)} · ${requests[i].id}`,x:col*.53+.22,y:1-row/rows,xref:'paper',yref:'paper',showarrow:false,font:{size:10}});
      }
      const label=compare === 'runs' ? p.run_id.slice(0,8) : ({chnl:'Channel',tx:'Rx input',ctle:'CTLE',ffe:'Rx FFE',dfe:'DFE'})[requests[i].id.split('.')[1]];
      return p.data.map(trace => ({...trace,name:charts.length>1 && label ? `${label} · ${trace.name || requests[i].id}` : trace.name,...(facets ? {xaxis:x,yaxis:y,coloraxis:'coloraxis'} : {})}));
    });
    await Plotly.newPlot('plot',data,layout,{responsive:true,displaylogo:false});
    if (token !== renderToken) return;
    $('analysis-info').innerHTML = `<p>DFE responses are final-weight equivalent FIRs. Each trace uses its own physical x coordinates; no index alignment or resampling. Zoom/pan and double-click reset do not Run. Crossing-jitter bathtubs do not certify voltage margin/BER.</p>${charts.map(p => `<details><summary>${esc(p.run_id)} · ${esc(p.plot_id)} · ${esc(p.run.effective_input.mod_type)} · input ${p.run.input_hash.slice(0,12)}</summary><pre>${esc(JSON.stringify({window:p.metadata.window || p.run.window,metadata:p.metadata,source:p.run.observations?.[p.plot_id.split('.')[1]],native_sha:p.run.native_sha,adapter_sha:p.run.adapter_sha},null,2))}</pre></details>`).join('')}`;
    if ($('work-area').classList.contains('viewer-expanded')) $('analysis').scrollIntoView({block:'start',behavior:'instant'});
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
      validateWhenIdle();
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
  for (const id of ['analysis-kind','response-type','response-scope','analysis-point','compare-mode','channel-noise']) $(id).addEventListener('change',() => renderAnalysis().catch(inputError));
  $('expand-viewer').addEventListener('click',() => { const expanded=$('work-area').classList.toggle('viewer-expanded'); $('expand-viewer').textContent=expanded?'Restore settings':'Expand viewer'; renderAnalysis().catch(inputError); });
  window.addEventListener('pybert-analysis-navigation',event => {
    $('analysis-kind').value=event.detail.kind; $('analysis-point').value='node';
    $('compare-mode').value=event.detail.compare || 'none';
    if (event.detail.response) $('response-type').value=event.detail.response;
    renderAnalysis().catch(inputError);
  });
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
    try { await normalizeDraft(); if (as || !logicalName) { $('save-name').value = logicalName || 'pybert.yaml'; $('name-dialog').returnValue = 'cancel'; $('name-dialog').showModal(); } else download(logicalName); }
    catch (error) { inputError(error); }
  }
  $('save-config').addEventListener('click',() => save(false)); $('save-as').addEventListener('click',() => save(true));
  $('name-dialog').addEventListener('close',() => { if ($('name-dialog').returnValue === 'save') download($('save-name').value); });
  $('name-dialog').addEventListener('cancel',() => { $('name-dialog').returnValue = 'cancel'; });
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
    if (saved && patches.length) { revision++; normalizedRevision=-1; pendingValidation=true; }
    $('input-status').textContent = defaults.warnings.join(' '); controls();
    await poll();
  }
  init().catch(inputError);
})();
