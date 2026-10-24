async (page) => {
  const before=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  if(before.runs.length || before.references.length || before.active_task_id || before.resources.length) throw new Error('Restart restored temporary state unexpectedly');
  const unavailable=await page.locator('#results-status').textContent();
  await page.reload();await page.waitForFunction(()=>window.PYBERT_RUNS && window.PYBERT_WORKBENCH);
  const draftBefore=await page.evaluate(()=>JSON.stringify(window.PYBERT_WORKBENCH.getDraft()));
  for(const name of ['NRZ','PAM4']) {
    await page.locator('#results-file').setInputFiles(`C:/Users/yx/.codex/worktrees/pybert-issue5-archive/serial-bus-simulator/output/playwright/${name}-real.pybert_run`);
    await page.waitForFunction(name=>window.PYBERT_RUNS.selected()?.effective_input.mod_type===(name==='NRZ'?'NRZ':'PAM-4') && document.querySelector('#results-file').value==='',name);
  }
  const refs=await page.evaluate(()=>window.PYBERT_RUNS.references());
  await page.locator('#comparison-run').selectOption(refs[0].record_id);
  await page.locator('#analysis-kind').selectOption('eye');await page.locator('#analysis-point').selectOption('dfe');await page.locator('#compare-mode').selectOption('runs');
  await page.waitForFunction(()=>document.querySelector('#plot').data?.length===2 && document.querySelector('#plot').data[0].type==='heatmap');
  const grids=await page.evaluate(()=>document.querySelector('#plot').data.map(t=>({x:[t.x[0],t.x.at(-1)],y:[t.y[0],t.y.at(-1)],shape:[t.z.length,t.z[0].length]})));
  await page.locator('#analysis').scrollIntoViewIfNeeded();await page.screenshot({path:'output/playwright/18-reopened-after-restart.png'});
  if(draftBefore!==await page.evaluate(()=>JSON.stringify(window.PYBERT_WORKBENCH.getDraft())))throw new Error('Opening archive changed draft');
  await page.waitForFunction(async()=>!(await (await fetch('/api/state')).json()).active_task_id);
  const after=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  if(after.runs.length || after.com_tasks.length || after.resources.length || after.active_task_id)throw new Error('Archive viewing started numerical work/resources');
  return {initial_selection_was_empty:true,original_phase10_wait_timeout_preserved:true,unavailable,reload_did_not_restore_temporary_results:true,original_draft_unchanged:true,grids,before,after,COM_calls:0,main_calls:0};
}
