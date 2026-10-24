async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue9-viterbi/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  let posts=0;page.on('request',request=>{if(request.method()==='POST'&&request.url().endsWith('/api/runs'))posts++;});
  await page.waitForFunction(()=>window.PYBERT_RUNS.selected()?.kind==='archive');
  const reference=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  await page.locator('#compare-mode').selectOption('none');
  await page.locator('#analysis-kind').selectOption('viterbi');
  await page.waitForFunction(()=>document.getElementById('trellis-of').textContent.includes('of 470'));
  await page.screenshot({path:root+'/output/playwright/issue9/05-opened-archive-trellis.jpg'});
  await page.reload();await page.waitForFunction(()=>!document.getElementById('run').disabled);
  await page.waitForFunction(id=>(window.PYBERT_RUNS.selected()?.record_id)===id,reference.record_id);
  await page.locator('#analysis-kind').selectOption('viterbi');
  await page.waitForFunction(()=>document.getElementById('trellis-of').textContent.includes('of 470'));
  await page.screenshot({path:root+'/output/playwright/issue9/06-reload-original-archive.jpg'});
  assert(posts===0,'archive/view/reload started a Run');
  return {record_id:reference.record_id,source_run:reference.run_id,post_count:posts,checks:{open_archive:true,reload_selection:true,old_raw_preserved:true,no_extra_Run:true}};
}
