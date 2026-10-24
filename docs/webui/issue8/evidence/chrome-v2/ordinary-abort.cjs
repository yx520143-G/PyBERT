async page => {
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.waitForFunction(()=>!document.getElementById('tune-eq').disabled);
  await page.locator('#optimizer-open').click();
  const response=page.waitForResponse(r=>r.url().endsWith('/api/optimizations') && r.request().method()==='POST');
  await page.locator('#tune-eq').click();const start=await(await response).json();
  const cancelResponse=page.waitForResponse(r=>r.url().endsWith('/api/tasks/'+start.task_id+'/cancel'));
  await page.locator('#abort-eq').click();
  const requested=await(await cancelResponse).json();
  assert(requested.cancel_requested && !requested.worker_exited,'Ordinary click did not request cancellation before exit');
  await page.waitForFunction(id=>document.getElementById('task-state').textContent.includes(id.slice(0,8)) && document.getElementById('task-state').textContent.includes('cancelled'),start.task_id);
  const task=await(await page.request.get('http://127.0.0.1:8774/api/tasks/'+start.task_id)).json();
  assert(task.cancel_observed && task.worker_exited && task.state==='cancelled','Ordinary click cancellation incomplete');
  return {method:'ordinary Playwright locator.click, no force; request immediately after optimization 202 (may be prevalidation)',requested,task};
}
