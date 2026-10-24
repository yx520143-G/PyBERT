async (page) => {
  const legacy=__LEGACY_JSON__;
  const original=JSON.stringify(legacy),base='http://127.0.0.1:8770';
  await page.evaluate(original=>{for(const key of ['pybert-native-draft-v2','pybert-native-draft-v1','pybert-native-snapshot-v2','pybert-native-snapshot-v1','pybert-result-selection-v1'])localStorage.removeItem(key);localStorage.setItem('pybert-chain-draft-v1',original);},original);
  await page.reload();await page.waitForFunction(()=>JSON.parse(localStorage.getItem('pybert-native-draft-v2') || 'null')?.sources?.adapter_sha);
  const migrated=await page.evaluate(()=>({saved:JSON.parse(localStorage.getItem('pybert-native-draft-v2')),legacy:localStorage.getItem('pybert-chain-draft-v1'),error:window.PYBERT_WORKBENCH.migrationError()}));
  if(migrated.legacy!==original || migrated.saved.schema!==2 || migrated.saved.values.bit_rate!==25 || migrated.saved.values.vod!==1.25)throw new Error('PR7 migration/key preservation failed');
  const coverage=Object.entries(legacy.values).map(([key,value])=>({key,exact:JSON.stringify(migrated.saved.values[key])===JSON.stringify(value),retained:JSON.stringify(migrated.saved.retained_fields[key]?.value)===JSON.stringify(value)}));
  if(coverage.some(row=>!row.exact && !row.retained))throw new Error(JSON.stringify(coverage.filter(row=>!row.exact && !row.retained)));
  for(const key of ['adapter_sha','native_sha','prototype_sha'])if(!/^[a-f0-9]{40}$/.test(migrated.saved.sources[key]))throw new Error('Incomplete new source SHA');
  await page.screenshot({path:'output/playwright/20-full-pr7-migration.png'});
  const refused=[];
  for(const raw of ['invalid JSON',JSON.stringify({schema:999,values:{bit_rate:50}}),JSON.stringify({schema:2,values:{bit_rate:25},retained_fields:{future_physical_input:{value:123,blocking:false}}})]) {
    await page.evaluate(raw=>localStorage.setItem('pybert-native-draft-v2',raw),raw);await page.reload();
    await page.waitForFunction(()=>window.PYBERT_WORKBENCH?.migrationError());
    const value=await page.evaluate(()=>({raw:localStorage.getItem('pybert-native-draft-v2'),error:window.PYBERT_WORKBENCH.migrationError()}));
    if(raw.startsWith('invalid') || JSON.parse(raw).schema===999) {if(value.raw!==raw)throw new Error('Rejected storage overwritten');}
    else if(!value.error)throw new Error('Unknown retained flag bypass');
    refused.push(value);
  }
  await page.screenshot({path:'output/playwright/21-unknown-retained-blocked.png'});
  await page.evaluate(()=>{localStorage.removeItem('pybert-native-draft-v2');localStorage.removeItem('pybert-chain-draft-v1');});await page.reload();
  await page.waitForFunction(()=>window.PYBERT_WORKBENCH && !window.PYBERT_WORKBENCH.migrationError() && !document.querySelector('#run').disabled);
  await page.evaluate(()=>{window.originalStorageSet=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw new DOMException('evidence injected unavailable storage','QuotaExceededError');};});
  await page.locator('#control-bit_rate').fill('26');await page.locator('#control-bit_rate').blur();
  await page.waitForFunction(()=>document.querySelector('#draft-status').textContent.includes('仅当前页面保留'));
  if(await page.evaluate(()=>window.PYBERT_WORKBENCH.getDraft().bit_rate)!==26)throw new Error('Storage failure lost input');
  await page.screenshot({path:'output/playwright/22-storage-failure-input-retained.png'});
  await page.evaluate(()=>{Storage.prototype.setItem=window.originalStorageSet;});
  await page.locator('#control-bit_rate').fill('27');await page.locator('#control-bit_rate').blur();
  await page.waitForFunction(()=>JSON.parse(localStorage.getItem('pybert-native-draft-v2')).values.bit_rate===27 && document.querySelector('#draft-status').textContent.includes('草稿已保留'));
  const final=await (await page.request.get(base+'/api/state')).json();if(final.runs.length || final.com_tasks.length)throw new Error('Migration started main/COM');
  return {authentic_pr7_field_count:coverage.length,coverage,migration:migrated,refused,storage_failure_kept_input:26,recovery_saved_input:27,main_calls:0,COM_calls:0};
}
