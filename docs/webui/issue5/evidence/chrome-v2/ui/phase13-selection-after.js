async (page) => {
  await page.waitForFunction(()=>document.querySelector('#results-status').textContent.includes('当前不可用'));
  const storageBefore=await page.evaluate(()=>localStorage.getItem('pybert-result-selection-v1'));
  await page.reload();await page.waitForFunction(()=>document.querySelector('#results-status').textContent.includes('当前不可用'));
  const after=await page.evaluate(()=>({storage:localStorage.getItem('pybert-result-selection-v1'),message:document.querySelector('#results-status').textContent,selected:window.PYBERT_RUNS.selected()?.record_id}));
  if(storageBefore!==after.storage || after.selected)throw new Error('Restart lost unavailable identity or invented a result');
  await page.locator('#result-actions').scrollIntoViewIfNeeded();await page.screenshot({path:'output/playwright/24-restart-reload-unavailable-confirmed.png'});
  const state=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  if(state.runs.length || state.references.length || state.com_tasks.length || state.resources.length)throw new Error('Restart restored unavailable records');
  return {storageBefore,after,state,main_calls:0,COM_calls:0};
}
