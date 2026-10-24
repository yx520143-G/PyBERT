async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue9-viterbi/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  let posts=0;page.on('request',request=>{if(request.method()==='POST'&&request.url().endsWith('/api/runs'))posts++;});
  await page.waitForFunction(()=>document.getElementById('config-status').textContent.includes('PAM4-DISABLED.yaml')&&!document.getElementById('run').disabled);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/runs') && r.request().method()==='POST');
  await page.locator('#run').click();const task=await(await response).json();
  let final;for(let i=0;i<1200;i++){final=await(await page.request.get('http://127.0.0.1:8776/api/tasks/'+task.task_id)).json();if(final.worker_exited)break;await page.waitForTimeout(100);}
  assert(final.state==='succeeded'&&final.worker_exited,JSON.stringify(final));
  await page.waitForFunction(id=>window.PYBERT_RUNS.selected()?.run_id===id,task.task_id);
  await page.locator('#analysis-kind').selectOption('viterbi');
  await page.waitForFunction(()=>document.getElementById('trellis-status').textContent.includes('DFE: 596 bit errors'));
  const selected=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  assert(selected.summary.n_errs_dfe===596&&selected.summary.n_errs_viterbi===-1,'disabled must preserve actual DFE');
  assert(await page.locator('#trellis-position').isDisabled(),'disabled viewport');
  await page.locator('#expand-viewer').click();await page.locator('#analysis').scrollIntoViewIfNeeded();
  await page.screenshot({path:root+'/output/playwright/issue9/07-disabled-current-dfe596.jpg'});
  const download=page.waitForEvent('download');await page.locator('#save-results').click();
  await(await download).saveAs(root+'/output/playwright/issue9/PAM4-DISABLED.pybert_run');
  await page.getByRole('button',{name:'Noise',exact:true}).click();
  await page.locator('#expand-viewer').click();
  await page.locator('#control-rn').fill('0.16');await page.locator('#control-rn').press('Tab');
  await page.waitForFunction(()=>document.getElementById('stale').textContent.includes('Older input'));
  const dirty=await page.locator('#stale').innerText();
  assert(posts===1,'unexpected extra Run');
  return {run_id:task.task_id,terminal:final,summary:selected.summary,dirty,post_count:posts,checks:{disabled_minus1:true,current_DFE596:true,no_stale_trellis:true,dirty_old_result_preserved:true,saved:true}};
}
