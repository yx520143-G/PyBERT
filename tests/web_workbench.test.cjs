const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../src/pybert/web/static/workbench.js'), 'utf8');
const flush = () => new Promise(resolve => setImmediate(resolve));

// Exercise the shipped workbench's event/API boundary with a deliberately slow
// normalize response. No browser, numerical engine or timing-dependent sleeps.
async function workbench(records=[]) {
  const defaults = {mod_type:'NRZ', bit_rate:10, decision_scaler:0.5};
  let draft = structuredClone(defaults), nextTimer = 0, replacements = 0, blurs = 0;
  const elements = new Map(), timers = new Map(), requests = [], stored = new Map();
  const resultRequests = [], renderedPlots = new Map();
  const state = {runs:records, references:[], com_tasks:[]};
  function element(id) {
    if (!elements.has(id)) elements.set(id, Object.assign(new EventTarget(), {
      value:'', textContent:'', innerHTML:'', disabled:false, inert:false, hidden:false,
      style:{}, classList:{toggle(){}, add(){}, remove(){}, contains(){return false;}},
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
    Plotly:{purge(id){renderedPlots.delete(id);}, async newPlot(id, data){renderedPlots.set(id, structuredClone(data));}},
    setTimeout(callback,delay){const id=++nextTimer; timers.set(id,{callback,delay}); return id;},
    clearTimeout:id=>timers.delete(id),
    async fetch(url, options) {
      const body = options?.body ? JSON.parse(options.body) : undefined;
      if (url === '/api/version') return response({});
      if (url === '/api/state') return response(state);
      if (url.startsWith('/api/runs/') || url.startsWith('/api/tasks/')) return new Promise(resolve => resultRequests.push({url, resolve}));
      if (url === '/api/normalize' && body.mode === 'defaults') return response(result(defaults));
      if (url === '/api/normalize') return new Promise(resolve => requests.push({body, resolve}));
      throw new Error(`Unexpected request: ${url}`);
    },
  };
  element('analysis-kind').value='paired';
  element('analysis-point').value='chnl';
  vm.runInNewContext(source, context, {filename:'workbench.js'});
  await flush();
  return {
    element, requests, stored, result, response, resultRequests, renderedPlots, state,
    select:id=>window.PYBERT_RUNS.select(id), refresh:()=>window.PYBERT_RUNS.refresh(),
    selected:()=>window.PYBERT_RUNS.selected(),
    async finishResult(index, value) {resultRequests[index].resolve(response(value)); await flush();},
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

const run = id => ({run_id:id, kind:'temporary', input_hash:id, analysis_version:2,
  effective_input:{mod_type:'NRZ'}, logs:[], plots:{chnl_h:{}, 'eye.chnl':{}, tx_out_h:{}, 'eye.tx':{}}});
const chart = label => ({data:[{x:[0,1], y:[1,2], name:label}], xunit:'ns', yunit:'V/sample', availability:'available'});

async function displayedRun() {
  const env = await workbench([run('run-a')]);
  await env.finishResult(0, run('run-a'));
  await env.finishResult(1, chart('a-channel'));
  await env.finishResult(2, chart('a-eye'));
  return env;
}

test('paired views show an empty state without fetching or calculating a result', async () => {
  const env = await workbench();
  assert.equal(env.resultRequests.length, 0);
  assert.equal(env.renderedPlots.size, 0);
  for (const id of ['plot','eye-plot']) assert.match(env.element(id).innerHTML, /运行仿真或打开结果存档/);
});

test('a late observation response cannot replace the newer paired view', async () => {
  const env = await displayedRun();
  env.element('analysis-point').value='tx';
  env.element('analysis-point').dispatchEvent(new Event('change'));
  await flush();
  env.element('analysis-point').value='chnl';
  env.element('analysis-point').dispatchEvent(new Event('change'));
  await flush();
  await env.finishResult(5, chart('new-channel'));
  await env.finishResult(6, chart('new-eye'));
  await env.finishResult(3, chart('late-tx'));
  await env.finishResult(4, chart('late-tx-eye'));
  assert.equal(env.renderedPlots.get('plot')[0].name, 'new-channel');
  assert.equal(env.renderedPlots.get('eye-plot')[0].name, 'new-eye');
});

test('a late record response and old plot responses cannot mix paired runs', async () => {
  const env = await displayedRun();
  env.element('analysis-point').value='tx';
  env.element('analysis-point').dispatchEvent(new Event('change'));
  await flush();
  const old = env.select('run-old'), latest = env.select('run-b');
  await env.finishResult(6, run('run-b'));
  await env.finishResult(7, chart('b-tx'));
  await env.finishResult(8, chart('b-eye'));
  await latest;
  await env.finishResult(5, run('run-old'));
  await old;
  await env.finishResult(3, chart('late-a-tx'));
  await env.finishResult(4, chart('late-a-eye'));
  assert.equal(env.selected().run_id, 'run-b');
  assert.equal(env.resultRequests.length, 9, 'obsolete record must not fetch any plots');
  assert.equal(env.renderedPlots.get('plot')[0].name, 'b-tx');
  assert.equal(env.renderedPlots.get('eye-plot')[0].name, 'b-eye');
  assert.match(env.element('analysis-info').innerHTML, /run-b/);
});

test('an unavailable paired eye keeps the available impulse and its reason', async () => {
  const env = await workbench([run('run-a')]);
  await env.finishResult(0, run('run-a'));
  await env.finishResult(1, chart('available-impulse'));
  await env.finishResult(2, {availability:'unavailable', reason:'insufficient_timed_traces'});
  assert.equal(env.renderedPlots.get('plot')[0].name, 'available-impulse');
  assert.equal(env.renderedPlots.has('eye-plot'), false);
  assert.match(env.element('eye-plot').innerHTML, /Too few complete traces/);
});

test('a failed current task leaves the selected successful result intact', async () => {
  const env = await displayedRun();
  env.state.current_task_id='failed-task';
  env.state.active_task_id=null;
  const refresh = env.refresh();
  await flush();
  await env.finishResult(3, {task_id:'failed-task', operation:'run', state:'failed', phase:'failed',
    error:'fixture worker failed', logs:[], worker_exited:true});
  await refresh;
  assert.equal(env.selected().run_id, 'run-a');
  assert.equal(env.renderedPlots.get('plot')[0].name, 'a-channel');
  assert.equal(env.renderedPlots.get('eye-plot')[0].name, 'a-eye');
  assert.match(env.element('task-state').textContent, /fixture worker failed/);
  assert.equal(env.resultRequests.length, 4);
});
