async (page) => {
  const before=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  if(before.references.length!==3) throw new Error('Expected preserved three-reference state from phase9 timeout');
  await page.waitForFunction(()=>document.querySelector('#results-file').value==='');
  const file='C:/Users/yx/.codex/worktrees/pybert-issue5-archive/serial-bus-simulator/output/playwright/NRZ-real.pybert_run';
  await page.locator('#results-file').setInputFiles(file);
  await page.waitForFunction(()=>window.PYBERT_RUNS.references().length===4 && document.querySelector('#results-file').value==='');
  const full=await page.evaluate(()=>({id:window.PYBERT_RUNS.selected().record_id,refs:window.PYBERT_RUNS.references().map(r=>r.record_id)}));
  await page.locator('#results-file').setInputFiles(file);
  await page.waitForFunction(()=>document.querySelector('#results-status').textContent.includes('Reference budget'));
  const rejected=await page.evaluate(()=>({id:window.PYBERT_RUNS.selected().record_id,refs:window.PYBERT_RUNS.references().map(r=>r.record_id)}));
  if(JSON.stringify(full)!==JSON.stringify(rejected))throw new Error('Budget changed selection/references');
  await page.locator('#result-actions').scrollIntoViewIfNeeded();await page.screenshot({path:'output/playwright/16-reference-budget-no-eviction.png'});
  await page.locator('#clear-references').click();await page.waitForFunction(()=>window.PYBERT_RUNS.references().length===0);
  const after=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  if(after.current_task_id!==before.current_task_id || after.active_task_id || JSON.stringify(before.runs.map(r=>r.run_id))!==JSON.stringify(after.runs.map(r=>r.run_id)))throw new Error('Budget/load/clear changed tasks or successes');
  return {prefix_phase9_assertions_reached_budget_loop:true,original_phase9_timeout_retained:true,harness_correction:'wait for file-input finally reset before same-file duplicate selection',references_before:before.references,full,rejected,clear_preserved_successes:true,task_unchanged:true,after};
}
