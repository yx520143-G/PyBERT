/* Exercise shipped app/workbench reset and undo handlers without observers or numerical workers. */
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=path.join(__dirname,'..'),directory=path.join(root,'src/pybert/web/static');
const original=JSON.parse(fs.readFileSync(path.join(root,'docs/webui/issue5/evidence/chrome-raw-audit-20261024-110155/NRZ-manifest.json'),'utf8'));
function harness(savedDraft) {
  const elements=new Map(),events=new Map(),storage=new Map([['pybert-native-draft-v2',savedDraft]]);
  const element=id=>{if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',style:{},listeners:{},classList:{toggle(){},contains(){return false;}},querySelector(){return null;},querySelectorAll(){return [];},addEventListener(type,callback){this.listeners[type]=callback;}});return elements.get(id);};
  let bindings={ch_file:original.resource_bindings.ch_file};
  const window={PYBERT_NATIVE:true,addEventListener(type,callback){if(!events.has(type))events.set(type,[]);events.get(type).push(callback);},dispatchEvent(event){for(const callback of events.get(event.type)||[])callback(event);}};
  window.PYBERT_RESOURCES={bindings:()=>JSON.parse(JSON.stringify(bindings)),pending:()=>false,restore(value){bindings=JSON.parse(JSON.stringify(value));}};
  const context=vm.createContext({window,CustomEvent:class {constructor(type,options){this.type=type;this.detail=options.detail;}},location:{hash:''},localStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},document:{getElementById:element,addEventListener(){}},setTimeout(){return 1;},clearTimeout(){}});
  for(const file of ['catalog.js','settings.js','draft.js','gui-map.js'])vm.runInContext(fs.readFileSync(path.join(directory,file),'utf8'),context);
  let app=fs.readFileSync(path.join(directory,'app.js'),'utf8');
  app=app.replace(/  renderGuiIndex\(\);\r?\n  renderStage\(\);/,'  renderMap=renderOverview=renderSettings=updateFieldFeedback=renderStage=()=>{};');
  vm.runInContext(app,context);
  let workbench=fs.readFileSync(path.join(directory,'workbench.js'),'utf8');
  workbench=workbench.replace('  init().catch(inputError);',`  window.resetTest={seed:run=>{
    base=clone(run.requested_input);captured=clone(base);patches=[];runtimeExtensions=clone(run.runtime_extensions);
    sourceRecordId='ref-original';replayGuard={version:1,source_run_id:run.run_id,resource_hash:run.resource_hash,resources:clone(run.resources)};
    constructedConfig={...clone(base),ch_file:'',inter_sel:'native'};constructedRuntime={version:1,values:{rlm:.5,rx_use_clocks:true,ami_opt_trials:7}};
    ui.replaceDraft({...ui.getDraft(),...toDraft(base)});
  },nativeRecovery:()=>{snapshotRecoveryRequired=true;},snapshot:()=>({base,captured,patches,runtimeExtensions,sourceRecordId,replayGuard,snapshotRecoveryRequired,resource_bindings:resourceBindings()})};`);
  vm.runInContext(workbench,context);window.resetTest.seed(original);
  return {window,storage,click:id=>element(id).listeners.click(),snapshot:()=>JSON.parse(JSON.stringify(window.resetTest.snapshot()))};
}
const plain=JSON.stringify({schema:2,values:{bit_rate:25}}),archive=harness(plain);
const before=archive.snapshot(),draft=archive.window.PYBERT_WORKBENCH.getDraft();
archive.click('reset-draft');assert.equal(archive.snapshot().replayGuard,null);
archive.click('undo-reset');assert.deepEqual(archive.snapshot(),before);assert.deepEqual(archive.window.PYBERT_WORKBENCH.getDraft(),draft);
const persisted=JSON.parse(archive.storage.get('pybert-native-snapshot-v2'));
assert.deepEqual(persisted.replay_guard,before.replayGuard);assert.deepEqual(persisted.resource_bindings,before.resource_bindings);
assert.deepEqual(persisted.runtime_extensions,before.runtimeExtensions);assert.equal(persisted.source_record_id,'ref-original');
const retained=harness(JSON.stringify({schema:2,values:{bit_rate:25},retained_fields:{future_physical_input:{value:{gain:123},blocking:false}}}));
assert(retained.window.PYBERT_WORKBENCH.migrationError());
retained.click('reset-draft');assert.equal(retained.window.PYBERT_WORKBENCH.migrationError(),null);
retained.click('undo-reset');assert(retained.window.PYBERT_WORKBENCH.migrationError());
assert.equal(JSON.parse(retained.storage.get('pybert-native-draft-v2')).retained_fields.future_physical_input.value.gain,123);
const broken=harness('invalid JSON');broken.storage.set('pybert-native-snapshot-v2','invalid snapshot');broken.window.resetTest.nativeRecovery();
broken.click('reset-draft');broken.click('undo-reset');
assert(broken.window.PYBERT_WORKBENCH.migrationError());assert.equal(broken.storage.get('pybert-native-draft-v2'),'invalid JSON');
assert.equal(broken.storage.get('pybert-native-snapshot-v2'),'invalid snapshot');assert.equal(broken.snapshot().snapshotRecoveryRequired,true);
console.log('PASS: real archived inputs/runtime/resource bindings/replay guard survive reset+undo; unknown retained input and invalid draft/native storage recover their original blocking state. No observers/main/COM.');
