async (page) => {
  const source=await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id);
  const download=page.waitForEvent('download');
  await page.locator('#save-results').click();
  await (await download).saveAs('C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v4/nrz-reopened-resaved.pybert_run');
  await page.locator('#selected-opt').selectOption('283457ea-cc74-455e-a92a-8940cf84a2ab');
  await page.waitForFunction(()=>JSON.parse(document.getElementById('optimizer-record').textContent||'{}').status==='failed');
  const failure=await page.locator('#optimizer-provenance').textContent();
  if(await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id)!==source)throw new Error('Failed optimization replaced successful run');
  await page.locator('#optimizer-provenance').scrollIntoViewIfNeeded();
  await page.screenshot({path:'C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v4/failed-opt-retains-run.png'});
  await page.locator('#open-opt').click();
  return {source_run:source,failure};
}
