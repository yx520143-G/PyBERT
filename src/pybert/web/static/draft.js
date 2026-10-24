/* Stable field-ID migration, independent of catalog order and labels. */
(() => {
  const settings=window.PYBERT_SETTINGS;
  function migrate(saved) {
    if (![1,2].includes(saved?.schema) || !saved.values || typeof saved.values!=='object' || Array.isArray(saved.values)) throw new Error('未知草稿schema；原存储保留，需恢复默认或重新载入配置。');
    const values=settings.clone(settings.defaults),retained={...(saved.retained_fields || {})};
    for(const [key,value] of Object.entries(saved.values)) {
      if (!Object.hasOwn(values,key)) {retained[key]={value,reason:'当前版本未支持的稳定field ID'};continue;}
      let valid;
      if (settings.tableInfo[key]) valid=Array.isArray(value) && value.length===values[key].length && value.every((row,i)=>row && settings.tableInfo[key].columns.every(column=>typeof row[column]===typeof values[key][i][column] || (column!=='enabled' && row[column]==='')));
      else if(settings.fields[key]?.kind==='files') valid=Array.isArray(value) && value.every(item=>typeof item==='string');
      else valid=typeof value===typeof values[key] || (settings.fields[key]?.kind==='number' && value==='');
      if (valid && ['select','radio'].includes(settings.fields[key]?.kind)) {const options=settings.optionsFor(key,{...values,[key]:value});if(options && !options.includes(value)) valid=false;}
      if (valid) values[key]=settings.clone(value);else retained[key]={value,reason:'类型/表结构/枚举不匹配；未以默认值冒充执行'};
    }
    return {values,retained,source_schema:saved.schema,source_sha:saved.sources || {prototype_sha:saved.commit || 'unknown'}};
  }
  window.PYBERT_DRAFT={migrate};
})();
