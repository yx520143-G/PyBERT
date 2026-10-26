/* Presentation only: disclosures and chart sizing never submit a numerical task. */
(() => {
  const receiverKinds = ['adaptation','cdr','cdr.histogram','cdr.spectrum'];
  const pointKinds = ['paired','response','wave','eye','jitter.dist','jitter.spec','jitter.bathtub',...receiverKinds];
  const pointSelect = document.getElementById('analysis-point');
  const kindSelect = document.getElementById('analysis-kind');
  const compareSelect = document.getElementById('compare-mode');
  const viewGroups = [...kindSelect.children].map(group => ({group,options:[...group.children]}));
  function syncObservation(event) {
    const atDfe = pointSelect.value === 'dfe';
    let kind = event?.detail?.kind || kindSelect.value || 'paired';
    if (!atDfe && receiverKinds.includes(kind)) kind = 'paired';
    const atPoint = pointKinds.includes(kind);
    for (const {group,options} of viewGroups) {
      const visible = options.filter(option => atPoint
        ? pointKinds.includes(option.value) && (atDfe || !receiverKinds.includes(option.value))
        : option.value === kind);
      if (visible.length) { group.replaceChildren(...visible); kindSelect.append(group); }
      else group.remove();
    }
    kindSelect.value = kind;
    kindSelect.closest('label').hidden = !atPoint;
    const comparePoints = atPoint && kind !== 'paired' && !receiverKinds.includes(kind);
    if (!comparePoints && compareSelect.value === 'points') compareSelect.value = 'none';
    const allPoints = atPoint && compareSelect.value === 'points';
    const option = pointSelect.selectedOptions[0];
    const title = document.getElementById('observation-title');
    title.textContent = allPoints ? '信号对比' : atPoint ? option.textContent : kindSelect.selectedOptions[0].textContent;
    title.hidden = atPoint && !allPoints;
    pointSelect.hidden = !atPoint || allPoints;
    document.getElementById('reference-note').hidden = !atPoint || allPoints || pointSelect.value !== 'chnl';
    pointSelect.disabled = !atPoint || allPoints;
    document.getElementById('comparison-run').closest('label').hidden = compareSelect.value !== 'runs';
    compareSelect.closest('label').hidden = kind === 'compare';
    compareSelect.querySelector('[value="none"]').textContent = atPoint ? '单信号' : '所选 Run';
    compareSelect.querySelector('[value="points"]').disabled = !comparePoints;
    document.querySelectorAll('[data-observation]').forEach(marker => {
      const selected = atPoint && (allPoints ? ['tx','ctle','dfe'].includes(marker.dataset.observation) : marker.dataset.observation === pointSelect.value);
      marker.classList.toggle('selected', selected);
      marker.setAttribute('aria-pressed', String(selected));
    });
    const observedStage = kind === 'wave.source' ? 'source' : kind === 'wave.noise' ? 'noise' : atPoint && !allPoints && pointSelect.value === 'chnl' ? 'channel' : null;
    document.querySelectorAll('#chain-map [data-stage]').forEach(node => node.classList.toggle('observing',node.dataset.stage === observedStage));
  }
  for (const select of [pointSelect,kindSelect,compareSelect]) select.addEventListener('change', syncObservation);
  window.addEventListener('pybert-chain-rendered', syncObservation);
  window.addEventListener('pybert-analysis-view', syncObservation);
  syncObservation();
  const menus = [...document.querySelectorAll('.action-menu')];
  document.getElementById('close-optimizer').addEventListener('click', () => {
    document.getElementById('optimizer-workspace').open = false;
    document.getElementById('optimizer-open').focus();
  });
  for (const menu of menus) menu.addEventListener('toggle', () => {
    if (menu.open) for (const other of menus) if (other !== menu) other.open = false;
  });
  document.addEventListener('click', event => {
    const marker = event.target.closest('[data-observation]');
    if (marker) {
      window.dispatchEvent(new CustomEvent('pybert-analysis-navigation',{detail:{
        point:marker.dataset.observation,
        kind:pointKinds.includes(kindSelect.value) ? kindSelect.value : 'paired',
        compare:compareSelect.value === 'points' ? 'none' : compareSelect.value
      }}));
    }
    const analysisButton = event.target.closest('[data-analysis-kind]');
    if (analysisButton) window.dispatchEvent(new CustomEvent('pybert-analysis-navigation',{detail:{kind:analysisButton.dataset.analysisKind,compare:analysisButton.dataset.analysisKind === 'compare' ? 'runs' : 'none'}}));
    for (const menu of menus) {
      if (!menu.contains(event.target) || event.target.closest('button')) menu.open = false;
    }
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape' || document.querySelector('dialog[open]')) return;
    for (const menu of menus) menu.open = false;
    document.getElementById('logs').open = false;
    document.getElementById('input-notes').open = false;
    document.getElementById('optimizer-workspace').open = false;
  });
  let frame;
  const observer = new ResizeObserver(() => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => {
      for (const id of ['plot', 'eye-plot']) {
        const plot = document.getElementById(id);
        if (plot?.data && plot.clientWidth && plot.clientHeight) Plotly.Plots.resize(plot);
      }
    });
  });
  for (const id of ['plot', 'eye-plot']) observer.observe(document.getElementById(id));
})();
