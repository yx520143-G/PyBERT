/* Native observer editing defers only cross-field Npre constraints, never numeric validation. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const context = vm.createContext({window:{}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/pybert/web/static/settings.js'),'utf8'),context);
const settings = context.window.PYBERT_SETTINGS;
for (const count of [3,0]) {
  const values = settings.clone(settings.defaults);
  values.rx_n_taps=count; values.rx_n_pre=5;
  assert(settings.fieldError('rx_n_pre',values));
  assert.equal(settings.fieldError('rx_n_pre',values,{deferObserver:true}),'');
  for (const invalid of ['',-1,NaN,Infinity,1.5,100]) {
    values.rx_n_pre=invalid;
    assert(settings.fieldError('rx_n_pre',values,{deferObserver:true}));
  }
}
console.log('PASS: ordered observer edit defers Npre relation; finite/integer/range checks stay strict.');
