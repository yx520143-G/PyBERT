// Run through playwright-cli run-code --filename after a real UI view change.
async page => {
  const audit = page._realAudit;
  if (!audit) throw new Error('Install the passive network observer before Run.');
  const view = await page.evaluate(() => {
    const el = id => document.getElementById(id);
    const run = window.PYBERT_RUNS.selected();
    return {
      record_id: run?.record_id || run?.run_id, run_id: run?.run_id,
      input_hash: run?.input_hash, input_identity_hash: run?.input_identity_hash,
      kind: el('analysis-kind').value, point: el('analysis-point').value,
      compare: el('compare-mode').value, stale: el('stale').textContent,
      info: el('analysis-info').textContent,
      targets: (el('analysis-kind').value === 'paired' ? ['plot', 'eye-plot'] : ['plot']).map(id => ({
        id, data: (el(id).data || []).map(trace => Object.fromEntries(
          ['x', 'y', 'z', 'type'].filter(key => key in trace).map(key => [key, trace[key]]))),
        xunit: el(id).layout?.xaxis?.title?.text, yunit: el(id).layout?.yaxis?.title?.text,
        empty: el(id).querySelector('.empty-result')?.textContent,
      })),
    };
  });
  const numeric = trace => Object.fromEntries(['x', 'y', 'z', 'type'].filter(key => key in trace).map(key => [key, trace[key]]));
  const report = {...view, targets: []};
  for (const target of view.targets) {
    if (target.empty) throw new Error(`${target.id}: ${target.empty}`);
    const matches = target.data.map(trace => Object.entries(audit.plots).flatMap(([url, chart]) =>
      chart.data?.some(candidate => JSON.stringify(numeric(candidate)) === JSON.stringify(trace)) ? [{url, chart}] : []));
    if (!target.data.length || matches.some(rows => !rows.length)) throw new Error('Displayed samples differ from actual HTTP plot responses.');
    const ids = matches.map(rows => {
      const matching = rows.find(({url}) => url.includes(`/runs/${view.record_id}/`));
      if (!matching && view.compare !== 'runs') throw new Error('Displayed trace belongs to another record.');
      const {url, chart} = matching || rows[0];
      if (target.xunit !== chart.xunit || target.yunit !== chart.yunit) throw new Error('Axis units differ.');
      return {url, plot_id: chart.plot_id, source_run_id: chart.run_id, metadata: chart.metadata};
    });
    if (view.kind === 'paired') {
      const expected = target.id === 'eye-plot' ? `eye.${view.point}` : `${view.point === 'chnl' ? 'chnl' : view.point + '_out'}_h`;
      if (!ids.every(row => row.url.endsWith(`/plots/${expected}`))) throw new Error(`Wrong paired plot: ${expected}`);
    }
    const sha256 = await page.evaluate(async data => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(data))))).map(x => x.toString(16).padStart(2, '0')).join(''), target.data);
    report.targets.push({id: target.id, xunit: target.xunit, yunit: target.yunit,
      traces: target.data.length, exact_http_coordinates: true, sha256, sources: ids});
  }
  audit.checks ||= [];
  audit.checks.push(report);
  return {checked: audit.checks.length, record_id: view.record_id, kind: view.kind, point: view.point, compare: view.compare,
    targets: report.targets.map(({id, traces, xunit, yunit, sha256}) => ({id, traces, xunit, yunit, sha256})), evidence:report};
}
