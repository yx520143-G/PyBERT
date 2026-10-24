async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue8-optimizer/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.waitForFunction(()=>!document.getElementById('tune-eq').disabled);
  await page.locator('#optimizer-open').click();
  const before=await(await page.request.get('http://127.0.0.1:8773/api/state')).json();
  const response=page.waitForResponse(r=>r.url().endsWith('/api/optimizations') && r.request().method()==='POST');
  await page.locator('#tune-eq').click();const start=await(await response).json();
  let task;
  for(let i=0;i<2000;i++) {
    task=await(await page.request.get('http://127.0.0.1:8773/api/tasks/'+start.task_id)).json();
    if(task.phase.startsWith('native coopt') || task.phase.startsWith('Optimizing EQ') || task.worker_exited)break;
    await page.waitForTimeout(10);
  }
  assert(!task.worker_exited,'Cancel attempt naturally finished before request');
  const phaseAtRequest=task.phase;
  await page.locator('#abort-eq').click();
  const requested=await(await page.request.get('http://127.0.0.1:8773/api/tasks/'+start.task_id)).json();
  for(let i=0;i<2000;i++) {
    task=await(await page.request.get('http://127.0.0.1:8773/api/tasks/'+start.task_id)).json();
    if(task.worker_exited)break;await page.waitForTimeout(10);
  }
  assert(task.state==='cancelled' && task.cancel_requested && task.cancel_observed && task.worker_exited,'No observed/joined cancellation: '+JSON.stringify(task));
  assert(task.error_type==='OptimizationCancelled','Cancellation did not use native checkpoint bridge');
  const after=await(await page.request.get('http://127.0.0.1:8773/api/state')).json();
  assert(before.runs.map(r=>r.run_id).join()===after.runs.map(r=>r.run_id).join(),'Cancellation replaced successful Run');
  assert(before.optimizations.filter(r=>r.status==='succeeded').map(r=>r.opt_id).join()===after.optimizations.filter(r=>r.status==='succeeded').map(r=>r.opt_id).join(),'Cancellation removed previous successful candidates');
  await page.waitForFunction(id=>document.getElementById('selected-opt').value===id,start.task_id);
  assert(await page.locator('#use-eq').isDisabled(),'Cancelled candidate can Use EQ');
  await page.screenshot({path:root+'/output/playwright/issue8/05-cancelled.png'});
  return {task,phaseAtRequest,requested,checks:{native_coopt_in_progress:true,requested_observed_exited_distinct:true,cancelled_after_join:true,old_successes_kept:true,Use_disabled:true}};
}
