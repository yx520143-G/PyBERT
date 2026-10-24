async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue8-optimizer/serial-bus-simulator';
  const output=root+'/output/playwright/issue8/final',base='http://127.0.0.1:8775/api/';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.waitForFunction(()=>!document.getElementById('load-config').disabled);
  await page.locator('#optimizer-open').click();
  const draft=await page.evaluate(()=>JSON.stringify(window.PYBERT_WORKBENCH.getDraft())),records=[];
  const files=[output+'/O-PAM4-MMSE.pybert_opt',output+'/O-PAM4-MMSE-RLM080.pybert_opt',
    root+'/docs/webui/issue8/evidence/delivery-audit-20261024-130843/local/2e3d0d79-061f-4084-96bc-53d651486c2d.pybert_opt',
    root+'/docs/webui/issue8/evidence/delivery-audit-20261024-130843/local/333787d7-7a75-4536-9225-70df8983d5e0.pybert_opt'];
  for(let i=0;i<files.length;i++) {
    const response=page.waitForResponse(r=>r.url().endsWith('/api/optimization-references')&&r.request().method()==='POST');
    await page.locator('#opt-file').setInputFiles(files[i]);const record=await(await response).json();
    assert(record.record_id,'Archive open failed: '+JSON.stringify(record));records.push(record);
    await page.waitForFunction(id=>document.getElementById('selected-opt').value===id && document.getElementById('optimizer-record').textContent.includes(id),record.record_id);
    assert(await page.evaluate(()=>JSON.stringify(window.PYBERT_WORKBENCH.getDraft()))===draft,'Opening optimization mutated draft');
    if(i===0) {
      const prior=await page.locator('#selected-opt').inputValue();
      const bad=page.waitForResponse(r=>r.url().endsWith('/api/optimization-references')&&r.request().method()==='POST');
      await page.locator('#opt-file').setInputFiles(output+'/unknown.pybert_opt');const rejected=await bad;
      assert(rejected.status()===422,'Unknown schema not rejected');
      await page.waitForFunction(()=>document.getElementById('optimizer-status').textContent.includes('schema'));
      assert(await page.locator('#selected-opt').inputValue()===prior,'Rejected archive replaced selection');
    }
    if(i<3) {
      await page.waitForFunction(()=>!document.getElementById('save-opt').disabled);
      const download=page.waitForEvent('download');await page.locator('#save-opt').click();
      const saved=await download;assert(saved.suggestedFilename()===record.opt_id+'.pybert_opt','Save source filename mismatch');
      await saved.saveAs(output+'/reopened-'+i+'.pybert_opt');
    }
  }
  assert(await page.locator('#use-eq').isDisabled(),'Cancelled record can Use');
  const cancelled=await(await page.request.get(base+'optimizations/'+records[3].record_id)).json();
  assert(cancelled.status==='cancelled'&&cancelled.task.cancel_observed&&cancelled.task.worker_exited,'Cancelled lifecycle lost');
  await page.locator('#selected-opt').selectOption(records[0].record_id);
  await page.waitForFunction(()=>document.getElementById('optimizer-plot').data?.length===4);
  const plot=await page.locator('#optimizer-plot').evaluate(el=>({legend:el.data[3].visible,font:el.layout.font.family,axis:el.layout.xaxis.title.text}));
  assert(plot.legend==='legendonly'&&plot.font==='Arial'&&plot.axis==='ns','Final plot metadata wrong');
  await page.locator('#optimizer-plot').scrollIntoViewIfNeeded();
  await page.screenshot({path:output+'/07-final-mmse.png'});
  await page.locator('#selected-opt').selectOption(records[2].record_id);
  await page.waitForFunction(()=>document.getElementById('optimizer-provenance').textContent.includes('cursor/ISI grid'));
  await page.locator('#selected-candidate').selectOption('candidate-000000');
  await page.waitForFunction(()=>document.getElementById('optimizer-provenance').textContent.includes('candidate-000000'));
  await page.screenshot({path:output+'/08-final-grid.png'});
  for(const name of ['PAM4-RLM095','PAM4-RLM080']) {
    const response=page.waitForResponse(r=>r.url().endsWith('/api/references')&&r.request().method()==='POST');
    await page.locator('#results-file').setInputFiles(root+'/output/playwright/issue8/'+name+'.pybert_run');
    const loaded=await(await response).json();assert(loaded.record_id,'Run archive open failed');
  }
  await page.locator('#config-file').setInputFiles(root+'/output/playwright/issue8/used-reset.yaml');
  await page.waitForFunction(()=>document.getElementById('config-status').textContent.includes('已载入 used-reset.yaml'));
  const restored=await page.evaluate(()=>window.PYBERT_WORKBENCH.getDraft());
  assert(restored.rlm===.8&&restored.rn===.02,'YAML runtime/current edits lost');
  const save=page.waitForEvent('download');await page.locator('#save-config').click();await(await save).saveAs(output+'/used-reset-final.yaml');
  const forged=await page.request.post(base+'normalize',{data:{mode:'use_eq',config:{},optimization:{status:'succeeded'}}});
  assert(forged.status()===422,'Generic normalize accepts forged Use action');
  const state=await(await page.request.get(base+'state')).json();
  assert(state.runs.length===0&&state.optimizations.length===4&&state.references.length===2,'Recovery created computed result');
  return {browser:page.context().browser().version(),viewport:page.viewportSize(),records,plot,checks:{raw2_PAM95_PAM80_restored:true,unknown_schema_atomic:true,NRZ_save_download:true,cancelled_lifecycle:true,Run_references:2,YAML_runtime:true,forged_use_rejected:true,no_computed_runs:true},new_coopt:0,new_main:0,new_COM:0};
}
