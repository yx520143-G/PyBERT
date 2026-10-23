/* Read-only coverage check against the real TraitsUI view, without importing PyBERT. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const window = {};
for (const name of ['catalog', 'settings', 'gui-map']) vm.runInNewContext(fs.readFileSync(path.join(__dirname, name + '.js'), 'utf8'), {window});
const source = fs.readFileSync(path.join(__dirname, '../../../src/pybert/gui/view.py'), 'utf8').replace(/^[\t ]*#.*$/gm, line => ' '.repeat(line.length));
const matches = [...source.matchAll(/\bItem\(\s*(?:name\s*=\s*)?["'](\w+)["']/g)];
const controls = matches.map(match => match[1]);
assert.equal(controls.length, new Set(controls).size, 'Unexpected duplicate GUI control');
assert.deepEqual([...window.PYBERT_GUI.items.map(item => item.key)].sort(), controls.sort(), 'GUI inventory drift');
const s = window.PYBERT_SETTINGS;
const params = window.PYBERT_CATALOG.stages.flatMap(stage => stage.groups.flatMap(group => group.params));
const missing = controls.filter(key => !['btn_disable','btn_enable'].includes(key) && !params.some(param => s.keysFor(param).includes(key) || param.key === key));
assert.deepEqual(missing, [], 'GUI controls missing from catalog/editor');
for (const item of window.PYBERT_GUI.items) assert.match(source.split('\n')[item.line-1], /Item\(/, `Source line drift: ${item.key}`);
assert.equal(s.disabledReason('cac', s.defaults), '');
assert.equal(s.disabledReason('peak_freq', {...s.defaults,ctle_enable:false}), '');
assert.notEqual(s.disabledReason('ctle_sel', {...s.defaults,ctle_enable:false}), '');
assert.equal(s.disabledReason('rlm', {...s.defaults,mod_type:'PAM-4',use_mmse:false}), '');
assert(s.tableInfo.tx_tap_tuners.columns.includes('value'));
assert(s.tableInfo.ffe_tap_tuners.readonly.includes('enabled'));
assert(s.tableInfo.ffe_tap_tuners.readonly.includes('value'));
assert(s.tableInfo.dfe_tap_tuners.readonly.includes('value'));
for (const [key, info] of Object.entries(s.tableInfo)) {
  const index = matches.findIndex(match => match[1] === key);
  const block = source.slice(matches[index].index, matches[index + 1].index);
  const columns = [...block.matchAll(/ObjectColumn\(([^)]*)\)/g)].map(match => ({
    name: match[1].match(/name\s*=\s*["'](\w+)["']/)[1],
    readonly: /editable\s*=\s*False|style\s*=\s*["']readonly["']/.test(match[1])
  }));
  assert.deepEqual(['name', ...info.columns], columns.map(column => column.name), `GUI table columns: ${key}`);
  assert.deepEqual([...(info.readonly || [])], columns.filter(column => column.readonly && column.name !== 'name').map(column => column.name), `GUI read-only columns: ${key}`);
}
const old = s.clone(s.defaults);
delete old.tx_tap_tuners[0].value;
const restored = s.restore(old);
assert.equal(restored.tx_tap_tuners[0].value, 0, 'Old drafts must gain missing columns without losing data');
console.log(`PASS: ${controls.length} GUI controls inventoried and mapped; conditions, table columns and draft compatibility checked. No simulation executed.`);
