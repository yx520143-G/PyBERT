async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue9-viterbi/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  let runPosts=0;page.on('request',request=>{if(request.method()==='POST'&&request.url().endsWith('/api/runs'))runPosts++;});
  const run=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  assert(run?.summary.n_errs_viterbi===0 && run.effective_input.rx_viterbi_symbols===2,'prior actual Run missing');
  await page.locator('#analysis-kind').selectOption('viterbi');
  await page.waitForFunction(()=>document.getElementById('trellis-status').textContent.includes('0–9'));
  assert((await page.locator('#trellis-of').innerText()).includes('of 0'),'zero errors');
  await page.locator('#trellis-position').fill('50');await page.locator('#trellis-position').press('Tab');
  await page.waitForFunction(()=>document.getElementById('trellis-status').textContent.startsWith('50–59'));
  const slider=page.locator('#trellis-pan'),box=await slider.boundingBox(),max=Number(await slider.getAttribute('max'));
  await page.mouse.move(box.x+8+(box.width-16)*50/max,box.y+box.height/2);await page.mouse.down();
  await page.mouse.move(box.x+box.width*.65,box.y+box.height/2,{steps:8});await page.mouse.up();
  await page.waitForFunction(()=>Number(document.getElementById('trellis-position').value)>50);
  const dragged=await page.locator('#trellis-position').inputValue();
  await page.locator('#trellis-error').fill('0');await page.locator('#trellis-error').press('Tab');
  await page.locator('#expand-viewer').click();
  await page.locator('#trellis-chart-0 .plot-container').waitFor();
  await page.screenshot({path:root+'/output/playwright/issue9/01-pam4-no-errors-trellis.jpg'});
  const download=page.waitForEvent('download');await page.locator('#save-results').click();
  await(await download).saveAs(root+'/output/playwright/issue9/PAM4-ISI.pybert_run');
  await page.getByRole('button',{name:'DFE / Slicer',exact:true}).click();
  await page.locator('#analysis-kind').selectOption('response');
  await page.waitForFunction(()=>document.querySelector('#plot .plot-container'));
  await page.locator('#analysis-kind').selectOption('jitter.dist');
  await page.waitForFunction(()=>document.querySelector('#plot .plot-container'));
  await page.screenshot({path:root+'/output/playwright/issue9/02-same-run-dfe-jitter.jpg'});
  assert(runPosts===0,'view operations started a Run');
  console.log(JSON.stringify({viewport:page.viewportSize(),browser:page.context().browser().version(),run_id:run.run_id,dragged,
    checks:{prior_Run_inspected:true,trellis_zero_error:true,position_drag:true,DFE_Responses_Jitter:true,no_extra_Run:true,archive_downloaded:true}}));
}
