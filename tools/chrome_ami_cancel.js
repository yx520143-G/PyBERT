async (page) => {
  const prior=await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id);
  await page.getByRole('button',{name:'Run',exact:true}).click();
  await page.waitForFunction(()=>/running.*Running (DFE|CTLE|FFE|Tx|channel)/.test(document.getElementById('task-state').textContent),null,{timeout:60000});
  const before=await page.locator('#task-state').textContent();
  await page.getByRole('button',{name:'Abort',exact:true}).click();
  const requested=await page.locator('#task-state').textContent();
  await page.waitForFunction(()=>document.getElementById('task-state').textContent.includes('cancelled')&&!document.getElementById('run').disabled,null,{timeout:60000});
  if(await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id)!==prior)throw new Error('cancel replaced previous successful run');
  await page.screenshot({path:'C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v4/cancel-retains-success.png'});
  return {prior,before,requested,terminal:await page.locator('#task-state').textContent(),lifecycle:await page.locator('#live-log-id').textContent()};
}
