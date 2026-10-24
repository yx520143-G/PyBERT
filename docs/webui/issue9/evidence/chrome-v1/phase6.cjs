async page => {
  const root='C:/Users/yx/.codex/worktrees/pybert-issue9-viterbi/serial-bus-simulator';
  const assert=(ok,message)=>{if(!ok)throw new Error(message);};
  const before=await(await page.request.get('http://127.0.0.1:8776/api/state')).json();
  await page.waitForFunction(()=>document.getElementById('config-status').textContent.includes('V-PAM4-ISI.yaml')&&!document.getElementById('run').disabled);
  await page.getByRole('button',{name:'Viterbi / MLSD',exact:true}).click();
  await page.locator('#control-rx_viterbi_symbols').fill('4');await page.locator('#control-rx_viterbi_symbols').press('Tab');
  await page.waitForFunction(()=>document.getElementById('input-status').textContent.includes('N=4')&&!document.getElementById('run').disabled);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/runs')&&r.request().method()==='POST');
  await page.locator('#run').click();const budget=await response;
  assert(budget.status()===422,'PAM4 default N4 must refuse whole-window budget');
  const budgetBody=await budget.json();assert(budgetBody.detail.includes('budget'),'wrong reason');
  const afterBudget=await(await page.request.get('http://127.0.0.1:8776/api/state')).json();
  const latest=await(await page.request.get('http://127.0.0.1:8776/api/tasks/'+afterBudget.current_task_id)).json();
  assert(latest.operation==='normalize'&&!afterBudget.active_task_id&&JSON.stringify(afterBudget.runs.map(r=>r.run_id))===JSON.stringify(before.runs.map(r=>r.run_id)),'budget launched numerical Run worker');
  assert(await page.locator('#control-rx_viterbi_symbols').inputValue()==='4','N was silently reduced');
  await page.screenshot({path:root+'/output/playwright/issue9/10-default-N4-budget-refusal.jpg'});
  await page.locator('#control-rx_viterbi_symbols').fill('0');await page.locator('#control-rx_viterbi_symbols').press('Tab');
  await page.locator('#run').click();
  await page.waitForFunction(()=>document.getElementById('input-status').textContent.includes('最小值'));
  const invalid=await page.locator('#input-status').innerText();
  await page.locator('#control-rx_viterbi_symbols').fill('2');await page.locator('#control-rx_viterbi_symbols').press('Tab');
  await page.waitForFunction(()=>!document.getElementById('run').disabled&&document.getElementById('input-status').textContent.includes('N=2'));
  const fec=await page.request.post('http://127.0.0.1:8776/api/normalize',{data:{mode:'load',yaml:'rx_viterbi_fec: true\n'}});
  const fecBody=await fec.json();assert(fec.status()===422&&fecBody.detail.includes('unsupported_native_fec'),'FEC silently ignored');
  const selected=await page.evaluate(()=>window.PYBERT_RUNS.selected());
  const fecRun=await page.request.post('http://127.0.0.1:8776/api/runs',{data:{config:selected.effective_input,input_hash:selected.input_hash,rx_viterbi_fec:true}});
  assert(fecRun.status()===422&&(await fecRun.json()).detail.includes('unsupported_native_fec'),'API FEC accepted');
  const ami=await page.request.post('http://127.0.0.1:8776/api/normalize',{data:{mode:'load',config:{...selected.effective_input,rx_eq_sel:'IBIS-AMI'}}});
  assert(ami.status()===422&&(await ami.json()).detail.includes('#10'),'AMI decoding accepted');
  assert(await page.evaluate(()=>window.PYBERT_RUNS.selected()?.run_id)===selected.run_id,'rejection replaced success');
  return {budget:{status:budget.status(),body:budgetBody,N_retained:4,worker_started:false},invalid,
    fec:{status:fec.status(),body:fecBody},api_fec_status:fecRun.status(),ami_status:ami.status(),selected_run:selected.run_id,
    checks:{defaultN_budget:true,invalidN:true,unsupported_FEC:true,AMI_boundary:true,old_success_retained:true,no_new_main:true}};
}
