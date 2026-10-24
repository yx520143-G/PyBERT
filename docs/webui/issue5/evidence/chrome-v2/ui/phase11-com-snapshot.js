async (page) => {
  const child='a803f4ca-83f2-4031-a31c-af5213fc71d8';
  await page.waitForFunction(()=>window.PYBERT_RUNS?.selected()?.run_id==='c3cadfdc-13e8-4ed9-bee3-b3b11462cd96');
  const initial=await (await page.request.get('http://127.0.0.1:8771/api/state')).json();
  if(initial.active_task_id!==child || initial.com_tasks[0].worker_exited)throw new Error('Expected preserved historical active snapshot');
  const saved=page.waitForEvent('download',{timeout:120000});await page.locator('#save-results').click();await (await saved).saveAs('output/playwright/historical-COM-running-v3.pybert_run');
  await page.request.post('http://127.0.0.1:8771/_fixture/final');
  await page.waitForFunction(()=>document.querySelector('#task-state').textContent.includes('succeeded'));
  await page.locator('#results-file').setInputFiles('C:/Users/yx/.codex/worktrees/pybert-issue5-archive/serial-bus-simulator/output/playwright/historical-COM-running-v3.pybert_run');
  await page.waitForFunction(()=>window.PYBERT_RUNS.selected()?.kind==='archive');
  await page.locator('#analysis-kind').selectOption('overview');
  await page.waitForFunction(()=>document.querySelector('#analysis-info').textContent.includes('waiting_for_exit'));
  const archived=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  const snapshot=archived.saved_subfunctions.linked_tasks[child];
  if(snapshot.task.state!=='running' || snapshot.task.worker_exited || Object.values(snapshot.files).some(row=>row.availability!=='waiting_for_exit'))throw new Error('Snapshot spliced in current-session success');
  const details=page.locator('#analysis-info details');await details.locator('summary').click();
  await page.locator('#analysis').scrollIntoViewIfNeeded();await page.screenshot({path:'output/playwright/19-historical-com-snapshot-no-splice.png'});
  const resaved=page.waitForEvent('download',{timeout:120000});await page.locator('#save-results').click();await (await resaved).saveAs('output/playwright/historical-COM-running-v3-resaved.pybert_run');
  return {mode:'replay of real saved historical active/final tasks; no live COM',initial_task:initial.com_tasks[0],current_task:(await (await page.request.get('http://127.0.0.1:8771/api/state')).json()).com_tasks[0],archived_snapshot:snapshot,record_id:archived.record_id,source_run_id:archived.run_id,main_calls:0,COM_calls:0};
}


