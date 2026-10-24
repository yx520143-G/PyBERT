async (page) => {
  await page.waitForFunction(()=>window.PYBERT_RUNS && !document.querySelector('#run').disabled);
  await page.locator('#results-file').setInputFiles('C:/Users/yx/.codex/worktrees/pybert-issue5-archive/serial-bus-simulator/docs/webui/issue5/evidence/saved-roundtrip-20261024-104338/local/issue4-PAM4.pybert_run');
  await page.waitForFunction(()=>window.PYBERT_RUNS.selected()?.kind==='archive');
  await page.locator('#restore-run-input').click();
  await page.waitForFunction(()=>document.querySelector('#results-status').textContent.includes('已恢复原requested'));
  await page.locator('#clear-references').click();await page.waitForFunction(()=>window.PYBERT_RUNS.references().length===0);
  if(await page.evaluate(()=>document.querySelector('#work-area').classList.contains('viewer-expanded'))) await page.locator('#expand-viewer').click();
  await page.getByRole('button',{name:'Channel',exact:true}).click();
  await page.locator('[data-file-key="ch_file"]').setInputFiles('C:/Users/yx/.codex/worktrees/pybert-issue4-resources/serial-bus-simulator/docs/webui/issue4/local/resources/example2_THRU.s4p');
  await page.waitForFunction(()=>!document.querySelector('#run').disabled && JSON.parse(localStorage.getItem('pybert-native-snapshot-v2')).config.ch_file==='example2_THRU.s4p');
  await page.screenshot({path:'output/playwright/04-rebound-pam4-before-run.png'});
  return {snapshot:await page.evaluate(()=>JSON.parse(localStorage.getItem('pybert-native-snapshot-v2'))),migration_error:await page.evaluate(()=>window.PYBERT_WORKBENCH.migrationError()),selected:await page.evaluate(()=>window.PYBERT_RUNS.selected()),state:await (await page.request.get('http://127.0.0.1:8770/api/state')).json()};
}
