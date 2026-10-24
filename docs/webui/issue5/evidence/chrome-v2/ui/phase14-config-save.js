async (page) => {
  await page.waitForFunction(()=>!document.querySelector('#save-config').disabled);
  const before=await (await page.request.get('http://127.0.0.1:8770/api/state')).json();
  const download=page.waitForEvent('download');await page.locator('#save-config').click();await (await download).saveAs('output/playwright/NRZ-final-config.yaml');
  return {original_logical_name:await page.locator('#config-name').textContent(),downloaded:true,old_current_task:before.current_task_id,main_calls:0,COM_calls:0};
}
