async (page) => {
  await page.getByRole('button',{name:'选择 / 检查模型',exact:true}).click();
  await page.waitForFunction(()=>!document.getElementById('ami-apply').disabled&&document.getElementById('ami-status').textContent.startsWith('ready'));
  const draft=await page.evaluate(()=>window.PYBERT_RUNS.modelDraft());
  await page.getByRole('button',{name:'关闭',exact:true}).click();
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Save',exact:true}).click();
  await (await download).saveAs('C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v3/saved-nrz.yaml');
  return {draft,viewport:page.viewportSize(),saved:'saved-nrz.yaml'};
}
