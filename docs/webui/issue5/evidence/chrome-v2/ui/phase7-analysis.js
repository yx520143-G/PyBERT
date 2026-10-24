async (page) => {
  const original=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  const selected=await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id);
  const checks=[];
  async function chart(kind,point,type) {
    await page.locator('#compare-mode').selectOption('none');
    await page.locator('#analysis-kind').selectOption(kind);
    if(point) await page.locator('#analysis-point').selectOption(point);
    if(type) {await page.locator('#response-scope').selectOption('single');await page.locator('#response-type').selectOption(type);}
    const key=kind==='response' ? point==='chnl' && type==='H'?'channel.frequency':`${point}_${type}` : kind==='wave'?`wave.${({chnl:'chnl_out',tx:'rx_in',ctle:'ctle_out',ffe:'ffe_out',dfe:'dfe_out'})[point]}` : kind==='eye'?`eye.${point}` : kind.startsWith('jitter.')?`jitter.${point}.${kind.split('.')[1]}`:kind;
    const available=await page.evaluate(key=>window.PYBERT_RUNS.selected().plots[key]?.availability!=='unavailable',key);
    if(available) await page.waitForFunction(({key,id})=>document.querySelector('#analysis-info').textContent.includes(key) && document.querySelector('#analysis-info').textContent.includes(id),{key,id:selected});
    else await page.waitForFunction(()=>document.querySelector('#plot').textContent.includes('unavailable'));
    checks.push({kind,point,key,available,source_run:selected,trace_count:await page.evaluate(()=>document.querySelector('#plot').data?.length || 0)});
  }
  for(const type of ['h','s','p','H']) for(const point of ['chnl','tx','ctle','ffe','dfe']) await chart('response',point,type);
  for(const kind of ['wave','eye','jitter.dist','jitter.spec','jitter.bathtub']) for(const point of ['chnl','tx','ctle','ffe','dfe']) await chart(kind,point);
  for(const kind of ['adaptation','cdr','cdr.histogram','cdr.spectrum']) await chart(kind);
  await page.locator('#analysis-kind').selectOption('jitter.info');await page.waitForFunction(()=>document.querySelector('#analysis-info').textContent.includes('Rejection ratio'));
  await page.evaluate(()=>document.querySelector('#analysis').scrollIntoView({block:'start'}));await page.screenshot({path:'output/playwright/09-jitter-info-all-points.png'});
  await page.locator('#analysis-kind').selectOption('compare');await page.waitForFunction(()=>document.querySelector('#analysis-info').textContent.includes('Input differences'));
  await page.evaluate(()=>document.querySelector('#analysis').scrollIntoView({block:'start'}));await page.screenshot({path:'output/playwright/10-two-run-inputs.png'});
  await page.locator('#results-file').setInputFiles('C:/Users/yx/.codex/worktrees/pybert-issue5-archive/serial-bus-simulator/output/playwright/PAM4-real.pybert_run');
  await page.waitForFunction(()=>window.PYBERT_RUNS.selected()?.kind==='archive');
  const reference=await page.evaluate(()=>window.PYBERT_RUNS.selected().record_id);
  await page.locator('#selected-run').selectOption(selected);await page.waitForFunction(id=>window.PYBERT_RUNS.selected()?.run_id===id,selected);
  await page.locator('#comparison-run').selectOption(reference);await page.locator('#analysis-point').selectOption('chnl');
  await page.locator('#analysis-kind').selectOption('response');await page.locator('#response-type').selectOption('H');await page.locator('#compare-mode').selectOption('runs');
  await page.waitForFunction(()=>document.querySelector('#plot').data?.length===6);
  await page.evaluate(()=>document.querySelector('#analysis').scrollIntoView({block:'start'}));await page.screenshot({path:'output/playwright/11-current-plus-archive-frequency.png'});
  const traces=await page.evaluate(()=>document.querySelector('#plot').data.map(t=>({name:t.name,x_count:t.x.length,y_count:t.y.length})));
  await page.locator('#analysis-kind').selectOption('eye');await page.locator('#analysis-point').selectOption('dfe');await page.waitForFunction(()=>document.querySelector('#plot').data?.length===2 && document.querySelector('#plot').data[0].type==='heatmap');
  await page.evaluate(()=>document.querySelector('#analysis').scrollIntoView({block:'start'}));await page.screenshot({path:'output/playwright/12-current-plus-archive-eye.png'});
  const grids=await page.evaluate(()=>document.querySelector('#plot').data.map(t=>({x:[t.x[0],t.x.at(-1)],y:[t.y[0],t.y.at(-1)],shape:[t.z.length,t.z[0].length]})));
  const final=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  if(final.current_task_id!==original.current_task_id || final.active_task_id || final.com_tasks.length) throw new Error('Analysis/load/comparison started a numerical task');
  return {checks,compared_reference:reference,frequency_traces:traces,eye_grids:grids,current_task_unchanged:true,successful_runs:final.runs.map(r=>r.run_id)};
}
