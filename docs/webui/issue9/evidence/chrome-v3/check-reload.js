async page => {
  let runPosts=0;page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/api/runs'))runPosts++;});
  await page.reload();
  await page.waitForFunction(()=>window.PYBERT_RUNS?.selected()?.record_id==='ref-2ae1f5f1-388c-4a26-9042-e786e0feaf85');
  const run=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  if(run.decoding.schema_version!==2||run.decoding.dfe_decisions.decoder_start_symbol!==2420||runPosts!==0)throw new Error('reload metadata/no Run');
  return {record_id:run.record_id,schema:run.decoding.schema_version,mapping:run.decoding.dfe_decisions,runPosts};
}
