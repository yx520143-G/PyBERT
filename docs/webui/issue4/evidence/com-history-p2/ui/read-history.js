async page => {
  const success='e6e6867a-a976-4e47-a7bd-ee53767a2f9e', failed='c922f333-2a39-4fe3-abd0-5793c9bba535';
  const completed=[];
  const responses=response=>{if(response.url().includes('/api/com/'))completed.push(response.url().split('/').at(-1));};
  page.on('response',responses);
  const delayed=async route=>{await new Promise(resolve=>setTimeout(resolve,800));await route.continue();};
  await page.route('**/api/com/'+success,delayed);
  try {
    await page.getByText(/^e6e6867a.*succeeded/).click();
    await page.getByText(/^c922f333.*failed/).click();
    await page.locator(`[data-com-task="${failed}"] [data-com-source-status]`).waitFor({state:'visible'});
    await page.locator(`[data-com-task="${success}"] [data-com-identity]`).filter({hasText:success}).waitFor({state:'visible'});
    const read=async id=>{
      const row=page.locator(`[data-com-task="${id}"]`);
      return {id,open:await row.getAttribute('open'),status:await row.locator('[data-com-source-status]').textContent(),identity:JSON.parse(await row.locator('[data-com-identity]').textContent()),parameters:JSON.parse(await row.locator('[data-com-parameters]').textContent()),logs:await row.locator('[data-com-logs]').textContent(),error:await row.locator('[data-com-error]').count()?await row.locator('[data-com-error]').textContent():null};
    };
    const values=[await read(success),await read(failed)];
    if(completed.indexOf(failed)<0 || completed.indexOf(failed)>completed.indexOf(success))throw Error('Out-of-order GET completion not observed');
    const stable=await page.locator(`[data-com-task="${success}"]`).evaluate(async row=>{
      const identity=row.querySelector('[data-com-identity]'),logs=row.querySelector('[data-com-logs]');
      identity.scrollTop=40;
      await new Promise(resolve=>setTimeout(resolve,1700));
      return {open:row.open,same_row:row.isConnected,same_identity:identity===row.querySelector('[data-com-identity]'),same_logs:logs===row.querySelector('[data-com-logs]'),identity_scroll_top:identity.scrollTop};
    });
    if(!stable.open || !stable.same_row || !stable.same_identity || !stable.same_logs || stable.identity_scroll_top!==40)throw Error('Open COM history or its contents reset during poll');
    return {completed,values,stable};
  } finally {await page.unroute('**/api/com/'+success,delayed);page.off('response',responses);}
}
