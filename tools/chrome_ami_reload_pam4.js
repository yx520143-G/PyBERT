async (page) => {
  await page.getByRole('button',{name:'关闭',exact:true}).click();
  await page.getByRole('button',{name:'Load Config',exact:true}).click();
}
