/* Deferred-response regressions: no browser, services, or numerical computation. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const deferred=()=>{let resolve,reject;const promise=new Promise((done,fail)=>{resolve=done;reject=fail;});return {promise,resolve,reject};};
const tick=()=>new Promise(done=>setImmediate(done));
function app() {
  const elements=new Map(),events={},requests=[],applications=[];
  let revision=5;
  const element=id=>{if(!elements.has(id))elements.set(id,{value:'',listeners:{},textContent:'',
    addEventListener(type,fn){this.listeners[type]=fn;},replaceChildren(){},add(){},scrollIntoView(){},
    showModal(){this.open=true;},close(){this.open=false;},click(){}});return elements.get(id);};
  const runs={api(path,body){const request={path,body,...deferred()};requests.push(request);return request.promise;},
    revision:()=>revision,optimizationInput:async()=>({config:{rn:.02},runtime_extensions:{},draft_revision:revision}),
    optimizerAction:async()=>{const source_draft_revision=revision,result=await runs.api('reset');return {...result,source_draft_revision};},
    applyOptimizer:value=>applications.push(value)};
  const window={PYBERT_RUNS:runs,PYBERT_WORKBENCH:{getDraft:()=>({}),replaceDraft(){}},addEventListener:(name,fn)=>events[name]=fn};
  vm.runInNewContext(fs.readFileSync(require.resolve('../src/pybert/web/static/optimization.js'),'utf8'),{
    window,document:{getElementById:element,addEventListener(){},createElement:()=>({click(){}})},
    Option:class {},Plotly:{purge(){},newPlot(){}},URL:{createObjectURL:()=>'',revokeObjectURL(){}},setTimeout,
    fetch:()=>{const request={path:'download',...deferred()};requests.push(request);return request.promise;}});
  const record=id=>({opt_id:id,status:'succeeded',candidates:[],selected_candidate_id:id+'-winner',
    selected_values:{ctle_db:id==='A'?1:2},requested_input:{rn:.01},runtime_extensions:{}});
  const click=id=>element(id).listeners.click();
  const choose=id=>{element('selected-opt').value=id;element('selected-opt').listeners.change();};
  return {element,events,requests,applications,window,record,click,choose,edit:()=>revision++};
}
(async()=>{
  const a=app();a.choose('A');a.choose('B');
  a.requests[1].resolve(a.record('B'));await tick();
  a.requests[0].resolve(a.record('A'));await tick();
  assert.match(a.window.PYBERT_OPTIMIZER.field('peak_mag_tune'),/获选 B$/);
  a.choose('C');const before=a.requests.length;a.click('use-eq');a.click('save-opt');await tick();
  assert.equal(a.requests.length,before);assert.equal(a.element('use-eq').disabled,true);
  assert.equal(a.element('save-opt').disabled,true);assert.match(a.element('optimizer-status').textContent,/加载完成/);
  const b=app();b.choose('A');b.requests[0].resolve(b.record('A'));await tick();
  b.click('use-eq');await tick();b.edit();b.requests.at(-1).resolve({config:{rn:.02}});await tick();
  assert.equal(b.element('eq-dialog').open,undefined);assert.match(b.element('optimizer-status').textContent,/等待期间/);
  b.click('confirm-use-eq');await tick();assert.equal(b.applications.length,0);
  const c=app();c.choose('A');c.requests[0].resolve(c.record('A'));await tick();
  c.click('use-eq');await tick();c.requests.at(-1).resolve({config:{rn:.02}});await tick();
  assert.equal(c.element('eq-dialog').open,true);c.edit();c.click('confirm-use-eq');await tick();
  assert.equal(c.applications.length,0);assert.match(c.element('optimizer-status').textContent,/预览后/);
  const d=app();d.click('reset-eq');await tick();d.edit();d.requests[0].resolve({config:{rn:.01}});await tick();
  assert.equal(d.applications.length,0);assert.match(d.element('optimizer-status').textContent,/Reset 等待期间/);
  const e=app();e.choose('A');e.requests[0].resolve(e.record('A'));await tick();
  e.click('use-eq');await tick();e.requests.at(-1).resolve({config:{rn:.02}});await tick();
  e.click('confirm-use-eq');await tick();assert.equal(e.applications.length,1);
  assert.match(e.element('optimizer-status').textContent,/已显式应用 A \/ A-winner/);
  const f=app();f.choose('A');f.requests[0].resolve(f.record('A'));await tick();
  f.element('opt-file').files=[{}];f.element('opt-file').listeners.change();await tick();
  f.requests.at(-1).resolve({ok:false,json:async()=>({detail:'Missing or invalid required optimization plot/cursor arrays.'})});await tick();
  assert.equal(f.element('selected-opt').value,'A');assert.match(f.window.PYBERT_OPTIMIZER.field('peak_mag_tune'),/获选 A$/);
  assert.match(f.element('optimizer-status').textContent,/cursor/);assert.equal(f.applications.length,0);
  const g=app();g.choose('A');g.requests[0].resolve(g.record('A'));await tick();
  g.click('use-eq');await tick();g.requests.at(-1).reject(new Error('Use EQ requires matching Rx FFE topology'));await tick();
  assert.equal(g.applications.length,0);assert.equal(g.element('eq-dialog').open,undefined);
  assert.match(g.element('optimizer-status').textContent,/matching Rx FFE topology/);
  console.log('optimizer UI deferred-response checks passed (0 native calls)');
})().catch(error=>{console.error(error);process.exitCode=1;});
