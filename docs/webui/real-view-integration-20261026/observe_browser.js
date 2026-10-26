// Install once through playwright-cli run-code --filename, before clicking Run.
// This only observes Playwright events; it does not replace browser fetch or data.
async page => {
  if (page._realAudit) throw new Error('Observer is already installed.');
  page._realAudit = {runs:[], plots:{}, errors:[]};
  page.on('request', request => {
    if (request.method() === 'POST' && request.url().endsWith('/api/runs')) {
      page._realAudit.runs.push({url:request.url(), body:request.postDataJSON()});
    }
  });
  page.on('response', async response => {
    try {
      if (response.request().method() === 'POST' && response.url().endsWith('/api/runs')) {
        page._realAudit.runs.at(-1).response = await response.json();
      }
      if (/\/api\/runs\/[^/]+\/plots\//.test(response.url())) {
        page._realAudit.plots[response.url()] = await response.json();
      }
    } catch (error) { page._realAudit.errors.push(String(error)); }
  });
  return {installed:true};
}
