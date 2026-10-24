async (page) => {
  const response=page.waitForResponse(r=>r.url().endsWith('/api/runs') && r.request().method()==='POST');
  await page.locator('#run').click();const submitted=await response;const task=await submitted.json();
  if(submitted.status()!==202) throw new Error(JSON.stringify(task));
  await page.reload();
  const duringReload=await (await page.request.get(`http://127.0.0.1:8770/api/tasks/${task.task_id}`)).json();
  await page.waitForFunction(id=>window.PYBERT_RUNS?.selected()?.run_id===id,task.task_id,{timeout:60000});
  const final=await (await page.request.get(`http://127.0.0.1:8770/api/tasks/${task.task_id}`)).json();
  if(final.state!=='succeeded' || !final.worker_exited) throw new Error(JSON.stringify(final));
  await page.locator('#analysis-kind').selectOption('wave');await page.locator('#analysis-point').selectOption('ffe');
  await page.waitForFunction(id=>document.querySelector('#analysis-info').textContent.includes(id),task.task_id);
  if(!await page.evaluate(()=>document.querySelector('#work-area').classList.contains('viewer-expanded'))) await page.locator('#expand-viewer').click();
  await page.locator('#analysis').scrollIntoViewIfNeeded();await page.screenshot({path:'output/playwright/06-real-nrz-ffe-wave.png'});
  const download=page.waitForEvent('download');await page.locator('#save-results').click();await (await download).saveAs('output/playwright/NRZ-real.pybert_run');
  return {during_reload:duringReload,final_task:final,selected:await page.evaluate(()=>({run_id:window.PYBERT_RUNS.selected().run_id,summary:window.PYBERT_RUNS.selected().summary,window:window.PYBERT_RUNS.selected().window})),state:await (await page.request.get('http://127.0.0.1:8770/api/state')).json()};
}
