async (page) => {
  const response=page.waitForResponse(r=>r.url().endsWith('/api/runs') && r.request().method()==='POST');
  await page.locator('#run').click();const submitted=await response;const task=await submitted.json();
  if(submitted.status()!==202) throw new Error(JSON.stringify(task));
  await page.waitForFunction(id=>window.PYBERT_RUNS.selected()?.run_id===id,task.task_id,{timeout:60000});
  const final=await (await page.request.get(`http://127.0.0.1:8770/api/tasks/${task.task_id}`)).json();
  if(final.state!=='succeeded' || !final.worker_exited) throw new Error(JSON.stringify(final));
  await page.locator('#analysis-kind').selectOption('eye');await page.locator('#analysis-point').selectOption('dfe');
  await page.waitForFunction(()=>document.querySelector('#plot').data?.[0]?.type==='heatmap');
  await page.locator('#expand-viewer').click();await page.locator('#analysis').scrollIntoViewIfNeeded();
  await page.screenshot({path:'output/playwright/05-real-pam4-dfe-eye.png'});
  const download=page.waitForEvent('download');await page.locator('#save-results').click();await (await download).saveAs('output/playwright/PAM4-real.pybert_run');
  return {task:final,source_record_removed_replay_succeeded:true,selected:await page.evaluate(()=>({record_id:window.PYBERT_RUNS.selected().record_id,run_id:window.PYBERT_RUNS.selected().run_id,summary:window.PYBERT_RUNS.selected().summary,window:window.PYBERT_RUNS.selected().window})),draft_level:await page.evaluate(()=>window.PYBERT_WORKBENCH.getDraft().decision_scaler)};
}
