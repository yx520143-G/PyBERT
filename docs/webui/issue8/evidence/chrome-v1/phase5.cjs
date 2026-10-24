async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue8-optimizer/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.waitForFunction(()=>!document.getElementById('tune-eq').disabled);
  const before=await(await page.request.get('http://127.0.0.1:8773/api/state')).json();
  const response=page.waitForResponse(r=>r.url().endsWith('/api/optimizations') && r.request().method()==='POST');
  await page.locator('#tune-eq').click();const start=await(await response).json();
  await page.waitForFunction(id=>document.getElementById('task-state').textContent.includes(id.slice(0,8)) && document.getElementById('task-state').textContent.includes('failed'),start.task_id);
  const task=await(await page.request.get('http://127.0.0.1:8773/api/tasks/'+start.task_id)).json();
  assert(task.state==='failed' && task.error_type==='RuntimeError' && !task.cancel_observed,'RuntimeError mislabelled cancellation');
  assert(task.error.includes('No Tx tap weight combination'),'Not the expected real native failure');
  await page.waitForFunction(id=>document.getElementById('selected-opt').value===id,start.task_id);
  assert(await page.locator('#use-eq').isDisabled(),'Failed candidate can Use EQ');
  const after=await(await page.request.get('http://127.0.0.1:8773/api/state')).json();
  assert(before.runs.map(r=>r.run_id).join()===after.runs.map(r=>r.run_id).join(),'Failure replaced old Run');
  const download=page.waitForEvent('download');await page.locator('#save-opt').click();await(await download).saveAs(root+'/output/playwright/issue8/failed.pybert_opt');
  await page.screenshot({path:root+'/output/playwright/issue8/06-native-failure.png'});
  await page.getByRole('button',{name:'Optimizer',exact:true}).click();
  await page.locator('#control-max_mag_tune').fill('1000');await page.locator('#control-max_mag_tune').press('Tab');
  await page.waitForFunction(()=>!document.getElementById('optimizer-plan').disabled);
  const planResponse=page.waitForResponse(r=>r.url().includes('/api/optimizer-actions/optimizer_plan'));
  await page.locator('#optimizer-plan').click();const denied=await planResponse;
  assert(denied.status()===422,'Budget not refused');
  const final=await(await page.request.get('http://127.0.0.1:8773/api/state')).json();
  assert(final.optimizations.length===after.optimizations.length,'Budget refusal ran coopt');
  assert((await page.locator('#optimizer-status').innerText()).includes('budget'),'Budget reason not visible');
  return {failed_task:task,checks:{real_native_RuntimeError:true,not_cancelled:true,old_Run_kept:true,Use_disabled:true,failure_saved:true,budget_422_without_coopt:true}};
}
