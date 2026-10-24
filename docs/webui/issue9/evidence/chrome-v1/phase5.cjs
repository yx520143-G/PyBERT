async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue9-viterbi/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.waitForFunction(()=>document.getElementById('config-status').textContent.includes('V-CANCEL.yaml')&&!document.getElementById('run').disabled);
  const old=await page.evaluate(()=>window.PYBERT_RUNS.selected()?.run_id);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/runs') && r.request().method()==='POST');
  await page.locator('#run').click();const task=await(await response).json();
  const events=[];let status,requestState=null;
  for(let i=0;i<12000;i++){
    status=await(await page.request.get('http://127.0.0.1:8776/api/tasks/'+task.task_id)).json();
    if(!events.length||events.at(-1).phase!==status.phase)events.push(status);
    if(status.phase==='Running Viterbi...'&&!requestState){
      assert(await page.locator('#abort').isEnabled(),'Abort not enabled');
      const cancel=page.waitForResponse(r=>r.url().endsWith('/api/tasks/'+task.task_id+'/cancel'));
      await page.locator('#abort').press('Enter');requestState=await(await cancel).json();
      assert(requestState.cancel_requested&&!requestState.worker_exited,'request is not exit');
      assert(await page.locator('#run').isDisabled(),'slot prematurely released');
      await page.evaluate(()=>window.scrollTo(0,0));
      await page.screenshot({path:root+'/output/playwright/issue9/08-cancel-requested-worker-occupied.jpg'});
    }
    if(status.worker_exited)break;await page.waitForTimeout(10);
  }
  assert(requestState&&status.state==='cancelled'&&status.cancel_observed&&status.worker_exited&&status.exitcode===0,JSON.stringify(status));
  await page.waitForFunction(()=>document.getElementById('task-state').textContent.includes('cancelled'));
  assert(await page.evaluate(()=>window.PYBERT_RUNS.selected()?.run_id)===old,'old result replaced by cancelled run');
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:root+'/output/playwright/issue9/09-cancelled-old-result-retained.jpg'});
  return {task_id:task.task_id,old_result:old,requestState,events,terminal:status,
    method:'normal enabled Abort button + Enter, original checkpoint; no force/kill',checks:{requested_observed_exit_separate:true,slot_retained:true,cancelled:true,old_success_retained:true}};
}
