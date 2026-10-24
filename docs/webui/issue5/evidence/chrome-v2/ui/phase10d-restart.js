async (page) => {
  await page.waitForFunction(()=>document.querySelector('#results-status').textContent.includes('当前不可用'));
  const unavailable=await page.locator('#results-status').textContent();
  await page.locator('#result-actions').scrollIntoViewIfNeeded();await page.screenshot({path:'output/playwright/17-restart-unavailable.png'});
  await page.reload();await page.waitForFunction(()=>window.PYBERT_RUNS && window.PYBERT_WORKBENCH);
  const draft=await page.evaluate(()=>JSON.stringify(window.PYBERT_WORKBENCH.getDraft()));
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
  await page.waitForFunction(async()=>!(await (await fetch('/api/state')).json()).active_task_id);
  const state=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  if(state.runs.length || state.com_tasks.length || state.resources.length || state.references.length!==2 || draft!==await page.evaluate(()=>JSON.stringify(window.PYBERT_WORKBENCH.getDraft())))throw new Error('Reopen changed draft or started main/COM');
  return {unavailable,grids,state,draft_unchanged:true,main_calls:0,COM_calls:0};
}
