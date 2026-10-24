async (page) => {
  const id=await page.evaluate(()=>window.PYBERT_RUNS.selected().record_id);
  await page.reload();await page.waitForFunction(id=>window.PYBERT_RUNS?.selected()?.record_id===id,id);
  const status=await page.locator('#results-status').textContent();
  if(status.includes('当前不可用') || status.includes('正在查询'))throw new Error('Valid restored record retains speculative unavailable message');
  await page.screenshot({path:'output/playwright/23-existing-selection-confirmed.png'});
  return {record_id:id,restored_status:status,main_calls:0,COM_calls:0};
}
