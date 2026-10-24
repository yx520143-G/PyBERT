async (page) => {
  const before=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  const old=await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id);
  await page.locator('#config-file').setInputFiles('C:/Users/yx/.codex/worktrees/pybert-issue5-archive/serial-bus-simulator/docs/webui/issue5/fixtures/chrome-execution-v1/CTLE-BLOCKED.yaml');
  await page.waitForFunction(()=>document.querySelector('#config-name').textContent==='CTLE-BLOCKED.yaml' && !document.querySelector('#run').disabled);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/runs') && r.request().method()==='POST');await page.locator('#run').click();const task=await (await response).json();
  let final;for(let i=0;i<150;i++){final=await (await page.request.get(`http://127.0.0.1:8770/api/tasks/${task.task_id}`)).json();if(final.worker_exited)break;await page.waitForTimeout(200);}
  if(final.state!=='failed' || !final.error.includes('CTLE enabled')) throw new Error(JSON.stringify(final));
  await page.locator('#run-toolbar').scrollIntoViewIfNeeded();await page.screenshot({path:'output/playwright/13-native-preflight-failed-old-results.png'});
  const after=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  if(JSON.stringify(before.runs.map(r=>r.run_id))!==JSON.stringify(after.runs.map(r=>r.run_id)) || await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id)!==old)throw new Error('Failure changed successful results');
  await page.locator('#config-file').setInputFiles('C:/Users/yx/.codex/worktrees/pybert-issue5-archive/serial-bus-simulator/docs/webui/issue5/fixtures/chrome-execution-v1/NRZ.yaml');
  await page.waitForFunction(()=>document.querySelector('#config-name').textContent==='NRZ.yaml' && !document.querySelector('#run').disabled);
  return {failed_task:final,old_success_preserved:old,successful_run_ids:after.runs.map(r=>r.run_id),COM_tasks:after.com_tasks.length};
}
