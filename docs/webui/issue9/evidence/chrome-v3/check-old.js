async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue9-viterbi/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  let runPosts=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/runs'))runPosts++;});
  const run=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  assert(run?.run_id==='a371f8c8-a6bc-4497-950e-26153fc1958b','original archive selected');
  await page.getByRole('button',{name:'Viterbi / MLSD',exact:true}).click();
  await page.locator('#analysis-kind').selectOption('viterbi');
  await page.waitForFunction(()=>document.getElementById('analysis-info').textContent.includes('该字段元数据不可用于窗口对齐'));
  await page.locator('#trellis-error').fill('1');await page.locator('#trellis-error').press('Tab');
  await page.waitForFunction(()=>document.getElementById('trellis-error').value==='1');
  await page.locator('#analysis-info').scrollIntoViewIfNeeded();
  await page.screenshot({path:root+'/docs/webui/issue9/evidence/chrome-v3/13-legacy-metadata-erratum.jpg'});
  const before=await(await page.request.get('http://127.0.0.1:8778/api/state')).json();
  const refusals=[];
  for(const request of [{mode:'defaults',rx_viterbi_fec:true},{mode:'defaults',config:{rx_viterbi_fec:true}},
    {mode:'defaults',runtime_extensions:{version:1,values:{rx_viterbi_fec:true}}}]) {
    const response=await page.request.post('http://127.0.0.1:8778/api/normalize',{data:request});
    const body=await response.json();
    assert(response.status()===422&&body.detail.includes('unsupported_native_fec'),'warm-cache FEC refused');
    refusals.push({request,status:response.status(),body});
  }
  const after=await(await page.request.get('http://127.0.0.1:8778/api/state')).json();
  assert(JSON.stringify(before)===JSON.stringify(after),'FEC refusal changed state/records/task');
  assert(runPosts===0,'read-only phase started Run');
  const download=page.waitForEvent('download');await page.locator('#save-results').click();
  await(await download).saveAs(root+'/output/playwright/issue9/PAM4-ERROR-v3-legacy.pybert_run');
  return {source_run:run.run_id,record_id:run.record_id,viewport:page.viewportSize(),browser:page.context().browser().version(),
    legacy_schema:run.decoding.schema_version,warning_visible:true,refusals,state_unchanged:true,runPosts};
}
