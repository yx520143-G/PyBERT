async page => {
  const original=await (await page.request.get('http://127.0.0.1:8767/api/state')).json();
  await page.getByRole('button',{name:'Run',exact:true}).click();
  const deadline=Date.now()+30000;
  let before;
  do {
    const state=await (await page.request.get('http://127.0.0.1:8767/api/state')).json();
    before=await (await page.request.get('http://127.0.0.1:8767/api/tasks/'+state.current_task_id)).json();
    if(before.operation==='run' && before.task_id!==original.current_task_id) {
      if(before.phase==='Running DFE/CDR...')break;
      if(before.worker_exited)throw Error('Run exited before DFE cancellation interval');
    }
    if(Date.now()>deadline)throw Error('DFE cancellation interval not reached');
    await page.waitForTimeout(50);
  }while(true);
  if(before.request_hash!=='769673a42a84604e38b41f1079ee7cff93d342ea65b8a91e0196c1cc103c8b2b')throw Error('Unexpected numerical input');
  await page.getByRole('button',{name:'Abort',exact:true}).click();
  const pending=await (await page.request.get('http://127.0.0.1:8767/api/tasks/'+before.task_id)).json();
  await page.screenshot({path:'output/playwright/51-core-DFE-cancel-pending.png'});
  return {before,pending,previous_com_ids:original.com_tasks.map(t=>t.task_id)};
}
