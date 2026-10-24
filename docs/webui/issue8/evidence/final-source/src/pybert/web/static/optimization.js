/* Optimization UI owns candidate selection; the existing workbench owns editable inputs and Run. */
(() => {
  const $=id=>document.getElementById(id), runs=window.PYBERT_RUNS;
  let busy=true, active=null, rows=[], selected=null, selectedId=null, pending=null, token=0, plotting=Promise.resolve();
  const eq=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  const status=text=>{$('optimizer-status').textContent=text;};
  function controls() {
    for(const id of ['tune-eq','reset-eq','optimizer-plan']) $(id).disabled=busy;
    $('abort-eq').disabled=!active;
    $('use-eq').disabled=busy || selected?.status!=='succeeded';
    $('save-opt').disabled=!selected;
    $('confirm-use-eq').disabled=busy || !pending;
  }
  async function render() {
    const own=++token,id=$('selected-opt').value;
    selected=null;selectedId=null;controls();
    const result=id ? await runs.api(`optimizations/${id}`) : null;
    if(own!==token || $('selected-opt').value!==id) return;
    selected=result;selectedId=id;
    $('optimizer-record').textContent=selected ? JSON.stringify(selected,null,2) : '';
    $('selected-candidate').replaceChildren();
    if(selected) for(const row of selected.candidates || []) {
      const option=new Option(`${row.candidate_id} · FOM ${row.fom ?? 'invalid'}${row.candidate_id===selected.selected_candidate_id?' · 获选':''}`,row.candidate_id);
      option.disabled=row.availability!=='available';$('selected-candidate').add(option);
    }
    if(selected?.selected_candidate_id) $('selected-candidate').value=selected.selected_candidate_id;
    window.PYBERT_WORKBENCH.replaceDraft(window.PYBERT_WORKBENCH.getDraft());
    controls();await plot();
  }
  async function plot() {
    const own=++token,id=$('selected-opt').value;
    Plotly.purge('optimizer-plot');
    if(!selected || selected.status!=='succeeded') {
      $('optimizer-provenance').textContent=selected ? `${selected.opt_id} · ${selected.status} · ${selected.error || ''}；旧成功 Run/候选仍可选择。` : '未选优化记录。';return;
    }
    const payload=await runs.api(`optimizations/${id}/pulse?candidate=${encodeURIComponent($('selected-candidate').value)}`);
    if(own!==token || $('selected-opt').value!==id) return;
    const traces=[{x:payload.channel_x_ns,y:payload.channel_pulse,name:'同输入 Channel pulse'},{x:payload.x_ns,y:payload.pulse,name:`${payload.candidate.candidate_id} · ${payload.selected?'获选':'其他候选'}`}];
    if(payload.selected) traces.push({x:payload.cursor_ns,y:payload.cursor_V,name:'Cursor 时间标记'},{x:payload.x_ns,y:payload.clocks,name:'优化采样辅助线（非 CDR）',visible:'legendonly'});
    $('optimizer-provenance').textContent=`opt ${selected.opt_id} · ${payload.candidate.candidate_id} · ${selected.score_mode} · FOM ${payload.candidate.fom} · input ${selected.input_hash} · resource ${selected.resource_hash}。当前 Run 未改变；仅获选候选可 Use EQ。`;
    plotting=plotting.catch(()=>{}).then(()=>own===token ? Plotly.newPlot('optimizer-plot',traces,{title:{text:'优化模型 pulse / bounded ideal DFE',font:{size:13}},xaxis:{title:{text:'ns'},range:[0,30]},yaxis:{title:{text:'原生 pulse V / MMSE cursor=1'}},margin:{l:65,r:25,t:45,b:90},font:{family:'Arial',size:11},legend:{orientation:'h',font:{size:10},y:-.25}},{responsive:true,displaylogo:false}) : undefined);
    await plotting;
  }
  function open() {$('optimizer-workspace').open=true;$('optimizer-workspace').scrollIntoView({block:'start'});}
  $('optimizer-open').addEventListener('click',open);
  document.addEventListener('click',event=>{if(event.target.closest('[data-optimizer-open]'))open();});
  async function action(fn) {try{await fn();}catch(error){status(error.message);}finally{controls();}}
  $('optimizer-plan').addEventListener('click',()=>action(async()=>{const result=await runs.optimizerAction('optimizer_plan');status(JSON.stringify(result.import_report.optimization_plan));}));
  $('tune-eq').addEventListener('click',()=>action(async()=>{
    const input=await runs.optimizationInput();
    await runs.api('optimizer-actions/optimizer_plan',input);
    const task=await runs.api('optimizations',input);active=task.task_id;busy=true;runs.adoptTask(task);controls();
    status(`opt ${task.task_id} · validating；不自动 Use EQ。`);
  }));
  $('abort-eq').addEventListener('click',()=>action(async()=>{if(active) {const task=await runs.api(`tasks/${active}/cancel`,{});status(`${task.task_id} · ${task.state}；等待原生检查点与进程实际退出。`);}}));
  $('reset-eq').addEventListener('click',()=>action(async()=>{const result=await runs.optimizerAction('reset_eq');if(result.source_draft_revision!==runs.revision())throw new Error('Reset 等待期间草稿已改变；请重新执行。');runs.applyOptimizer(result);status('已按原 Reset EQ 同步当前实际 EQ 的初值/enable；搜索 min/max/step、DFE 与旧 Run 保留。');}));
  $('selected-opt').addEventListener('change',()=>action(render));
  $('selected-candidate').addEventListener('change',()=>action(plot));
  $('use-eq').addEventListener('click',()=>action(async()=>{
    const source=selected,recordId=$('selected-opt').value;
    if(!source || source.status!=='succeeded' || selectedId!==recordId)throw new Error('请等待所选成功优化记录加载完成。');
    const current=await runs.optimizationInput();
    const result=await runs.api('optimizer-actions/use_eq',{...current,record_id:recordId});
    if(current.draft_revision!==runs.revision() || recordId!==$('selected-opt').value)throw new Error('Use EQ 等待期间草稿或记录已改变；请重新预览差异。');
    const changed=Object.keys(current.config).filter(key=>!eq(current.config[key],source.requested_input[key]));
    const runtimeConflict=!eq(current.runtime_extensions,source.runtime_extensions);
    pending={result,revision:current.draft_revision,recordId,source};
    $('eq-differences').textContent=JSON.stringify({source_opt_id:source.opt_id,candidate_id:source.selected_candidate_id,
      draft_conflicts:changed.map(field=>({field,frozen:source.requested_input[field],current:current.config[field]})),
      runtime_conflict:runtimeConflict ? {frozen:source.runtime_extensions,current:current.runtime_extensions} : null,
      application:result.import_report},null,2);
    controls();$('eq-dialog').showModal();
  }));
  $('cancel-use-eq').addEventListener('click',()=>{pending=null;$('eq-dialog').close();controls();});
  $('eq-dialog').addEventListener('cancel',()=>{pending=null;controls();});
  $('confirm-use-eq').addEventListener('click',()=>action(async()=>{
    if(!pending || pending.revision!==runs.revision() || pending.recordId!==$('selected-opt').value) throw new Error('预览后草稿或候选已改变；请关闭并重新预览差异。');
    runs.applyOptimizer(pending.result);status(`已显式应用 ${pending.source.opt_id} / ${pending.source.selected_candidate_id}；请新 Run 评估时域效果。`);pending=null;$('eq-dialog').close();
  }));
  $('save-opt').addEventListener('click',()=>action(async()=>{
    const source=selected,recordId=$('selected-opt').value;
    if(!source || selectedId!==recordId)throw new Error('请等待所选优化记录加载完成。');
    const response=await fetch(`/api/optimizations/${recordId}/archive`);if(!response.ok) throw new Error((await response.json()).detail);
    const url=URL.createObjectURL(await response.blob()),a=document.createElement('a');a.href=url;a.download=`${source.opt_id}.pybert_opt`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status('已提交优化记录下载；含冻结输入、RLM、候选数组/评分、状态/成本；资源 bytes 不附带。');
  }));
  $('open-opt').addEventListener('click',()=>$('opt-file').click());
  $('opt-file').addEventListener('change',()=>action(async()=>{
    const file=$('opt-file').files[0];if(!file)return;
    try {const response=await fetch('/api/optimization-references',{method:'POST',body:file});const record=await response.json();if(!response.ok)throw new Error(record.detail);
      await runs.refresh();$('selected-opt').value=record.record_id;await render();status('已恢复优化记录；未 Run、未优化、未应用到草稿。');
    }finally{$('opt-file').value='';}
  }));
  window.addEventListener('pybert-worker-state',event=>{busy=event.detail.busy;controls();});
  window.addEventListener('pybert-optimizer-state',event=>{
    const state=event.detail;active=state.active_task_id;
    if(!eq(rows,state.optimizations || [])) {
      const prior=$('selected-opt').value,old=rows;rows=state.optimizations || [];$('selected-opt').replaceChildren(new Option('选择优化记录…',''));
      for(const row of rows) $('selected-opt').add(new Option(`${row.status} · ${row.opt_id.slice(0,8)} · ${row.score_mode || ''}`,row.record_id));
      const latest=rows.findLast(row=>!old.some(r=>r.record_id===row.record_id));$('selected-opt').value=latest?.record_id || prior;action(render);
      if(latest)status(`opt ${latest.opt_id} · ${latest.status}；查看所选记录，成功候选仍需显式 Use EQ。`);
    }
    controls();
  });
  window.PYBERT_OPTIMIZER={field:key=>key==='peak_mag_tune' && selected?.status==='succeeded' ? `${selected.selected_values.ctle_db} dB · 获选 ${selected.opt_id}` : null,value:(key,i)=>{
    if(selected?.status!=='succeeded')return null;
    const field=({tx_tap_tuners:'tx',ffe_tap_tuners:'ffe',dfe_tap_tuners:'dfe'})[key],value=selected.selected_values?.[field]?.[i];
    return value===undefined ? null : {value,source:`获选候选 ${selected.opt_id} / ${selected.selected_candidate_id}；不是当前草稿/DFE训练状态`};
  }};
})();
