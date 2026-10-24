async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue9-viterbi/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  let runPosts=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/runs'))runPosts++;});
  const run=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  assert(run?.decoding.schema_version===2&&run.metadata_derivation,'derived schema2 selected');
  assert(run.datasets['viterbi.symbols_dfe'].axis==='viterbi.dfe_symbol_index','full DFE axis');
  assert(run.datasets['viterbi.symbols_dfe'].window.symbol_stop_exclusive===7500,'full DFE window');
  assert(run.decoding.symbol_count===5080&&run.decoding.dfe_decisions.decoder_start_symbol===2420,'actual decoder tail mapping');
  await page.locator('#analysis-kind').selectOption('viterbi');
  await page.waitForFunction(()=>!document.getElementById('analysis-info').textContent.includes('该字段元数据不可用于窗口对齐'));
  await page.locator('#trellis-error').fill('1');await page.locator('#trellis-error').press('Tab');
  await page.locator('#analysis-info').scrollIntoViewIfNeeded();
  await page.screenshot({path:root+'/docs/webui/issue9/evidence/chrome-v3/14-schema2-derived-record.jpg'});
  const download=page.waitForEvent('download');await page.locator('#save-results').click();
  await(await download).saveAs(root+'/output/playwright/issue9/PAM4-ERROR-v3-schema2-derived.pybert_run');
  assert(runPosts===0,'schema2 view started Run');
  return {source_run:run.run_id,record_id:run.record_id,decoding_schema:run.decoding.schema_version,
    full_dfe:run.datasets['viterbi.symbols_dfe'],mapping:run.decoding.dfe_decisions,
    derivation:run.metadata_derivation,runPosts,warning_absent:true,saved:true};
}
