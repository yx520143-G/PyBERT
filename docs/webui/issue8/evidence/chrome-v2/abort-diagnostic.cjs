async page => {
  await page.evaluate(()=>{
    window.__eqEvents=[];
    for(const name of ['pybert-worker-state','pybert-optimizer-state'])window.addEventListener(name,event=>window.__eqEvents.push({at:performance.now(),name,busy:event.detail.busy,active:event.detail.activeTask ?? event.detail.active_task_id,disabled:document.getElementById('abort-eq').disabled}));
    new MutationObserver(()=>window.__eqEvents.push({at:performance.now(),name:'disabled mutation',disabled:document.getElementById('abort-eq').disabled})).observe(document.getElementById('abort-eq'),{attributes:true,attributeFilter:['disabled']});
  });
  await page.waitForFunction(()=>!document.getElementById('tune-eq').disabled);
  const response=page.waitForResponse(r=>r.url().endsWith('/api/optimizations') && r.request().method()==='POST');
  await page.locator('#tune-eq').click();const start=await(await response).json();
  let error=null;
  try{await page.locator('#abort-eq').click({timeout:8000});}catch(err){error=String(err);}
  await page.waitForTimeout(1000);
  return {start,error,events:await page.evaluate(()=>window.__eqEvents),task:await(await page.request.get('http://127.0.0.1:8774/api/tasks/'+start.task_id)).json()};
}
