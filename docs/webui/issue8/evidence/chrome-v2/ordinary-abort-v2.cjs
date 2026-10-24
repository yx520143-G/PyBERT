async page => {
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.waitForFunction(()=>!document.getElementById('tune-eq').disabled);
  await page.locator('#optimizer-open').click();
  const previous=await page.locator('#optimizer-status').innerText();
  await page.locator('#tune-eq').click();
  await page.waitForFunction(previous=>document.getElementById('optimizer-status').textContent!==previous && document.getElementById('optimizer-status').textContent.includes('validating'),previous);
  const text=await page.locator('#optimizer-status').innerText(),id=text.match(/opt ([a-f0-9-]+)/)[1];
  const cancelResponse=page.waitForResponse(r=>r.url().endsWith('/api/tasks/'+id+'/cancel'));
  await page.locator('#abort-eq').click();
  const requested=await(await cancelResponse).json();
  assert(requested.cancel_requested && !requested.worker_exited,'Normal Abort did not request before exit');
  await page.waitForFunction(id=>document.getElementById('task-state').textContent.includes(id.slice(0,8)) && document.getElementById('task-state').textContent.includes('cancelled'),id);
  const task=await(await page.request.get('http://127.0.0.1:8774/api/tasks/'+id)).json();
  assert(task.cancel_observed && task.worker_exited && task.state==='cancelled','Ordinary click cancellation incomplete');
  return {method:'ordinary locator.click without force on preregistered outer16/inner16',requested,task};
}
