/* Explicit resource bindings and the independent COM tool. */
(() => {
  const $ = id => document.getElementById(id), ui = window.PYBERT_WORKBENCH;
  const clone = value => structuredClone(value);
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let bindings = {}, refs = {}, inventory = [], busy = false, uploading = false, comTasks = [], selectedParent = null, selectedResources = [], configReport = {};
  const comDetails = new Map();
  let comMarkup = '';
  const dialog = document.createElement('dialog'); dialog.id = 'resource-dialog';
  dialog.innerHTML = `<button id="resources-close">关闭</button><h2>资源内容与独立 COM</h2><p>上传或显式登记路径后冻结 bytes / SHA-256。配置只保存引用和绑定身份，不附带资源；inactive 旧路径可保留。级联顺序和重复元素均保留。</p><label>目标字段 <select id="resource-field"><option>ch_file</option><option>ch_files</option><option>com_cfg_file</option></select></label><label>本机绝对路径 <input id="resource-path" placeholder="C:/.../channel.s4p"></label><button id="resource-register">登记并绑定</button><label>已登记资源 <select id="resource-existing"></select></label><button id="resource-bind">绑定当前引用</button><p id="resource-status" role="status"></p><div id="resource-bindings"></div><details><summary>完整资源清单与内容身份</summary><pre id="resource-inventory"></pre></details><hr><h3>COM · 单 THRU 工具</h3><p>使用原 calc_com；独立参数，不继承当前 EQ、bitrate、noise、FEXT 或 package。默认 IEEE_8023dj 搜索很大；调用内部没有取消检查点，Abort 在返回后观察。</p><label>THRU .s4p <select id="com-thru"></select></label><label>COM 参数 <select id="com-config"><option value="">明确采用 IEEE_8023dj defaults</option></select></label><label><input id="com-parent" type="checkbox">关联当前选中成功 run（可选）</label><button id="compute-com">独立计算 COM</button><div id="com-results"></div>`;
  document.body.append(dialog);
  dialog.querySelector('hr').insertAdjacentHTML('beforebegin','<label>Load YAML 的显式本机基目录（可选） <input id="yaml-base-directory" placeholder="留空则保留未绑定相对引用"></label>');
  $('resource-inventory').parentElement.insertAdjacentHTML('afterend','<details><summary>所选成功 Run 的实际端口 / 覆盖 / 解析记录</summary><pre id="selected-resource-report"></pre></details>');
  $('resource-inventory').parentElement.insertAdjacentHTML('afterend','<details><summary>配置导入 / 未解析引用 / runtime extensions</summary><pre id="config-import-report"></pre></details>');
  async function api(path, body) {
    const response = await fetch(`/api/${path}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const value = await response.json(); if (!response.ok) throw new Error(value.detail || response.statusText); return value;
  }
  function notify() {
    window.dispatchEvent(new CustomEvent('pybert-resource-change'));
    render();
  }
  function replace(field, values, ids) {
    const draft = ui.getDraft(); draft[field] = values;
    bindings[field] = ids; refs[field] = clone(values);
    ui.replaceDraft(draft);
    window.dispatchEvent(new CustomEvent('pybert-draft',{detail:{commit:true}}));
    notify();
  }
  function bind(row, preserveReference=false) {
    const field = $('resource-field').value, draft = ui.getDraft();
    if (field === 'ch_files') {
      const values = [...draft.ch_files, row.original_name], ids = [...(bindings.ch_files || draft.ch_files.map(() => null)), row.resource_id];
      replace(field, values, ids);
    } else replace(field, preserveReference ? draft[field] || row.original_name : row.source.path || row.original_name, row.resource_id);
  }
  function loadComDetails(task) {
    const id=task.task_id;
    if (!task.worker_exited || comDetails.has(id)) return;
    comDetails.set(id,{state:'loading'});
    (async()=>{
      try {
        const response=await fetch(`/api/com/${encodeURIComponent(id)}`), value=await response.json();
        if (!response.ok) throw new Error(value.detail || response.statusText);
        if (value.task?.task_id!==id || value.com_id && value.com_id!==id || value.saved_input && value.saved_input.com_id!==id) throw new Error('COM 保存记录身份不匹配。');
        comDetails.set(id,{state:'ready',value});
      } catch(error) { comDetails.set(id,{state:'error',error:error.message}); }
      render();
    })();
  }
  function comSource(task) {
    if (!task.worker_exited) return '<p>来源记录等待 worker 实际退出；当前任务日志保留如下。</p>';
    const detail=comDetails.get(task.task_id);
    if (!detail) return '<p>展开后读取此 COM 已保存的来源记录。</p>';
    if (detail.state==='loading') return '<p>正在读取此 COM 已保存的来源记录…</p>';
    if (detail.state==='error') return `<p>来源记录读取失败：${esc(detail.error)} <button data-com-retry="${esc(task.task_id)}">重试读取</button></p>`;
    const value=detail.value, record=value.com_id===task.task_id ? value : value.saved_input;
    const labels={available:'已保存',not_produced:'未生成',waiting_for_exit:'等待退出',unreadable:'无法读取',identity_mismatch:'身份不匹配'};
    const status=value.saved_detail_status || {};
    const identity=record ? {com_id:record.com_id,parameter_source:record.parameter_source?.kind ?? '未记录',parameters_sha256:record.parameter_source?.parameters_sha256 ?? '未记录',versions:record.versions ?? '未记录',adapter_sha:record.adapter_sha ?? '未记录',source_hashes:record.source_hashes ?? '未记录',helper:record.helper ?? '未记录',parameter_schema:record.parameter_schema ?? '未记录'} : '未生成可用来源记录；请求来源不能替代实际参数/hash/版本。';
    return `<h4>已保存计算来源</h4><p data-com-source-status>计算前快照：${esc(labels[status.input] || '未记录')}；结果记录：${esc(labels[status.result] || '未记录')}</p><pre data-com-identity>${esc(JSON.stringify(identity,null,2))}</pre><h4>完整实际 COM 参数</h4><pre data-com-parameters>${esc(JSON.stringify(record?.parameter_source?.parameters ?? '未记录；不从当前信号链或请求默认值推定。',null,2))}</pre>`;
  }
  function render() {
    if (dialog.open) {
      const draft = ui.getDraft();
      $('resource-bindings').innerHTML = ['ch_file','ch_files','com_cfg_file'].map(field => {
        const values = field === 'ch_files' ? draft[field] : [draft[field]], ids = field === 'ch_files' ? bindings[field] || [] : [bindings[field]];
        return `<h4>${field}</h4>` + values.map((ref,i) => `<div class="resource-row"><span>${i}: ${esc(ref || '(empty)')}<br><code>${esc(ids[i] || 'UNBOUND')}</code></span>${field === 'ch_files' ? ['bind','up','down','duplicate','remove'].map(action=>`<button data-resource-action="${action}" data-index="${i}">${action}</button>`).join('') : ''}</div>`).join('');
      }).join('');
      $('resource-inventory').textContent = JSON.stringify(inventory,null,2);
      $('selected-resource-report').textContent = JSON.stringify(selectedResources,null,2);
      $('config-import-report').textContent = JSON.stringify(configReport,null,2);
    }
    $('compute-com').disabled = busy || uploading;
    $('resource-register').disabled = uploading;
    const openTasks = new Set([...$('com-results').querySelectorAll('details[open]')].map(detail=>detail.dataset.comTask));
    for (const task of comTasks) if (openTasks.has(task.task_id)) loadComDetails(task);
    const markup = comTasks.map(task => {
      const thru=task.resource_inputs?.find(r=>r.field==='com_thru'),cfg=task.resource_inputs?.find(r=>r.field==='com_cfg_file');
      const matches=thru?.resource_id===$('com-thru').value && (cfg?.resource_id || '')===$('com-config').value;
      return `<details data-com-task="${esc(task.task_id)}"${openTasks.has(task.task_id)?' open':''}><summary>${esc(task.task_id)} · ${esc(task.state)}${task.result?.value_db !== undefined ? ` · ${task.result.value_db.toFixed(9)} dB` : ''} · ${matches?'匹配当前工具选择':'旧输入 / 与当前工具选择不同'}</summary><p>parent ${esc(task.parent_run_id || 'none')} · requested=${task.cancel_requested} / observed=${task.cancel_observed} / exited=${task.worker_exited}${task.error ? ` · ${esc(task.error)}` : ''}</p>${comSource(task)}<h4>资源与请求来源</h4><pre>${esc(JSON.stringify({requested_parameter_source:task.parameter_source,resource_inputs:task.resource_inputs},null,2))}</pre><h4>该 COM 历史任务日志 · ${esc(task.task_id)}</h4><pre data-com-logs>${esc(task.logs?.join('\n') || '该任务无保存日志。')}</pre>${task.traceback ? `<pre data-com-error>${esc(task.traceback)}</pre>` : ''}</details>`;
    }).join('');
    if (markup!==comMarkup) { $('com-results').innerHTML=markup; comMarkup=markup; }
  }
  $('com-results').addEventListener('toggle',event=>{
    if (!event.target.matches('details[data-com-task]') || !event.target.open) return;
    const task=comTasks.find(row=>row.task_id===event.target.dataset.comTask);
    if (task) {loadComDetails(task);render();}
  },true);
  $('com-results').addEventListener('click',event=>{
    const id=event.target.closest('[data-com-retry]')?.dataset.comRetry, task=comTasks.find(row=>row.task_id===id);
    if (task) {comDetails.delete(id);loadComDetails(task);render();}
  });
  function options() {
    for (const [id, allowed, first] of [['resource-existing',null,'选择已冻结资源'],['com-thru',['.s4p'],'选择 .s4p'],['com-config',['.xls','.xlsx'],'明确采用 IEEE_8023dj defaults']]) {
      const selected = $(id).value;
      $(id).innerHTML = `<option value="">${first}</option>` + inventory.filter(row => !allowed || allowed.includes(row.format)).map(row => `<option value="${row.resource_id}">${esc(row.original_name)} · ${row.sha256.slice(0,12)}</option>`).join('');
      if ([...$(id).options].some(option=>option.value===selected)) $(id).value=selected;
    }
  }
  async function upload(field, files) {
    uploading = true; notify(); $('resource-status').textContent='上传并冻结资源…';
    try {
      const rows = [];
      for (const file of files) {
        const content = await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(file);});
        const row = await api('resources',{name:file.name,content_base64:content}); rows.push(row);
        inventory = inventory.filter(old=>old.resource_id!==row.resource_id);inventory.push(row);
      }
      replace(field, field==='ch_files' ? rows.map(r=>r.original_name) : rows[0].original_name, field==='ch_files' ? rows.map(r=>r.resource_id) : rows[0].resource_id);
      options(); $('resource-status').textContent='内容已冻结；Run 前仍需内容/端口预检。';
    } catch(error) { $('resource-status').textContent=error.message; window.dispatchEvent(new CustomEvent('pybert-resource-error',{detail:error.message})); }
    finally {uploading=false;notify();}
  }
  window.addEventListener('pybert-resource-files',event=>upload(event.detail.field,event.detail.files));
  window.addEventListener('pybert-draft',()=>{
    const draft=ui.getDraft();
    for(const field of Object.keys(bindings)) if (JSON.stringify(refs[field])!==JSON.stringify(draft[field])) {delete bindings[field];delete refs[field];}
    render();
  });
  $('resources-open').onclick=()=>{options();dialog.showModal();render();}; $('resources-close').onclick=()=>dialog.close();
  $('resource-register').onclick=async()=>{try{const row=await api('resources/local',{path:$('resource-path').value});inventory=inventory.filter(r=>r.resource_id!==row.resource_id);inventory.push(row);bind(row);options();$('resource-status').textContent='路径 bytes 已冻结；后续外部修改不改变该内容身份。';}catch(error){$('resource-status').textContent=error.message;}};
  $('resource-bind').onclick=()=>{const row=inventory.find(r=>r.resource_id===$('resource-existing').value);if($('resource-field').value==='ch_files'){$('resource-status').textContent='请使用目标 ch_files 行的 bind，把已选资源绑定至该位置。';return;}if(row)bind(row,true);};
  $('resource-bindings').onclick=event=>{
    const button=event.target.closest('[data-resource-action]');if(!button)return;
    const values=ui.getDraft().ch_files,ids=[...(bindings.ch_files || values.map(()=>null))],i=Number(button.dataset.index),action=button.dataset.resourceAction;
    if(action==='bind'){const row=inventory.find(r=>r.resource_id===$('resource-existing').value);if(!row){$('resource-status').textContent='请先选择已冻结资源。';return;}ids[i]=row.resource_id;if(!values[i])values[i]=row.original_name;}
    if(action==='remove'){values.splice(i,1);ids.splice(i,1);}
    if(action==='duplicate'){values.splice(i+1,0,values[i]);ids.splice(i+1,0,ids[i]);}
    const j=action==='up'?i-1:action==='down'?i+1:i;
    if(j!==i && j>=0 && j<values.length){[values[i],values[j]]=[values[j],values[i]];[ids[i],ids[j]]=[ids[j],ids[i]];}
    replace('ch_files',values,ids);
  };
  $('compute-com').onclick=async()=>{try{const task=await api('com',{thru_resource_id:$('com-thru').value,config_resource_id:$('com-config').value || null,parameter_source:$('com-config').value?'spreadsheet':'IEEE_8023dj defaults',parent_run_id:$('com-parent').checked?selectedParent:null});busy=true;$('resource-status').textContent=`COM ${task.task_id} 已提交`;render();}catch(error){$('resource-status').textContent=error.message;}};
  $('com-thru').onchange=render;$('com-config').onchange=render;
  window.PYBERT_RESOURCES = {
    bindModel:(side,id)=>{bindings[`${side}_model_bundle`]=id;notify();},
    bindings:()=>clone(bindings), pending:()=>uploading,
    restore:(value,config)=>{bindings=clone(value || {});refs=Object.fromEntries(Object.keys(bindings).map(key=>[key,clone(config[key])]));render();},
    importReport:result=>{configReport={import_report:result.import_report,runtime_extensions:result.runtime_extensions,runtime_status:result.runtime_status,unresolved_references:result.unresolved_references};render();},
    state:(state,parent)=>{busy=!!state.active_task_id;selectedParent=parent?.run_id || null;selectedResources=parent?.resources || [];comTasks=state.com_tasks || [];const changed=JSON.stringify(inventory)!==JSON.stringify(state.resources || []);inventory=state.resources || [];if(changed)options();render();}
  };
})();
