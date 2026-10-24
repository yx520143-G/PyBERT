async (page) => {
  await page.waitForFunction(()=>document.getElementById('selected-opt').value.startsWith('opt-ref-')&&JSON.parse(document.getElementById('optimizer-record').textContent||'{}').status==='succeeded');
  const record=JSON.parse(await page.locator('#optimizer-record').textContent());
  const download=page.waitForEvent('download');
  await page.locator('#save-opt').click();
  await (await download).saveAs('C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v4/OPT-tpe4-reopened-resaved.pybert_opt');
  return {opt_id:record.opt_id,status:record.status,source_run:await page.evaluate(()=>window.PYBERT_RUNS.selected().run_id),selected_record:await page.locator('#selected-opt').inputValue()};
}
