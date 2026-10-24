async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue9-viterbi/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  let posts=0;page.on('request',request=>{if(request.method()==='POST'&&request.url().endsWith('/api/runs'))posts++;});
  const task_id='a371f8c8-a6bc-4497-950e-26153fc1958b';
  let final;for(let i=0;i<1200;i++){final=await(await page.request.get('http://127.0.0.1:8776/api/tasks/'+task_id)).json();if(final.worker_exited)break;await page.waitForTimeout(100);}
  assert(final.state==='succeeded'&&final.worker_exited,JSON.stringify(final));
  await page.waitForFunction(id=>window.PYBERT_RUNS.selected()?.run_id===id,task_id);
  await page.locator('#analysis-kind').selectOption('viterbi');await page.locator('#compare-mode').selectOption('none');
  await page.waitForFunction(()=>document.getElementById('trellis-of').textContent.includes('of 470'));
  await page.locator('#trellis-error').fill('1');await page.locator('#trellis-error').press('Tab');
  await page.waitForFunction(()=>document.getElementById('analysis-info').textContent.includes('Error 1: bit'));
  const selected=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  assert(selected.summary.n_errs_dfe===596 && selected.summary.n_errs_viterbi===470,'actual error counts');
  await page.locator('#analysis').scrollIntoViewIfNeeded();
  await page.screenshot({path:root+'/output/playwright/issue9/03-pam4-error1-trellis.jpg'});
  await page.locator('#trellis-position').fill('999999');await page.locator('#trellis-position').press('Tab');
  await page.waitForFunction(()=>document.getElementById('trellis-position').value===document.getElementById('trellis-position').max);
  const boundary=await page.locator('#trellis-position').inputValue();
  await page.locator('#trellis-position').fill('50');await page.locator('#trellis-position').press('Tab');
  await page.locator('#compare-mode').selectOption('runs');
  await page.locator('#trellis-chart-1 .plot-container').waitFor();
  await page.screenshot({path:root+'/output/playwright/issue9/04-two-run-trellis.jpg'});
  const download=page.waitForEvent('download');await page.locator('#save-results').click();
  await(await download).saveAs(root+'/output/playwright/issue9/PAM4-ERROR.pybert_run');
  assert(posts===0,'view operations started extra Run');
  return {run_id:task_id,terminal:final,summary:selected.summary,boundary,post_count:posts,
    layout:await page.evaluate(()=>({parent:document.getElementById('plot').getBoundingClientRect().width,child:document.getElementById('trellis-chart-0').getBoundingClientRect().width,plot:document.getElementById('trellis-chart-0').layout.width})),
    checks:{actual_errors:true,error1:true,actual_symbol_boundary:true,two_run_trellis:true,no_extra_Run:true,saved:true}};
}
