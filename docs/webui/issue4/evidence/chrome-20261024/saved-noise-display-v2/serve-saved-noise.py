"""Read-only review of already computed data; all calculation submissions are rejected."""
import copy
import json
from pathlib import Path
import uvicorn
from pybert.web.config import normalize
from pybert.web.data import plot_payload
from pybert.web.server import create_app
from pybert.web.tasks import BusyError

root=Path.cwd()
paths=[root/'docs/webui/issue4/evidence/chrome-20261024/c3cadfdc-13e8-4ed9-bee3-b3b11462cd96',root/'docs/webui/issue4/evidence/saved-resource-check-20261024-090903/F4-L0-ON/worker']
class SavedReview:
    def __init__(self):
        self.rows={json.loads((p/'manifest.json').read_text())['run_id']:p for p in paths}
        self.defaults=normalize({'mode':'defaults'}) # constructor only, no main simulation
    def normalize(self,request):
        if request!={'mode':'defaults'}:raise BusyError('Read-only saved review; no computation')
        return copy.deepcopy(self.defaults)
    def index(self):
        rows=[json.loads((p/'manifest.json').read_text()) for p in self.rows.values()]
        return {'active_task_id':None,'current_task_id':None,'runs':[{k:r[k] for k in ('run_id','input_hash','effective_input','summary','resource_hash')} for r in rows],'com_tasks':[],'resources':[]}
    def directory(self,run_id):return self.rows[run_id]
    def start(self,*a,**k):raise BusyError('Read-only saved review; no computation')

if __name__=='__main__':
    manager=SavedReview()
    checks=[]
    for run_id,p in manager.rows.items():
        manifest=json.loads((p/'manifest.json').read_text())
        payload=plot_payload(p,'noise')
        disabled=manifest['interference']['availability']=='disabled'
        assert ('FEXT disabled' in payload['title'])==disabled
        assert payload['metadata']['interference']==manifest['interference']
        assert len(payload['data'])==2+manifest['interference']['fext_count']
        checks.append({'run_id':run_id,'source_manifest':str(p/'manifest.json'),'title':payload['title'],'availability':payload['metadata']['interference']['availability'],'traces':len(payload['data'])})
    (root/'output/playwright/67-saved-noise-checks.json').write_text(json.dumps({'main_simulation':False,'COM':False,'checks':checks},indent=2),encoding='utf-8')
    uvicorn.run(create_app(manager),host='127.0.0.1',port=8768,access_log=False)
