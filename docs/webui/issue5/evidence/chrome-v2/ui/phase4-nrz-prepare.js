async (page) => {
  const original=await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id);
  await page.locator('#config-file').setInputFiles('C:/Users/yx/.codex/worktrees/pybert-issue5-archive/serial-bus-simulator/docs/webui/issue5/fixtures/chrome-execution-v1/NRZ.yaml');
  await page.waitForFunction(()=>document.querySelector('#config-name').textContent==='NRZ.yaml' && !document.querySelector('#run').disabled);
  if(await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id)!==original) throw new Error('Config load replaced successful result');
  const download=page.waitForEvent('download');await page.locator('#save-results').click();await (await download).saveAs('output/playwright/PAM4-while-NRZ-draft.pybert_run');
  return {original_selected:original,stale:await page.locator('#stale').innerText(),snapshot:await page.evaluate(()=>JSON.parse(localStorage.getItem('pybert-native-snapshot-v2')))};
}
