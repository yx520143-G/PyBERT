/* Stable field-ID migration, independent of catalog order and labels. */
(() => {
  const settings=window.PYBERT_SETTINGS;
  function migrate(saved) {
    if (![1,2].includes(saved?.schema) || !saved.values || typeof saved.values!=='object' || Array.isArray(saved.values)) throw new Error('未知草稿schema；原存储保留，需恢复默认或重新载入配置。');
    const values=settings.clone(settings.defaults),retained={};
    for(const [key,row] of Object.entries(saved.retained_fields || {})) {
      const table=key.endsWith('.value') ? key.slice(0,-6) : '';
      const computed=['tx_tap_tuners','ffe_tap_tuners','dfe_tap_tuners'].includes(table) && Array.isArray(row?.value) && row.value.length===values[table].length && row.value.every(value=>value===null || typeof value==='number' && Number.isFinite(value));
      retained[key]={...(row && typeof row==='object' && !Array.isArray(row) ? row : {value:row,reason:'未知保留字段结构'}),blocking:!computed};
    }
    const savedValues={...saved.values};
    if(Number.isFinite(retained.peak_mag_tune?.value)) {savedValues.peak_mag_tune=retained.peak_mag_tune.value;delete retained.peak_mag_tune;}
    for(const [key,value] of Object.entries(savedValues)) {
      if (!Object.hasOwn(values,key)) {retained[key]={value,reason:'当前版本未支持的稳定field ID'};continue;}
      let valid;
      if (settings.tableInfo[key]) {
        valid=Array.isArray(value) && value.length===values[key].length && value.every((row,i)=>row && settings.tableInfo[key].columns.every(column=>column==='value' && key.endsWith('_tap_tuners') ? row[column]===undefined || typeof row[column]==='number' && Number.isFinite(row[column]) : typeof row[column]===typeof values[key][i][column] || (column!=='enabled' && row[column]==='')));
        if(valid && key.endsWith('_tap_tuners') && value.some(row=>row.value!==undefined)) retained[`${key}.value`]={value:value.map(row=>row.value ?? null),reason:'优化value保留；当前Native Run不消费，#8专项处理。',blocking:false};
      }
      else if(settings.fields[key]?.kind==='files') valid=Array.isArray(value) && value.every(item=>typeof item==='string');
      else valid=typeof value===typeof values[key] || (settings.fields[key]?.kind==='number' && value==='');
      if(key==='peak_mag_tune' && typeof value==='number' && Number.isFinite(value)) valid=true;
      if (valid && ['select','radio'].includes(settings.fields[key]?.kind)) {const options=settings.optionsFor(key,{...values,[key]:value});if(options && !options.includes(value)) valid=false;}
      if (valid) values[key]=settings.clone(value);else retained[key]={value,reason:'类型/表结构/枚举不匹配；未以默认值冒充执行'};
    }
    return {values,retained,source_schema:saved.schema,source_sha:saved.sources || {prototype_sha:saved.commit || 'unknown'}};
  }
  window.PYBERT_DRAFT={migrate};
})();
