/* Execute the shipped modal against first-match DOM IDs; no models or workers. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function harness(clocks=false){
  const all=[],events=new Map();
  function element(id=''){
    const e={id,value:'',checked:false,disabled:false,open:false,children:[],textContent:'',
      querySelectorAll(){return [];},showModal(){this.open=true;},close(){this.open=false;},after(){}};
    Object.defineProperty(e,'innerHTML',{set(html){this.children=[];for(const m of html.matchAll(/id="([^"]+)"/g)){const child=element(m[1]);this.children.push(child);all.push(child);}}});
    return e;
  }
  const main=element('ami-clocks');main.checked=clocks;all.push(main,element('resources-open'));
  let draft={config:{tx_sel:'native',tx_eq_sel:'Native',tx_use_getwave:false,tx_use_ts4:false,
    rx_sel:'ibis',rx_eq_sel:'IBIS-AMI',rx_use_getwave:true,rx_use_ts4:false},
    runtime_extensions:{version:1,values:{rx_use_clocks:clocks}},resource_bindings:{}};
  let submitted;
  const window={addEventListener:(name,cb)=>events.set(name,cb),PYBERT_RUNS:{
    modelDraft:()=>structuredClone(draft),configureModel:async input=>{
      submitted=structuredClone(input);draft=structuredClone(input);main.checked=input.runtime_extensions.values.rx_use_clocks;return {ami_models:{}};
    }}};
  const document={getElementById:id=>all.find(e=>e.id===id),createElement:()=>element(),body:{append:e=>all.push(e)},addEventListener(){}};
  vm.runInNewContext(fs.readFileSync('src/pybert/web/static/ami.js','utf8'),{window,document,structuredClone});
  events.get('pybert-worker-state')({detail:{busy:false}});
  const dialog=document.getElementById('ami-dialog');
  return {main,window,all,child:id=>dialog.children.find(e=>e.id===id),
    modalClock:()=>dialog.children.find(e=>e.id==='ami-modal-clocks'||e.id==='ami-clocks'),
    submitted:()=>submitted};
}
(async()=>{
  const outcomes=[];
  for(const [name,run] of [
    ['unique IDs',async()=>{const h=harness();assert.equal(new Set(h.all.filter(e=>e.id).map(e=>e.id)).size,h.all.filter(e=>e.id).length);}],
    ['Rx modal submits its own clock request',async()=>{const h=harness();h.window.PYBERT_AMI.open('rx');h.modalClock().checked=true;await h.child('ami-apply').onclick();assert.equal(h.submitted().runtime_extensions.values.rx_use_clocks,true);assert.equal(h.main.checked,true);}],
    ['main request initializes Rx modal',async()=>{const h=harness(true);h.window.PYBERT_AMI.open('rx');assert.equal(h.modalClock().checked,true);}],
    ['Tx rendering leaves Rx main enabled',async()=>{const h=harness();h.window.PYBERT_AMI.open('tx');assert.equal(h.main.disabled,false);assert.equal(h.modalClock().disabled,true);}],
    ['Tx Apply preserves Rx request',async()=>{const h=harness(true);h.window.PYBERT_AMI.open('tx');h.modalClock().checked=false;await h.child('ami-apply').onclick();assert.equal(h.submitted().runtime_extensions.values.rx_use_clocks,true);}]
  ]){try{await run();outcomes.push({name,passed:true});}catch(error){outcomes.push({name,passed:false,error:error.message});}}
  console.log(JSON.stringify(outcomes,null,2));if(outcomes.some(r=>!r.passed))process.exitCode=1;
})();
