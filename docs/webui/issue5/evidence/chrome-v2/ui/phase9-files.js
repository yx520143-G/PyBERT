async (page) => {
  await page.waitForFunction(()=>!document.querySelector('#run').disabled);
  const before=await page.evaluate(()=>({draft:JSON.stringify(window.PYBERT_WORKBENCH.getDraft()),id:window.PYBERT_RUNS.selected().record_id,refs:window.PYBERT_RUNS.references().map(r=>r.record_id)}));
  const results='C:/Users/yx/.codex/worktrees/pybert-issue5-archive/serial-bus-simulator/output/playwright/';
  for(const file of ['corrupt.pybert_run','unknown-version.pybert_run']) {
    await page.locator('#results-file').setInputFiles(results+file);await page.waitForFunction(()=>document.querySelector('#results-status').textContent.includes('打开结果失败'));
    const state=await page.evaluate(()=>({draft:JSON.stringify(window.PYBERT_WORKBENCH.getDraft()),id:window.PYBERT_RUNS.selected().record_id,refs:window.PYBERT_RUNS.references().map(r=>r.record_id)}));
    if(JSON.stringify(state)!==JSON.stringify(before)) throw new Error('Bad file mutated live state');
  }
  await page.route('**/api/runs/*/archive',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'injected download failure'})}));
  await page.locator('#save-results').click();await page.waitForFunction(()=>document.querySelector('#results-status').textContent.includes('injected download failure'));await page.unroute('**/api/runs/*/archive');
  const logicalName=await page.locator('#config-name').innerText();await page.locator('#save-as').click();await page.locator('#name-dialog').waitFor({state:'visible'});await page.locator('#save-name').fill('cancelled.yaml');await page.keyboard.press('Escape');
  if(await page.locator('#config-name').innerText()!==logicalName) throw new Error('Save As cancellation changed name');
  await page.locator('#results-file').setInputFiles([]);
  const baseline=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  const legacy='C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/docs/webui/issue4/evidence/light-compat-20261024-091034/native-cli.pybert_data';
  await page.locator('#trust-legacy').uncheck();await page.locator('#results-file').setInputFiles(legacy);await page.waitForFunction(()=>document.querySelector('#results-status').textContent.includes('请先明确确认'));
  if(await page.evaluate(()=>window.PYBERT_RUNS.references().length)!==baseline.references.length) throw new Error('Untrusted legacy imported');
  await page.locator('#trust-legacy').check();await page.locator('#results-file').setInputFiles(legacy);await page.waitForFunction(()=>window.PYBERT_RUNS.selected()?.kind==='legacy');
  const legacyId=await page.evaluate(()=>window.PYBERT_RUNS.selected().record_id);
  await page.locator('#compare-mode').selectOption('none');await page.locator('#analysis-kind').selectOption('response');await page.locator('#analysis-point').selectOption('chnl');await page.locator('#response-scope').selectOption('single');await page.locator('#response-type').selectOption('H');
  await page.waitForFunction(()=>document.querySelector('#plot').layout?.xaxis?.title?.text==='frequency-bin index');
  await page.evaluate(()=>document.querySelector('#analysis').scrollIntoView({block:'start'}));await page.screenshot({path:'output/playwright/14-trusted-legacy-frequency-index.png'});
  const legacyPlot=await page.evaluate(()=>({xunit:document.querySelector('#plot').layout.xaxis.title.text,yunit:document.querySelector('#plot').layout.yaxis.title.text,x_start:document.querySelector('#plot').data[0].x[0],x_stop:document.querySelector('#plot').data[0].x.at(-1),y_head:document.querySelector('#plot').data[0].y.slice(0,5)}));
  await page.locator('#legacy-results').click();await page.locator('#legacy-dialog').waitFor({state:'visible'});
  const nativeDisabled=await page.locator('#legacy-download').isDisabled();if(!nativeDisabled)throw new Error('Missing tx_out allowed native export');
  const sidecar=page.waitForEvent('download');await page.locator('#legacy-sidecar').click();await (await sidecar).saveAs('output/playwright/real-native-legacy-sidecar.json');await page.screenshot({path:'output/playwright/15-legacy-missing-tx-out.png'});await page.keyboard.press('Escape');
  await page.locator('#selected-run').selectOption(before.id);await page.waitForFunction(id=>window.PYBERT_RUNS.selected()?.record_id===id,before.id);await page.locator('#comparison-run').selectOption(legacyId);await page.locator('#compare-mode').selectOption('runs');
  await page.waitForFunction(()=>document.querySelector('#plot').textContent.includes('Legacy无物理轴'));
  for(const count of [3,4]) {await page.locator('#results-file').setInputFiles(results+'NRZ-real.pybert_run');await page.waitForFunction(count=>window.PYBERT_RUNS.references().length===count,count);}
  const full=await page.evaluate(()=>({id:window.PYBERT_RUNS.selected().record_id,refs:window.PYBERT_RUNS.references().map(r=>r.record_id)}));
  await page.locator('#results-file').setInputFiles(results+'NRZ-real.pybert_run');await page.waitForFunction(()=>document.querySelector('#results-status').textContent.includes('Reference budget'));
  const rejected=await page.evaluate(()=>({id:window.PYBERT_RUNS.selected().record_id,refs:window.PYBERT_RUNS.references().map(r=>r.record_id)}));if(JSON.stringify(full)!==JSON.stringify(rejected))throw new Error('Budget silently evicted or changed selection');
  await page.locator('#result-actions').scrollIntoViewIfNeeded();await page.screenshot({path:'output/playwright/16-reference-budget-no-eviction.png'});
  await page.locator('#clear-references').click();await page.waitForFunction(()=>window.PYBERT_RUNS.references().length===0);
  const final=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  if(JSON.stringify(final.runs.map(r=>r.run_id))!==JSON.stringify(baseline.runs.map(r=>r.run_id)) || final.current_task_id!==baseline.current_task_id || final.active_task_id) throw new Error('File/reference action changed numerical tasks/successes');
  return {corrupt_atomic:true,unknown_version_atomic:true,download_failure_atomic:true,save_as_escape_name_preserved:true,empty_selection_preserved:true,legacy_trust_required:true,legacy_plot:legacyPlot,legacy_native_export_blocked:nativeDisabled,legacy_overlay_refused:true,reference_budget_no_eviction:true,clear_preserved_successes:true,current_task_unchanged:true,final_state:final};
}
