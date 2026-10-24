async page => {
  const read=async id=>{
    const row=page.locator(`[data-com-task="${id}"]`);
    await row.locator('[data-com-source-status]').waitFor({state:'visible'});
    return {id,status:await row.locator('[data-com-source-status]').textContent(),identity:JSON.parse(await row.locator('[data-com-identity]').textContent()),parameters:JSON.parse(await row.locator('[data-com-parameters]').textContent()),logs:await row.locator('[data-com-logs]').textContent(),summary:await row.locator('summary').textContent()};
  };
  const cancelled=[await read('b6b85201-e481-4c69-98ce-c66650043535'),await read('a4dbc128-d042-43fd-b4a8-ede21c019527')];
  const id='a803f4ca-83f2-4031-a31c-af5213fc71d8';let gets=0;
  const injected=async route=>{gets++;if(gets===1)await route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Injected read failure; saved artifacts unchanged'})});else await route.continue();};
  await page.route('**/api/com/'+id,injected);
  try {
    await page.getByText(/^a803f4ca.*succeeded/).click();
    const row=page.locator(`[data-com-task="${id}"]`);
    await row.getByRole('button',{name:'重试读取',exact:true}).waitFor({state:'visible'});
    const missing={message:await row.textContent(),identity_count:await row.locator('[data-com-identity]').count()};
    if(missing.identity_count!==0 || !missing.message.includes('来源记录读取失败'))throw Error('Read failure misrepresented as saved metadata');
    await row.getByRole('button',{name:'重试读取',exact:true}).click();
    await row.locator('[data-com-identity]').filter({hasText:id}).waitFor({state:'visible'});
    const recovered=await read(id);
    if(gets!==2)throw Error('Unexpected duplicate/repeated metadata reads');
    return {cancelled,injected_failure:missing,recovered,GET_count:gets};
  } finally {await page.unroute('**/api/com/'+id,injected);}
}
