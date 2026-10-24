/* Exercise stable field migration without changing browser storage or running an engine. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const window={},ctx=vm.createContext({window});
for(const file of ['settings.js','draft.js']) vm.runInContext(fs.readFileSync(path.join(__dirname,'../src/pybert/web/static',file),'utf8'),ctx);
const original={schema:1,commit:'1bc905d577d2f3bd9471421cfbf3d422d4e6080e',values:{bit_rate:25,vod:1.25,new_feature:{gain:3},nbits:'bad'}};
const migrated=window.PYBERT_DRAFT.migrate(original);
assert.equal(migrated.values.bit_rate,25);assert.equal(migrated.values.vod,1.25);
assert.equal(migrated.retained.new_feature.value.gain,3);assert.equal(migrated.retained.nbits.value,'bad');
const reordered={schema:2,sources:{adapter_sha:'a'.repeat(40)},values:{vod:1.25,bit_rate:25},retained_fields:migrated.retained};
const current=window.PYBERT_DRAFT.migrate(reordered);
assert.equal(current.values.vod,1.25);assert.equal(current.values.bit_rate,25);
assert.deepEqual(current.retained,migrated.retained);
assert.throws(()=>window.PYBERT_DRAFT.migrate({schema:999,values:{bit_rate:50}}),/schema/);
assert.throws(()=>window.PYBERT_DRAFT.migrate({schema:2,values:null}),/schema/);
console.log('PASS: v1→v2 field-ID migration, catalog order independence, retained unsupported/invalid values, unknown schema refusal.');
