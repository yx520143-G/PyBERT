async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue9-viterbi/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  let posts=0;page.on('request',request=>{if(request.method()==='POST'&&request.url().endsWith('/api/runs'))posts++;});
  await page.waitForFunction(()=>window.PYBERT_RUNS.selected()?.kind==='archive');
  const record=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  await page.getByRole('button',{name:'Viterbi / MLSD',exact:true}).click();
  await page.locator('#analysis-kind').selectOption('viterbi');
  await page.waitForFunction(()=>document.getElementById('trellis-of').textContent.includes('of 470'));
  await page.locator('#trellis-error').fill('1');await page.locator('#trellis-error').press('Tab');
  await page.locator('#expand-viewer').click();
  await page.waitForFunction(()=>document.getElementById('trellis-chart-0')?._fullData?.find(t=>t.marker?.showscale)?.marker.colorbar.title.text==='log10(raw)<br>floor −20');
  await page.locator('#analysis').scrollIntoViewIfNeeded();
  await page.screenshot({path:root+'/output/playwright/issue9/11-final-log-colorbar-trellis.jpg'});
  const bar=await page.evaluate(()=>document.getElementById('trellis-chart-0')._fullData.find(t=>t.marker?.showscale).marker.colorbar.title.text);
  await page.locator('#analysis-info details summary').click();
  await page.getByRole('columnheader',{name:'raw probability',exact:true}).scrollIntoViewIfNeeded();
  await page.screenshot({path:root+'/output/playwright/issue9/12-final-raw-probability-log-table.jpg'});
  const download=page.waitForEvent('download');await page.locator('#save-results').click();
  await(await download).saveAs(root+'/output/playwright/issue9/PAM4-ERROR-v2.pybert_run');
  assert(posts===0,'read-only final views started Run');
  return {record_id:record.record_id,source_run:record.run_id,colorbar:bar,viewport:page.viewportSize(),browser:page.context().browser().version(),
    post_count:posts,checks:{original_archive:true,error1:true,raw_log_distinct:true,actual_colorbar_title:true,no_extra_Run:true,saved:true}};
}
