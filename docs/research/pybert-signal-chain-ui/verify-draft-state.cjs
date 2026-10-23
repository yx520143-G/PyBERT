/* Exercise real app handlers; DOM rendering is covered separately in Chrome. */
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const {test} = require('node:test');

function app() {
  const elements = new Map();
  const element = id => {
    if (id.startsWith('settings-table-')) return null;
    if (!elements.has(id)) elements.set(id, {
      innerHTML: '', listeners: {}, classList: {toggle() {}}, querySelector() { return null; },
      addEventListener(type, callback) { this.listeners[type] = callback; }
    });
    return elements.get(id);
  };
  const storage = {value: null, fail: false,
    getItem() { return this.value; },
    setItem(key, value) { if (this.fail) throw new Error('Injected storage write failure'); this.value = value; }
  };
  const window = {addEventListener() {}};
  const context = vm.createContext({window, location: {hash: ''}, localStorage: storage,
    document: {getElementById: element, addEventListener() {}}});
  for (const file of ['catalog.js', 'settings.js', 'gui-map.js']) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, file), 'utf8'), context);
  }
  const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  const bootstrap = /  renderGuiIndex\(\);\r?\n  renderStage\(\);/;
  assert(bootstrap.test(source), 'App bootstrap changed; update the test seam');
  vm.runInContext(source.replace(bootstrap, `
    renderMap = renderOverview = () => {};
    renderSettings = updateFieldFeedback = updateDraftStatus;
    window.testApp = {editField, showReset, get draft() { return draft; }};
  `), context);
  const api = window.testApp;
  return {api, storage, settings: window.PYBERT_SETTINGS,
    edit: (key, value) => api.editField({dataset: {setting: key}, type: 'number', value: String(value)}, true),
    undo: () => element('undo-reset').listeners.click(),
    status: () => element('draft-status').innerHTML};
}

const counts = draft => [draft.rx_n_taps, draft.rx_taps.filter(t => t.enabled).length,
  draft.ffe_tap_tuners.filter(t => t.enabled).length];

test('Ntaps edit, field reset, undo and persisted reload agree', () => {
  const a = app();
  a.edit('rx_n_taps', 9);
  assert.deepEqual(counts(a.api.draft), [9, 9, 9]);
  a.api.showReset(['rx_n_taps'], 'reset');
  assert.deepEqual(counts(a.api.draft), [15, 15, 15]);
  assert.deepEqual(counts(a.settings.restore(JSON.parse(a.storage.value).values)), [15, 15, 15]);
  a.undo();
  assert.deepEqual(counts(a.api.draft), [9, 9, 9]);
  assert.deepEqual(counts(a.settings.restore(JSON.parse(a.storage.value).values)), [9, 9, 9]);
});

test('Resetting only the optimizer table derives Enabled without overwriting manual Native taps', () => {
  const a = app();
  a.edit('rx_n_taps', 9);
  a.api.draft.rx_taps[2].enabled = false;
  a.api.showReset(['ffe_tap_tuners'], 'reset');
  assert.deepEqual(counts(a.api.draft), [9, 8, 9]);
  assert.deepEqual(counts(a.settings.restore(JSON.parse(a.storage.value).values)), [9, 8, 9]);
});

test('Storage write failure stays visible alongside invalid input and recovers independently', () => {
  const a = app();
  a.edit('bit_rate', 11);
  const saved = a.storage.value;
  a.storage.fail = true;
  a.edit('bit_rate', '');
  assert.match(a.status(), /待修正/);
  assert.match(a.status(), /仅当前页面保留/);
  assert.equal(a.storage.value, saved);
  a.edit('bit_rate', 12);
  assert.doesNotMatch(a.status(), /待修正/);
  assert.match(a.status(), /仅当前页面保留/);
  a.storage.fail = false;
  a.edit('bit_rate', '');
  assert.match(a.status(), /待修正/);
  assert.match(a.status(), /草稿已保留/);
});
