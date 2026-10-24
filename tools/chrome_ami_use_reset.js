async (page) => {
  const originalRun=await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id);
  const before=await page.evaluate(()=>window.PYBERT_RUNS.modelDraft());
  const record=JSON.parse(await page.locator('#optimizer-record').textContent());
  await page.locator('#use-eq').click();
  await page.waitForFunction(()=>document.getElementById('eq-dialog').open);
  const preview=await page.locator('#eq-differences').textContent();
  if(JSON.stringify(await page.evaluate(()=>window.PYBERT_RUNS.modelDraft()))!==JSON.stringify(before))throw new Error('Preview mutated draft');
  await page.screenshot({path:'C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v4/use-eq-preview.png'});
  await page.locator('#confirm-use-eq').click();
  await page.waitForFunction(()=>!document.getElementById('eq-dialog').open&&document.getElementById('optimizer-status').textContent.includes('已显式应用'));
  const applied=await page.evaluate(()=>window.PYBERT_RUNS.modelDraft());
  for(const [side,patch] of Object.entries(record.ami.dynamic_patch))for(const row of patch.parameters){
    const actual=applied.runtime_extensions.values.ami_models[side].parameters.find(p=>JSON.stringify(p.path)===JSON.stringify(row.path));
    if(actual?.value!==row.value)throw new Error('Use dynamic patch differs');
  }
  await page.locator('#reset-eq').click();
  await page.waitForFunction(()=>document.getElementById('optimizer-status').textContent.startsWith('已按原 Reset EQ'));
  const reset=await page.evaluate(()=>window.PYBERT_RUNS.modelDraft());
  for(const key of ['ami_models','ami_opt_trials'])if(JSON.stringify(reset.runtime_extensions.values[key])!==JSON.stringify(applied.runtime_extensions.values[key]))throw new Error('Native Reset mutated AMI settings');
  if(await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id)!==originalRun)throw new Error('Use/Reset replaced previous Run');
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Save',exact:true}).click();
  await (await download).saveAs('C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v4/after-use-reset.yaml');
  return {opt_id:record.opt_id,originalRun,preview:JSON.parse(preview),before,applied,reset};
}
