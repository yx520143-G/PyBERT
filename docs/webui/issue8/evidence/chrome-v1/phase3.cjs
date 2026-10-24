async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue8-optimizer/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.waitForFunction(()=>!document.getElementById('tune-eq').disabled);
  const previous=await(await page.request.get('http://127.0.0.1:8773/api/state')).json();
  const response=page.waitForResponse(r=>r.url().endsWith('/api/optimizations') && r.request().method()==='POST');
  await page.locator('#tune-eq').click();const task=await(await response).json();
  assert(await page.locator('#run').isDisabled(),'Run enabled during Tune');
  await page.waitForFunction(id=>document.getElementById('task-state').textContent.includes(id.slice(0,8)) && document.getElementById('task-state').textContent.includes('succeeded'),task.task_id);
  await page.waitForFunction(id=>document.getElementById('selected-opt').value===id,task.task_id);
  const result=await(await page.request.get('http://127.0.0.1:8773/api/optimizations/'+task.task_id)).json();
  assert(result.score_mode==='cursor/ISI grid' && result.candidates.length===4,'Not Native non-MMSE grid');
  await page.getByRole('button',{name:'Rx FFE',exact:true}).click();
  await page.locator('#settings-table-ffe_tap_tuners').evaluate(el=>el.open=true);
  assert(await page.locator('#settings-table-ffe_tap_tuners tbody tr').count()===100,'FFE slots omitted');
  assert(await page.locator('#settings-table-ffe_tap_tuners tbody input[type=checkbox]').count()===0,'FFE enabled editable');
  await page.locator('#optimizer-open').click();
  await page.locator('#selected-candidate').selectOption('candidate-000000');
  await page.waitForFunction(()=>document.getElementById('optimizer-provenance').textContent.includes('candidate-000000'));
  const state=await(await page.request.get('http://127.0.0.1:8773/api/state')).json();
  assert(state.runs.map(r=>r.run_id).join()===previous.runs.map(r=>r.run_id).join(),'Switching candidate changed Run');
  assert(state.optimizations.length===previous.optimizations.length+1,'Switching candidate recomputed');
  await page.screenshot({path:root+'/output/playwright/issue8/04-grid-candidate.png'});
  const download=page.waitForEvent('download');await page.locator('#save-opt').click();await(await download).saveAs(root+'/output/playwright/issue8/nrz.pybert_opt');
  return {opt_id:task.task_id,checks:{non_MMSE_grid:true,Run_Tune_mutex:true,FFE_100_slots:true,FFE_enabled_readonly:true,candidate_switch_no_calculation:true,old_Runs_kept:true,archive_download:true}};
}
