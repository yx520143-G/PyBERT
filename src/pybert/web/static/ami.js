/* IBIS resources and dynamic AMI drafts; the worker owns parsers and libraries. */
(() => {
  const $=id=>document.getElementById(id), runs=window.PYBERT_RUNS;
  const clone=structuredClone, esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let reports={}, current=null, uploaded=null, busy=true;
  const dialog=document.createElement('dialog');dialog.id='ami-dialog';
  dialog.innerHTML=`<button id="ami-close">关闭</button><h2>IBIS 电气 / AMI 模型</h2><p>两侧独立选择。AMI 替代对应 Native EQ。检查/Run/Tune 共用计算槽，每任务 fresh spawn；检查仅证明资源解析/库加载，执行另有 postcondition。</p>
    <label>Side <select id="ami-side"><option value="tx">Tx</option><option value="rx">Rx</option></select></label>
    <label>本机模型完整目录 <input id="ami-directory" placeholder="C:/models/example"></label><button id="ami-register">登记目录</button>
    <label>或上传完整目录 <input id="ami-upload" type="file" webkitdirectory multiple></label>
    <label>目录内 IBIS 相对路径 <input id="ami-ibis" placeholder="example_rx.ibs"></label>
    <label><input id="ami-rebind" type="checkbox">明确重绑新内容，并重新建立该侧参数树（旧结果保留）</label>
    <p id="ami-resource-identity"></p><button id="ami-check">选择 / 检查模型</button>
    <p id="ami-status" role="status"></p><div id="ami-selection"></div>
    <label>Electrical <select id="ami-electrical"><option value="native">Native</option><option value="ibis">IBIS</option></select></label>
    <label>EQ <select id="ami-eq"><option>Native</option><option>IBIS-AMI</option></select></label>
    <label>AMI mode <select id="ami-mode"><option value="Init">Init</option><option value="GetWave">GetWave</option></select></label>
    <label><input id="ami-ts4" type="checkbox">使用模型 Ts4file</label><label><input id="ami-clocks" type="checkbox">请求 Rx clocks（有效返回才采用）</label>
    <p>Tx GetWave：rx_in 是诊断参考；下游显式 noise 路径有原生限制。双 GetWave 丢弃 Rx clocks。Rx AMI 绕过 Native RxFFE；无有效 clocks 继续 Native CDR/DFE/AGC 分支。Native/Init Tx 的 disabled CTLE File 不加载；Tx GetWave + Native Rx 的 File 即使 disabled 仍 blocked。</p>
    <div id="ami-parameters"></div><h3>Init TPE 搜索</h3><p>只支持有效 Init response。无自由维度只评估1次；范围/步长/初值与本次预算保存于 runtime extension。Use 显式应用获选参数；Native Reset 仅 current→search，不重置 AMI。</p><div id="ami-search"></div><button id="ami-apply">Apply 参数 / 模式到草稿</button>
    <details><summary>View：真实只读解析 / 源文件 / 能力</summary><pre id="ami-view"></pre></details>
    <p>YAML 通过版本化 Web extension 保存完整树、选择、clocks、搜索预算；资源 bytes 另行提供。原生 YAML 字段本身不足以表示完整 AMI 工程。非 Windows / GetWave-only / Ts4 数值及未提供模型能力须按实际 fixture 报未验证。</p>`;
  document.body.append(dialog);
  const button=document.createElement('button');button.id='ami-open';button.textContent='IBIS / AMI';$('resources-open').after(button);
  function controls(){for(const id of ['ami-register','ami-check','ami-apply'])$(id).disabled=busy;$('ami-upload').disabled=busy;}
  function render(){
    const side=$('ami-side').value, input=runs.modelDraft();current=clone(input.runtime_extensions.values?.ami_models?.[side]||null);
    const report=reports[side];$('ami-view').textContent=JSON.stringify(report||{status:'not configured / unverified'},null,2);
    $('ami-status').textContent=report?`${report.status} · ${report.stage} · ${report.binary_load}`:'未配置 / 未验证；选择完整目录后检查。';
    $('ami-resource-identity').textContent=uploaded?`待绑定 ${uploaded.resource_id} · ${uploaded.bytes} bytes`:`当前模型 ${current?.model_hash||'未绑定'}`;
    $('ami-ibis').value=current?.selection.ibis_path||input.config[`${side}_ibis_file`]||'';
    $('ami-electrical').value=input.config[`${side}_sel`];$('ami-eq').value=input.config[`${side}_eq_sel`];$('ami-mode').value=input.config[`${side}_use_getwave`]?'GetWave':'Init';
    $('ami-ts4').checked=input.config[`${side}_use_ts4`];$('ami-clocks').checked=input.runtime_extensions.values?.rx_use_clocks||false;$('ami-clocks').disabled=side!=='rx';
    $('ami-selection').innerHTML=current?['comp','pin','mod'].map((key,i)=>`<label>${key} <select data-ami-selection="${key}">${(report?.[['components','pins','models'][i]]||[current.selection[key]]).map(value=>`<option ${value===current.selection[key]?'selected':''}>${esc(value)}</option>`).join('')}</select></label>`).join(''):'';
    $('ami-parameters').innerHTML=current?`<h3>完整动态参数树</h3><table><thead><tr><th>完整路径 / 类型 / usage / format</th><th>Value</th><th>范围 / 单位</th></tr></thead><tbody>${current.parameters.map((row,i)=>`<tr><td>${esc(row.path.join(' / '))}<br>${esc(row.type)} / ${esc(row.usage)} / ${esc(row.format)}</td><td><input data-ami-param="${i}" aria-label="${esc(row.path.join('/'))}" value="${esc(typeof row.value==='object'?JSON.stringify(row.value):row.value)}" ${row.editable?'':'disabled'}></td><td>${esc(JSON.stringify([row.min,row.max,row.values]))}<br>${esc(row.unit)}<br>${esc(row.description)}</td></tr>`).join('')}</tbody></table>`:'';
    $('ami-search').innerHTML=current?`<table><tr><th>Path</th><th>Enabled</th><th>Min</th><th>Max</th><th>Step</th><th>初值</th></tr>${current.search.map((row,i)=>`<tr><td>${esc(row.path.join('/'))}</td>${['enabled','min_val','max_val','step','value'].map(key=>`<td><input data-ami-search="${i}" data-property="${key}" type="${key==='enabled'?'checkbox':'number'}" ${key==='enabled'?(row[key]?'checked':''):`value="${row[key]}"`} ${key==='value'?'disabled':''}></td>`).join('')}</tr>`).join('')}</table>`:'';
    controls();
  }
  function open(side){if(side)$('ami-side').value=side;render();dialog.showModal();}
  $('ami-selection').onchange=event=>{
    const key=event.target.dataset.amiSelection,map=reports[$('ami-side').value]?.selection_map;
    if(!map)return;
    const control=name=>$('ami-selection').querySelector(`[data-ami-selection="${name}"]`);
    const options=(element,values)=>{element.replaceChildren(...values.map(value=>new Option(value,value)));};
    if(key==='comp')options(control('pin'),Object.keys(map[control('comp').value]));
    if(key==='comp'||key==='pin')options(control('mod'),map[control('comp').value][control('pin').value]);
    $('ami-status').textContent='内部选择已改变；请明确重绑并检查新模型参数树后再 Apply。';
  };
  button.onclick=()=>open();$('ami-close').onclick=()=>dialog.close();$('ami-side').onchange=()=>{uploaded=null;render();};
  async function action(fn){try{await fn();}catch(error){$('ami-status').textContent=`失败，原参数草稿保留：${error.message}`;}}
  $('ami-register').onclick=()=>action(async()=>{uploaded=await runs.api('models',{directory:$('ami-directory').value});render();});
  $('ami-upload').onchange=()=>action(async()=>{const files=[];for(const file of $('ami-upload').files){const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));files.push({relative_path:file.webkitRelativePath.split('/').slice(1).join('/'),content_base64:btoa(binary)});}uploaded=await runs.api('models',{files});render();});
  async function apply(discover){
    const side=$('ami-side').value,input=runs.modelDraft(),models=clone(input.runtime_extensions.values?.ami_models||{});
    input.runtime_extensions={version:1,values:{...input.runtime_extensions.values}};
    if(uploaded){if(current?.model_hash!==uploaded.sha256&&!$('ami-rebind').checked&&current)throw new Error('新内容需要明确重绑与参数差异确认。');input.resource_bindings[`${side}_model_bundle`]=uploaded.resource_id;if($('ami-rebind').checked)delete models[side];}
    if(!discover&&models[side]){
      const model=clone(models[side]);for(const control of $('ami-parameters').querySelectorAll('[data-ami-param]')){const row=model.parameters[Number(control.dataset.amiParam)];if(row.editable){if(row.type==='Boolean'&&!['true','false'].includes(control.value.toLowerCase()))throw new Error('Boolean 参数必须为 true 或 false。');row.value=row.type==='Boolean'?control.value.toLowerCase()==='true':['Float','Integer','UI','Tap'].includes(row.type)?Number(control.value):control.value;}}
      for(const control of $('ami-search').querySelectorAll('[data-ami-search]')){const row=model.search[Number(control.dataset.amiSearch)],key=control.dataset.property;if(key!=='value')row[key]=key==='enabled'?control.checked:Number(control.value);}
      for(const control of $('ami-selection').querySelectorAll('[data-ami-selection]'))model.selection[control.dataset.amiSelection]=control.value;
      models[side]=model;
    }
    const relative=$('ami-ibis').value;
    if(!current || current.selection.ibis_path!==relative)input.config[`${side}_ibis_file`]=relative;
    if(models[side]){
      models[side].selection.ibis_path=$('ami-ibis').value;
      for(const control of $('ami-selection').querySelectorAll('[data-ami-selection]'))models[side].selection[control.dataset.amiSelection]=control.value;
      if($('ami-rebind').checked)models[side]={model_hash:models[side].model_hash,selection:models[side].selection,rebind:true};
    }
    if(!discover){input.config[`${side}_sel`]=$('ami-electrical').value;input.config[`${side}_eq_sel`]=$('ami-eq').value;input.config[`${side}_use_getwave`]=$('ami-mode').value==='GetWave';input.config[`${side}_use_ts4`]=$('ami-ts4').checked;input.runtime_extensions.values.rx_use_clocks=$('ami-clocks').checked;}
    if(Object.keys(models).length)input.runtime_extensions.values.ami_models=models;else delete input.runtime_extensions.values.ami_models;
    const result=await runs.configureModel(input);reports=result.ami_models||{};uploaded=null;render();
  }
  $('ami-check').onclick=()=>action(()=>apply(true));$('ami-apply').onclick=()=>action(()=>apply(false));
  window.addEventListener('pybert-model-state',event=>{reports=event.detail.ami_models||{};if(dialog.open)render();});
  window.addEventListener('pybert-worker-state',event=>{busy=event.detail.busy;controls();});
  document.addEventListener('click',event=>{const control=event.target.closest('[data-ami-open]');if(control)open(control.dataset.amiOpen);});
  window.PYBERT_AMI={open,report:side=>reports[side],field:key=>{
    const side=key.slice(0,2),report=reports[side];if(!report)return null;
    if(key.endsWith('_ibis_valid'))return report.selection?'真实 IBIS 解析成功':'未验证';
    if(key.endsWith('_ami_valid'))return report.parameters?'真实 AMI 解析成功':'not configured';
    if(key.endsWith('_dll_valid'))return report.binary_load==='loaded'?'真实库加载成功（执行另验）':'unavailable / not configured';
    if(key.endsWith('_ami_file'))return report.ami_path;
    if(key.endsWith('_dll_file'))return report.binary_path;
    return null;
  }};
})();
