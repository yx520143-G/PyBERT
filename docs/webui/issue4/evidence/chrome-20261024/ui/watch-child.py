import json
import time
from pathlib import Path
from urllib.request import urlopen

def get(path):
    with urlopen('http://127.0.0.1:8767/api/'+path) as r:
        return r.read()

out=Path('docs/webui/issue4/evidence/chrome-20261024')
target=out/'run-child-transitions.json'
assert not target.exists()
deadline=time.monotonic()+180
core=None
before=None
events=[]
last=None
while time.monotonic()<deadline:
    state=json.loads(get('state'))
    current=json.loads(get('tasks/'+state['current_task_id']))
    if current['operation']=='run' and current['request_hash']=='769673a42a84604e38b41f1079ee7cff93d342ea65b8a91e0196c1cc103c8b2b':
        core=current['task_id']
    children=[t for t in state['com_tasks'] if t['parent_run_id']==core] if core else []
    signature=(state['active_task_id'],current['task_id'],current['state'],current['phase'])
    if signature!=last:
        events.append({'at':time.time(),'active':state['active_task_id'],'task':current})
        last=signature
    if core and any(r['run_id']==core for r in state['runs']) and before is None:
        before=get('runs/'+core)
        (out/'core-before-child-finished.json').write_bytes(before)
    if children and children[-1]['worker_exited']:
        child=children[-1]
        parent=json.loads(get('tasks/'+core))
        after=get('runs/'+core)
        (out/'core-after-child-finished.json').write_bytes(after)
        assert before==after
        assert parent['worker_exited'] and parent['state']=='succeeded'
        assert child['created_at']>=parent['worker_exit_confirmed_at']
        assert child['state']=='succeeded' and child['exitcode']==0
        assert json.loads(after)['input_identity_hash']=='d0867f7ff100b12525d0960e0b0e7575ea5adf2f3ea8a1226ea7a1e2d3a642d7'
        target.write_text(json.dumps({'events':events,'parent':parent,'child':child,'immutable_core':True},indent=2),encoding='utf-8')
        print(json.dumps({'core':core,'child':child['task_id'],'immutable_core':True,'events':len(events)}))
        break
    time.sleep(.1)
else:
    target.write_text(json.dumps({'events':events,'incomplete':True},indent=2),encoding='utf-8')
    raise TimeoutError('No completed frozen core/child pair')
