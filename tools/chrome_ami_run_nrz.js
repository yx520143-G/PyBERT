async (page) => {
  await page.getByRole('button',{name:'Run',exact:true}).click();
  await page.waitForFunction(()=>window.PYBERT_RUNS.selected()?.status==='succeeded',null,{timeout:60000});
  const run=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'保存所选结果',exact:true}).click();
  await (await download).saveAs('C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v3/nrz.pybert_run');
  await page.getByRole('button',{name:'Rx CTLE',exact:true}).first().click();
  await page.screenshot({path:'C:/Users/yx/.codex/worktrees/pybert-issue10-ami/serial-bus-simulator/docs/webui/issue10/evidence/chrome-v3/nrz-response.png'});
  return {run_id:run.run_id,input_identity_hash:run.input_identity_hash,summary:run.summary,branch:run.ami.actual_branch,
    wrappers:run.ami.library_calls.length,dll_calls:run.ami.dll_calls.reduce((a,r)=>(a[r.method]=(a[r.method]||0)+1,a),{})};
}
