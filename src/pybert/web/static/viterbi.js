/* Immutable Native trellis views. Position/Error/drag never submit a Run. */
(() => {
  const $=id=>document.getElementById(id), positions=new Map();
  const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let current=null;
  function position(value) {
    if (!current) return;
    const state=positions.get(current);
    state.position=Math.max(0,Math.min(Number($('trellis-position').max),Math.round(Number(value)||0)));
    state.error=0;
    window.dispatchEvent(new CustomEvent('pybert-trellis-view'));
  }
  $('trellis-position').addEventListener('change',event=>position(event.target.value));
  $('trellis-pan').addEventListener('input',event=>position(event.target.value));
  $('trellis-error').addEventListener('change',event=>{
    if (!current) return;
    positions.get(current).error=Math.max(0,Math.min(Number(event.target.max),Math.round(Number(event.target.value)||0)));
    window.dispatchEvent(new CustomEvent('pybert-trellis-view'));
  });
  function berText(ber) {
    const reason=row=>row.reason==='insufficient_frozen_ber_decisions' ? 'Too few actual decisions for this BER window.' : row.reason;
    return ['dfe','viterbi'].map(name=>`${name.toUpperCase()}: ${ber?.[name]?.availability==='available' ? `${ber[name].count} bit errors` : ber?.[name]?.availability==='disabled' ? '未启用（−1，未计算）' : ber?.[name]?.availability==='unavailable' ? `Unavailable: ${reason(ber[name])}` : '该记录未采集'}`).join(' · ');
  }
  async function render(run,other,isCurrent) {
    const id=run.record_id||run.run_id;
    current=id;
    if (!positions.has(id)) positions.set(id,{position:0,error:0});
    const state=positions.get(id), api=window.PYBERT_RUNS.api;
    const records=other?[run,other]:[run];
    const charts=await Promise.all(records.map((record,index)=>api(`runs/${record.record_id||record.run_id}/trellis?position=${state.position}&error=${index?0:state.error}`)));
    if (!isCurrent()) return;
    const first=charts[0],available=first.availability==='available';
    for(const key of ['trellis-position','trellis-pan','trellis-error']) $(key).disabled=!available;
    $('trellis-status').textContent=available ? `${first.position}–${first.stop_exclusive-1} / ${first.symbol_count} symbols · ${berText(first.ber)}` : `${first.reason} · ${berText(first.ber||run.decoding?.ber)} · DFE ${run.summary.n_errs_dfe ?? '该记录未采集'}`;
    if (available) {
      state.position=first.position;
      $('trellis-position').max=$('trellis-pan').max=first.max_position;
      $('trellis-position').value=$('trellis-pan').value=first.position;
      $('trellis-error').max=first.error_count;$('trellis-error').value=first.error;
      $('trellis-of').textContent=`of ${first.error_count} bit-error entries`;
    } else {
      $('trellis-position').value=$('trellis-pan').value=$('trellis-error').value=0;
      $('trellis-of').textContent='of 0（无可用错误清单）';
    }
    Plotly.purge('plot');$('plot').innerHTML='';
    const panes=charts.map((chart,index)=>{
      const pane=document.createElement('div');pane.id=`trellis-chart-${index}`;pane.style.height='330px';$('plot').append(pane);
      if(chart.availability!=='available') {pane.innerHTML=`<p>${escape(records[index].run_id)} · ${escape(chart.reason)}</p>`;return null;}
      return Plotly.newPlot(pane,chart.data,{title:{text:`${records[index].run_id.slice(0,8)} · Native trellis · ${berText(chart.ber)}`,font:{size:12}},
        xaxis:{title:{text:'symbol index · this decoder window'},range:[chart.position-.3,chart.stop_exclusive-.7],dtick:1},
        yaxis:{title:{text:'state index'},range:[-.6,chart.state_count-.5],dtick:Math.max(1,Math.ceil(chart.state_count/16))},
        margin:{l:55,r:65,t:40,b:75},legend:{orientation:'h',y:-.28,font:{size:9}},paper_bgcolor:'#fff',plot_bgcolor:'#f7f9fc'},
        {responsive:true,displaylogo:false});
    });
    $('plot').style.height=`${charts.length*330}px`;
    await Promise.all(panes);
    if (!isCurrent()) return;
    $('analysis-info').innerHTML=`<p>原 producer 的连线、路径和前三状态。raw probability 无量纲，不能解释为 BER；颜色为 log10(raw)，仅显示裁剪到 −20。Position/拖动/Error/比较/存档均读取原数组，不 Run。PAM4 两个 bit 错误落在同一 symbol 时保留两条。</p>${charts.map((chart,index)=>`<details><summary>${escape(records[index].run_id)} · ${berText(chart.ber||records[index].decoding?.ber)}${chart.selected_error?` · Error ${chart.selected_error.entry}: bit ${chart.selected_error.bit_index} → symbol ${chart.selected_error.symbol_index}`:''}</summary><pre>${escape(JSON.stringify({ber:chart.ber,selected_error:chart.selected_error,display:chart.display},null,2))}</pre>${chart.top3?`<table><tr><th>symbol</th><th>rank/state</th><th>raw probability</th><th>display log10 (floor −20)</th></tr>${chart.top3.flatMap(row=>row.symbol_indices.map((symbol,j)=>`<tr><td>${symbol}</td><td>${row.rank} / ${row.state_indices[j]}</td><td>${row.raw_probabilities[j]}</td><td>${row.display_log10[j]}</td></tr>`)).join('')}</table>`:''}</details>`).join('')}`;
    $('analysis-info').insertAdjacentHTML('afterbegin',charts.map((chart,index)=>chart.metadata_warning?`<p>${escape(records[index].run_id)} · ${escape(chart.metadata_warning)}</p>`:'').join(''));
  }
  window.PYBERT_VITERBI={render};
})();
