const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../src/pybert/web/static/workbench.js'), 'utf8');
const flush = () => new Promise(resolve => setImmediate(resolve));

// Exercise the shipped workbench's event/API boundary with a deliberately slow
// normalize response. No browser, numerical engine or timing-dependent sleeps.
async function workbench() {
  const defaults = {mod_type:'NRZ', bit_rate:10, decision_scaler:0.5};
  let draft = structuredClone(defaults), nextTimer = 0, replacements = 0, blurs = 0;
  const elements = new Map(), timers = new Map(), requests = [], stored = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, Object.assign(new EventTarget(), {
      value:'', textContent:'', innerHTML:'', disabled:false, inert:false, hidden:false,
      style:{}, classList:{toggle(){}, remove(){}, contains(){return false;}},
      querySelectorAll(){return [];}, scrollIntoView(){},
    }));
    return elements.get(id);
  }
  const settings = {
    defaults:structuredClone(defaults), clone:structuredClone,
    fields:Object.fromEntries(Object.keys(defaults).map(key => [key, {}])),
    tableInfo:{tx_tap_tuners:{}}, fieldError:()=>'', tableError:()=>'',
  };
  const ui = {
    getDraft:()=>structuredClone(draft), getStage:()=> 'source', migrationError:()=>'',
    hasSavedDraft:()=>false, setSources(){}, setDefaults(){},
    replaceDraft(value){draft=structuredClone(value); replacements++;},
  };
  const window = Object.assign(new EventTarget(), {PYBERT_SETTINGS:settings, PYBERT_WORKBENCH:ui});
  const result = config => ({config, runtime_extensions:{version:1, values:{}}, runtime_defaults:{}, warnings:[], input_hash:JSON.stringify(config)});
  const response = value => ({ok:true, json:async()=>value});
  const context = {
    window, CustomEvent, structuredClone,
    document:{getElementById:element, activeElement:{blur(){blurs++;}}, addEventListener(){}},
    localStorage:{getItem:key=>stored.get(key) ?? null, setItem:(key,value)=>stored.set(key,value)},
    Plotly:{purge(){}},
    setTimeout(callback,delay){const id=++nextTimer; timers.set(id,{callback,delay}); return id;},
    clearTimeout:id=>timers.delete(id),
    async fetch(url, options) {
      const body = options?.body ? JSON.parse(options.body) : undefined;
      if (url === '/api/version') return response({});
      if (url === '/api/state') return response({runs:[], references:[], com_tasks:[]});
      if (url === '/api/normalize' && body.mode === 'defaults') return response(result(defaults));
      if (url === '/api/normalize') return new Promise(resolve => requests.push({body, resolve}));
      throw new Error(`Unexpected request: ${url}`);
    },
  };
  vm.runInNewContext(source, context, {filename:'workbench.js'});
  await flush();
  return {
    element, requests, stored, result, response,
    draft:()=>draft, replacements:()=>replacements, blurs:()=>blurs,
    edit(value, commit=true) {
      if (element('inspector').inert) return false;
      draft.mod_type=value;
      window.dispatchEvent(new CustomEvent('pybert-draft', {detail:{commit}}));
      return true;
    },
    async validate() {
      const entry = [...timers].findLast(([,timer])=>timer.delay===200);
      assert.ok(entry, 'a committed draft must schedule validation');
      timers.delete(entry[0]); entry[1].callback(); await flush();
    },
    async finish(index, value, ok=true) {
      requests[index].resolve({ok, json:async()=>value}); await flush();
    },
  };
}

for (const staleFailure of [false, true]) test(`rapid modulation edits survive a stale ${staleFailure ? 'failed' : 'successful'} validation`, async () => {
  const env = await workbench();
  env.edit('PAM-4'); await env.validate();
  assert.equal(env.requests.length, 1);
  assert.equal(env.element('inspector').inert, false, 'background validation must not swallow the next click');
  assert.equal(env.blurs(), 0, 'background validation must not steal editing focus');
  assert.equal(env.element('run').disabled, true);
  assert.equal(env.element('save-config').disabled, true);
  const rendered = env.replacements();
  assert.equal(env.edit('NRZ'), true);
  await env.validate();
  assert.equal(env.requests.length, 1, 'keep a single native validation in flight');
  const old = staleFailure ? {detail:'obsolete draft rejected'} : env.result({mod_type:'PAM-4', bit_rate:10, decision_scaler:1/6});
  await env.finish(0, old, !staleFailure);
  assert.equal(env.draft().mod_type, 'NRZ');
  assert.equal(env.replacements(), rendered, 'old responses must not replace the newer draft');
  assert.equal(env.element('input-status').textContent, '');
  await env.validate();
  assert.equal(env.requests.length, 2, 'validate the latest committed selection after the old request exits');
  assert.equal(env.requests[1].body.patches.at(-1).value, 'NRZ');
  const latest = {mod_type:'NRZ', bit_rate:10, decision_scaler:0.5};
  await env.finish(1, env.result(latest));
  assert.deepEqual(env.draft(), latest);
  assert.equal(env.replacements(), rendered+1);
  assert.equal(env.element('run').disabled, false);
  assert.deepEqual(JSON.parse(env.stored.get('pybert-native-snapshot-v2')).config, latest);
});

test('a current validation error remains visible and does not discard the draft', async () => {
  const env = await workbench();
  env.edit('PAM-4'); await env.validate();
  await env.finish(0, {detail:'current draft rejected'}, false);
  assert.equal(env.draft().mod_type, 'PAM-4');
  assert.match(env.element('input-status').textContent, /current draft rejected/);
  assert.equal(env.element('inspector').inert, false);
});

test('explicit save still locks and validates an immutable input', async () => {
  const env = await workbench();
  env.edit('PAM-4');
  env.element('save-config').dispatchEvent(new Event('click'));
  await flush();
  assert.equal(env.element('inspector').inert, true);
  assert.equal(env.edit('NRZ'), false);
  assert.equal(env.requests[0].body.patches.at(-1).value, 'PAM-4');
  await env.finish(0, {detail:'save validation rejected'}, false);
  assert.match(env.element('config-status').textContent, /save validation rejected/);
  assert.equal(env.element('inspector').inert, false);
});
