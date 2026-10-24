/* Result files and references never normalize a draft or start a numerical task. */
(() => {
  const $=id=>document.getElementById(id), runs=window.PYBERT_RUNS;
  const status=message=>{$('results-status').textContent=message;};
  const id=()=>runs.selected()?.record_id || runs.selected()?.run_id;
  async function download(path,name) {
    const response=await fetch(`/api/${path}`);
    if (!response.ok) throw new Error((await response.json()).detail || response.statusText);
    const blob=await response.blob(), url=URL.createObjectURL(blob), link=document.createElement('a');
    link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    status(`已向浏览器交付 ${name}；完成状态见下载面板，未确认覆盖本地文件。`);
  }
  $('open-results').addEventListener('click',()=>$('results-file').click());
  $('results-file').addEventListener('change',async event=>{
    const file=event.target.files[0];if (!file) return;
    try {
      const trusted=$('trust-legacy').checked;
      if (file.name.toLowerCase().endsWith('.pybert_data') && !trusted) throw new Error('请先明确确认该本机pickle可信；可执行代码。未读取文件，原状态保留。');
      status(`正在校验 ${file.name}；完整校验通过才加入参考。`);
      const response=await fetch(`/api/references?name=${encodeURIComponent(file.name)}&trusted=${trusted}`,{method:'POST',body:file,headers:{'Content-Type':'application/octet-stream'}});
      const value=await response.json();if (!response.ok) throw new Error(value.detail || response.statusText);
      await runs.refresh();await runs.select(value.record_id);
      status(`已加载 ${file.name} · record ${value.record_id} · source ${value.run_id}；草稿未改，未Run。${value.legacy?'Legacy仅index诊断；缺少完整原输入/物理轴，不能保存完整Web archive，可查看原生子集/sidecar。':''}`);
    } catch (error) {status(`打开结果失败，原草稿/记录/选择保留：${error.message}`);}
    finally {event.target.value='';}
  });
  $('save-results').addEventListener('click',()=>{if(id()) download(`runs/${id()}/archive`,`${id()}.pybert_run`).catch(error=>status(`保存结果失败，所选记录保留：${error.message}`));});
  $('restore-run-input').addEventListener('click',()=>{if(id()) runs.restore(id()).catch(error=>status(`恢复输入失败，原草稿保留：${error.message}`));});
  $('remove-reference').addEventListener('click',async()=>{
    try {if(id()) await runs.api(`references/${id()}/remove`,{});await runs.refresh();status('已移除所选参考与图层；当前成功Run和磁盘源文件保留。');}
    catch(error){status(`移除失败：${error.message}`);}
  });
  $('clear-references').addEventListener('click',async()=>{
    try {for(const row of runs.references()) await runs.api(`references/${row.record_id}/remove`,{});await runs.refresh();status('已清除加载的参考；当前成功Run、草稿与磁盘源文件保留。');}
    catch(error){status(`清除参考未完成：${error.message}`);}
  });
  let legacyReport=null, legacyId=null;
  $('legacy-results').addEventListener('click',async()=>{
    try {legacyId=id();legacyReport=await runs.api(`runs/${legacyId}/legacy-report`);$('legacy-save-guidance').textContent=legacyReport.recommendation;$('legacy-report').textContent=JSON.stringify(legacyReport,null,2);$('legacy-download').disabled=!legacyReport.available;$('legacy-dialog').showModal();}
    catch(error){status(`原生保存检查失败：${error.message}`);}
  });
  $('legacy-download').addEventListener('click',()=>download(`runs/${legacyId}/legacy`,`${legacyId}.pybert_data`).catch(error=>status(`原生导出失败：${error.message}`)));
  $('legacy-sidecar').addEventListener('click',()=>{
    const link=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(legacyReport,null,2)],{type:'application/json'}));
    link.href=url;link.download=`${legacyId}.legacy-sidecar.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    status('已向浏览器交付独立损失/来源/轴元数据sidecar；它不是完整结果文件。');
  });
})();
