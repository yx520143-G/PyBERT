async page => {
  await page.getByRole('button', {name:'独立计算 COM',exact:true}).click();
  const deadline = Date.now()+30000;
  let before;
  do {
    const state = await (await page.request.get('http://127.0.0.1:8767/api/state')).json();
    before = await (await page.request.get('http://127.0.0.1:8767/api/tasks/'+state.current_task_id)).json();
    if (before.operation === 'com' && before.phase.startsWith('native COM helper')) break;
    if (before.worker_exited || Date.now()>deadline) throw Error('Helper interval not reached');
    await page.waitForTimeout(100);
  } while(true);
  await page.getByRole('button', {name:'关闭',exact:true}).click();
  await page.getByRole('button', {name:'Abort',exact:true}).click();
  const pending = await page.evaluate(async id => (await fetch('/api/tasks/'+id)).json(), before.task_id);
  await page.screenshot({path:'output/playwright/26-COM-helper-cancel-pending.png'});
  if (!pending.cancel_requested || pending.cancel_observed || pending.worker_exited) throw Error('Missing actual helper cancellation interval');
  return {before,pending};
}
