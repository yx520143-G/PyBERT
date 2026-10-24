async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue8-optimizer/serial-bus-simulator',base='http://127.0.0.1:8775/api/';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  const response=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/references'&&r.request().method()==='POST');
  await page.locator('#results-file').setInputFiles(root+'/output/playwright/issue8/PAM4-RLM080.pybert_run');
  assert((await response).status()===201,'Second Run archive rejected');
  await page.locator('#config-file').setInputFiles(root+'/output/playwright/issue8/used-reset.yaml');
  await page.waitForFunction(()=>document.getElementById('config-status').textContent.includes('已载入 used-reset.yaml'));
  const restored=await page.evaluate(()=>window.PYBERT_WORKBENCH.getDraft());
  assert(restored.rlm===.8&&restored.rn===.02,'YAML runtime/current edits lost');
  const save=page.waitForEvent('download');await page.locator('#save-config').click();await(await save).saveAs(root+'/output/playwright/issue8/final/used-reset-final.yaml');
  const forged=await page.request.post(base+'normalize',{data:{mode:'use_eq',config:{},optimization:{status:'succeeded'}}});
  assert(forged.status()===422,'Generic normalize accepts forged Use action');
  const state=await(await page.request.get(base+'state')).json();
  assert(state.runs.length===0&&state.optimizations.length===4&&state.references.length===2,'Recovery created computed result');
  return {browser:page.context().browser().version(),viewport:page.viewportSize(),checks:{Run_references:2,YAML_RLM080_Rn002:true,forged_use_rejected:true,no_computed_runs:true},new_coopt:0,new_main:0,new_COM:0};
}
