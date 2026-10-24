async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue8-optimizer/serial-bus-simulator',base='http://127.0.0.1:8775/api/';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.reload();await page.waitForFunction(()=>!document.getElementById('load-config').disabled);
  const state=await(await page.request.get(base+'state')).json();
  await page.locator('#optimizer-open').click();const records=[];
  for(const row of state.optimizations) {
    const record=await(await page.request.get(base+'optimizations/'+row.record_id)).json();
    records.push({record_id:row.record_id,opt_id:record.opt_id,status:record.status,raw_schema:record.optimization_raw_schema,rlm:record.runtime_extensions.values.rlm});
    if(record.status==='succeeded')assert(record.candidates.length===4,'Candidate inventory changed');
    else assert(record.status==='cancelled'&&record.task.cancel_observed&&record.task.worker_exited,'Cancelled evidence changed');
  }
  for(const [index,row] of state.optimizations.entries()) {
    if(index!==0&&index!==2)continue;
    await page.locator('#selected-opt').selectOption(row.record_id);
    await page.waitForFunction(id=>document.getElementById('optimizer-provenance').textContent.includes(id),row.opt_id);
    await page.waitForFunction(()=>document.getElementById('optimizer-plot').data?.length>=2);
    const stroke=await page.locator('#optimizer-plot svg').first().evaluate(el=>getComputedStyle(el).strokeWidth);
    assert(stroke==='0px','Icon CSS still strokes plot text');
    await page.locator('#optimizer-plot').scrollIntoViewIfNeeded();
    await page.screenshot({path:root+'/output/playwright/issue8/final/'+(index===0?'09-readable-mmse.png':'10-readable-grid.png')});
  }
  await page.getByRole('button',{name:'Rx FFE',exact:true}).click();
  await page.locator('#settings-table-ffe_tap_tuners').evaluate(el=>el.open=true);
  assert(await page.locator('#settings-table-ffe_tap_tuners tbody tr').count()===100,'Missing FFE slots');
  assert(await page.locator('#settings-table-ffe_tap_tuners tbody input[type=checkbox]').count()===0,'FFE enable editable');
  const forged=await page.request.post(base+'normalize',{data:{mode:'use_eq',config:{},optimization:{status:'succeeded'}}});
  assert(forged.status()===422,'Forged action accepted');
  const after=await(await page.request.get(base+'state')).json();
  assert(after.runs.length===0&&after.optimizations.length===4&&after.references.length===2,'Computed inventory changed');
  return {browser:page.context().browser().version(),viewport:page.viewportSize(),records,checks:{raw_schema2_both_RLM:true,cancelled_lifecycle:true,readable_plot_stroke:'0px',FFE_slots:100,FFE_enable_readonly:true,forged_use_rejected:true,no_computed_results:true},new_coopt:0,new_main:0,new_COM:0};
}
