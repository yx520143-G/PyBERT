/* Native snapshots, task identity and plots are separate from the editable prototype draft. */
(() => {
  const $ = id => document.getElementById(id);
  const ui = window.PYBERT_WORKBENCH, settings = window.PYBERT_SETTINGS;
  const clone = settings.clone;
  const tables = {tx_taps: ['enabled', 'value', 'min_val', 'max_val'], rx_taps: ['enabled', 'value', 'min_val', 'max_val'], tx_tap_tuners: ['enabled', 'pos', 'min_val', 'max_val', 'step'], ffe_tap_tuners: ['enabled', 'pos', 'min_val', 'max_val', 'step'], dfe_tap_tuners: ['enabled', 'min_val', 'max_val']};
  let base = null, captured = null, patches = [], normalized = null, revision = 0, normalizedRevision = -1;
  let activeTask = null, currentTask = null, runs = [], selected = null, normalizing = null, timer = null, pendingValidation = false, disconnected = false, logicalName = '', renderToken = 0;
  let runtimeExtensions = {};
  let comTasks = [];
  let references = [], sourceRecordId = null;
  let sourceVersion=null;
  let snapshotRecoveryRequired=false;
  let replayGuard=null;
  let constructedConfig=null,constructedRuntime=null;
  const recordId = row => row.record_id || row.run_id;
  const allRecords = () => [...runs,...references];
  const resourceBindings = () => window.PYBERT_RESOURCES?.bindings() || {};
  function extraInput() {
    const values = {...runtimeExtensions.values};
    for (const key of ['rlm','rx_use_clocks','ami_opt_trials']) if (key in ui.getDraft()) values[key]=ui.getDraft()[key];
    return {runtime_extensions:{version:1,values},resource_bindings:resourceBindings()};
  }
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
    Object.assign(draft,runtimeExtensions.values || {});
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
    if(snapshotRecoveryRequired) return '配置快照恢复失败；请显式恢复全部默认或Load Config，原存储保留。';
    if(ui.migrationError()) return ui.migrationError();
    const draft = ui.getDraft();
    const changingTapCount = patches.some(patch => patch.field === 'rx_n_taps');
    return Object.keys(settings.fields).map(key => settings.fieldError(key,draft,{deferObserver:key==='rx_n_pre' && changingTapCount})).find(Boolean) || Object.keys(tables).map(key => settings.tableError(key,draft)).find(Boolean);
  }
  function controls() {
    const locked = !base || !!normalizing || disconnected || window.PYBERT_RESOURCES?.pending();
    for (const id of ['run','save-config','save-as','load-config']) $(id).disabled = locked || !!activeTask;
    $('abort').disabled = !activeTask || disconnected;
    $('resources-open').disabled = locked;
    $('inspector').inert = !!normalizing;
    for (const id of ['reset-draft','reset-stage','tx-mode','rx-mode','reset-modes','undo-reset']) $(id).disabled = !!normalizing;
    $('stale').textContent = selected ? (normalizedRevision !== revision || selected.input_hash !== normalized?.input_hash || selected.input_identity_hash && selected.input_identity_hash !== normalized?.input_identity_hash ? 'Older input · draft or resource binding changed' : 'Matches validated input') : '';
    if(selected?.legacy) $('stale').textContent='原输入与物理轴未知；index诊断参考。';
    if ($('resource-dialog')) $('resource-dialog').inert=!!normalizing;
    for (const id of ['save-results','legacy-results']) $(id).disabled=!selected || disconnected;
    $('restore-run-input').disabled=!selected || !!selected.legacy || !!activeTask || !!normalizing || disconnected;
    $('remove-reference').disabled=!selected || selected.kind==='temporary' || disconnected;
    const child = selected && selected.kind==='temporary' && comTasks.findLast(task=>task.parent_run_id===selected.run_id);
    $('parent-com-state').textContent = selected ? `核心结果成功 · ${selected.run_id.slice(0,8)}${child ? `；COM 子任务 ${child.task_id.slice(0,8)}：${child.state}${child.result?.value_db!==undefined ? ` · ${child.result.value_db.toFixed(9)} dB` : ''}` : selected.execution_strategy?.deferred_com ? '；COM 子任务等待启动' : '；COM 未随此 Run 启用'}` : '';
    $('parent-com-state').title=selected ? `run_id=${selected.run_id}; com_id=${child?.task_id || selected.execution_strategy?.deferred_com?.com_id || 'none'}` : '';
    if (selected && selected.kind!=='temporary') $('parent-com-state').textContent=`外部参考 ${recordId(selected)} · 原run ${selected.run_id} · ${selected.legacy?'legacy诊断子集':'完整存档'}；子任务仅显示保存时快照，见概览。`;
  }
  async function normalizeDraft() {
    if (normalizing) return normalizing;
    if (activeTask) throw new Error('Native slot busy; input validation is pending.');
    if (window.PYBERT_RESOURCES?.pending()) throw new Error('Resource upload is still in progress.');
    document.activeElement?.blur();
    record();
    pendingValidation = false;
    const error = localError();
    if (error) throw new Error(error);
    const expectedRevision = revision;
    const request = patches.length ? {mode:'patch', config:base, patches:clone(patches)} : {mode:'load', config:base};
    normalizing = api('normalize', {...request,...extraInput()});
    $('input-status').textContent = 'Normalizing native observers…'; controls();
    try {
      const result = await normalizing;
      base = result.config; normalized = result; patches = []; runtimeExtensions=result.runtime_extensions;
      window.PYBERT_RESOURCES?.restore(result.resource_bindings,base);
      window.PYBERT_RESOURCES?.importReport(result);
      ui.replaceDraft(toDraft(base)); captured = toNative(ui.getDraft());
      persistNative();
      normalizedRevision = expectedRevision;
      $('input-status').textContent = result.warnings.join(' ');
      return result;
    } finally { normalizing = null; controls(); }
  }
  function inputError(error) { $(ui.migrationError() || snapshotRecoveryRequired?'config-status':'input-status').textContent = `${ui.migrationError() || snapshotRecoveryRequired?'草稿恢复':'Input'}: ${error.message}`; controls(); }
  function validateWhenIdle() {
    if (pendingValidation && !activeTask && !normalizing) normalizeDraft().catch(inputError);
  }
  function persistNative() {
    try { localStorage.setItem('pybert-native-snapshot-v2',JSON.stringify({schema:2,sources:sourceVersion,config:base,name:logicalName,source_record_id:sourceRecordId,replay_guard:replayGuard,...extraInput()})); }
    catch { $('config-status').textContent='本地配置快照写入失败；当前页面草稿仍保留，属于存储故障。'; }
  }
  window.addEventListener('pybert-draft', event => {
    if(event.detail.resetAll) {
      sourceRecordId=null;replayGuard=null;snapshotRecoveryRequired=false;
      if(constructedConfig) {base=clone(constructedConfig);captured=clone(base);patches=[];runtimeExtensions=clone(constructedRuntime);window.PYBERT_RESOURCES?.restore({},base);}
    }
    revision++; controls();
    if (event.detail.commit) {
      record();
      pendingValidation = true;
      clearTimeout(timer);
      timer = setTimeout(validateWhenIdle, 200);
    } else $('input-status').textContent = activeTask ? 'Draft edited; native validation pending until worker exit.' : 'Draft edited; commit the field to validate.';
  });
  window.addEventListener('pybert-resource-change',()=>{revision++;pendingValidation=true;controls();clearTimeout(timer);timer=setTimeout(validateWhenIdle,200);});
  window.addEventListener('pybert-resource-error',event=>inputError(new Error(event.detail)));
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
    if (kind === 'wave') return stage === 'noise' ? 'noise' : point ? `wave.${point}` : stage === 'source' ? 'wave.x' : null;
    if (kind === 'eye') return chosenPoint ? `eye.${chosenPoint}${chosenPoint === 'chnl' && $('channel-noise').checked ? '.gui_noise' : ''}` : null;
    if (kind.startsWith('jitter.') && kind !== 'jitter.info') return chosenPoint ? `jitter.${chosenPoint}.${kind.split('.')[1]}` : null;
    return kind;
  }
  function empty(message) { Plotly.purge('plot'); $('plot').innerHTML = `<p class="empty-result">${esc(message)}</p>`; }
  function comparisonRecord() {
    const chosen=$('comparison-run').value;
    return allRecords().find(row=>recordId(row)!==recordId(selected) && (!chosen || recordId(row)===chosen));
  }
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
      empty(`Record ${recordId(selected)} · source run ${selected.run_id} · ${selected.effective_input.mod_type || 'legacy input unknown'} · ${selected.input_hash.slice(0,12)}`);
      $('analysis-info').innerHTML = `<pre>${esc(JSON.stringify({summary:selected.summary,window:selected.window,warnings:selected.warnings,legacy:selected.legacy,lifecycle:selected.lifecycle,native_sha:selected.native_sha,adapter_sha:selected.adapter_sha},null,2))}</pre><details><summary>保存时子功能快照 / 来源</summary><pre>${esc(JSON.stringify({saved_at:selected.archive_saved_at,subfunctions:selected.saved_subfunctions},null,2))}</pre></details>`;
      return;
    }
    if (id === 'jitter.info') {
      if (selected.legacy) return empty('Legacy没有jitter统计/输入/窗口；不借当前Run补算。');
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
      const other=comparisonRecord();
      if (!other) return empty('选择另一条成功记录或加载参考；失败/取消任务不参与。');
      const [a,b] = await Promise.all([selected,api(`runs/${recordId(other)}`)]);
      if (token !== renderToken) return;
      if (a.legacy || b.legacy) return empty('Legacy缺少输入/物理轴，无法做物理域比较；可单独查看index诊断。');
      const differences = Object.keys(a.effective_input).filter(key => !equal(a.effective_input[key],b.effective_input[key]));
      empty(`A ${recordId(a)} / source ${a.run_id} · B ${recordId(b)} / source ${b.run_id}`);
      $('analysis-info').innerHTML = `<table><tr><th></th><th>A ${esc(a.run_id.slice(0,8))}</th><th>B ${esc(b.run_id.slice(0,8))}</th></tr>${['n_errs_dfe','chnl_dly_s','rel_power','initial_level_v','final_level_v'].map(key => `<tr><td>${key}</td><td>${a.summary[key]}</td><td>${b.summary[key]}</td></tr>`).join('')}</table><p>Input differences: ${esc(differences.join(', ') || 'None')}</p><pre>${esc(JSON.stringify(differences.map(key => ({field:key,A:a.effective_input[key],B:b.effective_input[key]})),null,2))}</pre><p>A window ${esc(JSON.stringify(a.window))}<br>B window ${esc(JSON.stringify(b.window))}</p>`;
      $('analysis-info').innerHTML += `<p>Resources/runtime A</p><pre>${esc(JSON.stringify({resources:a.resources,runtime:a.runtime_extensions},null,2))}</pre><p>Resources/runtime B</p><pre>${esc(JSON.stringify({resources:b.resources,runtime:b.runtime_extensions},null,2))}</pre>`;
      return;
    }
    const compare = $('compare-mode').value, kind = $('analysis-kind').value;
    const pointKinds = ['response','wave','eye','jitter.dist','jitter.spec','jitter.bathtub'];
    const points = compare === 'points' && pointKinds.includes(kind) ? ['chnl','tx','ctle','ffe','dfe'] : [observation()];
    let sources = [selected];
    if (compare === 'runs') {
      const other = comparisonRecord();
      if (!other) return empty('Two successful runs are required for chart comparison.');
      sources.push(await api(`runs/${recordId(other)}`));
    }
    if (sources.length>1 && sources.some(run=>run.legacy)) return empty('Legacy无物理轴，禁止与其他记录叠加；请单独查看index诊断。');
    if (token !== renderToken) return;
    const requests = sources.flatMap(run => points.map(point => {
      let id=pickPlot(point);
      if (run.legacy) id=$('analysis-kind').value==='response' ? `${point === 'chnl' || $('response-scope').value==='single' ? point : point+'_out'}_${$('response-type').value}` : $('analysis-kind').value==='wave' ? 'tx_out' : id;
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
      const plot=await api(`runs/${recordId(r.run)}/plots/${r.id}`);
      if (!r.run.legacy && !r.run.analysis_version && r.id === 'chnl_H') {
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
      const label=compare === 'runs' ? recordId(p.run).slice(0,12) : ({chnl:'Channel',tx:'Rx input',ctle:'CTLE',ffe:'Rx FFE',dfe:'DFE'})[requests[i].id.split('.')[1]];
      return p.data.map(trace => ({...trace,name:charts.length>1 && label ? `${label} · ${trace.name || requests[i].id}` : trace.name,...(facets ? {xaxis:x,yaxis:y,coloraxis:'coloraxis'} : {})}));
    });
    await Plotly.newPlot('plot',data,layout,{responsive:true,displaylogo:false});
    if (token !== renderToken) return;
    $('analysis-info').innerHTML = `<p>${selected.legacy?'Legacy index诊断：物理轴/窗口未知。':'DFE responses are final-weight equivalent FIRs. Each trace uses its own physical x coordinates; no index alignment or resampling.'} Zoom/pan and switching views do not Run. Crossing-jitter bathtubs do not certify voltage margin/BER.</p>${charts.map(p => `<details><summary>${esc(recordId(p.run))} · source ${esc(p.run_id)} · ${esc(p.plot_id)} · ${esc(p.run.effective_input.mod_type || 'unknown')} · input ${p.run.input_hash.slice(0,12)}</summary><pre>${esc(JSON.stringify({window:p.metadata.window || p.run.window,metadata:p.metadata,source:p.run.observations?.[p.plot_id.split('.')[1]],native_sha:p.run.native_sha,adapter_sha:p.run.adapter_sha},null,2))}</pre></details>`).join('')}`;
    if ($('work-area').classList.contains('viewer-expanded')) $('analysis').scrollIntoView({block:'start',behavior:'instant'});
  }
  async function chooseRun(id) {
    const result = id ? await api(`runs/${id}`) : null;
    if ($('selected-run').value !== (id || '')) return;
    selected = result;
    try { if(id) localStorage.setItem('pybert-result-selection-v1',JSON.stringify({record_id:id})); } catch { $('results-status').textContent='结果选择仅当前页面保留；本地存储失败。'; }
    controls(); await renderAnalysis();
  }
  async function poll(once=false) {
    if (disconnected) return;
    try {
      const state = await api('state');
      activeTask = state.active_task_id;
      currentTask = state.current_task_id;
      comTasks = state.com_tasks || [];
      window.PYBERT_RESOURCES?.state(state,selected);
      if (currentTask) {
        const task = await api(`tasks/${currentTask}`);
        $('task-state').textContent = `${task.operation} ${task.task_id.slice(0,8)} · ${task.state} · ${task.phase}${task.error ? ` · ${task.error}`:''}`;
        $('live-log-id').textContent = `Current task: ${task.task_id} · cancel requested=${task.cancel_requested}, observed=${task.cancel_observed}, exited=${task.worker_exited}`;
        $('live-log').textContent = [...task.logs,task.error || ''].join('\n');
      }
      $('result-budget').textContent=`临时成功缓存 ${state.runs.length}/2 · ${state.result_budget?.temporary_file_bytes || 0} bytes（第三次成功淘汰最旧临时记录）；参考 ${(state.references || []).length}/4 · ${state.result_budget?.reference_used_bytes || 0}/1073741824 数组bytes；参考超预算拒绝，可显式移除。完整raw不存localStorage。`;
      if (!equal([...state.runs,...(state.references || [])].map(recordId),allRecords().map(recordId))) {
        if(selected && ![...state.runs,...(state.references || [])].some(row=>recordId(row)===recordId(selected))) $('results-status').textContent=`原记录 ${recordId(selected)} 当前不可用（服务重启、缓存淘汰或参考移除）；未保存的临时结果无法恢复，请重新打开已保存archive。`;
        const previous = runs.map(r => r.run_id); runs = state.runs; references=state.references || [];
        const options=allRecords().map(r=>`<option value="${recordId(r)}">${r.kind==='legacy'?'Legacy':r.kind==='archive'?'参考':'Run'} · ${esc(r.effective_input?.mod_type || r.name || '')} · ${recordId(r).slice(0,12)}</option>`).join('');
        $('selected-run').innerHTML = '<option value="">Select record…</option>' + options;
        const comparison=$('comparison-run').value;
        $('comparison-run').innerHTML='<option value="">自动选择另一条</option>'+options;
        if (allRecords().some(r=>recordId(r)===comparison)) $('comparison-run').value=comparison;
        const latest = runs.findLast(r => !previous.includes(r.run_id));
        const id = latest?.run_id || (selected && allRecords().some(r => recordId(r) === recordId(selected)) ? recordId(selected) : recordId(allRecords().at(-1) || {}));
        $('selected-run').value = id || ''; await chooseRun(id);
      }
      controls();
      validateWhenIdle();
    } catch (error) { $('task-state').textContent = `Service unavailable: ${error.message}`; }
    if (!once) setTimeout(()=>poll(),1000);
  }
  $('run').addEventListener('click',async () => {
    clearTimeout(timer);
    try {
      const input = await normalizeDraft();
      const task = await api('runs',{config:input.config,input_hash:input.input_hash,input_identity_hash:input.input_identity_hash,draft_revision:revision,source_record_id:sourceRecordId,replay_guard:replayGuard,...extraInput()});
      activeTask = currentTask = task.task_id; controls();
      $('task-state').textContent = `Run ${task.task_id} · validating`;
    } catch (error) { inputError(error); }
  });
  $('abort').addEventListener('click',async () => { if (activeTask) { const task = await api(`tasks/${activeTask}/cancel`,{}); $('task-state').textContent = `${task.task_id} · ${task.state}; awaiting worker exit`; } });
  $('selected-run').addEventListener('change',() => chooseRun($('selected-run').value).catch(inputError));
  for (const id of ['analysis-kind','response-type','response-scope','analysis-point','compare-mode','comparison-run','channel-noise']) $(id).addEventListener('change',() => renderAnalysis().catch(inputError));
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
  function applyLoadedInput(result,sourceId=null,name='',guard=null) {
    base=result.config;normalized=result;patches=[];runtimeExtensions=result.runtime_extensions;revision++;normalizedRevision=revision;
    sourceRecordId=sourceId;replayGuard=guard;snapshotRecoveryRequired=false;logicalName=name;
    $('config-status').textContent='';
    $('config-name').textContent=name || 'Untitled';
    window.PYBERT_RESOURCES?.restore(result.resource_bindings,base);
    window.PYBERT_RESOURCES?.importReport(result);
    ui.replaceLoadedDraft(toDraft(base));captured=toNative(ui.getDraft());persistNative();
  }
  $('config-file').addEventListener('change',async event => {
    const file = event.target.files[0]; if (!file) return;
    clearTimeout(timer);
    try {
      const baseDirectory=document.getElementById('yaml-base-directory')?.value;
      normalizing = (async()=>{
        const request = {mode:'load'};
        if (file.name.endsWith('.pybert_cfg')) request.legacy_base64 = await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);});
        else request.yaml = await file.text();
        if (baseDirectory) request.base_directory=baseDirectory;
        return api('normalize',request);
      })(); controls();
      const result = await normalizing;
      applyLoadedInput(result,null,file.name);
      $('config-status').textContent=`已载入 ${logicalName}；未自动 Run。`;
      $('input-status').textContent = result.warnings.join(' ') + ` 未解析引用 ${Object.keys(result.unresolved_references).length} 类；完整导入/扩展报告见“资源 / COM”。`; controls();
    } catch (error) { $('config-status').textContent=`Load 失败，原草稿与名称保留：${error.message}`; }
    finally { normalizing = null; controls(); }
    event.target.value = '';
  });
  function download(name) {
    const a = document.createElement('a'), url = URL.createObjectURL(new Blob([normalized.yaml],{type:'application/yaml'}));
    a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000);
    logicalName = name; $('config-name').textContent = name;
    $('config-status').textContent=`已向浏览器提交 ${name} 下载请求；完成状态见下载面板。资源 bytes 未附带；runtime extensions 保存在版本化注释中。`;
    persistNative();
  }
  async function save(as) {
    clearTimeout(timer);
    try { await normalizeDraft(); if (as || !logicalName || !/\.ya?ml$/i.test(logicalName)) { $('save-name').value = logicalName ? logicalName.replace(/\.[^.]+$/,'.yaml') : 'pybert.yaml'; $('name-dialog').returnValue = 'cancel'; $('name-dialog').showModal(); } else download(logicalName); }
    catch (error) { $('config-status').textContent=`Save 失败，原名称保留：${error.message}`; }
  }
  $('save-config').addEventListener('click',() => save(false)); $('save-as').addEventListener('click',() => save(true));
  $('name-dialog').addEventListener('close',() => { if ($('name-dialog').returnValue === 'save') { try { download($('save-name').value); } catch(error) { $('config-status').textContent=`Save 失败，原名称保留：${error.message}`; } } });
  $('name-dialog').addEventListener('cancel',() => { $('name-dialog').returnValue = 'cancel'; });
  $('help').addEventListener('click',() => $('help-dialog').showModal()); $('close-help').addEventListener('click',() => $('help-dialog').close());
  $('quit').addEventListener('click',() => { disconnected=true; controls(); $('task-state').textContent='Disconnected. You may close this tab; backend tasks continue.'; });
  window.PYBERT_RUNS={api,selected:()=>selected,references:()=>references.slice(),refresh:()=>poll(true),
    select:async id=>{$('selected-run').value=id;await chooseRun(id);},
    restore:async id=>{
      if (activeTask || normalizing) throw new Error('Native slot busy; restore input after worker exit.');
      const original=await api(`runs/${id}/replay-input`);
      normalizing=api('normalize',{mode:'load',config:original.config,runtime_extensions:original.runtime_extensions,resource_bindings:original.resource_bindings});controls();
      try {
        const result=await normalizing;
        applyLoadedInput(result,id,'',original.replay_guard);
        $('results-status').textContent=`已恢复原requested输入；原资源须显式重绑并匹配hash后才能Run。${JSON.stringify(original.expected_resources)}`;
      } finally {normalizing=null;controls();}
    }};
  async function init() {
    controls();
    let saved = null;
    try { if (ui.hasSavedDraft()) saved = ui.getDraft(); } catch { /* existing draft status shows storage failure */ }
    settings.tableInfo.tx_tap_tuners.readonly = ['value'];
    const version = await api('version');sourceVersion=version;ui.setSources(version); $('version-info').textContent = JSON.stringify(version,null,2);
    const defaults = await api('normalize',{mode:'defaults'});
    base = defaults.config; normalized = defaults; runtimeExtensions={version:1,values:defaults.runtime_defaults}; normalizedRevision = revision;
    constructedConfig=clone(base);constructedRuntime=clone(runtimeExtensions);
    ui.setDefaults(toDraft(base));
    try { const previous=JSON.parse(localStorage.getItem('pybert-native-snapshot-v2') || localStorage.getItem('pybert-native-snapshot-v1') || 'null'); if (previous && (![1,2].includes(previous.schema) || !previous.config || typeof previous.config!=='object')) throw new Error('未知配置快照schema/字段');if(previous) {base=previous.config;logicalName=previous.name || '';runtimeExtensions=previous.runtime_extensions || runtimeExtensions;sourceRecordId=previous.source_record_id || null;replayGuard=previous.replay_guard || null;window.PYBERT_RESOURCES?.restore(previous.resource_bindings,base);revision++;normalizedRevision=-1;pendingValidation=true;} } catch(error) {snapshotRecoveryRequired=true; $('config-status').textContent=`配置快照恢复失败，原存储保留：${error.message}`; }
    $('config-name').textContent=logicalName || 'Untitled';
    ui.replaceDraft(saved ? {...toDraft(base),...saved} : toDraft(base));
    captured = clone(base); record();
    if (saved && patches.length) { revision++; normalizedRevision=-1; pendingValidation=true; }
    $('input-status').textContent = ui.migrationError() || defaults.warnings.join(' '); controls();
    try {const selection=JSON.parse(localStorage.getItem('pybert-result-selection-v1') || 'null');if(selection?.record_id) $('results-status').textContent=`正在查询原记录 ${selection.record_id}；服务重启后临时结果未保存/当前不可用，请重新打开archive。`;} catch { $('results-status').textContent='结果选择状态读取失败；不会据本地存储伪造成功。'; }
    await poll();
  }
  init().catch(inputError);
})();
