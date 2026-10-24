async (page) => {
  const before=await page.evaluate(()=>window.PYBERT_RUNS.modelDraft());
  await page.getByRole('checkbox',{name:'使用模型 Ts4file',exact:true}).check();
  await page.getByRole('button',{name:'Apply 参数 / 模式到草稿',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('ami-status').textContent.includes('no Ts4file'));
  const ts4=await page.locator('#ami-status').textContent();
  await page.screenshot({path:'C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v3/ts4-blocked.png'});
  if(JSON.stringify(before.config)!==JSON.stringify((await page.evaluate(()=>window.PYBERT_RUNS.modelDraft())).config))throw new Error('Failed model Apply mutated draft');
  await page.getByRole('checkbox',{name:'使用模型 Ts4file',exact:true}).uncheck();
  await page.getByRole('combobox',{name:'Electrical',exact:true}).selectOption('native');
  await page.getByRole('button',{name:'Apply 参数 / 模式到草稿',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('ami-status').textContent.includes('requires an explicit IBIS'));
  const invalid=await page.locator('#ami-status').textContent();
  await page.getByRole('combobox',{name:'Electrical',exact:true}).selectOption('ibis');
  await page.getByRole('button',{name:'选择 / 检查模型',exact:true}).click();
  await page.waitForFunction(()=>document.getElementById('ami-status').textContent.startsWith('ready'));
  await page.screenshot({path:'C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v3/model-ready.png'});
  return {ts4,invalid,draft:await page.evaluate(()=>window.PYBERT_RUNS.modelDraft()),viewport:page.viewportSize()};
}
