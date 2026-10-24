async (page) => {
  const run=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  const name=run.effective_input.mod_type==='PAM-4'?'pam4':'nrz';
  const results=[];
  await page.getByRole('button',{name:'Rx CTLE',exact:true}).first().click();
  await page.locator('#analysis-point').selectOption('ctle');
  for(const [kind,type,title,x,y] of [
    ['response','H','ctle_out_H','GHz','dB'],
    ['eye',null,'Rx AMI output eye','ps','V'],
    ['jitter.dist',null,'Rx AMI output · dist','ps','1/ps']
  ]) {
    await page.locator('#analysis-kind').selectOption(kind);
    if(type)await page.locator('#response-type').selectOption(type);
    await page.waitForFunction(({id,kind,title,x,y})=>{
      const p=document.getElementById('plot');
      return window.PYBERT_RUNS.selected()?.run_id===id&&document.getElementById('analysis-kind').value===kind&&
        p.layout?.title?.text?.includes(title)&&p.layout.xaxis.title.text===x&&
        p.layout.yaxis.title.text===y&&p.data?.length>0&&
        (kind!=='eye'||p.data.some(t=>t.type==='heatmap'))&&document.getElementById('analysis-info').textContent.includes(id);
    },{id:run.run_id,kind,title,x,y});
    await page.locator('#plot').scrollIntoViewIfNeeded();
    await page.screenshot({path:`C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v4/${name}-${kind.replace('.','-')}-verified.png`});
    results.push(await page.locator('#plot').evaluate(p=>({title:p.layout.title.text,x:p.layout.xaxis.title.text,y:p.layout.yaxis.title.text,types:p.data.map(t=>t.type)})));
  }
  return {run_id:run.run_id,viewport:page.viewportSize(),results};
}
