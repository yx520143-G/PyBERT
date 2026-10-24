/* Exercise the shipped product handlers with a failing storage adapter, independently of native workers. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const elements = new Map();
const element = id => {
  if (id.startsWith('settings-table-')) return null;
  if (!elements.has(id)) elements.set(id, {innerHTML:'',listeners:{},classList:{toggle(){}},querySelector(){return null;},addEventListener(type,callback){this.listeners[type]=callback;}});
  return elements.get(id);
};
const storage={value:null,fail:false,getItem(){return this.value;},setItem(_key,value){if(this.fail)throw new Error('Injected storage failure');this.value=value;}};
const window={PYBERT_NATIVE:true,addEventListener(){},dispatchEvent(){}};
const context=vm.createContext({window,CustomEvent:class {},location:{hash:''},localStorage:storage,document:{getElementById:element,addEventListener(){}}});
const directory=path.join(__dirname,'../src/pybert/web/static');
for (const file of ['catalog.js','settings.js','draft.js','gui-map.js']) vm.runInContext(fs.readFileSync(path.join(directory,file),'utf8'),context);
const source=fs.readFileSync(path.join(directory,'app.js'),'utf8');
const bootstrap=/  renderGuiIndex\(\);\r?\n  renderStage\(\);/;
assert(bootstrap.test(source));
vm.runInContext(source.replace(bootstrap,`
  renderMap = renderOverview = () => {};
  renderSettings = updateFieldFeedback = updateDraftStatus;
  window.storageTest = {editField};
`),context);
function edit(value){window.storageTest.editField({dataset:{setting:'bit_rate'},type:'number',value:String(value)},true);}
edit(11);
const previous=storage.value;
storage.fail=true;edit('');
assert.match(element('draft-status').innerHTML,/待修正/);
assert.match(element('draft-status').innerHTML,/仅当前页面保留/);
assert.equal(storage.value,previous);
edit(12);
assert.doesNotMatch(element('draft-status').innerHTML,/待修正/);
assert.match(element('draft-status').innerHTML,/仅当前页面保留/);
storage.fail=false;edit('');
assert.match(element('draft-status').innerHTML,/待修正/);
assert.match(element('draft-status').innerHTML,/草稿已保留/);
console.log('PASS: shipped Native product distinguishes input errors, failed storage, and independent recovery.');
