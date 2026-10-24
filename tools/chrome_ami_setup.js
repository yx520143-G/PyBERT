async (page) => {
  await page.waitForFunction(() => !document.getElementById('run').disabled);
  await page.getByRole('button', {name:'IBIS / AMI', exact:true}).click();
  await page.getByRole('combobox', {name:'Side', exact:true}).selectOption('rx');
  await page.getByRole('textbox', {name:'本机模型完整目录', exact:true}).fill('C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/models/ibisami');
  await page.getByRole('button', {name:'登记目录', exact:true}).click();
  await page.waitForFunction(() => document.getElementById('ami-resource-identity').textContent.includes('待绑定'));
  await page.getByRole('button', {name:'选择 / 检查模型', exact:true}).click();
  await page.waitForFunction(() => document.getElementById('ami-status').textContent.startsWith('ready'));
  return await page.locator('#ami-status').textContent();
}
