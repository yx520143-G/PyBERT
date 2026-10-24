async (page) => {
  await page.waitForFunction(()=>!document.querySelector('#run').disabled);
  const before=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  const old=await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/runs') && r.request().method()==='POST');
  await page.locator('#run').click();const submitted=await response;const task=await submitted.json();
  if(submitted.status()!==202) throw new Error(JSON.stringify(task));
  await page.waitForFunction(short=>{const text=document.querySelector('#task-state').textContent;return text.includes(short) && (text.includes('Running DFE/CDR') || text.includes('succeeded') || text.includes('failed'));},task.task_id.slice(0,8),{timeout:60000});
  const atAbort=await (await page.request.get(`http://127.0.0.1:8770/api/tasks/${task.task_id}`)).json();
  if(!atAbort.phase.includes('DFE/CDR')) return {target_missed:true,task:atAbort,before_runs:before.runs.map(r=>r.run_id)};
  const cancellation=page.waitForResponse(r=>r.url().includes(`/api/tasks/${task.task_id}/cancel`));
  await page.locator('#abort').click();const requested=await (await cancellation).json();
  await page.screenshot({path:'output/playwright/07-cancel-request-old-success.png'});
  const transitions=[];let final;
  for(let index=0;index<150;index++) {
    final=await (await page.request.get(`http://127.0.0.1:8770/api/tasks/${task.task_id}`)).json();
    transitions.push({state:final.state,phase:final.phase,requested:final.cancel_requested,observed:final.cancel_observed,exited:final.worker_exited});
    if(final.worker_exited) break;
    await page.waitForTimeout(200);
  }
  const after=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  if(JSON.stringify(before.runs.map(r=>r.run_id))!==JSON.stringify(after.runs.map(r=>r.run_id))) throw new Error('Cancelled task replaced success cache');
  if(await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id)!==old) throw new Error('Cancelled task became selected result');
  await page.screenshot({path:'output/playwright/08-cancel-exited-old-success.png'});
  return {target_missed:false,at_abort:atAbort,requested,final,transitions,before_runs:before.runs.map(r=>r.run_id),after_runs:after.runs.map(r=>r.run_id),selected_old_run:old};
}
